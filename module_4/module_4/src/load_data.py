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
    from psycopg import sql
except ModuleNotFoundError:  # pragma: no cover - optional dependency diagnostic
    psycopg = None  # type: ignore[assignment]
    sql = None  # type: ignore[assignment]

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

EXPECTED_FIELD_NAMES: tuple[str, ...] = tuple(
    column_name for column_name, _ in EXPECTED_DATABASE_SCHEMA
)

CREATE_TABLE_SQL_TEMPLATE = """
CREATE TABLE IF NOT EXISTS {} (
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

# Backwards-compatible public-schema SQL string retained for documentation/audits.
CREATE_TABLE_SQL = CREATE_TABLE_SQL_TEMPLATE.format("applicants")

UPSERT_SQL_TEMPLATE = """
INSERT INTO {} (
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

# Backwards-compatible public-schema SQL string.
UPSERT_SQL = UPSERT_SQL_TEMPLATE.format("applicants")

# Original constants below are replaced by the schema-aware templates above.


class DatabaseConnectionError(RuntimeError):
    """Raised when psycopg is unavailable or PostgreSQL cannot be reached."""


def _psycopg_database_url(database_url: str) -> str:
    """Normalize a SQLAlchemy-style PostgreSQL URL for psycopg."""

    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def connect_database(database_url: str | None = None) -> Connection[Any]:
    """Connect to PostgreSQL using ``DATABASE_URL`` or standard ``PG*`` vars.

    Module 4 and GitHub Actions prefer ``DATABASE_URL``.  If no URL is
    supplied, psycopg/libpq automatically reads PGHOST, PGPORT, PGDATABASE,
    PGUSER and PGPASSWORD, preserving the Module 3 workflow.
    """
    if psycopg is None:
        raise DatabaseConnectionError(
            "psycopg is not installed. Run: python -m pip install -r requirements.txt"
        )

    target_url = database_url or os.getenv("DATABASE_URL")
    try:
        if target_url:
            return psycopg.connect(_psycopg_database_url(target_url))
        return psycopg.connect()
    except psycopg.OperationalError as exc:
        raise DatabaseConnectionError(
            "Could not connect to PostgreSQL. Set DATABASE_URL or PGHOST, PGPORT, "
            "PGDATABASE, PGUSER and PGPASSWORD, and make sure PostgreSQL is running."
        ) from exc


def _applicants_table(schema: str):
    """Return a safely quoted ``schema.applicants`` SQL identifier."""

    if sql is None:
        raise DatabaseConnectionError("psycopg is required for database operations")
    return sql.Identifier(schema, "applicants")


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


def create_applicants_table(connection: Connection[Any], schema: str = "public") -> None:
    """Create the required applicants table in ``schema`` and verify it."""

    statement = sql.SQL(CREATE_TABLE_SQL_TEMPLATE).format(_applicants_table(schema))
    with connection.cursor() as cursor:
        cursor.execute(statement)
    validate_database_schema(connection, schema=schema)


def validate_database_schema(
    connection: Connection[Any], schema: str = "public"
) -> None:
    """Fail if an applicants table does not match the Module 3 schema."""

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = 'applicants'
            ORDER BY ordinal_position;
            """,
            (schema,),
        )
        actual_schema = tuple(cursor.fetchall())

        cursor.execute(
            """
            SELECT attribute.attname
            FROM pg_index index_info
            JOIN pg_attribute attribute
              ON attribute.attrelid = index_info.indrelid
             AND attribute.attnum = ANY(index_info.indkey)
            WHERE index_info.indrelid = to_regclass(%s)
              AND index_info.indisprimary
            ORDER BY attribute.attnum;
            """,
            (f"{schema}.applicants",),
        )
        primary_key_columns = tuple(row[0] for row in cursor.fetchall())

    if actual_schema != EXPECTED_DATABASE_SCHEMA:
        raise RuntimeError(
            f"Existing {schema}.applicants table does not match the required schema.\n"
            f"Expected: {EXPECTED_DATABASE_SCHEMA}\n"
            f"Actual:   {actual_schema}"
        )

    if primary_key_columns != ("p_id",):
        raise RuntimeError(
            "The applicants table must use p_id as its primary key. "
            f"Found primary key columns: {primary_key_columns}"
        )


def count_database_rows(connection: Connection[Any], schema: str = "public") -> int:
    """Return the current number of rows in the selected applicants table."""

    statement = sql.SQL("SELECT COUNT(*) FROM {};").format(_applicants_table(schema))
    with connection.cursor() as cursor:
        cursor.execute(statement)
        result = cursor.fetchone()
    if result is None:
        raise RuntimeError("COUNT(*) unexpectedly returned no result")
    return int(result[0])


def upsert_records(
    connection: Connection[Any],
    records: Sequence[dict[str, Any]],
    schema: str = "public",
) -> None:
    """Insert/update records by ``p_id`` without creating duplicates."""

    rows = [_to_database_row(record) for record in records]
    if not rows:
        return
    statement = sql.SQL(UPSERT_SQL_TEMPLATE).format(_applicants_table(schema))
    with connection.cursor() as cursor:
        cursor.executemany(statement, rows)


def load_records_into_connection(
    connection: Connection[Any],
    records: Sequence[dict[str, Any]],
    schema: str = "public",
) -> tuple[int, int, int]:
    """Validate and upsert already-cleaned records into an existing connection.

    This is the dependency-injection seam used by Module 4 PostgreSQL tests: the
    Flask endpoint receives fake scraper rows while the loader writes them to a
    real, isolated PostgreSQL test schema.
    """

    validate_cleaned_records(records)
    _validate_value_types(records)
    create_applicants_table(connection, schema=schema)
    rows_before = count_database_rows(connection, schema=schema)
    upsert_records(connection, records, schema=schema)
    rows_after = count_database_rows(connection, schema=schema)
    return rows_before, rows_after, len(records)


def load_into_database(input_path: str | Path = DEFAULT_INPUT) -> tuple[int, int, int]:
    """Create/validate ``public.applicants`` and upsert cleaned JSON records."""

    records = load_cleaned_records(input_path)
    with connect_database() as connection:
        return load_records_into_connection(connection, records, schema="public")


def _database_environment_summary() -> str:
    """Describe the target without ever printing a password."""
    host = os.getenv("PGHOST", "PostgreSQL default")
    port = os.getenv("PGPORT", "PostgreSQL default")
    database = os.getenv("PGDATABASE", "PostgreSQL default")
    user = os.getenv("PGUSER", "PostgreSQL default")
    return f"host={host}, port={port}, database={database}, user={user}"


def main() -> None:  # pragma: no cover - CLI wrapper
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


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
