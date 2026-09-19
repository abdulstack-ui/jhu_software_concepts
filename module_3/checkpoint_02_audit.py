"""Audit Module 3 Checkpoint 02: PostgreSQL schema and data loading."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import Any

from load_data import (
    CREATE_TABLE_SQL,
    UPSERT_SQL,
    DatabaseConnectionError,
    EXPECTED_DATABASE_SCHEMA,
    connect_database,
    load_cleaned_records,
    validate_database_schema,
)

SOURCE_PATH = Path("cleaned_applicant_data.json")
EXPECTED_FIELDS = (
    "p_id",
    "program",
    "comments",
    "date_added",
    "url",
    "status",
    "term",
    "us_or_international",
    "gpa",
    "gre",
    "gre_v",
    "gre_aw",
    "degree",
    "llm_generated_program",
    "llm_generated_university",
)


def local_audit() -> list[dict[str, Any]]:
    """Verify the database input and loader contract without needing PostgreSQL."""
    records = load_cleaned_records(SOURCE_PATH)
    if len(records) < 30_000:
        raise AssertionError(f"Expected at least 30,000 records, found {len(records):,}")

    if tuple(records[0].keys()) != EXPECTED_FIELDS:
        raise AssertionError("Cleaned JSON field order/schema is not the required schema")

    p_ids = {record["p_id"] for record in records}
    urls = {record["url"] for record in records}
    if len(p_ids) != len(records):
        raise AssertionError("Duplicate p_id values exist in cleaned input")
    if len(urls) != len(records):
        raise AssertionError("Duplicate URLs exist in cleaned input")

    expected_names = tuple(name for name, _ in EXPECTED_DATABASE_SCHEMA)
    if expected_names != EXPECTED_FIELDS:
        raise AssertionError("PostgreSQL schema and cleaned JSON fields are out of sync")

    normalized_create = " ".join(CREATE_TABLE_SQL.lower().split())
    for name, data_type in EXPECTED_DATABASE_SCHEMA:
        required_definition = f"{name} {data_type}"
        if name == "p_id":
            required_definition += " primary key"
        if required_definition not in normalized_create:
            raise AssertionError(
                f"CREATE TABLE statement is missing: {required_definition}"
            )
    if "on conflict (p_id) do update" not in " ".join(UPSERT_SQL.lower().split()):
        raise AssertionError("Loader is missing p_id conflict handling/idempotency")

    print("CHECKPOINT 02 LOCAL AUDIT: PASS")
    print(f"Cleaned records validated: {len(records):,}")
    print("Required applicants columns: 15 / 15")
    print("Duplicate p_id values: 0")
    print("Duplicate URLs: 0")
    print("Credentials are supplied through PostgreSQL environment variables.")
    return records


def _database_value(value: Any) -> Any:
    """Normalize PostgreSQL-returned values for comparison to JSON."""
    if isinstance(value, date):
        return value.isoformat()
    return value


def database_audit(records: list[dict[str, Any]]) -> None:
    """Verify live PostgreSQL schema, uniqueness, and row-for-row source fidelity."""
    source_by_id = {record["p_id"]: record for record in records}
    source_ids = list(source_by_id)

    with connect_database() as connection:
        validate_database_schema(connection)

        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM applicants;")
            total_rows = int(cursor.fetchone()[0])

            cursor.execute(
                "SELECT COUNT(*) - COUNT(DISTINCT p_id) FROM applicants;"
            )
            duplicate_ids = int(cursor.fetchone()[0])

            cursor.execute(
                "SELECT COUNT(*) - COUNT(DISTINCT url) FROM applicants;"
            )
            duplicate_urls = int(cursor.fetchone()[0])

            cursor.execute(
                """
                SELECT p_id, program, comments, date_added, url, status, term,
                       us_or_international, gpa, gre, gre_v, gre_aw, degree,
                       llm_generated_program, llm_generated_university
                FROM applicants
                WHERE p_id = ANY(%s)
                ORDER BY p_id;
                """,
                (source_ids,),
            )
            database_rows = cursor.fetchall()

    if duplicate_ids != 0:
        raise AssertionError(f"Database contains {duplicate_ids} duplicate p_id rows")
    if duplicate_urls != 0:
        raise AssertionError(f"Database contains {duplicate_urls} duplicate URLs")

    if len(database_rows) != len(records):
        raise AssertionError(
            "Not all cleaned source rows are present in PostgreSQL: "
            f"expected {len(records):,}, found {len(database_rows):,}"
        )

    field_names = EXPECTED_FIELDS
    for row in database_rows:
        database_record = {
            field: _database_value(value)
            for field, value in zip(field_names, row, strict=True)
        }
        source_record = source_by_id[database_record["p_id"]]
        if database_record != source_record:
            differences = {
                field: (source_record[field], database_record[field])
                for field in field_names
                if source_record[field] != database_record[field]
            }
            raise AssertionError(
                f"Database/source mismatch for p_id={database_record['p_id']}: "
                f"{differences}"
            )

    print("CHECKPOINT 02 LIVE DATABASE AUDIT: PASS")
    print(f"Database rows currently present: {total_rows:,}")
    print(f"Cleaned source rows matched exactly: {len(database_rows):,}")
    print("Primary key: p_id")
    print("Duplicate p_id rows: 0")
    print("Duplicate URLs: 0")
    print("Source NULL values remain SQL NULL; no values were fabricated by the loader.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database",
        action="store_true",
        help="Also connect to PostgreSQL and verify the live applicants table.",
    )
    args = parser.parse_args()

    records = local_audit()
    if args.database:
        try:
            database_audit(records)
        except DatabaseConnectionError as exc:
            raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
