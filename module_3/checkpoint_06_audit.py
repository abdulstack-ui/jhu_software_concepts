"""Checkpoint 06 audit: Pull Data integration and concurrency safeguards."""

from __future__ import annotations

import ast
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def static_audit() -> None:
    app_path = ROOT / "app.py"
    pull_path = ROOT / "pull_data.py"
    template_path = ROOT / "templates" / "index.html"
    css_path = ROOT / "static" / "styles.css"

    for path in (app_path, pull_path, template_path, css_path):
        assert path.exists(), f"Missing required file: {path.relative_to(ROOT)}"

    app_source = app_path.read_text(encoding="utf-8")
    pull_source = pull_path.read_text(encoding="utf-8")
    template = template_path.read_text(encoding="utf-8")

    ast.parse(app_source, filename="app.py")
    ast.parse(pull_source, filename="pull_data.py")

    assert '@app.post("/pull-data")' in app_source
    assert '@app.post("/update-analysis")' in app_source
    assert "subprocess.Popen" in app_source
    assert "PULL_LOCK_FILE" in app_source
    assert "Pull Data is already running" in app_source
    assert "capture(" in pull_source, "Pull Data must reuse the Module 2 capture code"
    assert "PAGES_DIR.mkdir" in pull_source, "Pull Data must create its capture-pages directory"
    assert "require_root_start=True" in pull_source
    assert "resume=False" in pull_source
    assert "upsert_records" in pull_source
    assert "clean_record" in pull_source
    assert "O_EXCL" in pull_source, "Worker must enforce an exclusive lock"
    assert "llm-generated-program" in pull_source
    assert "llm-generated-university" in pull_source
    assert "Pull Data" in template
    assert "Update Analysis" in template
    assert "disabled" in template

    # Update Analysis must remain a database refresh, not a scraper trigger.
    tree = ast.parse(app_source)
    update_source = None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "update_analysis":
            update_source = ast.get_source_segment(app_source, node) or ""
            break
    assert update_source is not None
    assert "_start_pull_process" not in update_source
    assert "Popen" not in update_source

    print("CHECKPOINT 06 STATIC PULL-DATA AUDIT: PASS")
    print("Pull Data reuses the Module 2 Selenium capture/parser.")
    print("Exclusive app/process locking prevents concurrent scrapes.")
    print("Update Analysis does not launch or interrupt a scrape.")


def live_audit() -> None:
    import app as app_module

    # Do not launch a real browser/scraper during the audit. The route itself is
    # tested by temporarily replacing the process-start helper.
    original_running = app_module._pull_is_running
    original_start = app_module._start_pull_process
    started = {"count": 0}

    try:
        app_module._pull_is_running = lambda: False
        app_module._start_pull_process = lambda: started.__setitem__("count", started["count"] + 1)

        client = app_module.app.test_client()
        home = client.get("/")
        update = client.post("/update-analysis", follow_redirects=True)
        pull = client.post("/pull-data", follow_redirects=False)

        assert home.status_code == 200
        assert update.status_code == 200
        assert pull.status_code in {302, 303}
        assert started["count"] == 1
        assert b"Pull Data" in home.data
        assert b"Update Analysis" in home.data

        # Simulate an active worker and prove a second scrape is refused.
        app_module._pull_is_running = lambda: True
        # The route also checks its process/lock state directly; inject a tiny
        # fake process object so no child is started.
        class FakeProcess:
            def poll(self):
                return None

        app_module._pull_process = FakeProcess()  # type: ignore[assignment]
        before = started["count"]
        duplicate = client.post("/pull-data", follow_redirects=False)
        assert duplicate.status_code in {302, 303}
        assert started["count"] == before

        with app_module.SessionLocal() as session:
            analyses = app_module.run_web_analysis(session)
        assert len(analyses) == 11

        print("CHECKPOINT 06 LIVE FLASK AUDIT: PASS")
        print("GET /, POST /update-analysis, and POST /pull-data routes are operational.")
        print("A simulated concurrent Pull Data request was refused.")
        print(f"Dynamic analyses available through ORM: {len(analyses)} / 11")
    finally:
        app_module._pull_is_running = original_running
        app_module._start_pull_process = original_start
        app_module._pull_process = None


def main() -> int:
    static_audit()
    try:
        live_audit()
    except Exception as exc:
        print("CHECKPOINT 06 LIVE FLASK AUDIT: FAIL")
        print(f"{type(exc).__name__}: {exc}")
        print(
            "Confirm PostgreSQL is running and PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD "
            "are set in this PowerShell session."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
