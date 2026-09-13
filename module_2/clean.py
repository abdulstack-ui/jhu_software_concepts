from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _clean_text(value: Any) -> str | None:
    """Normalize whitespace/HTML entities without changing applicant meaning."""
    if value is None:
        return None
    text = html.unescape(str(value))
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def clean_record(record: Dict[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for key, value in record.items():
        cleaned[key] = _clean_text(value) if isinstance(value, str) or value is None else value
    return cleaned


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


def run_llm_standardization(input_path: str | Path, output_path: str | Path, workers: int = 1) -> None:
    """Run the instructor local model integration and write the required JSON array."""
    from llm_hosting.app import standardize_rows
    rows = clean_data(load_json(input_path))
    standardized = standardize_rows(rows, workers=workers)
    save_json(standardized, output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean Module 2 raw data and optionally run the local LLM standardizer.")
    parser.add_argument("--input", default="applicant_data.json")
    parser.add_argument("--output", default="llm_extend_applicant_data.json")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--text-only", action="store_true", help="Only normalize whitespace/entities; do not run the LLM")
    args = parser.parse_args()

    if args.text_only:
        save_json(clean_data(load_json(args.input)), args.output)
    else:
        run_llm_standardization(args.input, args.output, workers=args.workers)


if __name__ == "__main__":
    main()
