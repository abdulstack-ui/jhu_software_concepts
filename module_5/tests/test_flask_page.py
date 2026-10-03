"""Checkpoint 01 tests for Flask app creation and page rendering."""

from __future__ import annotations

import pytest
from bs4 import BeautifulSoup


@pytest.mark.web
def test_app_factory_exposes_required_routes(app):
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/analysis" in rules
    assert "/pull-data" in rules
    assert "/update-analysis" in rules
    assert app.config["TESTING"] is True
    assert app.config["DATABASE_URL"].startswith("postgresql+psycopg://")


@pytest.mark.web
def test_get_analysis_renders_required_components(client):
    response = client.get("/analysis")
    assert response.status_code == 200

    soup = BeautifulSoup(response.data, "html.parser")
    text = soup.get_text(" ", strip=True)

    assert "Analysis" in text
    assert "Answer:" in text
    assert soup.select_one('[data-testid="pull-data-btn"]') is not None
    assert soup.select_one('[data-testid="update-analysis-btn"]') is not None
    assert soup.select_one('[data-testid="analysis-card"]') is not None


@pytest.mark.web
def test_root_redirects_to_analysis(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/analysis")
