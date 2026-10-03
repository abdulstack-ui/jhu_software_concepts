# Checkpoint 05B — full-source coverage tests

The coverage probe showed that the inherited Module 3 acquisition/parsing modules were being counted by `--cov=module_4/src`, so this patch adds deterministic offline tests rather than hiding those files from coverage.

What this patch adds:

- offline parser coverage for `scrape.py`
- fake-driver coverage for `capture.py` (no browser or internet is opened)
- isolated orchestration coverage for `pull_data.py`
- helper/error-path coverage for `clean.py`, `load_data.py`, `query_data.py`, `models.py`, `orm_queries.py`, and `app.py`
- only command-line `main()` wrappers are excluded with standard `# pragma: no cover` comments
- the Checkpoint 05 marker audit now recognizes valid module-level `pytestmark` declarations

Run from the repository root with the PostgreSQL environment variables already configured:

```powershell
python .\module_4\checkpoint_05_audit.py
python -m pytest .\module_4\tests -q 2>&1 | Tee-Object -FilePath .\module_4\coverage_summary.txt
```

Target: all tests pass and the TOTAL coverage line is 100%.
