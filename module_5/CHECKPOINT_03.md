# Module 4 Checkpoint 03 — Analysis Formatting and PostgreSQL Writes

Checkpoint 03 covers the rubric's analysis-formatting and database-test requirements.

## Added

- `tests/test_analysis_format.py`
  - every rendered analysis card has an `Answer:` label
  - rendered percentages use exactly two decimal places
  - the ORM percentage formatter is tested directly
- `tests/test_db_insert.py`
  - a fake scraper feeds deterministic rows through `POST /pull-data`
  - the injected loader writes those rows into a **real PostgreSQL** table
  - each test uses a disposable PostgreSQL schema so the production `public.applicants` table is untouched
  - repeated pulls are idempotent by `p_id`
  - a simple query returns a dictionary with the exact Module 3 field keys
- `load_data.py`
  - PostgreSQL connections now accept `DATABASE_URL` as well as the existing `PG*` variables
  - schema-aware table helpers enable isolated database tests
  - `load_records_into_connection(...)` provides a testable real-DB loader seam
- `query_data.py`
  - `fetch_applicant_dict(...)` returns one row using the exact required field names

## Local PostgreSQL setup

The DB tests require a running PostgreSQL server. Credentials remain in environment variables and are never written to the repository.

Example PowerShell setup:

```powershell
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
$secure = Read-Host "Enter PostgreSQL password" -AsSecureString
$plain = [System.Net.NetworkCredential]::new("", $secure).Password
$env:PGHOST = "localhost"
$env:PGPORT = "5432"
$env:PGDATABASE = "gradcafe"
$env:PGUSER = "postgres"
$env:PGPASSWORD = $plain
```

## Verification

```powershell
python -m pytest .\module_4\tests\test_flask_page.py .\module_4\tests\test_buttons.py .\module_4\tests\test_analysis_format.py .\module_4\tests\test_db_insert.py -q
python .\module_4\checkpoint_03_audit.py
```

Expected test count at this checkpoint: **14 passed**.
