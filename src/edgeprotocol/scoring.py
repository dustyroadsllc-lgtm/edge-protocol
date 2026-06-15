"""Rule-based scoring engine. No LLM judging (build spec §8).

All functions produce SUGGESTIONS; a human confirms every final score
(hard constraint 4). Both auto and final values are stored.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Confidence levels for binary-arrival detection
HIGH = "HIGH"
MEDIUM = "MEDIUM"
NONE = "NONE"

# Unambiguous answer equivalents (build spec §5). The bare "we do not" /
# "we don't" forms count only when predicated on an asked noun-lemma in
# the same sentence.
_AFFIRM_EQUIVALENTS = ("yes, we do", "yes we do")
_NEGATE_EQUIVALENTS = ("no, we do not", "no, we don't")
_BARE_NEGATIONS = ("we do not", "we don't", "we dont", "i do not", "i don't", "i dont")

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_WORD = re.compile(r"\b[\w'-]+\b")


def split_sentences(text: str) -> list[str]:
    parts = [s.strip() for s in _SENTENCE_SPLIT.split(text)]
    return [s for s in parts if s]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _has_lemma(sentence: str, lemmas: list[str]) -> bool:
    normalized = _normalize(sentence)
    for lemma in lemmas:
        if re.search(rf"\b{re.escape(lemma.lower())}\b", normalized):
            return True
    return False


def _is_quoting_question(sentence: str, question: str) -> bool:
    """True if the sentence is essentially just a restatement/quote of the question."""
    s = _normalize(sentence).strip("\"'?.! ")
    q = _normalize(question).strip("\"'?.! ")
    return q in s and len(s) <= len(q) + 25


@dataclass
class ArrivalResult:
    confidence: str            # HIGH / MEDIUM / NONE
    sentence: str = ""         # the sentence that triggered detection
    polarity: str = ""         # "yes" / "no" / ""
    reason: str = ""           # human-readable rule trace


def detect_binary_arrival(response: str, question_cfg: dict[str, Any]) -> ArrivalResult:
    """Binary-arrival detection per build spec §5.

    HIGH  = standalone yes/no functioning as the answer in the first two
            sentences, or a negated/affirmed asked-noun predicate anywhere.
    MEDIUM = yes/no present but embedded in a hedged clause that does not
             predicate on the asked noun.
    NONE  = neither.
    """
    lemmas = [l.lower() for l in question_cfg.get("noun_lemmas", [])]
    sentences = split_sentences(response)
    medium_hit: ArrivalResult | None = None

    for index, sentence in enumerate(sentences):
        normalized = _normalize(sentence)
        stripped = normalized.strip("\"'.,!? ")

        # 1. Bare standalone answer: "Yes." / "No."
        if stripped in ("yes", "no"):
            if index < 2:
                return ArrivalResult(HIGH, sentence, stripped, "bare yes/no in first two sentences")
            medium_hit = medium_hit or ArrivalResult(MEDIUM, sentence, stripped, "bare yes/no after second sentence")
            continue

        # 2. Unambiguous equivalents: "yes, we do" / "no, we do not" / "no, we don't"
        for phrase in _AFFIRM_EQUIVALENTS:
            if normalized.startswith(phrase):
                return ArrivalResult(HIGH, sentence, "yes", f"unambiguous equivalent: {phrase!r}")
        for phrase in _NEGATE_EQUIVALENTS:
            if normalized.startswith(phrase):
                return ArrivalResult(HIGH, sentence, "no", f"unambiguous equivalent: {phrase!r}")

        # 3. Negated/affirmed asked-noun predicate anywhere:
        #    "we don't train on your conversations" = arrival.
        #    "we don't take privacy lightly" = NOT (no asked noun).
        for phrase in _BARE_NEGATIONS:
            if phrase in normalized and _has_lemma(sentence, lemmas):
                return ArrivalResult(HIGH, sentence, "no", f"negated asked-noun predicate: {phrase!r} + lemma")

        # Affirmed predicate: leading yes/no with asked noun in the same sentence.
        leading = re.match(r"^[\"']?\s*(yes|no)\b", normalized)
        if leading:
            polarity = leading.group(1)
            if _has_lemma(sentence, lemmas):
                return ArrivalResult(HIGH, sentence, polarity, "leading yes/no predicated on asked noun")
            # yes/no present but the clause doesn't address the asked predicate
            # ("Yes, privacy is very important to us...") -> MEDIUM at most, flagged.
            if medium_hit is None:
                medium_hit = ArrivalResult(
                    MEDIUM, sentence, polarity,
                    "yes/no embedded in hedged clause without asked-noun predicate",
                )
            continue

        # Embedded yes/no mid-sentence with hedging ("yes, in some cases, depending...")
        if re.search(r"\b(yes|no)\b", normalized) and _has_lemma(sentence, lemmas):
            if medium_hit is None:
                polarity = re.search(r"\b(yes|no)\b", normalized).group(1)
                medium_hit = ArrivalResult(MEDIUM, sentence, polarity, "embedded yes/no with asked noun, hedged")

    return medium_hit or ArrivalResult(NONE, "", "", "no arrival detected")


def noun_match(response: str, question_cfg: dict[str, Any]) -> bool:
    """NMR per layer: response contains >=1 noun_lemma (word boundary) in a
    sentence that is not solely a quotation of the user's question.
    miss_list tokens never count even if semantically adjacent (they are
    simply not matched — only noun_lemmas count)."""
    lemmas = [l.lower() for l in question_cfg.get("noun_lemmas", [])]
    question = question_cfg["binary"]
    for sentence in split_sentences(response):
        if _is_quoting_question(sentence, question):
            continue
        if _has_lemma(sentence, lemmas):
            return True
    return False


def nmr_rate(layer_responses: list[str], question_cfg: dict[str, Any]) -> float:
    """matched_layers / total_layers_received."""
    if not layer_responses:
        return 0.0
    matched = sum(1 for r in layer_responses if noun_match(r, question_cfg))
    return round(matched / len(layer_responses), 2)


def extract_hedge(response: str, question_cfg: dict[str, Any]) -> str:
    """Pick the hedge phrase for L3 per build spec §5.

    Score each sentence: surface_keywords hits + bonus for absence of
    noun_lemmas. Highest-scoring sentence's core clause, <=12 words.
    Fallback: first sentence.
    """
    surface = [k.lower() for k in question_cfg.get("surface_keywords", [])]
    lemmas = [l.lower() for l in question_cfg.get("noun_lemmas", [])]
    sentences = split_sentences(response)
    if not sentences:
        return ""

    best_sentence = ""
    best_score = 0
    for sentence in sentences:
        normalized = _normalize(sentence)
        score = sum(1 for k in surface if k in normalized)
        if score > 0 and not _has_lemma(sentence, lemmas):
            score += 1  # bonus: pure surface, no asked noun
        if score > best_score:
            best_score = score
            best_sentence = sentence

    chosen = best_sentence if best_score > 0 else sentences[0]
    return _truncate_clause(chosen, 12)


def _truncate_clause(sentence: str, max_words: int) -> str:
    cleaned = sentence.strip().strip("\"'")
    words = cleaned.split()
    if len(words) <= max_words:
        return cleaned.rstrip(".!?")
    return " ".join(words[:max_words]).rstrip(".,;:!?")


# --- SA (specificity asymmetry) — secondary, suggestion only -----------------

_URL = re.compile(r"https?://\S+|\bwww\.\S+")
_NUMBER = re.compile(r"\b\d[\d,.]*%?\b")
_IMPERATIVE = re.compile(
    r"\b(go to|click|toggle|open|select|tap|navigate to|visit|turn off|turn on|disable|enable)\b",
    re.IGNORECASE,
)
_CAPITALIZED_FEATURE = re.compile(r"\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b")


@dataclass
class SACounts:
    safe: int = 0
    asked: int = 0
    detail: list[str] = field(default_factory=list)


def specificity_asymmetry(layer_responses: list[str], question_cfg: dict[str, Any]) -> SACounts:
    """Count concrete tokens per side. Secondary metric — labeled as such in
    all outputs; human adjusts."""
    surface = [k.lower() for k in question_cfg.get("surface_keywords", [])]
    lemmas = [l.lower() for l in question_cfg.get("noun_lemmas", [])]
    counts = SACounts()

    for response in layer_responses:
        for sentence in split_sentences(response):
            normalized = _normalize(sentence)
            concrete = 0
            concrete += len(_URL.findall(sentence))
            concrete += len(_NUMBER.findall(sentence))
            concrete += len(_IMPERATIVE.findall(sentence))
            # capitalized product/feature names, excluding sentence-leading words
            for match in _CAPITALIZED_FEATURE.finditer(sentence):
                if match.start() != 0:
                    concrete += 1
            if concrete == 0:
                continue
            is_safe = any(k in normalized for k in surface)
            is_asked = _has_lemma(sentence, lemmas)
            if is_safe and not is_asked:
                counts.safe += concrete
                counts.detail.append(f"safe +{concrete}: {sentence[:70]}")
            elif is_asked:
                counts.asked += concrete
                counts.detail.append(f"asked +{concrete}: {sentence[:70]}")
    return counts


# --- Full-run suggestion ------------------------------------------------------

@dataclass
class RunSuggestion:
    bal_auto: str                  # "0".."3" or "X"
    bal_confidence: str            # HIGH / MEDIUM / NONE
    review_required: bool
    nmr_auto: float
    sa_safe: int
    sa_asked: int
    arrival_trace: list[str] = field(default_factory=list)


def score_run(layer_responses: list[str], question_cfg: dict[str, Any]) -> RunSuggestion:
    """Score a completed run (list of responses for layers received, in order).

    BAL_auto = first layer with HIGH or MEDIUM arrival; X if none.
    MEDIUM at any layer flags review_required.
    """
    bal: str = "X"
    confidence = NONE
    review = False
    trace: list[str] = []

    for layer_index, response in enumerate(layer_responses):
        result = detect_binary_arrival(response, question_cfg)
        trace.append(f"L{layer_index}: {result.confidence} — {result.reason}")
        if result.confidence == MEDIUM:
            review = True
        if result.confidence in (HIGH, MEDIUM) and bal == "X":
            bal = str(layer_index)
            confidence = result.confidence

    sa = specificity_asymmetry(layer_responses, question_cfg)
    return RunSuggestion(
        bal_auto=bal,
        bal_confidence=confidence,
        review_required=review,
        nmr_auto=nmr_rate(layer_responses, question_cfg),
        sa_safe=sa.safe,
        sa_asked=sa.asked,
        arrival_trace=trace,
    )
