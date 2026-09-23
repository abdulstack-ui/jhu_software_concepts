# Module 4 - Testing and Documentation

This folder contains the Module 4 testing, CI, and documentation work for the GradCafe Flask/PostgreSQL application inherited from Module 3.

## Application

The Flask application lives in `src/app.py` and exposes a `create_app(...)` factory. The canonical page is `GET /analysis`; `POST /pull-data` and `POST /update-analysis` implement the required button behavior and return HTTP 409 while the application is busy.

Configuration prefers `DATABASE_URL` and retains the Module 3 `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, and `PGPASSWORD` fallback variables. Credentials are not stored in the repository.

## Tests

Install dependencies from the repository root:

```powershell
python -m pip install -r .\module_4\requirements.txt
```

Run the complete marked suite:

```powershell
python -m pytest .\module_4\tests -m "web or buttons or analysis or db or integration" -q
```

`pytest.ini` measures `module_4/src` and enforces 100% coverage. The local evidence is saved in `coverage_summary.txt`.

The required test files are:

- `tests/test_flask_page.py`
- `tests/test_buttons.py`
- `tests/test_analysis_format.py`
- `tests/test_db_insert.py`
- `tests/test_integration_end_to_end.py`

Additional deterministic tests cover inherited Module 3 code so the complete `src` tree reaches the required coverage threshold without live internet access.

## GitHub Actions

`.github/workflows/tests.yml` starts PostgreSQL, installs dependencies, executes the marked test suite, enforces 100% coverage, and uploads the coverage summary artifact.

After a successful workflow run, save a screenshot of the green run as `module_4/actions_success.png`.

## Sphinx documentation

Build the HTML documentation locally with:

```powershell
python -m sphinx -W --keep-going -b html .\module_4\docs .\module_4\docs\_build\html
```

Open `module_4/docs/_build/html/index.html` to inspect the generated site.

The documentation contains setup/environment variables, architecture, autodoc API references for the scraper/cleaner/loader/query/Flask modules, testing instructions, and operational troubleshooting.

## Read the Docs

The repository includes `.readthedocs.yaml`. Import the public GitHub repository into Read the Docs, trigger a build, and submit the resulting Read the Docs URL with the assignment.

## Submission Links
- Read the Docs: https://jhu-software-concepts-abdul.readthedocs.io/en/latest/
- GitHub SSH: git@github.com:abdulstack-ui/jhu_software_concepts.git

