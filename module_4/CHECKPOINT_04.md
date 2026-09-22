# Module 4 Checkpoint 04 — End-to-End Integration

Checkpoint 04 adds the required integration test file and exercises the complete deterministic application path without live internet access.

## Added

- `tests/test_integration_end_to_end.py`
  - fake scraper returns multiple complete Module 3-style rows
  - `POST /pull-data` passes those rows to the real PostgreSQL test loader
  - loader writes into the isolated disposable PostgreSQL schema created by the shared fixture
  - `POST /update-analysis` re-queries the database-backed analysis provider
  - `GET /analysis` renders the new database state with an `Answer:` label
  - an observable injected busy flag simulates overlapping Pull Data requests without `sleep()`
  - busy requests return HTTP 409 and cannot invoke the scraper/loader or alter the database
  - a later retry remains idempotent by `p_id`

No test contacts GradCafe or launches Selenium.

## Verification

Keep the PostgreSQL environment variables from Checkpoint 03 set, then run:

```powershell
python -m pytest .\module_4\tests\test_flask_page.py .\module_4\tests\test_buttons.py .\module_4\tests\test_analysis_format.py .\module_4\tests\test_db_insert.py .\module_4\tests\test_integration_end_to_end.py -q
python .\module_4\checkpoint_04_audit.py
```

Expected test count at this checkpoint: **16 passed**.
