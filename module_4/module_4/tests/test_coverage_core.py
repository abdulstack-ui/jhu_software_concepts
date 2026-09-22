"""Focused unit tests that cover the remaining deterministic source helpers."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import SQLAlchemyError

pytestmark = pytest.mark.analysis

import app as app_module
import clean
import load_data
import models
import orm_queries
import query_data


def _raw_record(result_id: int = 123456) -> dict:
    return {
        "entry_url": f"https://www.thegradcafe.com/result/{result_id}",
        "university": " Example University ",
        "raw_program_text": " Computer Science PhD ",
        "program_name": "Computer Science",
        "comments": "  hello &amp; goodbye  ",
        "date_added": "Sep 20, 2026",
        "applicant_status": "Accepted",
        "program_start": "Fall 2026",
        "student_type": "International",
        "gpa": "3.90",
        "gre_score": "168",
        "gre_verbal": "160",
        "gre_aw": "4.5",
        "degree": "PhD",
        "llm-generated-program": "Computer Science",
        "llm-generated-university": "Example University",
    }


def _clean_record(result_id: int = 123456) -> dict:
    return clean.clean_record(_raw_record(result_id))


class DummyCursor:
    def __init__(self, *, fetchone=None, fetchalls=None):
        self.fetchone_value = fetchone
        self.fetchalls = list(fetchalls or [])
        self.executed = []
        self.executemany_calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, *args):
        self.executed.append(args)

    def executemany(self, *args):
        self.executemany_calls.append(args)

    def fetchone(self):
        return self.fetchone_value

    def fetchall(self):
        return self.fetchalls.pop(0) if self.fetchalls else []


class DummyConnection:
    def __init__(self, cursors):
        self.cursors = list(cursors)

    def cursor(self):
        if len(self.cursors) == 1:
            return self.cursors[0]
        return self.cursors.pop(0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


# ---------------------------------------------------------------------------
# clean.py
# ---------------------------------------------------------------------------

def test_clean_text_numeric_date_and_identifier_helpers():
    assert clean._clean_text(None) is None
    assert clean._clean_text("  A &amp;   B ") == "A & B"
    assert clean._clean_text(" N/A ") is None

    assert clean._to_float(None, field_name="x") is None
    assert clean._to_float(3, field_name="x") == 3.0
    assert clean._to_float("1,234.5", field_name="x") == 1234.5
    assert clean._to_float(" - ", field_name="x") is None
    with pytest.raises(ValueError):
        clean._to_float("three", field_name="x")

    assert clean._to_gre_quantitative(None) is None
    assert clean._to_gre_quantitative("168") == 168.0
    assert clean._to_gre_quantitative("320") is None

    assert clean._to_iso_date(None) is None
    assert clean._to_iso_date("Sep 20, 2026") == "2026-09-20"
    assert clean._to_iso_date("September 20, 2026") == "2026-09-20"
    assert clean._to_iso_date("2026-09-20") == "2026-09-20"
    with pytest.raises(ValueError):
        clean._to_iso_date("20/09/2026")

    with pytest.raises(ValueError):
        clean._result_id(None)
    with pytest.raises(ValueError):
        clean._result_id("https://example.com/no-result")
    assert clean._result_id("https://www.thegradcafe.com/result/42?x=1") == 42


def test_clean_program_mapping_and_full_record():
    assert clean._original_program({"university": "U", "program_name": "P"}) == "U | P"
    assert clean._original_program({"university": "U"}) == "U"
    assert clean._original_program({"program_name": "P"}) == "P"

    result = clean.clean_record(_raw_record())
    assert result["p_id"] == 123456
    assert result["comments"] == "hello & goodbye"
    assert tuple(result) == clean.OUTPUT_FIELDS


def test_validate_cleaned_records_all_error_paths():
    valid = _clean_record(1001)
    clean.validate_cleaned_records([valid])

    wrong_schema = dict(valid)
    wrong_schema.pop("comments")
    wrong_schema["extra"] = 1
    with pytest.raises(ValueError, match="wrong schema"):
        clean.validate_cleaned_records([wrong_schema])

    bad = dict(valid, p_id="1001")
    with pytest.raises(ValueError, match="not an integer"):
        clean.validate_cleaned_records([bad])

    with pytest.raises(ValueError, match="Duplicate p_id"):
        clean.validate_cleaned_records([valid, dict(valid)])

    for field, message in [
        ("url", "missing url"),
        ("program", "missing program"),
        ("date_added", "missing date_added"),
        ("status", "missing status"),
    ]:
        bad = dict(valid)
        bad[field] = None
        with pytest.raises(ValueError, match=message):
            clean.validate_cleaned_records([bad])

    other = _clean_record(1002)
    other["url"] = valid["url"]
    with pytest.raises(ValueError, match="Duplicate url"):
        clean.validate_cleaned_records([valid, other])


def test_clean_data_json_io(tmp_path):
    records = clean.clean_data([_raw_record(2001)])
    assert records[0]["p_id"] == 2001

    source = tmp_path / "source.json"
    source.write_text(json.dumps([{"x": 1}]), encoding="utf-8")
    assert clean.load_json(source) == [{"x": 1}]

    source.write_text(json.dumps({"x": 1}), encoding="utf-8")
    with pytest.raises(ValueError, match="top-level JSON array"):
        clean.load_json(source)

    output = tmp_path / "output.json"
    clean.save_json(records, output)
    assert json.loads(output.read_text(encoding="utf-8"))[0]["p_id"] == 2001


# ---------------------------------------------------------------------------
# models.py and app.py
# ---------------------------------------------------------------------------

def test_model_database_url_explicit_and_session_factory(monkeypatch):
    url = models._database_url("postgresql://user:pass@localhost/db")
    assert url.drivername == "postgresql+psycopg"
    sqlite_url = models._database_url("sqlite:///:memory:")
    assert sqlite_url.drivername == "sqlite"

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("PGHOST", "localhost")
    monkeypatch.setenv("PGPORT", "5432")
    monkeypatch.setenv("PGDATABASE", "gradcafe")
    monkeypatch.setenv("PGUSER", "postgres")
    monkeypatch.setenv("PGPASSWORD", "secret")
    fallback_url = models._database_url()
    assert fallback_url.drivername == "postgresql+psycopg"
    assert fallback_url.port == 5432

    captured = {}

    def fake_create_engine(url, pool_pre_ping):
        captured["url"] = url
        captured["pool_pre_ping"] = pool_pre_ping
        return object()

    def fake_sessionmaker(**kwargs):
        captured.update(kwargs)
        return "factory"

    monkeypatch.setattr(models, "create_engine", fake_create_engine)
    monkeypatch.setattr(models, "sessionmaker", fake_sessionmaker)
    assert models.make_session_factory("sqlite:///:memory:") == "factory"
    assert captured["pool_pre_ping"] is True
    assert captured["expire_on_commit"] is False


def test_app_status_and_worker_helpers(tmp_path, monkeypatch):
    status_path = tmp_path / "status.json"
    lock_path = tmp_path / "pull.lock"
    log_path = tmp_path / "pull.log"
    monkeypatch.setattr(app_module, "PULL_STATUS_FILE", status_path)
    monkeypatch.setattr(app_module, "PULL_LOCK_FILE", lock_path)
    monkeypatch.setattr(app_module, "PULL_LOG_FILE", log_path)

    assert app_module._read_pull_status() is None
    status_path.write_text("not-json", encoding="utf-8")
    assert app_module._read_pull_status() is None
    status_path.write_text("[]", encoding="utf-8")
    assert app_module._read_pull_status() is None
    status_path.write_text('{"state": "ok"}', encoding="utf-8")
    assert app_module._read_pull_status() == {"state": "ok"}

    class Proc:
        def __init__(self, result):
            self.result = result

        def poll(self):
            return self.result

    monkeypatch.setattr(app_module, "_pull_process", Proc(None))
    assert app_module._pull_is_running() is True
    monkeypatch.setattr(app_module, "_pull_process", Proc(0))
    assert app_module._pull_is_running() is False
    lock_path.write_text("locked", encoding="utf-8")
    assert app_module._pull_is_running() is True

    created = {}

    def fake_popen(args, cwd, stdout, stderr):
        created.update(args=args, cwd=cwd, stdout=stdout, stderr=stderr)
        return Proc(None)

    monkeypatch.setattr(app_module.subprocess, "Popen", fake_popen)
    app_module._start_pull_process()
    assert created["args"][0]
    assert log_path.exists()


def test_default_analysis_provider_and_factory_error(monkeypatch):
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(app_module, "make_session_factory", lambda url: lambda: FakeSession())
    monkeypatch.setattr(app_module, "run_web_analysis", lambda session: [{"number": 1}])
    provider = app_module._default_analysis_provider("postgresql://example")
    assert provider() == [{"number": 1}]

    with pytest.raises(ValueError, match="supplied together"):
        app_module.create_app(
            {"TESTING": True},
            analysis_provider=lambda: [],
            busy_checker=lambda: False,
            status_reader=lambda: None,
            pull_starter=lambda: None,
            scraper=lambda: [],
        )


def test_app_database_error_routes_and_background_pull():
    def broken_analysis():
        raise SQLAlchemyError("database down")

    flask_app = app_module.create_app(
        {"TESTING": True},
        analysis_provider=broken_analysis,
        busy_checker=lambda: False,
        status_reader=lambda: None,
        pull_starter=lambda: None,
    )
    client = flask_app.test_client()
    page = client.get("/analysis")
    assert page.status_code == 200
    assert b"could not query PostgreSQL" in page.data
    response = client.post("/update-analysis")
    assert response.status_code == 500
    assert response.get_json()["error"] == "analysis query failed"

    started = []
    flask_app = app_module.create_app(
        {"TESTING": True},
        analysis_provider=lambda: [],
        busy_checker=lambda: False,
        status_reader=lambda: None,
        pull_starter=lambda: started.append(True),
    )
    response = flask_app.test_client().post("/pull-data")
    assert response.status_code == 202
    assert response.get_json()["background"] is True
    assert started == [True]

    def broken_start():
        raise OSError("cannot spawn")

    flask_app = app_module.create_app(
        {"TESTING": True},
        analysis_provider=lambda: [],
        busy_checker=lambda: False,
        status_reader=lambda: None,
        pull_starter=broken_start,
    )
    response = flask_app.test_client().post("/pull-data")
    assert response.status_code == 500
    assert response.get_json()["error"] == "pull data could not start"


# ---------------------------------------------------------------------------
# load_data.py
# ---------------------------------------------------------------------------

def test_load_database_connection_helpers(monkeypatch):
    assert load_data._psycopg_database_url("postgresql+psycopg://u:p@h/db") == "postgresql://u:p@h/db"

    original = load_data.psycopg
    monkeypatch.setattr(load_data, "psycopg", None)
    with pytest.raises(load_data.DatabaseConnectionError, match="not installed"):
        load_data.connect_database()

    class OperationalError(Exception):
        pass

    calls = []

    def connect(value=...):
        calls.append(value)
        if value == "bad":
            raise OperationalError("nope")
        return "connection"

    fake = SimpleNamespace(OperationalError=OperationalError, connect=connect)
    monkeypatch.setattr(load_data, "psycopg", fake)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert load_data.connect_database() == "connection"
    assert calls[-1] is ...
    assert load_data.connect_database("postgresql+psycopg://u:p@h/db") == "connection"
    assert calls[-1] == "postgresql://u:p@h/db"
    with pytest.raises(load_data.DatabaseConnectionError, match="Could not connect"):
        load_data.connect_database("bad")

    monkeypatch.setattr(load_data, "psycopg", original)
    original_sql = load_data.sql
    monkeypatch.setattr(load_data, "sql", None)
    with pytest.raises(load_data.DatabaseConnectionError, match="required"):
        load_data._applicants_table("public")
    monkeypatch.setattr(load_data, "sql", original_sql)
    assert load_data._applicants_table("public") is not None


def test_load_cleaned_records_and_value_validation(tmp_path):
    valid = _clean_record(3001)
    path = tmp_path / "clean.json"
    path.write_text(json.dumps([valid]), encoding="utf-8")
    assert load_data.load_cleaned_records(path)[0]["p_id"] == 3001

    path.write_text(json.dumps({"not": "list"}), encoding="utf-8")
    with pytest.raises(ValueError, match="JSON array"):
        load_data.load_cleaned_records(path)

    bad_date = dict(valid, date_added="not-a-date")
    with pytest.raises(ValueError, match="invalid date_added"):
        load_data._validate_value_types([bad_date])

    bad_numeric = dict(valid, gpa=True)
    with pytest.raises(ValueError, match="not numeric"):
        load_data._validate_value_types([bad_numeric])

    row = load_data._to_database_row(valid)
    assert row[0] == 3001
    assert row[3].isoformat() == valid["date_added"]


def test_load_schema_failure_count_and_empty_upsert(monkeypatch):
    wrong_schema = [("p_id", "integer")]
    cursor = DummyCursor(fetchalls=[wrong_schema, [("p_id",)]])
    with pytest.raises(RuntimeError, match="does not match"):
        load_data.validate_database_schema(DummyConnection([cursor]), schema="x")

    cursor = DummyCursor(fetchalls=[list(load_data.EXPECTED_DATABASE_SCHEMA), [("wrong",)]])
    with pytest.raises(RuntimeError, match="primary key"):
        load_data.validate_database_schema(DummyConnection([cursor]), schema="x")

    cursor = DummyCursor(fetchone=None)
    with pytest.raises(RuntimeError, match="COUNT"):
        load_data.count_database_rows(DummyConnection([cursor]), schema="x")

    cursor = DummyCursor()
    load_data.upsert_records(DummyConnection([cursor]), [], schema="x")
    assert cursor.executemany_calls == []


def test_load_into_database_environment_and_create_table(monkeypatch):
    record = _clean_record(4001)
    monkeypatch.setattr(load_data, "load_cleaned_records", lambda path: [record])

    fake_connection = object()

    @contextmanager
    def fake_connect():
        yield fake_connection

    monkeypatch.setattr(load_data, "connect_database", fake_connect)
    monkeypatch.setattr(
        load_data,
        "load_records_into_connection",
        lambda connection, records, schema: (1, 2, 1),
    )
    assert load_data.load_into_database("input.json") == (1, 2, 1)

    monkeypatch.setenv("PGHOST", "host")
    monkeypatch.setenv("PGPORT", "5432")
    monkeypatch.setenv("PGDATABASE", "db")
    monkeypatch.setenv("PGUSER", "user")
    summary = load_data._database_environment_summary()
    assert "host=host" in summary and "user=user" in summary


# ---------------------------------------------------------------------------
# query_data.py
# ---------------------------------------------------------------------------

def test_query_formatters_and_fetch_dict():
    fields = load_data.EXPECTED_FIELD_NAMES
    row = tuple(range(len(fields)))
    cursor = DummyCursor(fetchone=row)
    result = query_data.fetch_applicant_dict(DummyConnection([cursor]), 7, schema="test")
    assert result == dict(zip(fields, row))

    cursor = DummyCursor(fetchone=None)
    assert query_data.fetch_applicant_dict(DummyConnection([cursor]), 7, schema="test") is None

    assert query_data._scalar([(3,)]) == 3
    with pytest.raises(ValueError, match="one scalar"):
        query_data._scalar([(1, 2)])
    assert query_data.format_integer([(3,)]) == "3"
    assert query_data.format_percentage([(None,)]) == "N/A"
    assert query_data.format_percentage([(12.345,)]) == "12.35%"
    assert query_data.format_average([(None,)]) == "N/A"
    assert query_data.format_average([(3.456,)]) == "3.46"
    assert "GPA: 3.50" in query_data.format_four_averages([(3.5, None, 160, 4.5)])
    with pytest.raises(ValueError, match="four averages"):
        query_data.format_four_averages([(1, 2)])
    assert query_data.format_top_universities([]) == "N/A"
    assert query_data.format_top_universities([("A", 2), ("B", 1)]) == "A: 2; B: 1"


def test_run_query_and_all_queries(monkeypatch, capsys):
    cursor = DummyCursor(fetchalls=[[(5,)]])
    spec = query_data.QuerySpec(1, "Q", "SELECT 1", "E", query_data.format_integer)
    assert query_data.run_query(DummyConnection([cursor]), spec) == [(5,)]

    specs = (
        query_data.QuerySpec(8, "eight", "SQL8", "E8", query_data.format_integer),
        query_data.QuerySpec(9, "nine", "SQL9", "E9", query_data.format_integer),
    )
    monkeypatch.setattr(query_data, "QUERIES", specs)

    @contextmanager
    def fake_connect():
        yield object()

    monkeypatch.setattr(query_data, "connect_database", fake_connect)
    monkeypatch.setattr(query_data, "run_query", lambda conn, spec: [(8 if spec.number == 8 else 10,)])
    results = query_data.run_all_queries(show_sql=True)
    assert results[8][1] == "8"
    assert results[9][1] == "10"
    output = capsys.readouterr().out
    assert "difference=+2" in output
    assert "SQL8" in output


# ---------------------------------------------------------------------------
# orm_queries.py
# ---------------------------------------------------------------------------

class FakeResult:
    def __init__(self, *, one=None, all_rows=None):
        self._one = one
        self._all = all_rows or []

    def one(self):
        return self._one

    def all(self):
        return self._all


class FakeSession:
    def __init__(self, *, scalar_value=0, one=None, all_rows=None):
        self.scalar_value = scalar_value
        self.one_value = one
        self.all_rows = all_rows or []

    def scalar(self, statement):
        return self.scalar_value

    def execute(self, statement):
        return FakeResult(one=self.one_value, all_rows=self.all_rows)


def test_orm_expressions_questions_and_formatters():
    assert orm_queries._original_target_university_expression() is not None
    assert orm_queries._original_computer_science_expression() is not None
    assert orm_queries._llm_target_university_expression() is not None
    assert orm_queries._llm_computer_science_expression() is not None

    assert orm_queries.question_1(FakeSession(scalar_value=4)) == 4
    assert orm_queries.question_2(FakeSession(one=(1, 4))) == 25.0
    assert orm_queries.question_2(FakeSession(one=(0, 0))) is None
    assert orm_queries.question_3(FakeSession(one=(3.5, None, 160, 4.0))) == (3.5, None, 160.0, 4.0)
    assert orm_queries.question_4(FakeSession(scalar_value=3.8)) == 3.8
    assert orm_queries.question_4(FakeSession(scalar_value=None)) is None
    assert orm_queries.question_5(FakeSession(one=(2, 4))) == 50.0
    assert orm_queries.question_5(FakeSession(one=(0, 0))) is None
    assert orm_queries.question_6(FakeSession(scalar_value=3.7)) == 3.7
    assert orm_queries.question_6(FakeSession(scalar_value=None)) is None
    assert orm_queries.question_7(FakeSession(scalar_value=5)) == 5
    assert orm_queries.question_8(FakeSession(scalar_value=6)) == 6
    assert orm_queries.question_9(FakeSession(scalar_value=7)) == 7
    assert orm_queries.question_10(FakeSession(one=(3, 4))) == 75.0
    assert orm_queries.question_10(FakeSession(one=(0, 0))) is None
    assert orm_queries.question_11(FakeSession(all_rows=[("U", 2)])) == [("U", 2)]

    assert orm_queries._format_average(None) == "N/A"
    assert orm_queries._format_average(3.456) == "3.46"
    assert orm_queries._format_percentage(None) == "N/A"
    assert orm_queries._format_percentage(12.345) == "12.35%"
    assert "GPA: 3.50" in orm_queries._format_four_averages((3.5, None, 160, 4.0))
    assert orm_queries._format_top_universities([]) == "N/A"
    assert orm_queries._format_top_universities([("U", 2)]) == "U: 2"


def test_orm_run_analysis_and_web_analysis(monkeypatch):
    monkeypatch.setattr(orm_queries, "question_1", lambda s: 1)
    monkeypatch.setattr(orm_queries, "question_2", lambda s: 25.0)
    monkeypatch.setattr(orm_queries, "question_3", lambda s: (3.5, 168.0, None, 4.5))
    monkeypatch.setattr(orm_queries, "question_4", lambda s: 3.6)
    monkeypatch.setattr(orm_queries, "question_5", lambda s: 50.0)
    monkeypatch.setattr(orm_queries, "question_6", lambda s: 3.7)
    monkeypatch.setattr(orm_queries, "question_7", lambda s: 7)
    monkeypatch.setattr(orm_queries, "question_8", lambda s: 8)
    monkeypatch.setattr(orm_queries, "question_9", lambda s: 10)
    monkeypatch.setattr(orm_queries, "question_10", lambda s: 75.0)
    monkeypatch.setattr(orm_queries, "question_11", lambda s: [("U", 2)])

    summary = orm_queries.run_orm_analysis(object())
    assert summary[9] == (8, 10, 2)

    web = orm_queries.run_web_analysis(object())
    assert len(web) == 11
    assert web[1]["result"] == "25.00%"
    assert "Difference: +2" in web[8]["result"]
