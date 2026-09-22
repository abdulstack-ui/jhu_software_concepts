"""Flask application for the GradCafe analytics service.

Module 4 exposes :func:`create_app` so tests can construct an isolated Flask
application and inject deterministic analysis, busy-state, scraper, and loader
functions without using the network or requiring a live PostgreSQL connection.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable

from flask import Flask, current_app, jsonify, redirect, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError

from models import make_session_factory
from orm_queries import run_web_analysis

ROOT = Path(__file__).resolve().parent
PULL_SCRIPT = ROOT / "pull_data.py"
PULL_STATUS_FILE = ROOT / "pull_data_status.json"
PULL_LOCK_FILE = ROOT / "pull_data.lock"
PULL_LOG_FILE = ROOT / "pull_data.log"

_pull_guard = threading.Lock()
_pull_process: subprocess.Popen[Any] | None = None

AnalysisProvider = Callable[[], list[dict[str, Any]]]
BusyChecker = Callable[[], bool]
StatusReader = Callable[[], dict[str, Any] | None]
PullStarter = Callable[[], None]
Scraper = Callable[[], Iterable[dict[str, Any]]]
Loader = Callable[[list[dict[str, Any]]], Any]


def _read_pull_status() -> dict[str, Any] | None:
    """Read the background Pull Data status file when one exists."""

    if not PULL_STATUS_FILE.exists():
        return None
    try:
        payload = json.loads(PULL_STATUS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _pull_is_running() -> bool:
    """Return ``True`` while this app's Pull Data worker or lock is active."""

    global _pull_process
    with _pull_guard:
        if _pull_process is not None:
            if _pull_process.poll() is None:
                return True
            _pull_process = None
    return PULL_LOCK_FILE.exists()


def _start_pull_process() -> None:
    """Start one background Pull Data worker without blocking Flask."""

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
        # The child keeps its duplicated handle; Flask does not need one.
        log_handle.close()


def _default_analysis_provider(database_url: str | None) -> AnalysisProvider:
    """Build the normal PostgreSQL-backed analysis callable."""

    session_factory = make_session_factory(database_url)

    def query_analysis() -> list[dict[str, Any]]:
        with session_factory() as session:
            return run_web_analysis(session)

    return query_analysis


def create_app(
    config: dict[str, Any] | None = None,
    *,
    analysis_provider: AnalysisProvider | None = None,
    busy_checker: BusyChecker | None = None,
    status_reader: StatusReader | None = None,
    pull_starter: PullStarter | None = None,
    scraper: Scraper | None = None,
    loader: Loader | None = None,
) -> Flask:
    """Create and configure a testable GradCafe Flask application.

    ``analysis_provider``, ``busy_checker``, ``status_reader`` and
    ``pull_starter`` preserve the Module 3 production behaviour while allowing
    deterministic Flask tests.  Module 4 button tests may additionally inject
    both ``scraper`` and ``loader``.  When those two test doubles are supplied,
    ``POST /pull-data`` runs them synchronously and passes the scraper rows
    directly to the loader, avoiding live internet access.
    """

    if (scraper is None) != (loader is None):
        raise ValueError("scraper and loader must be supplied together")

    flask_app = Flask(__name__)
    flask_app.config.from_mapping(
        DATABASE_URL=os.getenv("DATABASE_URL"),
        TESTING=False,
    )
    if config:
        flask_app.config.update(config)

    analysis_fn = analysis_provider or _default_analysis_provider(
        flask_app.config.get("DATABASE_URL")
    )
    busy_fn = busy_checker or _pull_is_running
    status_fn = status_reader or _read_pull_status
    start_pull_fn = pull_starter or _start_pull_process

    # Make dependencies observable for tests and later extension.
    flask_app.extensions["gradcafe_services"] = {
        "analysis_provider": analysis_fn,
        "busy_checker": busy_fn,
        "status_reader": status_fn,
        "pull_starter": start_pull_fn,
        "scraper": scraper,
        "loader": loader,
    }

    @flask_app.get("/")
    def home():
        """Keep the Module 3 root URL working while making /analysis canonical."""

        return redirect(url_for("analysis"))

    @flask_app.get("/analysis")
    def analysis():
        """Render the current database analysis and Pull Data state."""

        status = request.args.get("status")
        pull_running = busy_fn()
        pull_status = status_fn()

        try:
            analyses = analysis_fn()
            error = None
        except SQLAlchemyError as exc:
            analyses = []
            error = (
                "The analysis page could not query PostgreSQL. Confirm that the database "
                "is running and DATABASE_URL (or the PG* environment variables) is set."
            )
            current_app.logger.exception("Database query failed", exc_info=exc)

        return render_template(
            "index.html",
            analyses=analyses,
            status=status,
            error=error,
            pull_running=pull_running,
            pull_status=pull_status,
            updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    @flask_app.post("/update-analysis")
    def update_analysis():
        """Refresh analysis when idle and reject the request while Pull Data is busy."""

        if busy_fn():
            return jsonify(ok=False, busy=True), 409

        try:
            analyses = analysis_fn()
        except SQLAlchemyError as exc:
            current_app.logger.exception("Analysis refresh failed", exc_info=exc)
            return jsonify(ok=False, busy=False, error="analysis query failed"), 500

        return jsonify(ok=True, busy=False, analysis_count=len(analyses)), 200

    @flask_app.post("/pull-data")
    def pull_data():
        """Run an injected fake pull in tests or start the production background worker."""

        if busy_fn():
            return jsonify(ok=False, busy=True), 409

        # Deterministic test mode: fake scraper rows are passed directly to the
        # fake loader, which lets the test prove the endpoint's orchestration
        # without touching GradCafe or a real PostgreSQL database.
        if scraper is not None and loader is not None:
            try:
                rows = list(scraper())
                loader(rows)
            except Exception as exc:  # endpoint boundary intentionally catches service failures
                current_app.logger.exception("Injected Pull Data service failed", exc_info=exc)
                return jsonify(ok=False, busy=False, error="pull data failed"), 500
            return jsonify(ok=True, busy=False, rows=len(rows)), 200

        try:
            start_pull_fn()
        except OSError as exc:
            current_app.logger.exception("Could not start Pull Data", exc_info=exc)
            return jsonify(ok=False, busy=False, error="pull data could not start"), 500

        return jsonify(ok=True, busy=False, background=True), 202

    return flask_app


app = create_app()


if __name__ == "__main__":  # pragma: no cover - development server entry point
    # One process owns the background worker state; no debug reloader duplicate.
    app.run(debug=True, use_reloader=False)
