"""Load cleaned GradCafe applicant data into PostgreSQL.

Module 3, Part 1 requires one PostgreSQL table named ``applicants``.  This
module creates that table if it does not yet exist, validates its schema, and
upserts the database-ready records produced by ``clean.py``.

Database credentials are never stored in source code.  psycopg reads the
standard PostgreSQL environment variables (PGHOST, PGPORT, PGDATABASE,
PGUSER, and PGPASSWORD).
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Sequence

try:
    import psycopg
except ModuleNotFoundError:  # lets local/static audits run before dependencies are installed
    psycopg = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from psycopg import Connection

from clean import validate_cleaned_records

DEFAULT_INPUT = "cleaned_applicant_data.json"

EXPECTED_DATABASE_SCHEMA: tuple[tuple[str, str], ...] = (
    ("p_id", "integer"),
    ("program", "text"),
    ("comments", "text"),
    ("date_added", "date"),
    ("url", "text"),
    ("status", "text"),
    ("term", "text"),
    ("us_or_international", "text"),
    ("gpa", "double precision"),
    ("gre", "double precision"),
    ("gre_v", "double precision"),
    ("gre_aw", "double precision"),
    ("degree", "text"),
    ("llm_generated_program", "text"),
    ("llm_generated_university", "text"),
)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS applicants (
    p_id INTEGER PRIMARY KEY,
    program TEXT,
    comments TEXT,
    date_added DATE,
    url TEXT,
    status TEXT,
    term TEXT,
    us_or_international TEXT,
    gpa DOUBLE PRECISION,
    gre DOUBLE PRECISION,
    gre_v DOUBLE PRECISION,
    gre_aw DOUBLE PRECISION,
    degree TEXT,
    llm_generated_program TEXT,
    llm_generated_university TEXT
);
"""

UPSERT_SQL = """
INSERT INTO applicants (
    p_id,
    program,
    comments,
    date_added,
    url,
    status,
    term,
    us_or_international,
    gpa,
    gre,
    gre_v,
    gre_aw,
    degree,
    llm_generated_program,
    llm_generated_university
)
VALUES (
    %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s
)
ON CONFLICT (p_id) DO UPDATE SET
    program = EXCLUDED.program,
    comments = EXCLUDED.comments,
    date_added = EXCLUDED.date_added,
    url = EXCLUDED.url,
    status = EXCLUDED.status,
    term = EXCLUDED.term,
    us_or_international = EXCLUDED.us_or_international,
    gpa = EXCLUDED.gpa,
    gre = EXCLUDED.gre,
    gre_v = EXCLUDED.gre_v,
    gre_aw = EXCLUDED.gre_aw,
    degree = EXCLUDED.degree,
    llm_generated_program = EXCLUDED.llm_generated_program,
    llm_generated_university = EXCLUDED.llm_generated_university;
"""


class DatabaseConnectionError(RuntimeError):
    """Raised when psycopg is unavailable or PostgreSQL cannot be reached."""


def connect_database() -> Connection[Any]:
    """Connect using standard PostgreSQL environment variables.

    psycopg/libpq automatically reads PGHOST, PGPORT, PGDATABASE, PGUSER,
    and PGPASSWORD.  Keeping connection settings in the process environment
    prevents credentials from being committed to Git.
    """
    if psycopg is None:
        raise DatabaseConnectionError(
            "psycopg is not installed. Run: python -m pip install -r requirements.txt"
        )
    try:
        return psycopg.connect()
    except psycopg.OperationalError as exc:
        raise DatabaseConnectionError(
            "Could not connect to PostgreSQL. Make sure the service is running and "
            "PGHOST, PGPORT, PGDATABASE, PGUSER, and PGPASSWORD are set."
        ) from exc


def load_cleaned_records(path: str | Path) -> list[dict[str, Any]]:
    """Read and validate the database-ready JSON file."""
    input_path = Path(path)
    with input_path.open("r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError("Expected cleaned applicant data to be a JSON array")

    validate_cleaned_records(records)
    _validate_value_types(records)
    return records


def _validate_value_types(records: Iterable[dict[str, Any]]) -> None:
    """Validate values that PostgreSQL must receive with specific types."""
    numeric_fields = ("gpa", "gre", "gre_v", "gre_aw")

    for index, record in enumerate(records, start=1):
        try:
            date.fromisoformat(record["date_added"])
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Record {index} has invalid date_added: {record['date_added']!r}"
            ) from exc

        for field in numeric_fields:
            value = record[field]
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, (int, float))
            ):
                raise ValueError(
                    f"Record {index} field {field} is not numeric/NULL: {value!r}"
                )


