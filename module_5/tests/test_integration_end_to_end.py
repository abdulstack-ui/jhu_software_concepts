"""Checkpoint 04 end-to-end tests for the Module 4 Flask data flow."""

from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from app import create_app
from load_data import (
    count_database_rows,
    create_applicants_table,
    load_records_into_connection,
)


def _database_analysis_provider(connection, schema):
    """Return a deterministic analysis provider backed by the test database."""

    def provider():
        count = count_database_rows(connection, schema=schema)
        return [
            {
                "number": 1,
                "question": "How many applicant rows are currently loaded?",
                "result": str(count),
                "explanation": "Counted from the isolated PostgreSQL test schema.",
            }
        ]

    return provider


def _database_loader(connection, schema):
    """Return a loader that writes fake scraper rows to the test schema."""

    def loader(rows):
        return load_records_into_connection(connection, rows, schema=schema)

    return loader


@pytest.mark.integration
def test_fake_scrape_pull_update_and_render_end_to_end(
    postgres_test_schema, sample_db_rows
):
    """Fake scrape -> real DB load -> update -> rendered analysis page."""

    connection, schema = postgres_test_schema
    create_applicants_table(connection, schema=schema)

    scraper_calls = {"count": 0}

    def fake_scraper():
        scraper_calls["count"] += 1
        return sample_db_rows

    app = create_app(
        {"TESTING": True},
        analysis_provider=_database_analysis_provider(connection, schema),
        busy_checker=lambda: False,
        status_reader=lambda: None,
        scraper=fake_scraper,
        loader=_database_loader(connection, schema),
    )
    client = app.test_client()

    assert count_database_rows(connection, schema=schema) == 0

    pull_response = client.post("/pull-data")
    assert pull_response.status_code == 200
    assert pull_response.get_json() == {
        "ok": True,
        "busy": False,
        "rows": len(sample_db_rows),
    }
    assert scraper_calls["count"] == 1
    assert count_database_rows(connection, schema=schema) == len(sample_db_rows)

    update_response = client.post("/update-analysis")
    assert update_response.status_code == 200
    assert update_response.get_json() == {
        "ok": True,
        "busy": False,
        "analysis_count": 1,
    }

    page_response = client.get("/analysis")
    assert page_response.status_code == 200
    soup = BeautifulSoup(page_response.data, "html.parser")
    card = soup.select_one('[data-testid="analysis-card"]')
    assert card is not None
    assert "How many applicant rows are currently loaded?" in card.get_text(" ", strip=True)
    assert f"Answer: {len(sample_db_rows)}" in card.get_text(" ", strip=True)


@pytest.mark.integration
def test_overlapping_pull_requests_are_rejected_and_database_stays_consistent(
    postgres_test_schema, sample_db_rows
):
    """Observable busy state rejects overlap without duplicate/partial DB writes."""

    connection, schema = postgres_test_schema
    create_applicants_table(connection, schema=schema)

    busy = {"value": True}
    calls = {"scraper": 0, "loader": 0}

    def fake_scraper():
        calls["scraper"] += 1
        return sample_db_rows

    def loader(rows):
        calls["loader"] += 1
        return load_records_into_connection(connection, rows, schema=schema)

    app = create_app(
        {"TESTING": True},
        analysis_provider=_database_analysis_provider(connection, schema),
        busy_checker=lambda: busy["value"],
        status_reader=lambda: None,
        scraper=fake_scraper,
        loader=loader,
    )
    client = app.test_client()

    # Simulate a request arriving while another pull owns the busy state.
    blocked_first = client.post("/pull-data")
    assert blocked_first.status_code == 409
    assert blocked_first.get_json() == {"ok": False, "busy": True}
    assert count_database_rows(connection, schema=schema) == 0
    assert calls == {"scraper": 0, "loader": 0}

    # Once idle, the pull succeeds and writes the complete fake batch.
    busy["value"] = False
    accepted = client.post("/pull-data")
    assert accepted.status_code == 200
    assert count_database_rows(connection, schema=schema) == len(sample_db_rows)
    assert calls == {"scraper": 1, "loader": 1}

    # Another overlapping request is rejected and cannot alter the database.
    busy["value"] = True
    blocked_second = client.post("/pull-data")
    assert blocked_second.status_code == 409
    assert count_database_rows(connection, schema=schema) == len(sample_db_rows)
    assert calls == {"scraper": 1, "loader": 1}

    # A later ordinary retry is idempotent by p_id.
    busy["value"] = False
    retry = client.post("/pull-data")
    assert retry.status_code == 200
    assert count_database_rows(connection, schema=schema) == len(sample_db_rows)
    assert calls == {"scraper": 2, "loader": 2}
