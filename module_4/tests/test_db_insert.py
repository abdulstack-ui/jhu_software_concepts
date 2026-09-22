"""Checkpoint 03 PostgreSQL schema, insert, idempotency, and query tests."""

from __future__ import annotations

import pytest

from app import create_app
from load_data import (
    EXPECTED_FIELD_NAMES,
    count_database_rows,
    create_applicants_table,
    load_records_into_connection,
)
from query_data import fetch_applicant_dict


def _db_backed_app(connection, schema, rows, sample_analyses):
    def loader(scraped_rows):
        return load_records_into_connection(connection, scraped_rows, schema=schema)

    return create_app(
        {"TESTING": True},
        analysis_provider=lambda: sample_analyses,
        busy_checker=lambda: False,
        status_reader=lambda: None,
        scraper=lambda: rows,
        loader=loader,
    )


@pytest.mark.db
def test_pull_data_inserts_rows_into_real_postgresql(
    postgres_test_schema, sample_db_rows, sample_analyses
):
    connection, schema = postgres_test_schema
    create_applicants_table(connection, schema=schema)
    assert count_database_rows(connection, schema=schema) == 0

    app = _db_backed_app(connection, schema, sample_db_rows, sample_analyses)
    response = app.test_client().post("/pull-data")

    assert response.status_code == 200
    assert response.get_json() == {"ok": True, "busy": False, "rows": 2}
    assert count_database_rows(connection, schema=schema) == 2

    inserted = fetch_applicant_dict(connection, 990001, schema=schema)
    assert inserted is not None
    for required in ("p_id", "program", "date_added", "url", "status"):
        assert inserted[required] is not None


@pytest.mark.db
def test_duplicate_pull_is_idempotent(
    postgres_test_schema, sample_db_rows, sample_analyses
):
    connection, schema = postgres_test_schema
    app = _db_backed_app(connection, schema, sample_db_rows, sample_analyses)
    client = app.test_client()

    first = client.post("/pull-data")
    second = client.post("/pull-data")

    assert first.status_code == 200
    assert second.status_code == 200
    assert count_database_rows(connection, schema=schema) == len(sample_db_rows)


@pytest.mark.db
def test_simple_query_returns_required_module3_keys(postgres_test_schema, sample_db_rows):
    connection, schema = postgres_test_schema
    load_records_into_connection(connection, sample_db_rows, schema=schema)

    applicant = fetch_applicant_dict(connection, 990002, schema=schema)

    assert applicant is not None
    assert tuple(applicant.keys()) == EXPECTED_FIELD_NAMES
    assert applicant["p_id"] == 990002
    assert applicant["program"] == "Johns Hopkins University | Computer Science"
    assert applicant["status"] == "Rejected"
