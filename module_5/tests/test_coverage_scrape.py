"""Deterministic offline coverage for the inherited GradCafe HTML parser."""

from __future__ import annotations

import json

import pytest
from bs4 import BeautifulSoup

pytestmark = pytest.mark.integration

import scrape


def _tag(html: str):
    return BeautifulSoup(html, "html.parser").find()


def test_url_json_and_normalization_helpers(tmp_path):
    assert scrape.build_url("/survey") == "https://www.thegradcafe.com/survey"
    with pytest.raises(ValueError, match="scheme"):
        scrape.build_url("ftp://thegradcafe.com/file")
    with pytest.raises(ValueError, match="Only GradCafe"):
        scrape.build_url("https://example.com/survey")

    missing = tmp_path / "missing.json"
    assert scrape.load_data(missing) == []
    output = tmp_path / "nested" / "data.json"
    scrape.save_data([{"x": 1}], output)
    assert scrape.load_data(output) == [{"x": 1}]
    output.write_text(json.dumps({"x": 1}), encoding="utf-8")
    with pytest.raises(ValueError, match="top-level JSON array"):
        scrape.load_data(output)

    assert scrape._clean_cell_text(None) is None
    tag = BeautifulSoup("<td>  Alpha   Beta </td>", "html.parser").td
    assert scrape._clean_cell_text(tag) == "Alpha   Beta"

    normalized = scrape._normalize_scraped_record({"program_name": "  A   B  ", "gpa": 3.5})
    assert normalized["program_name"] == "A B"
    assert normalized["gpa"] == 3.5
    assert scrape.clean_data([{"program_name": " X "}])[0]["program_name"] == "X"


def test_status_match_degree_and_program_helpers():
    assert scrape._status("Accepted offer") == "Accepted"
    assert scrape._status("application rejected") == "Rejected"
    assert scrape._status("Wait listed") == "Waitlisted"
    assert scrape._status("Interview invitation") == "Interview"
    assert scrape._status("Pending") is None

    assert scrape._match(r"GPA\s+([0-9.]+)", "GPA 3.9") == "3.9"
    assert scrape._match(r"GPA\s+([0-9.]+)", "none") is None

    for text, expected in [
        ("Computer Science Ph.D.", "PhD"),
        ("Computer Science Doctoral", "PhD"),
        ("Computer Science M.S.", "Masters"),
        ("Law JD", "JD"),
        ("Business MBA", "MBA"),
        ("Computer Science", None),
    ]:
        assert scrape._infer_degree(text, text) == expected

    assert scrape._program_without_degree(None) is None
    assert scrape._program_without_degree("Computer Science PhD") == "Computer Science"
    assert scrape._program_without_degree("Computer Science") == "Computer Science"


def test_entry_url_comments_and_table_helpers():
    row = BeautifulSoup("<tr><td>No links</td></tr>", "html.parser").tr
    assert scrape._extract_entry_url(row, scrape.SURVEY_URL) is None

    row = BeautifulSoup(
        '<tr><td><a href="/survey?cursor=abc">next</a>'
        '<a href="/result/123">result</a></td></tr>',
        "html.parser",
    ).tr
    assert scrape._extract_entry_url(row, scrape.SURVEY_URL).endswith("/result/123")

    assert scrape._extract_comments(None, []) is None
    cell = BeautifulSoup(
        "<td><div>Accepted</div><p>This is a useful applicant comment.</p></td>",
        "html.parser",
    ).td
    assert scrape._extract_comments(cell, ["Accepted"]) == "This is a useful applicant comment."

    status_only = BeautifulSoup("<td>Accepted</td>", "html.parser").td
    assert scrape._extract_comments(status_only, []) is None
    long_plain = BeautifulSoup("<td>Accepted Wonderful experience overall</td>", "html.parser").td
    assert scrape._extract_comments(long_plain, ["Accepted"]) == "Wonderful experience overall"
    short_plain = BeautifulSoup("<td>Accepted hi</td>", "html.parser").td
    assert scrape._extract_comments(short_plain, ["Accepted"]) is None

    table = BeautifulSoup("<table></table>", "html.parser").table
    assert scrape._table_headers(table) == []
    table = BeautifulSoup(
        "<table><tr><th>School</th><th>Program</th><th>Decision</th></tr></table>",
        "html.parser",
    ).table
    assert scrape._table_headers(table) == ["school", "program", "decision"]

    soup = BeautifulSoup("<table><tr><th>Other</th></tr></table>", "html.parser")
    assert scrape._find_results_table(soup) is None
    soup = BeautifulSoup(
        "<table><tr><th>School</th><th>Program</th><th>Decision</th></tr></table>",
        "html.parser",
    )
    assert scrape._find_results_table(soup) is not None


