Operations and Troubleshooting
==============================

PostgreSQL connection errors
----------------------------

Confirm PostgreSQL is running and that ``DATABASE_URL`` or the fallback
``PG*`` variables are correct. The Flask analysis page reports a database
configuration message rather than fabricating results.

Busy responses
--------------

A Pull Data or Update Analysis request can return HTTP 409 with
``{"busy": true}`` while a pull is already active. Retry after the active
operation finishes rather than starting overlapping workers.

Pull Data failures
------------------

The production pull workflow writes status/log information beside the source
module. Tests replace the live scraper and loader with deterministic fakes, so
CI never depends on GradCafe availability.

GitHub Actions
--------------

The ``Module 4 Tests`` workflow starts PostgreSQL 16, installs
``module_4/requirements.txt``, executes the required marked suite, enforces
100 percent source coverage, and uploads ``coverage_summary.txt``.

Read the Docs
-------------

The repository-level ``.readthedocs.yaml`` points Read the Docs at
``module_4/docs/conf.py`` and installs the same project requirements used by
local builds. After importing the public GitHub repository into Read the Docs,
trigger a build and submit the resulting documentation URL with the assignment.
