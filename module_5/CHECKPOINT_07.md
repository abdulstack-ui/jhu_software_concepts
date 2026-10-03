# Checkpoint 07 - Sphinx and Read the Docs

This checkpoint adds the Module 4 documentation deliverables:

- Sphinx configuration and HTML source pages under `module_4/docs/`
- setup and `DATABASE_URL` / `PG*` documentation
- web/ETL/database architecture documentation
- autodoc API reference for `app.py`, `scrape.py`, `clean.py`, `load_data.py`, and `query_data.py`
- testing/coverage guide
- operational troubleshooting notes
- repository-level `.readthedocs.yaml`
- Sphinx and Read the Docs theme dependencies

Validate locally:

```powershell
python -m pip install -r .\module_4\requirements.txt
python .\module_4\checkpoint_07_audit.py
python -m sphinx -W --keep-going -b html .\module_4\docs .\module_4\docs\_build\html
```
