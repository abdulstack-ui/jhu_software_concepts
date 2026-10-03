"""Static audit for Module 4 Checkpoint 01."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent

required = [
    ROOT / "src" / "app.py",
    ROOT / "src" / "models.py",
    ROOT / "src" / "templates" / "index.html",
    ROOT / "tests" / "conftest.py",
    ROOT / "tests" / "test_flask_page.py",
    ROOT / "pytest.ini",
    ROOT / "requirements.txt",
]

missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
if missing:
    raise SystemExit(f"CHECKPOINT 01 FAIL: missing files: {missing}")

app_text = (ROOT / "src" / "app.py").read_text(encoding="utf-8")
html_text = (ROOT / "src" / "templates" / "index.html").read_text(encoding="utf-8")
models_text = (ROOT / "src" / "models.py").read_text(encoding="utf-8")

checks = {
    "create_app factory": "def create_app(" in app_text,
    "analysis route": '@flask_app.get("/analysis")' in app_text,
    "DATABASE_URL support": "DATABASE_URL" in app_text and "DATABASE_URL" in models_text,
    "pull selector": 'data-testid="pull-data-btn"' in html_text,
    "update selector": 'data-testid="update-analysis-btn"' in html_text,
    "Answer label": "Answer:" in html_text,
}

failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit(f"CHECKPOINT 01 FAIL: {failed}")

print("CHECKPOINT 01 STATIC AUDIT: PASS")
for name in checks:
    print(f"  PASS: {name}")
