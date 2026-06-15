"""Append-only run storage. Raw transcripts are sacred (hard constraint 5).

Every run is written as a complete JSON document with a UUID before any
scoring is finalized. No run data is ever overwritten. The two datasets
(field / api) live in separate directories and separate CSV logs and are
never merged (hard constraint 2).
"""
from __future__ import annotations

import csv
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIELD_RUNS = PROJECT_ROOT / "data" / "field" / "runs"
API_RUNS = PROJECT_ROOT / "data" / "api" / "runs"
FIELD_LOG = PROJECT_ROOT / "data" / "field" / "edge-protocol-log.csv"
API_LOG = PROJECT_ROOT / "data" / "api" / "edge-protocol-api-log.csv"

FIELD_COLUMNS = [
    "date", "product", "model_version_shown", "tier", "question_id", "run_n",
    "BAL_auto", "BAL_final", "NMR_auto", "NMR_final", "SA_safe", "SA_asked",
    "WP_YN", "BN_YN", "transcript_file", "screenshots", "account_state", "notes",
]

API_COLUMNS = [
    "date", "phase", "provider", "model_id", "temperature", "system_prompt_used",
    "question_id", "run_n",
    "BAL_auto", "BAL_final", "NMR_auto", "NMR_final", "SA_safe", "SA_asked",
    "WP_YN", "BN_YN", "transcript_file", "review_required", "notes",
]


def new_run_id() -> str:
    return str(uuid.uuid4())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_run_json(dataset: str, run_record: dict[str, Any]) -> Path:
    """Write a complete run record. Append-only: refuses to overwrite."""
    if dataset == "field":
        directory = FIELD_RUNS
        run_record.setdefault("dataset", "field_manual")
    elif dataset == "api":
        directory = API_RUNS
        run_record.setdefault("dataset", "model_baseline_api")
    else:
        raise ValueError(f"Unknown dataset {dataset!r}; must be 'field' or 'api'")

    directory.mkdir(parents=True, exist_ok=True)
    run_id = run_record.get("run_id") or new_run_id()
    run_record["run_id"] = run_id
    path = directory / f"{run_id}.json"
    if path.exists():
        raise FileExistsError(f"Run {run_id} already exists; runs are append-only.")
    path.write_text(json.dumps(run_record, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def append_log_row(dataset: str, row: dict[str, Any]) -> Path:
    if dataset == "field":
        log_path, columns = FIELD_LOG, FIELD_COLUMNS
        header_comment = "# dataset: field_manual — consumer products, manual collection. Never merge with api log.\n"
    elif dataset == "api":
        log_path, columns = API_LOG, API_COLUMNS
        header_comment = "# dataset: model_baseline_api — raw models via official APIs. Never merge with field log.\n"
        row.setdefault("phase", "collection")
    else:
        raise ValueError(f"Unknown dataset {dataset!r}")

    log_path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not log_path.exists()
    with log_path.open("a", encoding="utf-8", newline="") as handle:
        if new_file:
            handle.write(header_comment)
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
        else:
            writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writerow({k: row.get(k, "") for k in columns})
    return log_path


def read_log(dataset: str) -> list[dict[str, str]]:
    log_path = FIELD_LOG if dataset == "field" else API_LOG
    if not log_path.exists():
        return []
    with log_path.open("r", encoding="utf-8") as handle:
        lines = [line for line in handle if not line.startswith("#")]
    if not lines:
        return []
    return list(csv.DictReader(lines))
