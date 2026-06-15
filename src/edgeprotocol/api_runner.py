"""API mode: automated model baseline via official provider APIs only.

This is the *model baseline* dataset (model_baseline_api). It is never
merged with the field dataset (hard constraint 2). No system prompt of
our own; provider defaults; everything sent is logged exactly.
"""
from __future__ import annotations

import os
import time
from typing import Any, Callable

from . import scoring, store
from .bank import get_question, question_ids

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

MAX_RETRIES = 3
BACKOFF_SECONDS = 5

# Rough per-run token estimate for the cost guard: 4 short user turns plus
# 4 product responses of a few hundred tokens each.
EST_TOKENS_PER_RUN = 2500


class ProviderUnavailable(RuntimeError):
    pass


# --- Provider adapters --------------------------------------------------------
# Each adapter takes (model, messages) where messages is a list of
# {"role": "user"|"assistant", "content": str}, and returns the assistant text.
# SDK imports are lazy so a missing package only disables that provider.

def _call_anthropic(model: str, messages: list[dict[str, str]]) -> str:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise ProviderUnavailable("ANTHROPIC_API_KEY not set")
    try:
        import anthropic
    except ImportError as exc:
        raise ProviderUnavailable("anthropic SDK not installed") from exc
    client = anthropic.Anthropic()
    response = client.messages.create(model=model, max_tokens=1024, messages=messages)
    return "".join(block.text for block in response.content if getattr(block, "type", "") == "text")


def _call_openai(model: str, messages: list[dict[str, str]]) -> str:
    if not os.environ.get("OPENAI_API_KEY"):
        raise ProviderUnavailable("OPENAI_API_KEY not set")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ProviderUnavailable("openai SDK not installed") from exc
    client = OpenAI()
    response = client.chat.completions.create(model=model, messages=messages)
    return response.choices[0].message.content or ""


def _call_google(model: str, messages: list[dict[str, str]]) -> str:
    if not os.environ.get("GOOGLE_API_KEY"):
        raise ProviderUnavailable("GOOGLE_API_KEY not set")
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError as exc:
        raise ProviderUnavailable("google-genai SDK not installed") from exc
    client = genai.Client()
    contents = [
        genai_types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[genai_types.Part(text=m["content"])],
        )
        for m in messages
    ]
    response = client.models.generate_content(model=model, contents=contents)
    return response.text or ""


def _call_xai(model: str, messages: list[dict[str, str]]) -> str:
    if not os.environ.get("XAI_API_KEY"):
        raise ProviderUnavailable("XAI_API_KEY not set")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ProviderUnavailable("openai SDK not installed (xAI uses OpenAI-compatible API)") from exc
    client = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")
    response = client.chat.completions.create(model=model, messages=messages)
    return response.choices[0].message.content or ""


def _call_deepseek(model: str, messages: list[dict[str, str]]) -> str:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise ProviderUnavailable("DEEPSEEK_API_KEY not set")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ProviderUnavailable("openai SDK not installed (DeepSeek uses OpenAI-compatible API)") from exc
    client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")
    response = client.chat.completions.create(model=model, messages=messages)
    return response.choices[0].message.content or ""


PROVIDERS: dict[str, Callable[[str, list[dict[str, str]]], str]] = {
    "anthropic": _call_anthropic,
    "openai": _call_openai,
    "google": _call_google,
    "xai": _call_xai,
    "deepseek": _call_deepseek,
}

DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "claude-haiku-4-5-20251001",
    "openai": "gpt-4o-mini",
    "google": "gemini-2.0-flash",
    "xai": "grok-3-mini",
    "deepseek": "deepseek-chat",
}


def _call_with_retry(provider: str, model: str, messages: list[dict[str, str]]) -> str:
    caller = PROVIDERS[provider]
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            return caller(model, messages)
        except ProviderUnavailable:
            raise
        except Exception as exc:  # rate limits, transient network errors
            last_error = exc
            time.sleep(BACKOFF_SECONDS * (attempt + 1))
    raise RuntimeError(f"Persistent API failure after {MAX_RETRIES} retries: {last_error}")


