"""edgeprotocol CLI. Every subcommand verifies the bank lock before running."""
from __future__ import annotations

import argparse
import sys

from .bank import BankIntegrityError, load_bank


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="edgeprotocol",
        description="Edge Protocol v0.1 runner — pre-registered AI edge-management evaluation.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_field = sub.add_parser("field", help="Manual session assistant (consumer products).")
    p_field.add_argument("--product", help="Product slug, e.g. chatgpt, claude, gemini.")
    p_field.add_argument("--question", help="Question id, e.g. Q1, C2.")
    p_field.add_argument("--run", type=int, default=1, help="Run number (1-3).")
    p_field.add_argument("--plan", action="store_true", help="Show the remaining collection grid.")

    p_api = sub.add_parser("api", help="Automated model baseline via official APIs.")
    p_api.add_argument("--provider", choices=["anthropic", "openai", "google", "xai", "deepseek"])
    p_api.add_argument("--model", help="Model id (defaults to a cheap model per provider).")
    p_api.add_argument("--question", help="Question id.")
    p_api.add_argument("--runs", type=int, default=1, help="Runs per question.")
    p_api.add_argument("--all", action="store_true", help="Full grid across configured providers.")
    p_api.add_argument("--yes", action="store_true", help="Skip the cost-guard confirmation.")

    p_report = sub.add_parser("report", help="Aggregate logs into tables.")
    p_report.add_argument("--dataset", choices=["field", "api", "both"], required=True)

    args = parser.parse_args(argv)

    # Hard constraint 3: verify the lock before doing anything at all.
    try:
        bank = load_bank()
    except BankIntegrityError as exc:
        print(f"REFUSING TO RUN: {exc}", file=sys.stderr)
        return 2

    if args.command == "field":
        from . import field
        if args.plan:
            field.print_plan(bank)
            return 0
        if not args.product or not args.question:
            print("field mode needs --product and --question (or --plan).", file=sys.stderr)
            return 1
        field.run_field_session(bank, args.product, args.question.upper(), args.run)
        return 0

    if args.command == "api":
        from . import api_runner
        if args.all:
            api_runner.run_grid(bank, runs=args.runs if args.runs > 1 else 3, assume_yes=args.yes)
            return 0
        if not args.provider or not args.question:
            print("api mode needs --provider and --question (or --all).", file=sys.stderr)
            return 1
        model = args.model or api_runner.DEFAULT_MODELS[args.provider]
        run_numbers = api_runner.missing_collection_run_numbers(args.provider, model, args.question.upper(), args.runs)
        if not run_numbers:
            print(f"collection already has runs 1-{args.runs} for {args.provider}/{model} {args.question.upper()}")
            return 0
        for run_n in run_numbers:
            try:
                api_runner.run_api_session(bank, args.provider, model, args.question.upper(), run_n)
            except api_runner.ProviderUnavailable as exc:
                print(f"Provider unavailable: {exc}", file=sys.stderr)
                return 1
        return 0

    if args.command == "report":
        from . import report
        try:
            paths = report.generate(args.dataset)
        except report.CrossDatasetError as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 2
        for path in paths:
            print(f"Wrote {path}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
