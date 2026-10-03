# Checkpoint 05 — Marker sweep and 100% coverage gate

This checkpoint turns on the assignment's final coverage gate without hiding missing lines.

Run from the repository root after PostgreSQL environment variables are set:

```powershell
python .\module_4\checkpoint_05_audit.py
python -m pytest .\module_4\tests -q 2>&1 | Tee-Object -FilePath .\module_4\coverage_summary.txt
```

The static audit should pass. The pytest command may initially fail only because the coverage percentage is below 100%; that terminal report is the coverage probe for the next patch. Keep `coverage_summary.txt` and send the complete coverage table, especially every `Missing` line range.

The final assignment target is 100% and the same command must eventually exit successfully.
