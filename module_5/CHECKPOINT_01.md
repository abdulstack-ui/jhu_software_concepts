# Module 4 Checkpoint 01 - Structure and Testability

This checkpoint establishes the Assignment 4 testing foundation without changing the Module 3 database schema.

## Added / changed

- `src/app.py`
  - exposes `create_app(...)`
  - adds canonical `GET /analysis`
  - keeps `/` as a compatibility redirect
  - supports dependency injection for analysis, busy state, status, and Pull Data startup
- `src/models.py`
  - accepts `DATABASE_URL`
  - retains the Module 3 `PG*` environment-variable fallback
  - exposes `make_session_factory(...)` for test overrides
- `src/templates/index.html`
  - stable `data-testid` selectors for both buttons
  - explicit `Answer:` label for each analysis item
- `tests/conftest.py`
  - deterministic fake services; no network or live database
- `tests/test_flask_page.py`
  - app factory/route test
  - `/analysis` rendering test
  - root compatibility redirect test
- `pytest.ini`
  - registers all required Module 4 markers
- `requirements.txt`
  - adds Pytest and pytest-cov

## Run

From the repository root:

```powershell
python -m pip install -r .\module_4\requirements.txt
python -m pytest .\module_4\tests\test_flask_page.py -q
python .\module_4\checkpoint_01_audit.py
```

Expected Pytest result: `3 passed`.

Checkpoint 02 will implement the exact Assignment-4 JSON button contracts and busy gating, plus deterministic fake loader/error-path tests.
