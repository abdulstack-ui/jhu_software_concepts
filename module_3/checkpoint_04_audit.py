"""Checkpoint 04 audit for the SQLAlchemy ORM portion of Module 3."""

from __future__ import annotations

import inspect as pyinspect
import re

import sqlalchemy
from sqlalchemy import inspect, select, func

import models
import orm_queries
from models import Applicant, SessionLocal, engine


EXPECTED_COLUMNS = (
    "p_id",
    "program",
    "comments",
    "date_added",
    "url",
    "status",
    "term",
    "us_or_international",
    "gpa",
    "gre",
    "gre_v",
    "gre_aw",
    "degree",
    "llm_generated_program",
    "llm_generated_university",
)


def static_audit() -> None:
    assert sqlalchemy.__version__.startswith("2."), (
        f"SQLAlchemy 2.x required, found {sqlalchemy.__version__}"
    )

    assert Applicant.__tablename__ == "applicants"
    assert tuple(Applicant.__table__.columns.keys()) == EXPECTED_COLUMNS
    assert tuple(column.name for column in Applicant.__table__.primary_key.columns) == (
        "p_id",
    )

    model_source = pyinspect.getsource(models)
    orm_source = pyinspect.getsource(orm_queries)

    assert "create_all" not in model_source, "models.py must not create a second table"
    assert "create_all" not in orm_source, "orm_queries.py must not create tables"
    assert not re.search(r"^\s*(?:from\s+psycopg|import\s+psycopg)", orm_source, re.MULTILINE), (
        "orm_queries.py must use SQLAlchemy ORM rather than importing psycopg"
    )
    assert ".cursor(" not in orm_source, "orm_queries.py must not use raw DB cursors"
    assert "text(" not in orm_source, "orm_queries.py must not bypass ORM with text()"
    assert not re.search(r"['\"]\s*SELECT\s", orm_source, re.IGNORECASE), (
        "orm_queries.py should not contain handwritten SELECT statements"
    )

    required_functions = (
        "question_1",
        "question_4",
        "question_5",
        "question_8",
        "question_9",
        "question_10",
    )
    for name in required_functions:
        assert callable(getattr(orm_queries, name, None)), f"Missing ORM function: {name}"

    print("CHECKPOINT 04 STATIC ORM AUDIT: PASS")
    print(f"SQLAlchemy version: {sqlalchemy.__version__}")
    print("Applicant model columns: 15 / 15")
    print("Primary key: p_id")
    print("No create_all(), raw psycopg cursor, text(), or handwritten SELECT is used.")


def live_audit() -> None:
    db_inspector = inspect(engine)
    actual_columns = tuple(
        column["name"] for column in db_inspector.get_columns("applicants", schema="public")
    )
    assert actual_columns == EXPECTED_COLUMNS, (
        f"Existing applicants schema mismatch: {actual_columns!r}"
    )

    pk = tuple(
        db_inspector.get_pk_constraint("applicants", schema="public").get(
            "constrained_columns"
        )
        or ()
    )
    assert pk == ("p_id",), f"Expected p_id primary key, found {pk!r}"

    with SessionLocal() as session:
        row_count = int(
            session.scalar(select(func.count()).select_from(Applicant)) or 0
        )
        results = orm_queries.run_orm_analysis(session)

    assert row_count == 30011, f"Expected checkpoint dataset of 30,011 rows, found {row_count:,}"
    assert results[1] == 29534, results
    assert results[4] is not None and round(results[4], 2) == 3.78, results
    assert results[5] is not None and round(results[5], 2) == 43.88, results
    assert results[8] == 25, results
    assert results[9] == (25, 25, 0), results
    assert results[10] is not None and round(results[10], 2) == 36.36, results

    print("CHECKPOINT 04 LIVE ORM AUDIT: PASS")
    print(f"Database rows analyzed through ORM: {row_count:,}")
    print("Q1 parity: 29,534")
    print("Q4 parity: 3.78")
    print("Q5 parity: 43.88%")
    print("Q8 parity: 25")
    print("Q9 parity: original=25; LLM=25; difference=+0")
    print("Q10 parity: 36.36%")


def main() -> None:
    static_audit()
    live_audit()


if __name__ == "__main__":
    main()
