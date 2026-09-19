"""Preflight checks for the Module 3 database-ready dataset.

The script identifies missing analysis-critical data before SQL work begins. It
never fabricates or infers applicant values.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_DATA = Path(__file__).with_name("cleaned_applicant_data.json")

REQUIRED_FIELDS = (
    "p_id",
    "program",
    "comments",
    "date_added",
    "url",
    "status",
    "term",
    "us_or_international",
    "gpa",
    "gre",
    "gre_v",
    "gre_aw",
    "degree",
    "llm_generated_program",
    "llm_generated_university",
)

ANALYSIS_CRITICAL = {
    "term": "Questions 1, 4, 5, 6, 8, and 9 need term data.",
    "us_or_international": "Questions 2 and 4 need nationality classification.",
    "gpa": "Questions 3, 4, and 6 need GPA data.",
    "gre": "Question 3 needs GRE Quantitative data.",
    "gre_v": "Question 3 needs GRE Verbal data.",
    "gre_aw": "Question 3 needs GRE Analytical Writing data.",
}


def _usable(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def audit(path: Path = DEFAULT_DATA) -> int:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("Expected a top-level JSON array")

    print(f"Rows: {len(rows):,}")
    print("\nField completeness:")
    populated: dict[str, int] = {}
    for field in REQUIRED_FIELDS:
        count = sum(_usable(row.get(field)) for row in rows)
        populated[field] = count
        pct = 100 * count / len(rows) if rows else 0
        print(f"  {field:28s} {count:7,d} / {len(rows):,} ({pct:6.2f}%)")

    wrong_schema = sum(set(row) != set(REQUIRED_FIELDS) for row in rows)
    ids = [row.get("p_id") for row in rows]
    urls = [row.get("url") for row in rows if _usable(row.get("url"))]
    duplicate_ids = len(ids) - len(set(ids))
    duplicate_urls = len(urls) - len(set(urls))

    print(f"\nRows with wrong field set: {wrong_schema:,}")
    print(f"Duplicate p_id values: {duplicate_ids:,}")
    print(f"Duplicate non-null URLs: {duplicate_urls:,}")

    structural_failures = wrong_schema or duplicate_ids or duplicate_urls
    blockers = [
        (field, reason)
        for field, reason in ANALYSIS_CRITICAL.items()
        if populated.get(field, 0) == 0
    ]

    if structural_failures:
        print("\nFAIL: structural validation failed.")
        return 1

    if blockers:
        print("\nANALYSIS READINESS WARNING:")
        for field, reason in blockers:
            print(f"  - {field}: 0 populated values. {reason}")
        print(
            "\nThe cleaned dataset is structurally valid, but these analyses cannot "
            "produce meaningful results until source-supported values are available."
        )
        print("Do not fabricate or impute values to make the queries non-null.")
        return 2

    print("\nPASS: structure and analysis-critical field availability checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(audit())