def run_api_session(
    bank: dict[str, Any], provider: str, model: str, question_id: str, run_n: int
) -> dict[str, Any] | None:
    """One automated run: L0 -> detection -> push layers -> hard stop after L3.

    Returns the run record, or None if the run aborted. Aborted runs are
    stored with status 'aborted' and never partially scored.
    """
    question_cfg = get_question(bank, question_id)
    push = bank["push_script"]

    messages: list[dict[str, str]] = []
    transcript: list[dict[str, str]] = []
    layer_responses: list[str] = []
    review_required = False
    hedge = ""
    status = "complete"

    for layer in range(4):
        if layer == 0:
            prompt_text = question_cfg["binary"]
        elif layer == 1:
            prompt_text = push["L1"].format(question=question_cfg["binary"])
        elif layer == 2:
            prompt_text = push["L2"]
        else:
            prompt_text = push["L3"].format(hedge=hedge)

        messages.append({"role": "user", "content": prompt_text})
        try:
            response = _call_with_retry(provider, model, messages)
        except ProviderUnavailable:
            raise
        except RuntimeError as exc:
            status = "aborted"
            transcript.append({"layer": f"L{layer}", "sent": prompt_text, "received": "", "error": str(exc)})
            break
        messages.append({"role": "assistant", "content": response})
        transcript.append({"layer": f"L{layer}", "sent": prompt_text, "received": response})
        layer_responses.append(response)

        arrival = scoring.detect_binary_arrival(response, question_cfg)
        if arrival.confidence == scoring.HIGH:
            break
        if arrival.confidence == scoring.MEDIUM:
            review_required = True  # continue the script, flag the run
        hedge = scoring.extract_hedge(response, question_cfg)

    run_record: dict[str, Any] = {
        "run_id": store.new_run_id(),
        "dataset": "model_baseline_api",
        "recorded_at": store.utc_now(),
        "provider": provider,
        "phase": "collection",
        "model_id": model,
        "temperature": "provider_default",
        "system_prompt_used": "",
        "question_id": question_id,
        "run_n": run_n,
        "status": status,
        "transcript": transcript,
    }

    if status == "aborted":
        store.write_run_json("api", run_record)  # raw transcript stored, never scored
        print(f"  ABORTED {provider}/{model} {question_id} r{run_n} (stored unscored)")
        return None

    suggestion = scoring.score_run(layer_responses, question_cfg)
    review_required = review_required or suggestion.review_required
    run_record["auto_scores"] = {
        "BAL_auto": suggestion.bal_auto,
        "BAL_confidence": suggestion.bal_confidence,
        "NMR_auto": suggestion.nmr_auto,
        "SA_safe_auto": suggestion.sa_safe,
        "SA_asked_auto": suggestion.sa_asked,
        "review_required": review_required,
        "arrival_trace": suggestion.arrival_trace,
    }
    # API mode has no interactive human in the loop at run time; final scores
    # start blank and are filled by a human review pass. Auto values recorded.
    run_record["final_scores"] = {
        "BAL_final": "", "NMR_final": "", "SA_safe": "", "SA_asked": "",
        "WP_YN": "", "BN_YN": "",
    }
    json_path = store.write_run_json("api", run_record)
    store.append_log_row("api", {
        "date": store.utc_now()[:10],
        "phase": "collection",
        "provider": provider,
        "model_id": model,
        "temperature": "provider_default",
        "system_prompt_used": "",
        "question_id": question_id,
        "run_n": run_n,
        "BAL_auto": suggestion.bal_auto,
        "BAL_final": "",
        "NMR_auto": suggestion.nmr_auto,
        "NMR_final": "",
        "SA_safe": suggestion.sa_safe,
        "SA_asked": suggestion.sa_asked,
        "WP_YN": "",
        "BN_YN": "",
        "transcript_file": json_path.name,
        "review_required": review_required,
        "notes": "",
    })
    flag = " [review_required]" if review_required else ""
    print(f"  {provider}/{model} {question_id} r{run_n}: BAL_auto={suggestion.bal_auto} NMR_auto={suggestion.nmr_auto}{flag}")
    return run_record


def existing_collection_run_numbers(provider: str, model: str, question_id: str) -> set[int]:
    """Existing collection run numbers for this provider/model/question.

    Setup/debug rows are deliberately ignored so early instrument checks do not
    block the clean collection sequence.
    """
    existing: set[int] = set()
    for row in store.read_log("api"):
        if (row.get("phase") or "collection").strip().lower() != "collection":
            continue
        if row.get("provider") != provider:
            continue
        if row.get("model_id") != model:
            continue
        if row.get("question_id", "").upper() != question_id.upper():
            continue
        try:
            existing.add(int(row.get("run_n", "")))
        except ValueError:
            continue
    return existing


def missing_collection_run_numbers(provider: str, model: str, question_id: str, target_runs: int) -> list[int]:
    existing = existing_collection_run_numbers(provider, model, question_id)
    return [run_n for run_n in range(1, target_runs + 1) if run_n not in existing]


def available_providers() -> list[str]:
    return [p for p in PROVIDERS if os.environ.get(f"{p.upper()}_API_KEY") or
            (p == "google" and os.environ.get("GOOGLE_API_KEY"))]


def run_grid(bank: dict[str, Any], runs: int = 3, assume_yes: bool = False) -> None:
    """Full grid across configured providers, with cost guard."""
    providers = available_providers()
    skipped = [p for p in PROVIDERS if p not in providers]
    for p in skipped:
        print(f"  WARNING: skipping {p} (no API key configured)")
    if not providers:
        print("No providers configured. Set keys in .env.")
        return

    qids = question_ids(bank)
    total_runs = len(providers) * len(qids) * runs
    est_tokens = total_runs * EST_TOKENS_PER_RUN
    print(f"\nGrid: {len(providers)} providers x {len(qids)} questions x {runs} runs = {total_runs} runs")
    print(f"Estimated tokens: ~{est_tokens:,} (rough; mostly small models)")
    if not assume_yes:
        if input("Proceed? [y/n]: ").strip().lower() not in ("y", "yes"):
            print("Cancelled.")
            return

    for provider in providers:
        model = DEFAULT_MODELS[provider]
        for qid in qids:
            for run_n in missing_collection_run_numbers(provider, model, qid, runs):
                try:
                    run_api_session(bank, provider, model, qid, run_n)
                except ProviderUnavailable as exc:
                    print(f"  skipping {provider}: {exc}")
                    break
