"""Run the Module 3 analysis questions with raw PostgreSQL SQL.

This file intentionally uses psycopg cursors and SQL strings only.  The
SQLAlchemy versions required later in the assignment belong in orm_queries.py.

The current scraped GradCafe listing data has no source-supported term,
nationality, GPA, or GRE values.  Correct PostgreSQL aggregate semantics are
therefore preserved: COUNT-based questions may return 0, while percentages or
averages with no usable observations return SQL NULL and are displayed as
"N/A" rather than fabricated as 0.00.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence

from load_data import DatabaseConnectionError, connect_database


@dataclass(frozen=True)
class QuerySpec:
    number: int
    question: str
    sql: str
    explanation: str
    formatter: Callable[[Sequence[tuple[Any, ...]]], str]


def _scalar(rows: Sequence[tuple[Any, ...]]) -> Any:
    if len(rows) != 1 or len(rows[0]) != 1:
        raise ValueError(f"Expected one scalar result, received {rows!r}")
    return rows[0][0]


def format_integer(rows: Sequence[tuple[Any, ...]]) -> str:
    value = _scalar(rows)
    return str(int(value))


def format_percentage(rows: Sequence[tuple[Any, ...]]) -> str:
    value = _scalar(rows)
    return "N/A" if value is None else f"{float(value):.2f}%"


def format_average(rows: Sequence[tuple[Any, ...]]) -> str:
    value = _scalar(rows)
    return "N/A" if value is None else f"{float(value):.2f}"


def format_four_averages(rows: Sequence[tuple[Any, ...]]) -> str:
    if len(rows) != 1 or len(rows[0]) != 4:
        raise ValueError(f"Expected four averages, received {rows!r}")
    labels = ("GPA", "GRE quantitative", "GRE verbal", "GRE analytical writing")
    rendered: list[str] = []
    for label, value in zip(labels, rows[0]):
        rendered_value = "N/A" if value is None else f"{float(value):.2f}"
        rendered.append(f"{label}: {rendered_value}")
    return "; ".join(rendered)


def format_top_universities(rows: Sequence[tuple[Any, ...]]) -> str:
    if not rows:
        return "N/A"
    return "; ".join(f"{name}: {int(count)}" for name, count in rows)


Q1_SQL = """
SELECT COUNT(*)
FROM applicants
WHERE LOWER(TRIM(term)) = 'fall 2026';
""".strip()

Q2_SQL = """
SELECT
    100.0 * COUNT(*) FILTER (
        WHERE LOWER(TRIM(us_or_international)) = 'international'
    )
    / NULLIF(
        COUNT(*) FILTER (
            WHERE LOWER(TRIM(us_or_international)) IN (
                'international', 'american', 'other'
            )
        ),
        0
    ) AS international_percentage
FROM applicants;
""".strip()

Q3_SQL = """
SELECT
    AVG(gpa) AS avg_gpa,
    AVG(gre) AS avg_gre_quantitative,
    AVG(gre_v) AS avg_gre_verbal,
    AVG(gre_aw) AS avg_gre_analytical_writing
FROM applicants;
""".strip()

Q4_SQL = """
SELECT AVG(gpa)
FROM applicants
WHERE LOWER(TRIM(term)) = 'fall 2026'
  AND LOWER(TRIM(us_or_international)) = 'american';
""".strip()

Q5_SQL = """
SELECT
    100.0 * COUNT(*) FILTER (
        WHERE LOWER(TRIM(status)) LIKE 'accept%'
    )
    / NULLIF(COUNT(*), 0) AS accepted_percentage
FROM applicants
WHERE LOWER(TRIM(term)) = 'fall 2025';
""".strip()

Q6_SQL = """
SELECT AVG(gpa)
FROM applicants
WHERE LOWER(TRIM(term)) = 'fall 2026'
  AND LOWER(TRIM(status)) LIKE 'accept%';
