# Module 4 Checkpoint 02 — Button Contracts and Busy-State Tests

This checkpoint adds deterministic tests for the two Flask controls required by
Module 4.

## What changed

- `POST /pull-data`
  - returns HTTP 200 with `{"ok": true}` in injected test mode;
  - passes fake scraper rows directly to the fake loader;
  - returns HTTP 409 with `{"busy": true}` while busy;
  - returns a non-200 response when the loader fails;
  - starts the inherited Module 3 background Pull Data process in production and
    returns HTTP 202 with `{"ok": true}`.
- `POST /update-analysis`
  - re-runs the analysis provider and returns HTTP 200 while idle;
  - returns HTTP 409 with `{"busy": true}` without querying when a pull is active.
- `tests/test_buttons.py` contains deterministic `@pytest.mark.buttons` tests.
- No test uses live GradCafe access or `sleep()` for busy-state behavior.

## Verification

From the repository root:

```powershell
python -m pytest .\module_4\tests\test_flask_page.py .\module_4\tests\test_buttons.py -q
python .\module_4\checkpoint_02_audit.py
```

Expected at this checkpoint: **8 passed** and `CHECKPOINT 02 STATIC AUDIT: PASS`.
