"""Checkpoint 02 tests for button endpoints and deterministic busy-state behavior."""

from __future__ import annotations

import pytest

from app import create_app


@pytest.mark.buttons
def test_pull_data_runs_fake_scraper_and_passes_rows_to_loader(sample_analyses):
    fake_rows = [
        {"p_id": 101, "program": "Computer Science"},
        {"p_id": 102, "program": "Applied Mathematics"},
    ]
    observed: dict[str, object] = {"scraper_calls": 0, "loaded_rows": None}

    def fake_scraper():
        observed["scraper_calls"] = int(observed["scraper_calls"]) + 1
        return fake_rows

    def fake_loader(rows):
        observed["loaded_rows"] = rows

    app = create_app(
        {"TESTING": True, "DATABASE_URL": "postgresql+psycopg://test:test@localhost/test"},
        analysis_provider=lambda: sample_analyses,
        busy_checker=lambda: False,
        status_reader=lambda: None,
        scraper=fake_scraper,
        loader=fake_loader,
    )

    response = app.test_client().post("/pull-data")

    assert response.status_code == 200
    assert response.get_json() == {"ok": True, "busy": False, "rows": 2}
    assert observed["scraper_calls"] == 1
    assert observed["loaded_rows"] == fake_rows


@pytest.mark.buttons
def test_update_analysis_returns_200_and_refreshes_when_idle(sample_analyses):
    calls = {"analysis": 0}

    def fake_analysis():
        calls["analysis"] += 1
        return sample_analyses

    app = create_app(
        {"TESTING": True, "DATABASE_URL": "postgresql+psycopg://test:test@localhost/test"},
        analysis_provider=fake_analysis,
        busy_checker=lambda: False,
        status_reader=lambda: None,
        pull_starter=lambda: None,
    )

    response = app.test_client().post("/update-analysis")

    assert response.status_code == 200
    assert response.get_json() == {"ok": True, "busy": False, "analysis_count": 2}
    assert calls["analysis"] == 1


@pytest.mark.buttons
def test_update_analysis_busy_returns_409_and_performs_no_update(sample_analyses):
    calls = {"analysis": 0}

    def fake_analysis():
        calls["analysis"] += 1
        return sample_analyses

    app = create_app(
        {"TESTING": True, "DATABASE_URL": "postgresql+psycopg://test:test@localhost/test"},
        analysis_provider=fake_analysis,
        busy_checker=lambda: True,
        status_reader=lambda: None,
        pull_starter=lambda: None,
    )

    response = app.test_client().post("/update-analysis")

    assert response.status_code == 409
    assert response.get_json() == {"ok": False, "busy": True}
    assert calls["analysis"] == 0


@pytest.mark.buttons
def test_pull_data_busy_returns_409_without_scraping_or_loading(sample_analyses):
    calls = {"scraper": 0, "loader": 0}

    def fake_scraper():
        calls["scraper"] += 1
        return [{"p_id": 1}]

    def fake_loader(rows):
        calls["loader"] += 1

    app = create_app(
        {"TESTING": True, "DATABASE_URL": "postgresql+psycopg://test:test@localhost/test"},
        analysis_provider=lambda: sample_analyses,
        busy_checker=lambda: True,
        status_reader=lambda: None,
        scraper=fake_scraper,
        loader=fake_loader,
    )

    response = app.test_client().post("/pull-data")

    assert response.status_code == 409
    assert response.get_json() == {"ok": False, "busy": True}
    assert calls == {"scraper": 0, "loader": 0}


@pytest.mark.buttons
def test_loader_failure_returns_non_200_without_second_attempt(sample_analyses):
    calls = {"loader": 0}
    fake_rows = [{"p_id": 501, "program": "Physics"}]

    def fake_loader(rows):
        calls["loader"] += 1
        assert rows == fake_rows
        raise RuntimeError("simulated loader failure")

    app = create_app(
        {"TESTING": True, "DATABASE_URL": "postgresql+psycopg://test:test@localhost/test"},
        analysis_provider=lambda: sample_analyses,
        busy_checker=lambda: False,
        status_reader=lambda: None,
        scraper=lambda: fake_rows,
        loader=fake_loader,
    )

    response = app.test_client().post("/pull-data")

    assert response.status_code == 500
    assert response.get_json() == {"ok": False, "busy": False, "error": "pull data failed"}
    assert calls["loader"] == 1
