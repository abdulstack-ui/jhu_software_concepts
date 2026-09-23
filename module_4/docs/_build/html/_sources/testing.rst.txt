Testing Guide
=============

Markers
-------

Every test is assigned at least one registered marker:

``web``
   Flask route and rendered-page behavior.

``buttons``
   Pull Data and Update Analysis endpoint behavior.

``analysis``
   Analysis labels, percentage formatting, and related output behavior.

``db``
   PostgreSQL schema, inserts, idempotency, and query behavior.

``integration``
   End-to-end flows spanning scraper fakes, PostgreSQL loading, update, and
   page rendering.

Run the complete marked suite
-----------------------------

From the repository root::

   python -m pytest module_4/tests -m "web or buttons or analysis or db or integration" -q

``pytest.ini`` also enables coverage for ``module_4/src`` and fails the run if
coverage drops below 100 percent.

Coverage evidence
-----------------

The checked-in ``module_4/coverage_summary.txt`` records the successful local
coverage run. GitHub Actions generates the same file in CI and uploads it as a
workflow artifact.

Determinism
-----------

Tests do not contact GradCafe. Scraper and loader dependencies are injected
where appropriate, busy-state tests do not use ``sleep()``, and database tests
use an isolated schema that is dropped after the test session.
