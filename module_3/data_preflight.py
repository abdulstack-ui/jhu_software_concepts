"""Preflight checks for Module 3 source data.

This script exists to prevent silent submission of a database that cannot answer
required analysis questions. It does not fabricate or infer missing applicant data.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

DEFAULT_DATA = Path(__file__).with_name("llm_extend_applicant_data.json")

REQUIRED_KEYS = (
    "program_name",
    "university",
    "comments",
    "date_added",
    "entry_url",
    "applicant_status",
    "program_start",
    "student_type",
    "gpa",
    "gre_score",
    "gre_verbal",
    "gre_aw",
    "degree",
    "llm-generated-program",
    "llm-generated-university",
)

ANALYSIS_CRITICAL = {
    "program_start": "Questions 1, 4, 5, 6, 8, and 9 need term data.",
    "student_type": "Questions 2 and 4 need nationality classification.",
    "gpa": "Questions 3, 4, and 6 need GPA data.",
    "gre_score": "Question 3 needs GRE Quantitative data.",
    "gre_verbal": "Question 3 needs GRE Verbal data.",
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
    missing_keys = Counter()
    populated: dict[str, int] = {}
    for key in REQUIRED_KEYS:
        count = sum(_usable(row.get(key)) for row in rows)
        populated[key] = count
        pct = 100 * count / len(rows) if rows else 0
        print(f"  {key:28s} {count:7,d} / {len(rows):,} ({pct:6.2f}%)")
        if any(key not in row for row in rows):
            missing_keys[key] = sum(key not in row for row in rows)

    duplicate_urls = len(rows) - len({row.get("entry_url") for row in rows if _usable(row.get("entry_url"))})
    null_urls = sum(not _usable(row.get("entry_url")) for row in rows)
    print(f"\nNull/blank entry URLs: {null_urls:,}")
    print(f"Duplicate non-null entry URLs: {duplicate_urls:,}")

    blockers = []
    for key, reason in ANALYSIS_CRITICAL.items():
        if populated.get(key, 0) == 0:
            blockers.append((key, reason))

    if blockers:
        print("\nSUBMISSION BLOCKERS:")
        for key, reason in blockers:
            print(f"  - {key}: 0 populated values. {reason}")
        print("\nDo not fabricate values. Recover them only from the public source data if available, ")
        print("or ask the instructor how Module 3 should be handled with the current GradCafe layout.")
        return 2

    print("\nPASS: every analysis-critical field has at least some usable data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(audit())