def test_program_metadata_comments_and_result_group():
    cell = BeautifulSoup(
        "<td><span>Computer Science</span><span>PhD</span></td>", "html.parser"
    ).td
    assert scrape._extract_program_and_degree(cell) == ("Computer Science", "PhD")

    cell = BeautifulSoup("<td>Computer Science Masters</td>", "html.parser").td
    assert scrape._extract_program_and_degree(cell) == ("Computer Science", "Masters")

    metadata = scrape._parse_metadata_text(
        "Fall 2026 International GPA 3.91 GRE V 162 GRE AW 4.5 GRE 168"
    )
    assert metadata == {
        "program_start": "Fall 2026",
        "student_type": "International",
        "gpa": "3.91",
        "gre_verbal": "162",
        "gre_aw": "4.5",
        "gre_score": "168",
    }

    row = BeautifulSoup("<tr><td>nothing</td></tr>", "html.parser").tr
    assert scrape._extract_group_comments([row]) is None
    row = BeautifulSoup(
        "<tr><td><p>short</p><p>This is the longest comment supplied.</p></td></tr>",
        "html.parser",
    ).tr
    assert scrape._extract_group_comments([row]) == "This is the longest comment supplied."

    bad = BeautifulSoup("<tr><td>A</td><td>B</td></tr>", "html.parser").tr
    assert scrape._parse_result_group(bad, [], scrape.SURVEY_URL) is None

    primary = BeautifulSoup(
        """
        <tr>
          <td>Example University</td>
          <td><span>Computer Science</span><span>PhD</span></td>
          <td>Sep 20, 2026</td>
          <td><a href="/result/777">Accepted on Sep 18, 2026</a></td>
        </tr>
        """,
        "html.parser",
    ).tr
    continuation = BeautifulSoup(
        "<tr><td colspan='4'>Fall 2026 International GPA 3.91 GRE V 162 GRE AW 4.5 GRE 168"
        "<p>Strong fit with the lab.</p></td></tr>",
        "html.parser",
    ).tr
    record = scrape._parse_result_group(primary, [continuation], scrape.SURVEY_URL)
    assert record["university"] == "Example University"
    assert record["degree"] == "PhD"
    assert record["decision_date"] == "Sep 18, 2026"
    assert record["comments"] == "Strong fit with the lab."
    assert scrape._parse_table_row(primary, scrape.SURVEY_URL)["entry_url"].endswith("/result/777")


def test_semantic_and_generic_html_parsing():
    semantic_html = """
    <html><body><table>
      <tr><th>School</th><th>Program</th><th>Date</th><th>Decision</th></tr>
      <tr><td>Example U</td><td><span>Computer Science</span><span>PhD</span></td>
          <td>Sep 20, 2026</td><td><a href='/result/100'>Accepted on Sep 19, 2026</a></td></tr>
      <tr><td colspan='4'>Fall 2026 International GPA 3.90 GRE 168<p>First comment is informative.</p></td></tr>
      <tr><td>Other U</td><td><span>Physics</span><span>Masters</span></td>
          <td>Sep 21, 2026</td><td><a href='/result/101'>Rejected on Sep 20, 2026</a></td></tr>
    </table></body></html>
    """
    soup = BeautifulSoup(semantic_html, "html.parser")
    records = scrape._parse_semantic_table(soup, scrape.SURVEY_URL)
    assert len(records) == 2
    assert records[0]["entry_url"].endswith("/result/100")

    no_table = BeautifulSoup("<html><body>No table</body></html>", "html.parser")
    assert scrape._parse_semantic_table(no_table, scrape.SURVEY_URL) == []

    generic_html = """
    <html><body>
      <article><a href='/result/201'>Accepted on Sep 1, 2026</a> Fall 2026 International GPA 3.80 GRE V 160 GRE AW 4.0 GRE 167 extra words here</article>
      <article><a href='/result/202'>Rejected on Sep 2, 2026</a> Spring 2027 American GPA 3.70 GRE V 159 GRE AW 4.5 GRE 166 extra words here</article>
    </body></html>
    """
    generic_soup = BeautifulSoup(generic_html, "html.parser")
    generic = scrape._parse_generic_rows(generic_soup, scrape.SURVEY_URL)
    assert len(generic) == 2
    assert generic[0]["applicant_status"] == "Accepted"

    parsed_semantic = scrape.parse_html(semantic_html, page_url="/survey")
    assert len(parsed_semantic) == 2
    parsed_generic = scrape.parse_html(generic_html, page_url="/survey")
    assert len(parsed_generic) == 2


def test_scrape_files_dedup_aliases_and_facade(tmp_path):
    html = """
    <article><a href='/result/301'>Accepted on Sep 1, 2026</a> Fall 2026 International GPA 3.80 GRE V 160 GRE AW 4.0 GRE 167 extra words here</article>
    <article><a href='/result/302'>Rejected on Sep 2, 2026</a> Fall 2026 American GPA 3.70 GRE V 159 GRE AW 4.5 GRE 166 extra words here</article>
    """
    path = tmp_path / "page.html"
    path.write_text(html, encoding="utf-8")
    records = scrape.scrape_data([path], page_url=scrape.SURVEY_URL)
    assert len(records) == 2

    with_url = {"entry_url": "https://www.thegradcafe.com/result/1"}
    assert scrape.record_key(with_url) == ("entry_url", with_url["entry_url"])
    fallback = {
        "university": "U",
        "raw_program_text": "P",
        "date_added": "D",
        "applicant_status": "A",
        "decision_date": "X",
        "raw_listing_text": "R",
    }
    assert scrape.record_key(fallback)[0] == "fallback"
    assert len(scrape.deduplicate([with_url, dict(with_url), fallback])) == 2

    assert scrape._normalize_status("accepted") == "Accepted"
    row = BeautifulSoup(
        "<tr><td>U</td><td>P</td><td>D</td><td><a href='/result/9'>Rejected</a></td></tr>",
        "html.parser",
    ).tr
    assert scrape._parse_entry(row, scrape.SURVEY_URL)["applicant_status"] == "Rejected"

    facade = scrape.GradCafeScraper()
    assert len(facade.parse_html(html, scrape.SURVEY_URL)) == 2
    assert len(facade.scrape_data([path], scrape.SURVEY_URL)) == 2
    assert facade.clean_data([{"program_name": " A "}])[0]["program_name"] == "A"
    output = tmp_path / "facade.json"
    facade.save_data([{"x": 1}], output)
    assert facade.load_data(output) == [{"x": 1}]
