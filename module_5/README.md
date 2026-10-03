# Module 5 - Software Assurance and Secure SQL

This module hardens the GradCafe Flask/PostgreSQL application against SQL injection, introduces least-privilege database access, dependency analysis, packaging, security scanning, and CI security checks.

## Fresh Install - pip

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

## Fresh Install - uv

```powershell
uv venv .venv
.\.venv\Scripts\Activate.ps1
uv pip sync requirements.txt
uv pip install -e .
```

## Database Configuration

Database credentials are supplied through environment variables and are never hard-coded in source code.

Copy `.env.example` and provide local values for:

- `PGHOST`
- `PGPORT`
- `PGDATABASE`
- `PGUSER`
- `PGPASSWORD`

`DATABASE_URL` is also supported.

The normal application role is `module5_app`. It has only `SELECT`, `INSERT`, and `UPDATE` privileges on `public.applicants`. It does not have `DELETE`, `TRUNCATE`, schema `CREATE`, superuser, database creation, or role creation privileges.

## SQL Injection Defenses

Dynamic SQL identifiers are composed with `psycopg.sql.Identifier` and `sql.SQL`. User-controlled values are passed separately through query parameters rather than interpolated into SQL strings. Query limits are validated and clamped to the allowed range before execution.

## Tests

Run the complete test suite:

```powershell
pytest
```

The project enforces 100% test coverage through `pytest.ini`.

## Pylint

Run Pylint against every Python file under `src`:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
$files = Get-ChildItem .\src\*.py | ForEach-Object { $_.FullName }
& pylint --fail-under=10 @files
```

The required score is 10.00/10.

## Dependency Graph

Graphviz must be installed and its `dot` executable available on PATH.

Generate the dependency graph with:

```powershell
cd .\src
pydeps app.py --noshow -T svg -o ..\dependency.svg
cd ..
```

The generated artifact is `dependency.svg` in the Module 5 root directory.

## Packaging

The root-level `setup.py` makes the Module 5 source installable as an editable Python project:

```powershell
python -m pip install -e .
python -m pip check
```

## Snyk

Dependency security scanning is performed with:

```powershell
snyk test
```

Static application security testing for extra credit uses:

```powershell
snyk code test
```

## Continuous Integration

GitHub Actions verifies Pylint at 10/10, regenerates the dependency graph, runs Snyk dependency scanning, and executes the pytest suite on pushes and pull requests.

## Read the Docs

Documentation remains available at:

https://jhu-software-concepts-abdul.readthedocs.io/en/latest/

## Repository

GitHub SSH:

`git@github.com:abdulstack-ui/jhu_software_concepts.git`
