# Checkpoint 06 — GitHub Actions CI

This checkpoint adds the required GitHub Actions workflow at:

`.github/workflows/tests.yml`

The workflow:

- runs on push, pull request, or manual dispatch;
- starts PostgreSQL 16 as a service;
- configures both `DATABASE_URL` and `TEST_DATABASE_URL`;
- installs `module_4/requirements.txt`;
- runs the complete marker-selected Pytest suite;
- enforces the existing 100% coverage gate from `pytest.ini`;
- writes and uploads `module_4/coverage_summary.txt`.

After the workflow succeeds on GitHub, capture the green successful workflow run and save the image as `module_4/actions_success.png` for the assignment deliverable.
