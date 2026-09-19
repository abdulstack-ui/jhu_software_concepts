"""Repeat selected Module 3 analyses using SQLAlchemy ORM expressions.

Required ORM repetitions:
- Question 1
- Question 4
- Question 5
- Question 8
- Question 9
- one original question (Question 10 here)

No handwritten SQL strings or raw psycopg cursors are used in this file.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from models import Applicant, SessionLocal


# Reusable SQLAlchemy expressions.  They mirror the filtering rules already
# used by the raw-SQL analysis in query_data.py.
TERM_FALL_2026 = func.lower(func.trim(Applicant.term)) == "fall 2026"
TERM_FALL_2025 = func.lower(func.trim(Applicant.term)) == "fall 2025"
AMERICAN = func.lower(func.trim(Applicant.us_or_international)) == "american"
ACCEPTED = func.lower(func.trim(Applicant.status)).like("accept%")
PHD = or_(
    func.lower(func.trim(Applicant.degree)).like("phd%"),
    func.lower(func.trim(Applicant.degree)).like("ph.d%"),
    func.lower(func.trim(Applicant.degree)).like("doctor%"),
)


def _original_target_university_expression() -> Any:
    program = func.lower(Applicant.program)
    return or_(
        program.like("%georgetown%"),
        program.like("%massachusetts institute of technology%"),
        program.op("~")(r"(^|[^a-z])mit([^a-z]|$)"),
        program.like("%stanford%"),
        program.like("%carnegie mellon%"),
        program.op("~")(r"(^|[^a-z])cmu([^a-z]|$)"),
    )


def _original_computer_science_expression() -> Any:
    program = func.lower(Applicant.program)
    return or_(
        program.like("%computer science%"),
        program.op("~")(r"(^|[^a-z])cs([^a-z]|$)"),
    )


def _llm_target_university_expression() -> Any:
    university = func.lower(Applicant.llm_generated_university)
    return or_(
        university.like("%georgetown%"),
        university.like("%massachusetts institute of technology%"),
        university.op("~")(r"(^|[^a-z])mit([^a-z]|$)"),
        university.like("%stanford%"),
        university.like("%carnegie mellon%"),
        university.op("~")(r"(^|[^a-z])cmu([^a-z]|$)"),
    )


def _llm_computer_science_expression() -> Any:
    program = func.lower(Applicant.llm_generated_program)
    return or_(
        program.like("%computer science%"),
        program.op("~")(r"(^|[^a-z])cs([^a-z]|$)"),
    )


def question_1(session: Session) -> int:
    """Q1: count Fall 2026 applicants."""

    statement = (
        select(func.count())
        .select_from(Applicant)
        .where(TERM_FALL_2026)
    )
    return int(session.scalar(statement) or 0)


def question_4(session: Session) -> float | None:
    """Q4: average GPA of American Fall 2026 applicants."""

    statement = select(func.avg(Applicant.gpa)).where(
        and_(
            TERM_FALL_2026,
            AMERICAN,
            Applicant.gpa.is_not(None),
        )
    )
    value = session.scalar(statement)
    return None if value is None else float(value)


def question_5(session: Session) -> float | None:
    """Q5: percentage of Fall 2025 entries that are acceptances."""

    statement = (
        select(
            func.count().filter(ACCEPTED),
            func.count(),
        )
        .select_from(Applicant)
        .where(TERM_FALL_2025)
    )
    accepted_count, total_count = session.execute(statement).one()
    if not total_count:
        return None
    return 100.0 * float(accepted_count) / float(total_count)


def question_8(session: Session) -> int:
    """Q8: original-field target-university Fall 2026 accepted PhD CS count."""

    statement = (
        select(func.count())
        .select_from(Applicant)
        .where(
            and_(
                TERM_FALL_2026,
                ACCEPTED,
                PHD,
                _original_target_university_expression(),
                _original_computer_science_expression(),
            )
        )
    )
    return int(session.scalar(statement) or 0)


def question_9(session: Session) -> int:
    """Q9: Q8 repeated with LLM program/university fields."""

    statement = (
        select(func.count())
        .select_from(Applicant)
        .where(
            and_(
                TERM_FALL_2026,
                ACCEPTED,
                PHD,
                _llm_target_university_expression(),
                _llm_computer_science_expression(),
            )
        )
    )
    return int(session.scalar(statement) or 0)


def question_10(session: Session) -> float | None:
    """Own Q10: percentage of records with a usable status that are accepted."""

    usable_status = and_(
        Applicant.status.is_not(None),
        func.trim(Applicant.status) != "",
    )
    statement = (
        select(
            func.count().filter(ACCEPTED),
            func.count(),
        )
        .select_from(Applicant)
        .where(usable_status)
    )
    accepted_count, total_count = session.execute(statement).one()
    if not total_count:
        return None
    return 100.0 * float(accepted_count) / float(total_count)


def run_orm_analysis(session: Session) -> dict[int, Any]:
    """Run the six analyses required for the ORM portion."""

    q1 = question_1(session)
    q4 = question_4(session)
    q5 = question_5(session)
    q8 = question_8(session)
    q9 = question_9(session)
    q10 = question_10(session)

    return {
        1: q1,
        4: q4,
        5: q5,
        8: q8,
        9: (q8, q9, q9 - q8),
        10: q10,
    }


def _format_average(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}"


def _format_percentage(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}%"


def main() -> None:
    with SessionLocal() as session:
        results = run_orm_analysis(session)

    original_count, llm_count, difference = results[9]

    print("Q1. How many applicants are for Fall 2026?")
    print(f"Result: {results[1]}")
    print()

    print("Q4. What is the average GPA of American applicants for Fall 2026?")
    print(f"Result: {_format_average(results[4])}")
    print()

    print("Q5. What percentage of Fall 2025 entries were accepted?")
    print(f"Result: {_format_percentage(results[5])}")
    print()

    print(
        "Q8. How many original-field Fall 2026 accepted PhD Computer Science "
        "records are at Georgetown, MIT, Stanford, or Carnegie Mellon?"
    )
    print(f"Result: {results[8]}")
    print()

    print("Q9. Repeat Q8 using the LLM-generated program and university fields.")
    print(
        "Result: "
        f"original={original_count}; LLM={llm_count}; difference={difference:+d}"
    )
    print()

    print(
        "Q10. Own question: What percentage of all records with a usable status "
        "are accepted?"
    )
    print(f"Result: {_format_percentage(results[10])}")


if __name__ == "__main__":
    main()