def _to_database_row(record: dict[str, Any]) -> tuple[Any, ...]:
    """Convert one validated JSON record to database parameter values."""
    return (
        record["p_id"],
        record["program"],
        record["comments"],
        date.fromisoformat(record["date_added"]),
        record["url"],
        record["status"],
        record["term"],
        record["us_or_international"],
        record["gpa"],
        record["gre"],
        record["gre_v"],
        record["gre_aw"],
        record["degree"],
        record["llm_generated_program"],
        record["llm_generated_university"],
    )


def create_applicants_table(connection: Connection[Any]) -> None:
    """Create the one required table if needed, then verify its schema."""
    with connection.cursor() as cursor:
        cursor.execute(CREATE_TABLE_SQL)
    validate_database_schema(connection)


def validate_database_schema(connection: Connection[Any]) -> None:
    """Fail if an existing applicants table does not match the assignment."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'applicants'
            ORDER BY ordinal_position;
            """
        )
        actual_schema = tuple(cursor.fetchall())

        cursor.execute(
            """
            SELECT attribute.attname
            FROM pg_index index_info
            JOIN pg_attribute attribute
              ON attribute.attrelid = index_info.indrelid
             AND attribute.attnum = ANY(index_info.indkey)
            WHERE index_info.indrelid = 'public.applicants'::regclass
              AND index_info.indisprimary
            ORDER BY attribute.attnum;
            """
        )
        primary_key_columns = tuple(row[0] for row in cursor.fetchall())

    if actual_schema != EXPECTED_DATABASE_SCHEMA:
        raise RuntimeError(
            "Existing public.applicants table does not match the required schema.\n"
            f"Expected: {EXPECTED_DATABASE_SCHEMA}\n"
            f"Actual:   {actual_schema}"
        )

    if primary_key_columns != ("p_id",):
        raise RuntimeError(
            "The applicants table must use p_id as its primary key. "
            f"Found primary key columns: {primary_key_columns}"
        )


def count_database_rows(connection: Connection[Any]) -> int:
    """Return the current number of rows in applicants."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM applicants;")
        result = cursor.fetchone()
    if result is None:
        raise RuntimeError("COUNT(*) unexpectedly returned no result")
    return int(result[0])


def upsert_records(
    connection: Connection[Any], records: Sequence[dict[str, Any]]
) -> None:
    """Insert records and update matching p_id rows without creating duplicates."""
    rows = [_to_database_row(record) for record in records]
    with connection.cursor() as cursor:
        cursor.executemany(UPSERT_SQL, rows)


def load_into_database(input_path: str | Path = DEFAULT_INPUT) -> tuple[int, int, int]:
    """Create/validate the table and upsert all cleaned records.

    Returns:
        A tuple of (rows_before, rows_after, records_processed).
    """
    records = load_cleaned_records(input_path)

    with connect_database() as connection:
        create_applicants_table(connection)
        rows_before = count_database_rows(connection)
        upsert_records(connection, records)
        rows_after = count_database_rows(connection)

    return rows_before, rows_after, len(records)


def _database_environment_summary() -> str:
    """Describe the target without ever printing a password."""
    host = os.getenv("PGHOST", "PostgreSQL default")
    port = os.getenv("PGPORT", "PostgreSQL default")
    database = os.getenv("PGDATABASE", "PostgreSQL default")
    user = os.getenv("PGUSER", "PostgreSQL default")
    return f"host={host}, port={port}, database={database}, user={user}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load cleaned Module 3 GradCafe data into PostgreSQL."
    )
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT,
        help=f"Database-ready JSON file (default: {DEFAULT_INPUT})",
    )
    args = parser.parse_args()

    print(f"PostgreSQL target: {_database_environment_summary()}")
    try:
        rows_before, rows_after, processed = load_into_database(args.input)
    except DatabaseConnectionError as exc:
        raise SystemExit(str(exc)) from exc

    print(f"Validated and processed: {processed:,} cleaned records")
    print(f"Database rows before:   {rows_before:,}")
    print(f"Database rows after:    {rows_after:,}")
    print(f"Net new rows:           {rows_after - rows_before:,}")
    print("Load complete. Re-running this script is safe: matching p_id rows are updated.")


if __name__ == "__main__":
    main()
