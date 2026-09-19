"""Checkpoint 01 provenance and schema audit.

Verifies that cleaned_applicant_data.json is a deterministic transformation of
llm_extend_applicant_data.json and that no analysis values were invented.
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
SOURCE = BASE / "llm_extend_applicant_data.json"
CLEANED = BASE / "cleaned_applicant_data.json"

EXPECTED_FIELDS = {
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
}


def text(value: Any) -> str | None:
    if value is None:
        return None
    value = re.sub(r"\s+", " ", html.unescape(str(value))).strip()
    return value or None


def iso_date(value: Any) -> str | None:
    value = text(value)
    if value is None:
        return None
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    raise AssertionError(f"Unexpected source date: {value!r}")


def source_id(url: str) -> int:
    match = re.search(r"/result/(\d+)", url)
    if not match:
        raise AssertionError(f"No result id in URL: {url}")
    return int(match.group(1))


def number(value: Any) -> float | None:
    if value is None or text(value) is None:
        return None
    return float(str(value).replace(",", ""))


def expected_program(row: dict[str, Any]) -> str | None:
    university = text(row.get("university"))
    program = text(row.get("raw_program_text")) or text(row.get("program_name"))
    if university and program:
        return f"{university} | {program}"
    return university or program


def main() -> int:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    cleaned = json.loads(CLEANED.read_text(encoding="utf-8"))

    assert len(source) == len(cleaned), (len(source), len(cleaned))
    assert len(source) == 30011, f"Expected 30,011 rows, found {len(source):,}"

    seen_ids: set[int] = set()
    seen_urls: set[str] = set()

    for i, (src, out) in enumerate(zip(source, cleaned), start=1):
        assert set(out) == EXPECTED_FIELDS, f"Row {i}: wrong output fields"

        url = text(src.get("entry_url"))
        assert url is not None, f"Row {i}: missing source URL"
        expected_id = source_id(url)
        assert out["p_id"] == expected_id, f"Row {i}: p_id mismatch"
        assert out["url"] == url, f"Row {i}: URL mismatch"
        assert out["program"] == expected_program(src), f"Row {i}: program mismatch"
        assert out["comments"] == text(src.get("comments")), f"Row {i}: comments mismatch"
        assert out["date_added"] == iso_date(src.get("date_added")), f"Row {i}: date mismatch"
        assert out["status"] == text(src.get("applicant_status")), f"Row {i}: status mismatch"
        assert out["term"] == text(src.get("program_start")), f"Row {i}: term mismatch"
        assert out["us_or_international"] == text(src.get("student_type")), f"Row {i}: nationality mismatch"
        assert out["gpa"] == number(src.get("gpa")), f"Row {i}: GPA mismatch"
        assert out["gre"] == number(src.get("gre_score")), f"Row {i}: GRE Q mismatch"
        assert out["gre_v"] == number(src.get("gre_verbal")), f"Row {i}: GRE V mismatch"
        assert out["gre_aw"] == number(src.get("gre_aw")), f"Row {i}: GRE AW mismatch"
        assert out["degree"] == text(src.get("degree")), f"Row {i}: degree mismatch"
        assert out["llm_generated_program"] == text(src.get("llm-generated-program")), f"Row {i}: LLM program mismatch"
        assert out["llm_generated_university"] == text(src.get("llm-generated-university")), f"Row {i}: LLM university mismatch"

        assert out["p_id"] not in seen_ids, f"Duplicate p_id {out['p_id']}"
        assert out["url"] not in seen_urls, f"Duplicate URL {out['url']}"
        seen_ids.add(out["p_id"])
        seen_urls.add(out["url"])

    print("CHECKPOINT 01 AUDIT: PASS")
    print(f"Rows verified: {len(cleaned):,}")
    print(f"Unique p_id values: {len(seen_ids):,}")
    print(f"Unique URLs: {len(seen_urls):,}")
    print("No GPA/GRE/term/nationality/degree values were inferred beyond source fields.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
