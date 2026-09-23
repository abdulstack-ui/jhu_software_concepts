Architecture
============

Web layer
---------

``app.py`` provides ``create_app`` and the Flask routes. The factory accepts
injected analysis, busy-state, scraper, and loader dependencies so tests do
not need live network access or uncontrolled background work.

The public route behavior is:

* ``GET /analysis`` renders analysis results and Pull Data state;
* ``POST /update-analysis`` refreshes analysis while idle and returns HTTP 409
  when Pull Data is busy;
* ``POST /pull-data`` starts the production pull workflow or executes injected
  scraper/loader fakes during deterministic tests.

ETL layer
---------

``scrape.py`` parses captured GradCafe HTML into structured records.
``clean.py`` normalizes records without inventing missing applicant data.
``load_data.py`` validates the Module 3 schema and performs idempotent
PostgreSQL writes.

Database and analysis layer
---------------------------

``models.py`` defines the SQLAlchemy ``Applicant`` mapping and session
factory. ``query_data.py`` contains raw SQL helpers, while ``orm_queries.py``
contains the ORM-backed analyses used by the Flask page.

Pull Data orchestration
-----------------------

The production ``pull_data.py`` workflow coordinates capture, parsing,
cleaning, and loading. Module 4 tests exercise equivalent orchestration using
injected fakes and a dedicated test schema so the suite remains deterministic.
