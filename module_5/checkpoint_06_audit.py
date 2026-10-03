"""Static audit for Module 4 Checkpoint 06: GitHub Actions CI."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"

checks: list[tuple[str, bool]] = []

checks.append(("workflow exists at .github/workflows/tests.yml", WORKFLOW.is_file()))
text = WORKFLOW.read_text(encoding="utf-8") if WORKFLOW.is_file() else ""

required_fragments = {
    "PostgreSQL service": "image: postgres:16",
    "PostgreSQL database": "POSTGRES_DB: gradcafe",
    "PostgreSQL user": "POSTGRES_USER: postgres",
    "PostgreSQL health check": "pg_isready -U postgres -d gradcafe",
    "checkout action": "actions/checkout@v4",
    "Python setup action": "actions/setup-python@v5",
    "Python 3.13": 'python-version: "3.13"',
    "requirements install": "python -m pip install -r module_4/requirements.txt",
    "DATABASE_URL": "DATABASE_URL: postgresql://postgres:postgres@localhost:5432/gradcafe",
    "TEST_DATABASE_URL": "TEST_DATABASE_URL: postgresql://postgres:postgres@localhost:5432/gradcafe",
    "required marker sweep": '-m "web or buttons or analysis or db or integration"',
    "coverage summary output": "tee module_4/coverage_summary.txt",
    "coverage artifact upload": "actions/upload-artifact@v4",
}

for label, fragment in required_fragments.items():
    checks.append((label, fragment in text))

print("CHECKPOINT 06 STATIC AUDIT")
failed = False
for label, passed in checks:
    print(f"  {'PASS' if passed else 'FAIL'}: {label}")
    failed = failed or not passed

if failed:
    print("CHECKPOINT 06 STATIC AUDIT: FAIL")
    sys.exit(1)

print("CHECKPOINT 06 STATIC AUDIT: PASS")
