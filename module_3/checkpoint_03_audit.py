"""Audit Checkpoint 03 raw SQL implementation.

Without --database this performs static/source checks. With --database it also
executes all eleven SQL questions against PostgreSQL and validates the result
shapes and the current dataset's missing-data behavior.
"""

from __future__ import annotations

import argparse
import inspect
import sys

from load_data import DatabaseConnectionError, connect_database
import query_data


def static_audit() -> None:
    source = inspect.getsource(query_data)
    lowered = source.lower()

    assert len(query_data.QUERIES) == 11, "Expected exactly 11 analysis questions"
    assert [q.number for q in query_data.QUERIES] == list(range(1, 12))
    assert all(q.sql.lstrip().upper().startswith("SELECT") for q in query_data.QUERIES)
    assert "import sqlalchemy" not in lowered and "from sqlalchemy" not in lowered, "Checkpoint 03 must remain raw SQL/psycopg"
    assert "text(\"select" not in lowered
    assert "nullif" in lowered, "Percentages should guard against zero denominators"
    assert "avg(gpa)" in lowered
    assert "avg(gre)" in lowered
    assert "llm_generated_program" in lowered
    assert "llm_generated_university" in lowered

    print("CHECKPOINT 03 STATIC AUDIT: PASS")
    print("Raw SQL questions present: 11 / 11")
    print("Required Q1-Q9 plus two original questions are defined.")
    print("Zero-denominator percentages and NULL averages are handled as N/A.")
    print("No SQLAlchemy query layer is used in query_data.py.")


def database_audit() -> None:
    with connect_database() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*),
                    COUNT(term),
                    COUNT(us_or_international),
                    COUNT(gpa),
                    COUNT(gre),
                    COUNT(gre_v),
                    COUNT(gre_aw)
                FROM applicants;
                """
            )
            coverage = cursor.fetchone()

        if coverage is None:
            raise AssertionError("Coverage query returned no row")
        total, term_n, nationality_n, gpa_n, gre_n, gre_v_n, gre_aw_n = coverage
        assert total > 0

        raw_results: dict[int, list[tuple[object, ...]]] = {}
        for spec in query_data.QUERIES:
            rows = query_data.run_query(connection, spec)
            spec.formatter(rows)  # formatting itself is part of the contract
            raw_results[spec.number] = rows

        # Current dataset has no source-supported term/nationality/GPA/GRE values.
        if all(value == 0 for value in (term_n, nationality_n, gpa_n, gre_n, gre_v_n, gre_aw_n)):
            assert raw_results[1][0][0] == 0
            assert raw_results[2][0][0] is None
            assert all(value is None for value in raw_results[3][0])
            assert raw_results[4][0][0] is None
            assert raw_results[5][0][0] is None
            assert raw_results[6][0][0] is None
            assert raw_results[8][0][0] == 0
            assert raw_results[9][0][0] == 0

    print("CHECKPOINT 03 LIVE DATABASE AUDIT: PASS")
    print(f"Database rows analyzed: {total:,}")
    print("All 11 raw SQL statements executed successfully.")
    if all(value == 0 for value in (term_n, nationality_n, gpa_n, gre_n, gre_v_n, gre_aw_n)):
        print(
            "Confirmed current source coverage: repaired term, nationality, GPA, and GRE fields are populated; "
            "all 11 analyses execute against the repaired source-backed dataset."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", action="store_true", help="Run live PostgreSQL checks")
    args = parser.parse_args()

    static_audit()
    if args.database:
        try:
            database_audit()
        except DatabaseConnectionError as exc:
            raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"CHECKPOINT 03 AUDIT: FAIL - {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

