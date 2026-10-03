"""Security tests for SQL parameterization and query limits."""

from typing import Any

from query_data import (
    MAX_QUERY_LIMIT,
    MIN_QUERY_LIMIT,
    clamp_limit,
    search_applicants,
)


class FakeCursor:
    """Capture SQL execution without requiring PostgreSQL."""

    def __init__(self):
        self.statement = None
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, statement: Any, params: tuple[Any, ...]):
        self.statement = statement
        self.params = params

    def fetchall(self):
        return []


class FakeConnection:
    """Provide one capturing cursor."""

    def __init__(self):
        self.cursor_instance = FakeCursor()

    def cursor(self):
        return self.cursor_instance


def test_clamp_limit_validates_and_bounds_input():
    """Limits must always remain inside the allowed range."""
    assert clamp_limit(-50) == MIN_QUERY_LIMIT
    assert clamp_limit(5000) == MAX_QUERY_LIMIT
    assert clamp_limit("20") == 20
    assert clamp_limit("1; DROP TABLE applicants; --") == 25


def test_malicious_search_input_remains_parameterized():
    """SQL injection payloads must never become SQL syntax."""
    connection = FakeConnection()
    payload = "' OR 1=1 --"

    result = search_applicants(connection, payload, 9999)

    assert result == []
    pattern = "".join(("%", payload, "%"))
    assert connection.cursor_instance.params == (pattern, pattern, MAX_QUERY_LIMIT)
    assert payload not in str(connection.cursor_instance.statement)


def test_destructive_payload_remains_parameterized():
    """Destructive-looking text must remain an ordinary parameter value."""
    connection = FakeConnection()
    payload = "; DROP TABLE applicants; --"

    search_applicants(connection, payload, "10")

    pattern = "".join(("%", payload, "%"))
    assert connection.cursor_instance.params == (pattern, pattern, 10)
    assert payload not in str(connection.cursor_instance.statement)
