Overview
========

Module 4 makes the existing GradCafe application testable and reproducible.
The application exposes a Flask application factory, injects external
services for deterministic tests, verifies PostgreSQL loading behavior, and
runs the complete marked test suite under GitHub Actions.

The documented system has four main responsibilities:

* acquire and parse GradCafe result rows;
* clean and persist applicant records in PostgreSQL;
* compute database-backed analysis results;
* expose the analysis and Pull Data controls through Flask.

The test suite never requires live internet access. Scraper behavior is
represented by deterministic fakes in the endpoint and integration tests,
while the PostgreSQL tests use an isolated temporary schema.
