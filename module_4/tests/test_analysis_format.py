"""Checkpoint 03 analysis labels and percentage formatting tests."""

from __future__ import annotations

import re

import pytest
from bs4 import BeautifulSoup

from orm_queries import _format_percentage


@pytest.mark.analysis
def test_each_rendered_analysis_card_has_answer_label(client):
    response = client.get("/analysis")
    assert response.status_code == 200

    soup = BeautifulSoup(response.data, "html.parser")
    cards = soup.select('[data-testid="analysis-card"]')
    assert cards
    for card in cards:
        result = card.select_one("p.result")
        assert result is not None
        assert result.get_text(" ", strip=True).startswith("Answer:")


@pytest.mark.analysis
def test_rendered_percentages_have_exactly_two_decimal_places(client):
    response = client.get("/analysis")
    text = BeautifulSoup(response.data, "html.parser").get_text(" ", strip=True)

    percentage_tokens = re.findall(r"\d+(?:\.\d+)?%", text)
    assert percentage_tokens
    assert all(re.fullmatch(r"\d+\.\d{2}%", token) for token in percentage_tokens)


@pytest.mark.analysis
def test_percentage_formatter_is_stable_to_two_decimals():
    assert _format_percentage(39.284) == "39.28%"
    assert _format_percentage(0.0) == "0.00%"
    assert _format_percentage(None) == "N/A"
