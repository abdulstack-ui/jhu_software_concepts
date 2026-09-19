from __future__ import annotations

import argparse
import html
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _clean_text(value: Any) -> str | None:
    """Normalize whitespace/HTML entities without inventing missing data."""
    if value is None:
        return None
    text = html.unescape(str(value))
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _to_float(value: Any) -> float | None:
    """Convert a supplied numeric value to float; preserve missing values as None."""
    text = _clean_text(value)
    if text is None:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _to_iso_date(value: Any) -> str | None:
    """Convert a supplied GradCafe date to YYYY-MM-DD; preserve missing values."""
    text = _clean_text(value)
    if text is None:
        return None

    for fmt in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass

    # Do not invent/guess a date if the source format is unexpected.
    return text


def _original_program(record: Dict[str, Any]) -> str | None:
    """Build Module 3's original program field from scraped source fields only."""
    university = _clean_text(record.get("university"))
    raw_program = _clean_text(record.get("raw_program_text"))
    program_name = _clean_text(record.get("program_name"))
    program = raw_program or program_name

    if university and program:
        return f"{university} | {program}"
    return university or program


def clean_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Map one real Module 2 record to the Module 3 input fields.

    Important: this function only normalizes/renames values that already exist.
    It does not infer degree, term, nationality, GPA, GRE, or other missing data.
    """
    return {
        "program": _original_program(record),
        "comments": _clean_text(record.get("comments")),
        "date_added": _to_iso_date(record.get("date_added")),
        "url": _clean_text(record.get("entry_url")),
        "status": _clean_text(record.get("applicant_status")),
        "term": _clean_text(record.get("program_start")),
        "us_or_international": _clean_text(record.get("student_type")),
        "gpa": _to_float(record.get("gpa")),
        "gre": _to_float(record.get("gre_score")),
        "gre_v": _to_float(record.get("gre_verbal")),
        "gre_aw": _to_float(record.get("gre_aw")),
        "degree": _clean_text(record.get("degree")),
        "llm_generated_program": _clean_text(record.get("llm-generated-program")),
        "llm_generated_university": _clean_text(record.get("llm-generated-university")),
    }


def clean_data(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [clean_record(record) for record in records]


def load_json(path: str | Path) -> List[Dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Expected a top-level JSON array")
    return data


def save_json(records: Iterable[Dict[str, Any]], path: str | Path) -> None:
    with Path(path).open("w", encoding="utf-8") as f:
        json.dump(list(records), f, indent=2, ensure_ascii=False)
        f.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create conservative Module 3 database-ready data from the Module 2 cleaned output."
    )
    parser.add_argument("--input", default="llm_extend_applicant_data.json")
    parser.add_argument("--output", default="cleaned_applicant_data.json")
    args = parser.parse_args()

    records = load_json(args.input)
    cleaned = clean_data(records)
    save_json(cleaned, args.output)
    print(f"Wrote {len(cleaned):,} cleaned records to {args.output}")


if __name__ == "__main__":
    main()
