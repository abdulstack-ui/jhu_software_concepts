from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

REQUIRED_KEYS = {
    "program_name",
    "university",
    "comments",
    "date_added",
    "entry_url",
    "applicant_status",
    "decision_date",
    "program_start",
    "student_type",
    "gre_score",
    "gre_verbal",
    "degree",
    "gpa",
    "gre_aw",
    "raw_program_text",
    "raw_listing_text",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Module 2 JSON output")
    parser.add_argument("file", nargs="?", default="applicant_data.json")
    parser.add_argument("--minimum", type=int, default=30000)
    args = parser.parse_args()

    path = Path(args.file)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("FAIL: top-level JSON value is not a list")

    print(f"records: {len(data)}")
    print(f"minimum required: {args.minimum}")
    print(f"count check: {'PASS' if len(data) >= args.minimum else 'NOT YET'}")

    missing_key_records = 0
    missing_counts = Counter()
    urls = []
    tag_fragments = 0

    for rec in data:
        if not isinstance(rec, dict):
            missing_key_records += 1
            continue
        missing = REQUIRED_KEYS - set(rec)
        if missing:
            missing_key_records += 1
            for key in missing:
                missing_counts[key] += 1
        if rec.get("entry_url"):
            urls.append(rec["entry_url"])
        raw = str(rec.get("raw_listing_text") or "")
        if "<td" in raw.lower() or "<tr" in raw.lower() or "&nbsp;" in raw.lower():
            tag_fragments += 1

    duplicate_urls = len(urls) - len(set(urls))
    print(f"records missing one or more expected keys: {missing_key_records}")
    if missing_counts:
        print("missing-key counts:", dict(missing_counts))
    print(f"duplicate non-null entry URLs: {duplicate_urls}")
    print(f"records with obvious remnant HTML/entities in raw listing text: {tag_fragments}")

    for key in sorted(REQUIRED_KEYS):
        present = sum(1 for r in data if isinstance(r, dict) and r.get(key) not in (None, ""))
        print(f"non-null {key}: {present}/{len(data)}")


if __name__ == "__main__":
    main()
