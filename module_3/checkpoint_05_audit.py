"""Static and live checks for Checkpoint 05: dynamic Flask analysis page."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, select

from app import app
from models import Applicant, SessionLocal
from orm_queries import run_web_analysis


ROOT = Path(__file__).resolve().parent


def static_audit() -> None:
    required = [
        ROOT / "app.py",
        ROOT / "templates" / "index.html",
        ROOT / "static" / "styles.css",
        ROOT / "models.py",
        ROOT / "orm_queries.py",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    assert not missing, f"Missing required Flask files: {missing}"

    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    template = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")

    assert "SessionLocal" in app_source and "run_web_analysis" in app_source
    assert "psycopg" not in app_source.lower()
    assert "SELECT " not in app_source.upper()
    assert "Update Analysis" in template
    assert "analysis-grid" in template
    assert len(css.strip()) > 500

    print("CHECKPOINT 05 STATIC FLASK AUDIT: PASS")
    print("Flask reads are routed through SQLAlchemy SessionLocal/run_web_analysis.")
    print("Template and CSS assets are present and non-trivial.")


def live_audit() -> None:
    with SessionLocal() as session:
        row_count = int(session.scalar(select(func.count()).select_from(Applicant)) or 0)
        analyses = run_web_analysis(session)

    assert row_count > 0
    assert len(analyses) == 11
    assert [item["number"] for item in analyses] == list(range(1, 12))

    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "GradCafe Application Analysis" in page
    assert "Q1" in page and "Q11" in page
    assert analyses[0]["result"] in page
    assert analyses[-1]["result"] in page

    refreshed = client.post("/update-analysis", follow_redirects=True)
    assert refreshed.status_code == 200
    refreshed_page = refreshed.get_data(as_text=True)
    assert "Analysis refreshed from PostgreSQL." in refreshed_page

    print("CHECKPOINT 05 LIVE FLASK AUDIT: PASS")
    print(f"Database rows queried through ORM: {row_count:,}")
    print("Dynamic analyses rendered: 11 / 11")
    print("GET / and POST /update-analysis both returned HTTP 200.")


def main() -> None:
    static_audit()
    live_audit()


if __name__ == "__main__":
    main()
