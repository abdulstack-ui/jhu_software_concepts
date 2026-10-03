"""Offline coverage for browser-control helpers and Pull Data orchestration."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

import capture
import clean
import pull_data


class Switcher:
    def __init__(self, driver, fail_handles=None):
        self.driver = driver
        self.fail_handles = set(fail_handles or [])

    def window(self, handle):
        if handle in self.fail_handles:
            raise capture.WebDriverException("switch failed")
        self.driver.current_window_handle = handle
        self.driver.current_url = self.driver.urls.get(handle, self.driver.current_url)


class FakeElement:
    def __init__(self):
        self.clicked = False

    def click(self):
        self.clicked = True


class FakeDriver:
    def __init__(self, url="https://www.thegradcafe.com/survey", html="<html></html>", title="GradCafe"):
        self.current_url = url
        self.page_source = html
        self.title = title
        self.current_window_handle = "h1"
        self.window_handles = ["h1"]
        self.urls = {"h1": url}
        self.switch_to = Switcher(self)
        self.get_calls = []
        self.find_results = []
        self.script_calls = []

    def get(self, url):
        self.get_calls.append(url)
        self.current_url = url

    def execute_script(self, script, *args):
        self.script_calls.append((script, args))
        if script == "return document.readyState":
            return "complete"
        return None

    def find_element(self, by, xpath):
        if self.find_results:
            item = self.find_results.pop(0)
            if isinstance(item, Exception):
                raise item
            return item
        raise capture.NoSuchElementException("not found")


class FakeOptions:
    def __init__(self):
        self.calls = []

    def add_experimental_option(self, key, value):
        self.calls.append((key, value))


class FakeWait:
    def __init__(self, driver, timeout):
        self.driver = driver
        self.timeout = timeout

    def until(self, callback):
        return callback(self.driver)


def _install_driver(monkeypatch, driver):
    options = FakeOptions()
    monkeypatch.setattr(capture.webdriver, "ChromeOptions", lambda: options)
    monkeypatch.setattr(capture.webdriver, "Chrome", lambda options=None: driver)
    return options


def _capture_args(tmp_path, **overrides):
    values = dict(
        target=1,
        output=tmp_path / "out.json",
        pages_dir=tmp_path / "pages",
        state_file=tmp_path / "state.json",
        delay_min=0.0,
        delay_max=0.0,
        resume=False,
        novelty_window=2,
        min_new_ratio=0.1,
        require_root_start=False,
    )
    values.update(overrides)
    return values


def _source_record(result_id=7001, *, date_added="Sep 20, 2026"):
    return {
        "entry_url": f"https://www.thegradcafe.com/result/{result_id}",
        "university": "Example University",
        "raw_program_text": "Computer Science PhD",
        "program_name": "Computer Science",
        "comments": "hello",
        "date_added": date_added,
        "applicant_status": "Accepted",
        "program_start": "Fall 2026",
        "student_type": "International",
        "gpa": "3.9",
        "gre_score": "168",
        "gre_verbal": "160",
        "gre_aw": "4.5",
        "degree": "PhD",
    }


# ---------------------------------------------------------------------------
# capture.py helper functions
# ---------------------------------------------------------------------------

def test_capture_block_tab_and_url_helpers(monkeypatch):
    assert capture._blocked("Verify you are human", "") is True
    assert capture._blocked("normal page", "GradCafe") is False

    driver = FakeDriver()
    driver.window_handles = ["h1", "h2", "bad"]
    driver.urls = {
        "h1": "https://www.thegradcafe.com/survey",
        "h2": "https://example.com/",
        "bad": "https://www.thegradcafe.com/survey?cursor=2",
    }
    driver.switch_to = Switcher(driver, {"bad"})
    tabs = capture._survey_tabs(driver)
    assert tabs == [("h1", "https://www.thegradcafe.com/survey")]

    # Also cover failure while restoring the original window.
    driver.switch_to = Switcher(driver, {"h1"})
    driver.current_window_handle = "h1"
    assert isinstance(capture._survey_tabs(driver), list)

    monkeypatch.setattr(capture, "_survey_tabs", lambda d: [])
    with pytest.raises(RuntimeError, match="No GradCafe"):
        capture._select_single_gradcafe_tab(driver)
    monkeypatch.setattr(
        capture,
        "_survey_tabs",
        lambda d: [("a", "https://www.thegradcafe.com/survey"), ("b", "https://www.thegradcafe.com/survey?cursor=2")],
    )
    with pytest.raises(RuntimeError, match="Multiple GradCafe"):
        capture._select_single_gradcafe_tab(driver)
    driver.switch_to = Switcher(driver)
    monkeypatch.setattr(capture, "_survey_tabs", lambda d: [("h1", capture.SURVEY_URL if hasattr(capture, 'SURVEY_URL') else "https://www.thegradcafe.com/survey")])
    capture._select_single_gradcafe_tab(driver)

    assert capture._is_root_survey_url("https://www.thegradcafe.com/survey") is True
    assert capture._is_root_survey_url("https://www.thegradcafe.com/survey?cursor=1") is False
    assert capture._contains_next_word("Next →") is True
    assert capture._contains_next_word("Previous") is False


def test_capture_next_click_wait_and_state(tmp_path, monkeypatch):
    current = "https://www.thegradcafe.com/survey"
    assert capture._next_url_from_html('<a rel="next" href="/survey?cursor=1">go</a>', current).endswith("cursor=1")
    assert capture._next_url_from_html('<a aria-label="Next page" href="/survey?cursor=2">go</a>', current).endswith("cursor=2")
    assert capture._next_url_from_html("<p>none</p>", current) is None

    driver = FakeDriver()
    element = FakeElement()
    driver.find_results = [capture.NoSuchElementException("x"), element]
    assert capture._click_next(driver) is True
    assert element.clicked is True
    driver.find_results = []
    assert capture._click_next(driver) is False

    monkeypatch.setattr(capture, "WebDriverWait", FakeWait)
    old = "0" * 40
    capture._wait_for_change(driver, old, timeout=1)

    state = tmp_path / "state.json"
    assert capture._load_state(state) == {}
    state.write_text('{"resume_url": "/survey?cursor=1"}', encoding="utf-8")
    assert capture._load_state(state)["resume_url"].endswith("cursor=1")
    state.write_text("[]", encoding="utf-8")
    assert capture._load_state(state) == {}
    state.write_text("bad-json", encoding="utf-8")
    assert capture._load_state(state) == {}

    capture._save_state(state, last_url=current, resume_url=None, records=5)
    payload = json.loads(state.read_text(encoding="utf-8"))
    assert payload["records"] == 5


def test_capture_rejects_non_root_start(tmp_path, monkeypatch):
    driver = FakeDriver(url="https://www.thegradcafe.com/survey?cursor=old")
    _install_driver(monkeypatch, driver)
    monkeypatch.setattr(capture, "_select_single_gradcafe_tab", lambda d: None)
    with pytest.raises(RuntimeError, match="must begin"):
        capture.capture(**_capture_args(tmp_path, require_root_start=True))


def test_capture_resume_setup_without_loop(tmp_path, monkeypatch):
    driver = FakeDriver()
    options = _install_driver(monkeypatch, driver)
    monkeypatch.setattr(capture, "_select_single_gradcafe_tab", lambda d: None)
    monkeypatch.setattr(capture, "WebDriverWait", FakeWait)
    monkeypatch.setattr(capture, "_load_state", lambda path: {"resume_url": "/survey?cursor=resume"})
    monkeypatch.setattr(capture, "load_data", lambda path: [{"entry_url": "https://www.thegradcafe.com/result/1"}])
    monkeypatch.setattr(capture, "save_data", lambda records, path: None)
    capture.capture(**_capture_args(tmp_path, target=1, resume=True))
    assert options.calls == [("debuggerAddress", "127.0.0.1:9222")]
    assert driver.get_calls


def _prepare_loop(monkeypatch, driver, *, existing=None, parsed=None, next_url=None):
    _install_driver(monkeypatch, driver)
    monkeypatch.setattr(capture, "_select_single_gradcafe_tab", lambda d: None)
    monkeypatch.setattr(capture, "_load_state", lambda p: {})
    monkeypatch.setattr(capture, "load_data", lambda p: list(existing or []))
    monkeypatch.setattr(capture, "save_data", lambda records, path: None)
    monkeypatch.setattr(capture, "parse_html", lambda html, page_url=None: list(parsed or []))
    monkeypatch.setattr(capture, "_next_url_from_html", lambda html, url: next_url)
    monkeypatch.setattr(capture, "_save_state", lambda *a, **k: None)
    monkeypatch.setattr(capture.time, "sleep", lambda seconds: None)


def test_capture_loop_safe_stop_paths(tmp_path, monkeypatch):
    # Selected tab leaves GradCafe.
    driver = FakeDriver(url="https://www.thegradcafe.com/not-survey")
    _prepare_loop(monkeypatch, driver)
    capture.capture(**_capture_args(tmp_path, target=2))

    # Blocking/challenge page.
    driver = FakeDriver(html="Verify you are human")
    _prepare_loop(monkeypatch, driver)
    capture.capture(**_capture_args(tmp_path, target=2))

    # Parsed row reaches target.
    row = {"entry_url": "https://www.thegradcafe.com/result/2"}
    driver = FakeDriver(html="<a rel='next' href='/survey?cursor=2'>next</a>")
    _prepare_loop(monkeypatch, driver, parsed=[row], next_url="/survey?cursor=2")
    capture.capture(**_capture_args(tmp_path, target=1))

    # No rows parsed.
    driver = FakeDriver()
    _prepare_loop(monkeypatch, driver, parsed=[])
    capture.capture(**_capture_args(tmp_path, target=2))

    # Duplicate-only novelty window trips stale-cursor protection.
    existing = [{"entry_url": "https://www.thegradcafe.com/result/3"}]
    driver = FakeDriver()
    _prepare_loop(monkeypatch, driver, existing=existing, parsed=list(existing))
    capture.capture(**_capture_args(tmp_path, target=3, novelty_window=1, min_new_ratio=0.5))


def test_capture_navigation_paths(tmp_path, monkeypatch):
    row = {"entry_url": "https://www.thegradcafe.com/result/4"}

    # Direct next URL, then make the following iteration leave the site.
    driver = FakeDriver()
    _prepare_loop(monkeypatch, driver, parsed=[row], next_url="/survey?cursor=2")

    def wait_and_leave(d, old_hash, timeout=30):
        d.current_url = "https://www.thegradcafe.com/not-survey"

    monkeypatch.setattr(capture, "_wait_for_change", wait_and_leave)
    capture.capture(**_capture_args(tmp_path, target=3))
    assert driver.get_calls

    # Click fallback succeeds; state captures the actual new URL.
    driver = FakeDriver()
    _prepare_loop(monkeypatch, driver, parsed=[row], next_url=None)

    def clicked(d):
        d.current_url = "https://www.thegradcafe.com/survey?cursor=clicked"
        return True

    saved = []
    monkeypatch.setattr(capture, "_click_next", clicked)
    monkeypatch.setattr(capture, "_wait_for_change", lambda d, h, timeout=30: None)
    monkeypatch.setattr(capture, "_save_state", lambda *a, **k: saved.append(k))
    monkeypatch.setattr(capture.time, "sleep", lambda seconds: setattr(driver, "current_url", "https://www.thegradcafe.com/not-survey"))
    capture.capture(**_capture_args(tmp_path, target=3))
    assert any((item.get("resume_url") or "").endswith("cursor=clicked") for item in saved)

    # Click fallback cannot find Next.
    driver = FakeDriver()
    _prepare_loop(monkeypatch, driver, parsed=[row], next_url=None)
    monkeypatch.setattr(capture, "_click_next", lambda d: False)
    capture.capture(**_capture_args(tmp_path, target=3))

    # Navigation raises and is caught safely.
    driver = FakeDriver()
    _prepare_loop(monkeypatch, driver, parsed=[row], next_url="/survey?cursor=boom")

    def bad_get(url):
        raise RuntimeError("navigation failed")

    driver.get = bad_get
    capture.capture(**_capture_args(tmp_path, target=3))


# ---------------------------------------------------------------------------
# pull_data.py
# ---------------------------------------------------------------------------

def test_pull_helpers_json_merge_and_lock(tmp_path, monkeypatch):
    assert "+" in pull_data._utc_now() or "Z" in pull_data._utc_now()

    path = tmp_path / "payload.json"
    pull_data._atomic_write_json(path, {"x": 1})
    assert json.loads(path.read_text(encoding="utf-8")) == {"x": 1}

    status_path = tmp_path / "status.json"
    monkeypatch.setattr(pull_data, "STATUS_PATH", status_path)
    pull_data._write_status("ok", "done", count=2)
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["state"] == "ok" and status["count"] == 2

    missing = tmp_path / "missing.json"
    assert pull_data._load_json_list(missing) == []
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON array"):
        pull_data._load_json_list(bad)
    bad.write_text("[1]", encoding="utf-8")
    with pytest.raises(ValueError, match="object records"):
        pull_data._load_json_list(bad)
    bad.write_text('[{"x": 1}]', encoding="utf-8")
    assert pull_data._load_json_list(bad) == [{"x": 1}]

    assert pull_data._url({"entry_url": " x "}) == "x"
    assert pull_data._url({"url": " y "}) == "y"
    assert pull_data._url({}) is None

    existing = [{"entry_url": "u1"}]
    merged = pull_data._merge_by_url(existing, [{"entry_url": "u1"}, {"entry_url": "u2"}, {}])
    assert [r.get("entry_url") for r in merged] == ["u1", "u2"]

    c1 = clean.clean_record(_source_record(8001))
    c2 = clean.clean_record(_source_record(8002))
    merged_clean = pull_data._merge_cleaned([c1], [dict(c1), c2])
    assert len(merged_clean) == 2

    placeholder = pull_data._llm_placeholder_record(_source_record(8003))
    assert "llm-generated-program" in placeholder
    already = _source_record(8004)
    already["llm-generated-program"] = "CS"
    assert pull_data._llm_placeholder_record(already)["llm-generated-program"] == "CS"

    lock = tmp_path / "pull.lock"
    monkeypatch.setattr(pull_data, "LOCK_PATH", lock)
    descriptor = pull_data._acquire_lock()
    assert lock.exists()
    pull_data._release_lock(descriptor)
    assert not lock.exists()

    lock.write_text("stale", encoding="utf-8")
    with pytest.raises(RuntimeError, match="already running"):
        pull_data._acquire_lock()

    monkeypatch.setattr(pull_data.os, "close", lambda descriptor: (_ for _ in ()).throw(OSError("closed")))
    pull_data._release_lock(999)
    pull_data._release_lock(None)


def _redirect_pull_paths(tmp_path, monkeypatch):
    for name, filename in {
        "RAW_PATH": "raw.json",
        "LLM_PATH": "llm.json",
        "CLEAN_PATH": "clean.json",
        "WORK_PATH": "work.json",
        "PAGES_DIR": "pages",
        "CAPTURE_STATE": "state.json",
        "STATUS_PATH": "status.json",
        "LOCK_PATH": "lock",
    }.items():
        monkeypatch.setattr(pull_data, name, tmp_path / filename)


def test_run_pull_refuses_empty_baseline(tmp_path, monkeypatch):
    _redirect_pull_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(pull_data, "load_raw_data", lambda path: [])
    with pytest.raises(RuntimeError, match="missing or empty"):
        pull_data.run_pull()


def test_run_pull_no_usable_new_records(tmp_path, monkeypatch):
    _redirect_pull_paths(tmp_path, monkeypatch)
    existing = [_source_record(9001)]
    invalid_new = _source_record(9002, date_added="not a date")

    def load(path):
        if path == pull_data.RAW_PATH:
            return existing
        if path == pull_data.WORK_PATH:
            return [*existing, invalid_new]
        return []

    monkeypatch.setattr(pull_data, "load_raw_data", load)
    monkeypatch.setattr(pull_data, "capture", lambda **kwargs: None)
    monkeypatch.setenv("PULL_DATA_TARGET_INCREMENT", "1")
    result = pull_data.run_pull()
    assert result["discovered"] == 1
    assert result["added"] == 0
    assert result["skipped"] == 1
    assert json.loads(pull_data.STATUS_PATH.read_text(encoding="utf-8"))["state"] == "complete"


def test_run_pull_success_updates_database_and_files(tmp_path, monkeypatch):
    _redirect_pull_paths(tmp_path, monkeypatch)
    existing = [_source_record(9101)]
    new = _source_record(9102)
    pull_data.LLM_PATH.write_text("[]", encoding="utf-8")
    pull_data.CLEAN_PATH.write_text("[]", encoding="utf-8")

    def load(path):
        if path == pull_data.RAW_PATH:
            return existing
        if path == pull_data.WORK_PATH:
            return [*existing, new]
        return []

    monkeypatch.setattr(pull_data, "load_raw_data", load)
    monkeypatch.setattr(pull_data, "capture", lambda **kwargs: None)

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(pull_data, "connect_database", lambda: Connection())
    monkeypatch.setattr(pull_data, "create_applicants_table", lambda connection: None)
    counts = iter([1, 2])
    monkeypatch.setattr(pull_data, "count_database_rows", lambda connection: next(counts))
    loaded = []
    monkeypatch.setattr(pull_data, "upsert_records", lambda connection, rows: loaded.extend(rows))

    result = pull_data.run_pull()
    assert result == {
        "discovered": 1,
        "added": 1,
        "skipped": 0,
        "database_before": 1,
        "database_after": 2,
    }
    assert loaded[0]["p_id"] == 9102
    assert len(json.loads(pull_data.RAW_PATH.read_text(encoding="utf-8"))) == 2
    assert len(json.loads(pull_data.LLM_PATH.read_text(encoding="utf-8"))) == 1
    assert len(json.loads(pull_data.CLEAN_PATH.read_text(encoding="utf-8"))) == 1