""".strip()

Q7_SQL = r"""
SELECT COUNT(*)
FROM applicants
WHERE (
        LOWER(program) LIKE '%johns hopkins%'
        OR LOWER(program) ~ '(^|[^a-z])jhu([^a-z]|$)'
      )
  AND (
        LOWER(program) LIKE '%computer science%'
        OR LOWER(program) ~ '(^|[^a-z])cs([^a-z]|$)'
      )
  AND (
        LOWER(TRIM(degree)) LIKE 'master%'
        OR LOWER(TRIM(degree)) IN ('ms', 'm.s.', 'msc', 'm.sc.')
      );
""".strip()

_TARGET_ORIGINAL_UNIVERSITIES = r"""(
        LOWER(program) LIKE '%georgetown%'
        OR LOWER(program) LIKE '%massachusetts institute of technology%'
        OR LOWER(program) ~ '(^|[^a-z])mit([^a-z]|$)'
        OR LOWER(program) LIKE '%stanford%'
        OR LOWER(program) LIKE '%carnegie mellon%'
        OR LOWER(program) ~ '(^|[^a-z])cmu([^a-z]|$)'
      )"""

Q8_SQL = rf"""
SELECT COUNT(*)
FROM applicants
WHERE LOWER(TRIM(term)) = 'fall 2026'
  AND LOWER(TRIM(status)) LIKE 'accept%'
  AND (
        LOWER(TRIM(degree)) LIKE 'phd%'
        OR LOWER(TRIM(degree)) LIKE 'ph.d%'
        OR LOWER(TRIM(degree)) LIKE 'doctor%'
      )
  AND {_TARGET_ORIGINAL_UNIVERSITIES}
  AND (
        LOWER(program) LIKE '%computer science%'
        OR LOWER(program) ~ '(^|[^a-z])cs([^a-z]|$)'
      );
""".strip()

Q9_SQL = r"""
SELECT COUNT(*)
FROM applicants
WHERE LOWER(TRIM(term)) = 'fall 2026'
  AND LOWER(TRIM(status)) LIKE 'accept%'
  AND (
        LOWER(TRIM(degree)) LIKE 'phd%'
        OR LOWER(TRIM(degree)) LIKE 'ph.d%'
        OR LOWER(TRIM(degree)) LIKE 'doctor%'
      )
  AND (
        LOWER(llm_generated_university) LIKE '%georgetown%'
        OR LOWER(llm_generated_university) LIKE '%massachusetts institute of technology%'
        OR LOWER(llm_generated_university) ~ '(^|[^a-z])mit([^a-z]|$)'
        OR LOWER(llm_generated_university) LIKE '%stanford%'
        OR LOWER(llm_generated_university) LIKE '%carnegie mellon%'
        OR LOWER(llm_generated_university) ~ '(^|[^a-z])cmu([^a-z]|$)'
      )
  AND (
        LOWER(llm_generated_program) LIKE '%computer science%'
        OR LOWER(llm_generated_program) ~ '(^|[^a-z])cs([^a-z]|$)'
      );
""".strip()

Q10_SQL = """
SELECT
    100.0 * COUNT(*) FILTER (
        WHERE LOWER(TRIM(status)) LIKE 'accept%'
    )
    / NULLIF(COUNT(*), 0) AS accepted_percentage
FROM applicants
WHERE status IS NOT NULL
  AND TRIM(status) <> '';
""".strip()

Q11_SQL = """
SELECT llm_generated_university, COUNT(*) AS application_count
FROM applicants
WHERE llm_generated_university IS NOT NULL
  AND TRIM(llm_generated_university) <> ''
