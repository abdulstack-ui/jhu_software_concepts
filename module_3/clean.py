from __future__ import annotations

import argparse
import html
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

OUTPUT_FIELDS = (
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

_MISSING_TEXT = {"", "none", "null", "n/a", "na", "-"}


def _clean_text(value: Any) -> str | None:
    """Normalize whitespace/HTML entities without inventing missing data."""
    if value is None:
        return None
    text = html.unescape(str(value))
    text = re.sub(r"\s+", " ", text).strip()
    if text.lower() in _MISSING_TEXT:
        return None
    return text or None


def _to_float(value: Any, *, field_name: str) -> float | None:
    """Convert a supplied numeric value to float without guessing.

    Missing values remain None. A non-empty value that is not a plain number is
    rejected so the cleaner cannot silently turn unexpected source data into NULL.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)

    text = _clean_text(value)
    if text is None:
        return None
    text = text.replace(",", "")
    if not re.fullmatch(r"[-+]?\d+(?:\.\d+)?", text):
        raise ValueError(f"Unexpected non-numeric value for {field_name}: {value!r}")
    return float(text)


def _to_iso_date(value: Any) -> str | None:
    """Convert a supplied GradCafe date to YYYY-MM-DD without guessing."""
    text = _clean_text(value)
    if text is None:
        return None

    for fmt in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass

    raise ValueError(f"Unexpected date format: {value!r}")


def _result_id(url: Any) -> int:
    """Use the numeric identifier already present in the public result URL."""
    text = _clean_text(url)
    if text is None:
        raise ValueError("Record is missing entry_url; cannot create p_id")
    match = re.search(r"/result/(\d+)(?:/|$|[?#])", text)
    if not match:
        raise ValueError(f"Could not extract result id from entry_url: {text!r}")
    return int(match.group(1))


def _original_program(record: Dict[str, Any]) -> str | None:
    """Create Module 3's original program field from downloaded source fields."""
    university = _clean_text(record.get("university"))
    raw_program = _clean_text(record.get("raw_program_text"))
    program_name = _clean_text(record.get("program_name"))
    program = raw_program or program_name

    if university and program:
        return f"{university} | {program}"
    return university or program


def clean_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Map one Module 2 cleaned record to the exact Module 3 database schema.

    Only values already present in the source/LLM-extended record are normalized
    or renamed. Missing degree, term, nationality, GPA, GRE, comments, etc. are
    not inferred or imputed.
    """
    cleaned = {
        "p_id": _result_id(record.get("entry_url")),
        "program": _original_program(record),
        "comments": _clean_text(record.get("comments")),
        "date_added": _to_iso_date(record.get("date_added")),
        "url": _clean_text(record.get("entry_url")),
        "status": _clean_text(record.get("applicant_status")),
        "term": _clean_text(record.get("program_start")),
        "us_or_international": _clean_text(record.get("student_type")),
        "gpa": _to_float(record.get("gpa"), field_name="gpa"),
        "gre": _to_float(record.get("gre_score"), field_name="gre_score"),
        "gre_v": _to_float(record.get("gre_verbal"), field_name="gre_verbal"),
        "gre_aw": _to_float(record.get("gre_aw"), field_name="gre_aw"),
        "degree": _clean_text(record.get("degree")),
        "llm_generated_program": _clean_text(record.get("llm-generated-program")),
        "llm_generated_university": _clean_text(record.get("llm-generated-university")),
    }
    return cleaned


def validate_cleaned_records(records: List[Dict[str, Any]]) -> None:
    """Fail loudly if the database-ready output violates the required schema."""
    expected = set(OUTPUT_FIELDS)
    seen_ids: set[int] = set()
    seen_urls: set[str] = set()

    for index, record in enumerate(records, start=1):
        keys = set(record)
        if keys != expected:
            missing = sorted(expected - keys)
            extra = sorted(keys - expected)
            raise ValueError(
                f"Record {index} has wrong schema. Missing={missing}, extra={extra}"
            )

        p_id = record["p_id"]
        if not isinstance(p_id, int):
            raise ValueError(f"Record {index} p_id is not an integer: {p_id!r}")
        if p_id in seen_ids:
            raise ValueError(f"Duplicate p_id detected: {p_id}")
        seen_ids.add(p_id)

        url = record["url"]
        if not url:
            raise ValueError(f"Record {index} is missing url")
        if url in seen_urls:
            raise ValueError(f"Duplicate url detected: {url}")
        seen_urls.add(url)

        if record["program"] is None:
            raise ValueError(f"Record {index} is missing program")
        if record["date_added"] is None:
            raise ValueError(f"Record {index} is missing date_added")
        if record["status"] is None:
            raise ValueError(f"Record {index} is missing status")


def clean_data(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cleaned = [clean_record(record) for record in records]
    validate_cleaned_records(cleaned)
    return cleaned


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
        description=(
            "Create conservative Module 3 database-ready data from the Module 2 "
            "LLM-extended output."
        )
    )
    parser.add_argument("--input", default="llm_extend_applicant_data.json")
    parser.add_argument("--output", default="cleaned_applicant_data.json")
    args = parser.parse_args()

    source_records = load_json(args.input)
    cleaned = clean_data(source_records)
    save_json(cleaned, args.output)
    print(f"Wrote {len(cleaned):,} validated records to {args.output}")


if __name__ == "__main__":
    main()
