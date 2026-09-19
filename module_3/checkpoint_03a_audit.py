from __future__ import annotations

import argparse
import json
from pathlib import Path

from scrape import parse_html


def synthetic_parser_test() -> None:
    html = '''
    <table>
      <tr><th>School</th><th>Program</th><th>Added On</th><th>Decision</th><th></th></tr>
      <tr>
        <td>Michigan State University</td>
        <td><div><span>Computational Mathematics, Science, and Engineering</span><span>PhD</span></div></td>
        <td>Sep 15, 2026</td><td>Accepted on May 04</td>
        <td><a href="/result/1020484">comments</a></td>
      </tr>
      <tr><td colspan="100%"><div>Fall 2026</div><div>American</div><div>GPA 3.80</div></td></tr>
      <tr><td colspan="100%"><p>Applicant comment here.</p></td></tr>
      <tr>
        <td>BUET</td>
        <td><div><span>Electrical Engineering and Computer Science</span><span>PhD</span></div></td>
        <td>Sep 10, 2026</td><td>Wait listed on Sep 10</td>
        <td><a href="/result/1020479">comments</a></td>
      </tr>
      <tr><td colspan="100%"><div>Spring 2027</div><div>International</div><div>GRE 163</div><div>GRE V 158</div><div>GRE AW 4.00</div><div>GPA 3.57</div></td></tr>
    </table>
    '''
    records = parse_html(html, page_url="https://www.thegradcafe.com/survey")
    assert len(records) == 2
    first, second = records
    assert first["program_start"] == "Fall 2026"
    assert first["student_type"] == "American"
    assert first["gpa"] == "3.80"
    assert first["degree"] == "PhD"
    assert first["comments"] == "Applicant comment here."
    assert second["program_start"] == "Spring 2027"
    assert second["student_type"] == "International"
    assert second["gre_score"] == "163"
    assert second["gre_verbal"] == "158"
    assert second["gre_aw"] == "4.00"
    assert second["gpa"] == "3.57"


def audit_repaired(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"Repaired candidate not found: {path}. Create it first, then rerun this audit.")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, list) and data
    urls = [r.get("entry_url") for r in data]
    assert all(urls)
    assert len(urls) == len(set(urls))

    checks = {
        "term": sum(bool(r.get("program_start")) for r in data),
        "nationality": sum(bool(r.get("student_type")) for r in data),
        "gpa": sum(r.get("gpa") not in (None, "") for r in data),
        "gre": sum(r.get("gre_score") not in (None, "") for r in data),
        "gre_v": sum(r.get("gre_verbal") not in (None, "") for r in data),
        "gre_aw": sum(r.get("gre_aw") not in (None, "") for r in data),
        "degree": sum(bool(r.get("degree")) for r in data),
        "comments": sum(bool(r.get("comments")) for r in data),
    }
    print(f"Candidate repaired rows: {len(data):,}")
    for key, value in checks.items():
        print(f"  {key}: {value:,}")
    if checks["term"] == 0 or checks["nationality"] == 0:
        raise AssertionError("Repaired data still has no term/nationality values")
    if checks["degree"] == 0:
        raise AssertionError("Repaired data still has no degree values")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repaired", type=Path, default=None)
    args = parser.parse_args()

    source = Path("scrape.py").read_text(encoding="utf-8")
    assert "from clean import clean_data" not in source
    assert "def _parse_result_group" in source
    assert "continuation_rows" in source
    synthetic_parser_test()
    print("CHECKPOINT 03A STATIC PARSER AUDIT: PASS")
    print("Grouped-row metadata extraction is regression-tested.")
    print("Scraper no longer imports Module 3's database cleaner.")

    if args.repaired is not None:
        audit_repaired(args.repaired)
        print("CHECKPOINT 03A REPAIRED-DATA AUDIT: PASS")


if __name__ == "__main__":
    main()
