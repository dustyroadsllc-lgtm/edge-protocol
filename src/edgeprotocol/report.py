"""Report mode: aggregation and table generation.

Neutral column names only (BAL, NMR, ...). No editorializing strings in
any generated output — interpretation lives in prose, separately.
The two datasets are never statistically combined (hard constraint 2).
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

from . import store

REPORTS_DIR = store.PROJECT_ROOT / "reports"

DATASET_LABELS = {
    "field": "Product (manual)",
    "api": "Model baseline (API)",
}


class CrossDatasetError(RuntimeError):
    """Raised on any attempt to compute statistics across datasets."""


def _bal_numeric(value: str) -> float | None:
    """X is treated as 4 for median computation but displayed as 'X'."""
    value = value.strip()
    if not value:
        return None
    if value.upper() == "X":
        return 4.0
    try:
        return float(value)
    except ValueError:
        return None


def _bal_display(numeric: float) -> str:
    return "X" if numeric >= 4.0 else str(int(numeric)) if numeric == int(numeric) else f"{numeric:.1f}"


def _subject_key(dataset: str) -> str:
    return "product" if dataset == "field" else "model_id"


def _score_column(rows: list[dict[str, str]], final_key: str, auto_key: str) -> list[str]:
    """Prefer final (human-confirmed) values; fall back to auto where final is blank."""
    values = []
    for row in rows:
        value = (row.get(final_key) or "").strip() or (row.get(auto_key) or "").strip()
        if value:
            values.append(value)
    return values


def aggregate(dataset: str) -> dict[str, Any]:
    if dataset not in ("field", "api"):
        raise CrossDatasetError(
            "Statistics are computed per dataset only. 'field' and 'api' are "
            "never merged; render them as separate tables via --dataset both."
        )
    rows = store.read_log(dataset)
    subject_key = _subject_key(dataset)

    by_subject: dict[str, dict[str, list[dict[str, str]]]] = {}
    for row in rows:
        subject = row.get(subject_key, "?")
        by_subject.setdefault(subject, {}).setdefault(row["question_id"], []).append(row)

    result: dict[str, Any] = {"dataset": dataset, "label": DATASET_LABELS[dataset], "subjects": {}}
    for subject, by_question in sorted(by_subject.items()):
        subject_summary: dict[str, Any] = {"questions": {}, "c2_baseline": ""}
        for qid, q_rows in sorted(by_question.items()):
            bal_values = [_bal_numeric(v) for v in _score_column(q_rows, "BAL_final", "BAL_auto")]
            bal_values = [v for v in bal_values if v is not None]
            nmr_values = []
            for v in _score_column(q_rows, "NMR_final", "NMR_auto"):
                try:
                    nmr_values.append(float(v))
                except ValueError:
                    pass
            sa_safe = sum(int(float(r.get("SA_safe") or 0)) for r in q_rows)
            sa_asked = sum(int(float(r.get("SA_asked") or 0)) for r in q_rows)
            wp = [r.get("WP_YN", "") for r in q_rows if r.get("WP_YN")]
            bn = [r.get("BN_YN", "") for r in q_rows if r.get("BN_YN")]
            question_summary = {
                "n_runs": len(q_rows),
                "BAL_median": _bal_display(median(bal_values)) if bal_values else "",
                "NMR_mean": round(sum(nmr_values) / len(nmr_values), 2) if nmr_values else "",
                "SA_safe": sa_safe,
                "SA_asked": sa_asked,
                "WP": "/".join(wp),
                "BN": "/".join(bn),
                "transcripts": [r.get("transcript_file", "") for r in q_rows],
            }
            subject_summary["questions"][qid] = question_summary
            if qid == "C2" and bal_values:
                subject_summary["c2_baseline"] = _bal_display(median(bal_values))
        result["subjects"][subject] = subject_summary
    return result


def render_markdown(agg: dict[str, Any]) -> str:
    lines = [
        f"## {agg['label']}",
        "",
        f"Dataset: `{agg['dataset']}` — generated {datetime.now(timezone.utc).isoformat()[:19]}Z",
        "",
        "SA and WP are secondary metrics. BN is the fairness column. "
        "C1 is the legitimate-uncertainty control (BN is the metric there; BAL is not penalized). "
        "C2 median BAL is the subject's baseline willingness to answer binaries.",
        "",
    ]
    for subject, summary in agg["subjects"].items():
        lines.append(f"### {subject}")
        if summary["c2_baseline"]:
            lines.append(f"C2 baseline BAL: {summary['c2_baseline']}")
        lines.append("")
        lines.append("| Question | n | BAL (median) | NMR (mean) | SA safe/asked (secondary) | WP (secondary) | BN |")
        lines.append("|---|---|---|---|---|---|---|")
        for qid, q in summary["questions"].items():
            lines.append(
                f"| {qid} | {q['n_runs']} | {q['BAL_median']} | {q['NMR_mean']} "
                f"| {q['SA_safe']}/{q['SA_asked']} | {q['WP']} | {q['BN']} |"
            )
        lines.append("")
    return "\n".join(lines)


def render_appendix(agg: dict[str, Any]) -> str:
    lines = [f"## Per-run appendix — {agg['label']}", ""]
    for subject, summary in agg["subjects"].items():
        for qid, q in summary["questions"].items():
            for transcript in q["transcripts"]:
                lines.append(f"- {subject} / {qid}: `{transcript}`")
    return "\n".join(lines) + "\n"


def write_csv_aggregate(agg: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    subject_key = _subject_key(agg["dataset"])
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(f"# dataset: {'field_manual' if agg['dataset'] == 'field' else 'model_baseline_api'} — {agg['label']}. Not comparable with the other dataset.\n")
        writer = csv.writer(handle)
        writer.writerow([subject_key, "question_id", "n_runs", "BAL_median", "NMR_mean", "SA_safe", "SA_asked", "WP", "BN"])
        for subject, summary in agg["subjects"].items():
            for qid, q in summary["questions"].items():
                writer.writerow([subject, qid, q["n_runs"], q["BAL_median"], q["NMR_mean"], q["SA_safe"], q["SA_asked"], q["WP"], q["BN"]])


def generate(dataset: str) -> list[Path]:
    """Generate report files. dataset is 'field', 'api', or 'both'."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    written: list[Path] = []

    if dataset == "both":
        # Two clearly separated tables; never combined statistics.
        sections = []
        for ds in ("field", "api"):
            agg = aggregate(ds)
            if agg["subjects"]:
                sections.append(render_markdown(agg))
                csv_path = REPORTS_DIR / f"aggregate-{ds}-{stamp}.csv"
                write_csv_aggregate(agg, csv_path)
                written.append(csv_path)
        md = (
            "# Edge Protocol v0.1 — Results\n\n"
            "**Methods note:** the two tables below come from different collection "
            "modes (manual consumer-product sessions vs. raw model APIs) and are "
            "not comparable; no combined statistics are computed.\n\n"
            + "\n\n---\n\n".join(sections)
        )
        md_path = REPORTS_DIR / f"report-both-{stamp}.md"
        md_path.write_text(md, encoding="utf-8")
        written.append(md_path)
        return written

    agg = aggregate(dataset)
    md_path = REPORTS_DIR / f"report-{dataset}-{stamp}.md"
    md_path.write_text(render_markdown(agg) + "\n\n" + render_appendix(agg), encoding="utf-8")
    written.append(md_path)
    csv_path = REPORTS_DIR / f"aggregate-{dataset}-{stamp}.csv"
    write_csv_aggregate(agg, csv_path)
    written.append(csv_path)
    return written
