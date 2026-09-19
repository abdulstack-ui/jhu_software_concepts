"""Flask analysis page for the Module 3 GradCafe PostgreSQL database."""

from __future__ import annotations

from datetime import datetime

from flask import Flask, redirect, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError

from models import SessionLocal
from orm_queries import run_web_analysis

app = Flask(__name__)


def _query_analysis():
    with SessionLocal() as session:
        return run_web_analysis(session)


@app.get("/")
def index():
    status = request.args.get("status")
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
        updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


@app.post("/update-analysis")
def update_analysis():
    # This route deliberately does not scrape. It simply redirects to the page,
    # causing all eleven ORM analyses to be queried again from PostgreSQL.
    return redirect(url_for("index", status="Analysis refreshed from PostgreSQL."))


if __name__ == "__main__":
    app.run(debug=True)
