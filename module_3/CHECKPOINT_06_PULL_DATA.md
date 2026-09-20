# Checkpoint 06 — Pull Data integration

The Flask analysis page now includes both required controls. **Pull Data** launches a background worker that reuses the Module 2 Selenium capture/parser, conservatively cleans newly discovered records, and upserts usable records into the existing PostgreSQL `applicants` table. **Update Analysis** remains independent: it only re-queries PostgreSQL and can be used while the scrape is active.

Concurrency is protected twice: the Flask process refuses to start a second child while one is active, and `pull_data.py` creates an exclusive `pull_data.lock` so a second worker cannot run concurrently. Runtime capture/status/log files are ignored by Git. The scraper continues to respect the Module 2 safety model: it attaches to the manually verified debug-Chrome session, stops on blocking/challenge pages, and does not bypass CAPTCHAs or rate limits.

New source records are preserved in `applicant_data.json`. Newly added records are also represented in `llm_extend_applicant_data.json`; because the Pull Data path does not fabricate an LLM result, their LLM-generated program/university fields remain `null` until a separate LLM-standardization pass is performed. Their source-backed fields are cleaned into the exact Module 3 schema and inserted into PostgreSQL.

The worker creates its runtime page-capture directory automatically before invoking `capture.py`, so a fresh checkout does not fail when `pull_data_pages/` is absent.
