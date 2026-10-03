"""Static audit for Module 4 Checkpoint 04."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
TESTS = ROOT / "tests"
INTEGRATION = TESTS / "test_integration_end_to_end.py"
PYTEST_INI = ROOT / "pytest.ini"

checks = {
    "required integration test file": (INTEGRATION, "def test_fake_scrape_pull_update_and_render_end_to_end"),
    "integration marker registered": (PYTEST_INI, "integration: end-to-end flows"),
    "integration tests marked": (INTEGRATION, "@pytest.mark.integration"),
    "fake scraper used": (INTEGRATION, "def fake_scraper"),
    "multiple fake rows flow through pull": (INTEGRATION, "len(sample_db_rows)"),
    "real PostgreSQL loader used": (INTEGRATION, "load_records_into_connection"),
    "pull endpoint exercised": (INTEGRATION, 'client.post("/pull-data")'),
    "update endpoint exercised": (INTEGRATION, 'client.post("/update-analysis")'),
    "analysis page rendered": (INTEGRATION, 'client.get("/analysis")'),
    "overlapping pull rejected with 409": (INTEGRATION, "status_code == 409"),
    "database consistency asserted": (INTEGRATION, "count_database_rows"),
}

failures: list[str] = []
for label, (path, needle) in checks.items():
    if not path.exists() or needle not in path.read_text(encoding="utf-8"):
        failures.append(label)

text = INTEGRATION.read_text(encoding="utf-8") if INTEGRATION.exists() else ""
if text.count("def test_") != 2:
    failures.append("exactly two Checkpoint 04 integration tests")
if text.count("@pytest.mark.integration") != text.count("def test_"):
    failures.append("every integration test carries the integration marker")
if "sleep(" in text or "time.sleep" in text:
    failures.append("integration busy-state tests must not use sleep")

if failures:
    print("CHECKPOINT 04 STATIC AUDIT: FAIL")
    for failure in failures:
        print(f"  FAIL: {failure}")
    raise SystemExit(1)

print("CHECKPOINT 04 STATIC AUDIT: PASS")
for label in checks:
    print(f"  PASS: {label}")
print("  PASS: exactly two integration tests")
print("  PASS: every integration test carries the integration marker")
print("  PASS: no sleep-based busy-state test")
