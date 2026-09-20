"""Flask analysis page for the Module 3 GradCafe PostgreSQL database."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, redirect, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError

from models import SessionLocal
from orm_queries import run_web_analysis

app = Flask(__name__)

ROOT = Path(__file__).resolve().parent
PULL_SCRIPT = ROOT / "pull_data.py"
PULL_STATUS_FILE = ROOT / "pull_data_status.json"
PULL_LOCK_FILE = ROOT / "pull_data.lock"
PULL_LOG_FILE = ROOT / "pull_data.log"

_pull_guard = threading.Lock()
_pull_process: subprocess.Popen[Any] | None = None


def _query_analysis():
    with SessionLocal() as session:
        return run_web_analysis(session)


def _read_pull_status() -> dict[str, Any] | None:
    if not PULL_STATUS_FILE.exists():
        return None
    try:
        payload = json.loads(PULL_STATUS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _pull_is_running() -> bool:
    """Return True while this app's Pull Data subprocess or its lock is active."""
    global _pull_process
    with _pull_guard:
        if _pull_process is not None:
            if _pull_process.poll() is None:
                return True
            _pull_process = None
    return PULL_LOCK_FILE.exists()


def _start_pull_process() -> None:
    """Start one background Pull Data worker without blocking the Flask request."""
    global _pull_process
    log_handle = PULL_LOG_FILE.open("a", encoding="utf-8")
    try:
        _pull_process = subprocess.Popen(
            [sys.executable, str(PULL_SCRIPT)],
            cwd=str(ROOT),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
        )
    finally:
        # The child keeps its duplicated log handle; the Flask process does not need one.
        log_handle.close()


@app.get("/")
def index():
    status = request.args.get("status")
    pull_running = _pull_is_running()
    pull_status = _read_pull_status()

    try:
        analyses = _query_analysis()
        error = None
    except SQLAlchemyError as exc:
        analyses = []
        error = (
            "The analysis page could not query PostgreSQL. Confirm that the database "
            "is running and your PGHOST, PGPORT, PGDATABASE, PGUSER, and PGPASSWORD "
            "environment variables are set."
        )
        app.logger.exception("Database query failed", exc_info=exc)

    return render_template(
        "index.html",
        analyses=analyses,
        status=status,
        error=error,
        pull_running=pull_running,
        pull_status=pull_status,
        updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


@app.post("/update-analysis")
def update_analysis():
    # This route deliberately does not scrape. It only causes the ORM analyses
    # to be queried again from PostgreSQL on the redirected GET request.
    if _pull_is_running():
        message = (
            "Analysis refreshed from PostgreSQL. Pull Data is still retrieving new "
            "GradCafe records in the background."
        )
    else:
        message = "Analysis refreshed from PostgreSQL."
    return redirect(url_for("index", status=message))


@app.post("/pull-data")
def pull_data():
    """Start Module 2 scraping in the background, but never start it twice."""
    global _pull_process

    with _pull_guard:
        process_running = _pull_process is not None and _pull_process.poll() is None
        lock_running = PULL_LOCK_FILE.exists()
        if process_running or lock_running:
            return redirect(
                url_for(
                    "index",
                    status=(
                        "Pull Data is already running. No second scraping process was started."
                    ),
                )
            )

        try:
            _start_pull_process()
        except OSError as exc:
            app.logger.exception("Could not start Pull Data", exc_info=exc)
            return redirect(
                url_for(
                    "index",
                    status=(
                        "Pull Data could not be started. Check pull_data.log and confirm "
                        "that Python can launch the scraper."
                    ),
                )
            )

    return redirect(
        url_for(
            "index",
            status=(
                "Pull Data started in the background. You can use Update Analysis while it runs."
            ),
        )
    )


if __name__ == "__main__":
    # Disabling the debug reloader keeps a single Flask process responsible for
    # the background scraper state while still showing normal development errors.
    app.run(debug=True, use_reloader=False)
