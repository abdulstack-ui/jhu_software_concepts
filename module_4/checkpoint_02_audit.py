"""Static audit for Module 4 Checkpoint 02."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent

required = [
    ROOT / "src" / "app.py",
    ROOT / "tests" / "test_flask_page.py",
    ROOT / "tests" / "test_buttons.py",
    ROOT / "pytest.ini",
]

missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
if missing:
    raise SystemExit(f"CHECKPOINT 02 FAIL: missing files: {missing}")

app_text = (ROOT / "src" / "app.py").read_text(encoding="utf-8")
test_text = (ROOT / "tests" / "test_buttons.py").read_text(encoding="utf-8")

checks = {
    "pull JSON success contract": "jsonify(ok=True, busy=False, rows=len(rows))" in app_text,
    "update JSON success contract": "jsonify(ok=True, busy=False, analysis_count=len(analyses))" in app_text,
    "busy 409 contract": "jsonify(ok=False, busy=True), 409" in app_text,
    "fake scraper injection": "scraper: Scraper | None = None" in app_text,
    "fake loader injection": "loader: Loader | None = None" in app_text,
    "scraper rows passed to loader": "loader(rows)" in app_text,
    "button tests marked": test_text.count("@pytest.mark.buttons") >= 5,
    "loader failure test": "test_loader_failure_returns_non_200" in test_text,
    "no sleep based busy test": "sleep(" not in test_text,
}

failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit(f"CHECKPOINT 02 FAIL: {failed}")

print("CHECKPOINT 02 STATIC AUDIT: PASS")
for name in checks:
    print(f"  PASS: {name}")
