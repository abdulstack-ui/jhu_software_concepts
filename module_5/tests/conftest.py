"""Shared deterministic fixtures for Module 4 tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app import create_app  # noqa: E402


@pytest.fixture
def sample_analyses():
    return [
        {
            "number": 1,
            "question": "How many applicants are for Fall 2026?",
            "result": "123",
            "explanation": "A deterministic test result.",
        },
        {
            "number": 2,
            "question": "What percentage are international?",
            "result": "39.28%",
            "explanation": "A deterministic two-decimal percentage.",
        },
    ]


@pytest.fixture
def app(sample_analyses):
    return create_app(
        {"TESTING": True, "DATABASE_URL": "postgresql+psycopg://test:test@localhost/test"},
        analysis_provider=lambda: sample_analyses,
        busy_checker=lambda: False,
        status_reader=lambda: None,
        pull_starter=lambda: None,
    )


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sample_db_rows():
    """Two complete, deterministic rows matching the Module 3 schema."""

    return [
        {
            "p_id": 990001,
            "program": "Massachusetts Institute of Technology | Computer Science",
            "comments": "Checkpoint 03 fixture",
            "date_added": "2026-09-20",
            "url": "https://www.thegradcafe.com/result/990001",
            "status": "Accepted",
            "term": "Fall 2026",
            "us_or_international": "International",
            "gpa": 3.91,
            "gre": 168.0,
            "gre_v": 162.0,
            "gre_aw": 4.5,
            "degree": "PhD",
            "llm_generated_program": "Computer Science",
            "llm_generated_university": "Massachusetts Institute of Technology",
        },
        {
            "p_id": 990002,
            "program": "Johns Hopkins University | Computer Science",
            "comments": None,
            "date_added": "2026-09-21",
            "url": "https://www.thegradcafe.com/result/990002",
            "status": "Rejected",
            "term": "Fall 2026",
            "us_or_international": "American",
            "gpa": 3.72,
            "gre": None,
            "gre_v": None,
            "gre_aw": None,
            "degree": "Masters",
            "llm_generated_program": "Computer Science",
            "llm_generated_university": "Johns Hopkins University",
        },
    ]


@pytest.fixture
def postgres_test_schema():
    """Yield a real PostgreSQL connection plus an isolated disposable schema."""

    import os
    from uuid import uuid4

    from psycopg import sql

    from load_data import DatabaseConnectionError, connect_database

    database_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    try:
        connection = connect_database(database_url)
    except DatabaseConnectionError as exc:
        pytest.fail(
            "PostgreSQL is required for Module 4 DB tests. Set TEST_DATABASE_URL / "
            "DATABASE_URL or the PGHOST, PGPORT, PGDATABASE, PGUSER and PGPASSWORD "
            f"environment variables. Original error: {exc}"
        )

    connection.autocommit = True
    schema = f"module4_test_{uuid4().hex[:12]}"
    with connection.cursor() as cursor:
        cursor.execute(sql.SQL("CREATE SCHEMA {};").format(sql.Identifier(schema)))

    try:
        yield connection, schema
    finally:
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE;").format(sql.Identifier(schema))
            )
        connection.close()