GROUP BY llm_generated_university
ORDER BY application_count DESC, llm_generated_university ASC
LIMIT 5;
""".strip()


QUERIES: tuple[QuerySpec, ...] = (
    QuerySpec(
        1,
        "How many applicants are for Fall 2026?",
        Q1_SQL,
        "Counts only rows whose source-backed term is explicitly Fall 2026.",
        format_integer,
    ),
    QuerySpec(
        2,
        "What percentage of usable nationality classifications are international?",
        Q2_SQL,
        "International is the numerator. International, American, and Other form the usable denominator; missing/blank values are excluded.",
        format_percentage,
    ),
    QuerySpec(
        3,
        "What are the average GPA, GRE quantitative, GRE verbal, and GRE analytical-writing scores?",
        Q3_SQL,
        "PostgreSQL AVG ignores NULL independently for each metric, so one missing score does not remove a row from the other averages.",
        format_four_averages,
    ),
    QuerySpec(
        4,
        "What is the average GPA of American applicants for Fall 2026?",
        Q4_SQL,
        "Filters to explicit American and Fall 2026 classifications, then averages only non-NULL GPA values.",
        format_average,
    ),
    QuerySpec(
        5,
        "What percentage of Fall 2025 entries were accepted?",
        Q5_SQL,
        "Uses all explicit Fall 2025 entries as the denominator and accepted statuses as the numerator.",
        format_percentage,
    ),
    QuerySpec(
        6,
        "What is the average GPA of accepted Fall 2026 applicants?",
        Q6_SQL,
        "Filters to explicit Fall 2026 accepted entries and averages only non-NULL GPA values.",
        format_average,
    ),
    QuerySpec(
        7,
        "How many original downloaded records are Johns Hopkins master's applications in Computer Science?",
        Q7_SQL,
        "Uses only original/source-backed program and degree fields and recognizes Johns Hopkins/JHU plus Computer Science/CS and master's degree variants.",
        format_integer,
    ),
    QuerySpec(
        8,
        "How many original-field Fall 2026 accepted PhD Computer Science records are at Georgetown, MIT, Stanford, or Carnegie Mellon?",
        Q8_SQL,
        "Uses the original downloaded program field for institution/program matching plus source term, status, and degree fields.",
        format_integer,
    ),
    QuerySpec(
        9,
        "Repeat Q8 using the LLM-generated program and university fields.",
        Q9_SQL,
        "Uses the LLM-standardized program/university fields while retaining source-backed term, status, and degree filters; the runner also reports the difference from Q8.",
        format_integer,
    ),
    QuerySpec(
        10,
        "Own question: What percentage of all records with a usable status are accepted?",
        Q10_SQL,
        "This analysis uses the well-populated status field and avoids relying on unavailable term/GPA/GRE data.",
        format_percentage,
    ),
    QuerySpec(
        11,
        "Own question: Which five LLM-standardized universities have the most application records?",
        Q11_SQL,
        "Groups the standardized university field and returns the five largest application counts.",
        format_top_universities,
    ),
)


def run_query(connection: Any, spec: QuerySpec) -> list[tuple[Any, ...]]:
    with connection.cursor() as cursor:
        cursor.execute(spec.sql)
        return list(cursor.fetchall())


def run_all_queries(show_sql: bool = False) -> dict[int, tuple[list[tuple[Any, ...]], str]]:
    results: dict[int, tuple[list[tuple[Any, ...]], str]] = {}

    with connect_database() as connection:
        for spec in QUERIES:
            rows = run_query(connection, spec)
            rendered = spec.formatter(rows)
            results[spec.number] = (rows, rendered)

            print(f"Q{spec.number}. {spec.question}")
            if show_sql:
                print("SQL:")
                print(spec.sql)
            if spec.number == 9:
                original_count = int(_scalar(results[8][0]))
                llm_count = int(_scalar(rows))
                difference = llm_count - original_count
                print(
                    "Result: "
                    f"original={original_count}; LLM={llm_count}; difference={difference:+d}"
                )
            else:
                print(f"Result: {rendered}")
            print(f"Explanation: {spec.explanation}")
            print()

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--show-sql",
        action="store_true",
        help="Print each SQL statement along with the result.",
    )
    args = parser.parse_args()

    try:
        run_all_queries(show_sql=args.show_sql)
    except DatabaseConnectionError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
