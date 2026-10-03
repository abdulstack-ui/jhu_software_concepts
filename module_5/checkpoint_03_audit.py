"""Static audit for Module 4 Checkpoint 03."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
TESTS = ROOT / "tests"

checks = {
    "analysis formatting tests": (TESTS / "test_analysis_format.py", "@pytest.mark.analysis"),
    "database tests": (TESTS / "test_db_insert.py", "@pytest.mark.db"),
    "two-decimal percentage assertion": (TESTS / "test_analysis_format.py", r"\d{2}%"),
    "real PostgreSQL loader helper": (SRC / "load_data.py", "load_records_into_connection"),
    "schema-aware table helper": (SRC / "load_data.py", "_applicants_table"),
    "DATABASE_URL psycopg support": (SRC / "load_data.py", "DATABASE_URL"),
    "idempotent upsert": (SRC / "load_data.py", "ON CONFLICT (p_id) DO UPDATE"),
    "required field names": (SRC / "load_data.py", "EXPECTED_FIELD_NAMES"),
    "simple dict query": (SRC / "query_data.py", "fetch_applicant_dict"),
    "isolated PostgreSQL schema fixture": (TESTS / "conftest.py", "module4_test_"),
}

failures: list[str] = []
for label, (path, needle) in checks.items():
    if not path.exists() or needle not in path.read_text(encoding="utf-8"):
        failures.append(label)

# Every test function in the new files must have the required marker nearby.
for filename, marker in (
    ("test_analysis_format.py", "@pytest.mark.analysis"),
    ("test_db_insert.py", "@pytest.mark.db"),
):
    text = (TESTS / filename).read_text(encoding="utf-8")
    test_count = text.count("def test_")
    marker_count = text.count(marker)
    if test_count == 0 or marker_count != test_count:
        failures.append(f"all {filename} tests marked")

if failures:
    print("CHECKPOINT 03 STATIC AUDIT: FAIL")
    for failure in failures:
        print(f"  FAIL: {failure}")
    raise SystemExit(1)

print("CHECKPOINT 03 STATIC AUDIT: PASS")
for label in checks:
    print(f"  PASS: {label}")
print("  PASS: all Checkpoint 03 tests carry required markers")
