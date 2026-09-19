"""Module 3 analyses expressed with SQLAlchemy 2.x ORM expressions.

The console entry point repeats the six analyses required for the ORM portion
(Q1, Q4, Q5, Q8, Q9, and Q10).  Additional ORM functions are provided for the
Flask analysis page so every database read shown in the webpage goes through
the existing ``Applicant`` SQLAlchemy model rather than handwritten SQL.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from models import Applicant, SessionLocal


TERM_FALL_2026 = func.lower(func.trim(Applicant.term)) == "fall 2026"
TERM_FALL_2025 = func.lower(func.trim(Applicant.term)) == "fall 2025"
AMERICAN = func.lower(func.trim(Applicant.us_or_international)) == "american"
ACCEPTED = func.lower(func.trim(Applicant.status)).like("accept%")
PHD = or_(
    func.lower(func.trim(Applicant.degree)).like("phd%"),
    func.lower(func.trim(Applicant.degree)).like("ph.d%"),
    func.lower(func.trim(Applicant.degree)).like("doctor%"),
)
MASTER = or_(
    func.lower(func.trim(Applicant.degree)).like("master%"),
    func.lower(func.trim(Applicant.degree)).in_(("ms", "m.s.", "msc", "m.sc.")),
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
    statement = select(func.count()).select_from(Applicant).where(TERM_FALL_2026)
    return int(session.scalar(statement) or 0)


def question_2(session: Session) -> float | None:
    nationality = func.lower(func.trim(Applicant.us_or_international))
    usable = nationality.in_(("international", "american", "other"))
    international = nationality == "international"
    statement = select(
        func.count().filter(international),
        func.count().filter(usable),
    ).select_from(Applicant)
    international_count, usable_count = session.execute(statement).one()
    if not usable_count:
        return None
    return 100.0 * float(international_count) / float(usable_count)


def question_3(session: Session) -> tuple[float | None, float | None, float | None, float | None]:
    statement = select(
        func.avg(Applicant.gpa),
        func.avg(Applicant.gre),
        func.avg(Applicant.gre_v),
        func.avg(Applicant.gre_aw),
    )
    row = session.execute(statement).one()
    return tuple(None if value is None else float(value) for value in row)  # type: ignore[return-value]


def question_4(session: Session) -> float | None:
    statement = select(func.avg(Applicant.gpa)).where(
        and_(TERM_FALL_2026, AMERICAN, Applicant.gpa.is_not(None))
    )
    value = session.scalar(statement)
    return None if value is None else float(value)


def question_5(session: Session) -> float | None:
    statement = (
        select(func.count().filter(ACCEPTED), func.count())
        .select_from(Applicant)
        .where(TERM_FALL_2025)
    )
    accepted_count, total_count = session.execute(statement).one()
    if not total_count:
        return None
    return 100.0 * float(accepted_count) / float(total_count)


def question_6(session: Session) -> float | None:
    statement = select(func.avg(Applicant.gpa)).where(
        and_(TERM_FALL_2026, ACCEPTED, Applicant.gpa.is_not(None))
    )
    value = session.scalar(statement)
    return None if value is None else float(value)


def question_7(session: Session) -> int:
    program = func.lower(Applicant.program)
    johns_hopkins = or_(
        program.like("%johns hopkins%"),
        program.op("~")(r"(^|[^a-z])jhu([^a-z]|$)"),
    )
    statement = (
        select(func.count())
        .select_from(Applicant)
        .where(and_(johns_hopkins, _original_computer_science_expression(), MASTER))
    )
    return int(session.scalar(statement) or 0)


def question_8(session: Session) -> int:
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
    usable_status = and_(Applicant.status.is_not(None), func.trim(Applicant.status) != "")
    statement = (
        select(func.count().filter(ACCEPTED), func.count())
        .select_from(Applicant)
        .where(usable_status)
    )
    accepted_count, total_count = session.execute(statement).one()
    if not total_count:
        return None
    return 100.0 * float(accepted_count) / float(total_count)


def question_11(session: Session) -> list[tuple[str, int]]:
    usable = and_(
        Applicant.llm_generated_university.is_not(None),
        func.trim(Applicant.llm_generated_university) != "",
    )
    application_count = func.count().label("application_count")
    statement = (
        select(Applicant.llm_generated_university, application_count)
        .where(usable)
        .group_by(Applicant.llm_generated_university)
        .order_by(application_count.desc(), Applicant.llm_generated_university.asc())
        .limit(5)
    )
    return [(str(name), int(count)) for name, count in session.execute(statement).all()]


def run_orm_analysis(session: Session) -> dict[int, Any]:
    """Run the six analyses required for the standalone ORM portion."""
    q1 = question_1(session)
    q4 = question_4(session)
    q5 = question_5(session)
    q8 = question_8(session)
    q9 = question_9(session)
    q10 = question_10(session)
    return {1: q1, 4: q4, 5: q5, 8: q8, 9: (q8, q9, q9 - q8), 10: q10}


def _format_average(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}"


def _format_percentage(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}%"


def _format_four_averages(values: tuple[float | None, float | None, float | None, float | None]) -> str:
    labels = ("GPA", "GRE quantitative", "GRE verbal", "GRE analytical writing")
    return "; ".join(f"{label}: {_format_average(value)}" for label, value in zip(labels, values))


def _format_top_universities(values: list[tuple[str, int]]) -> str:
    return "N/A" if not values else "; ".join(f"{name}: {count}" for name, count in values)


WEB_QUESTIONS = {
    1: "How many applicants are for Fall 2026?",
    2: "What percentage of usable nationality classifications are international?",
    3: "What are the average GPA, GRE quantitative, GRE verbal, and GRE analytical-writing scores?",
    4: "What is the average GPA of American applicants for Fall 2026?",
    5: "What percentage of Fall 2025 entries were accepted?",
    6: "What is the average GPA of accepted Fall 2026 applicants?",
    7: "How many original downloaded records are Johns Hopkins master's applications in Computer Science?",
    8: "How many original-field Fall 2026 accepted PhD Computer Science records are at Georgetown, MIT, Stanford, or Carnegie Mellon?",
    9: "Repeat Q8 using the LLM-generated program and university fields.",
    10: "Own question: What percentage of all records with a usable status are accepted?",
    11: "Own question: Which five LLM-standardized universities have the most application records?",
}

WEB_EXPLANATIONS = {
    1: "Counts rows whose source-backed term is Fall 2026.",
    2: "Uses International as the numerator and International, American, and Other as the usable denominator.",
    3: "Calculates each average independently, allowing each metric to use all of its own non-missing values.",
    4: "Filters to American Fall 2026 applicants and averages their non-missing GPA values.",
    5: "Divides accepted Fall 2025 entries by all Fall 2025 entries.",
    6: "Filters to accepted Fall 2026 applicants and averages their non-missing GPA values.",
    7: "Uses the original program and degree fields to identify JHU/Johns Hopkins master's Computer Science records.",
    8: "Uses original fields for the target universities/program plus source term, status, and degree.",
    9: "Uses LLM-standardized program/university fields while retaining source term, status, and degree filters.",
    10: "Calculates the share of records with a usable status that are classified as accepted.",
    11: "Groups by LLM-standardized university and returns the five largest application counts.",
}


def run_web_analysis(session: Session) -> list[dict[str, Any]]:
    """Return all eleven dynamically queried analyses for the Flask page."""
    q1 = question_1(session)
    q2 = question_2(session)
    q3 = question_3(session)
    q4 = question_4(session)
    q5 = question_5(session)
    q6 = question_6(session)
    q7 = question_7(session)
    q8 = question_8(session)
    q9 = question_9(session)
    q10 = question_10(session)
    q11 = question_11(session)

    formatted = {
        1: f"{q1:,}",
        2: _format_percentage(q2),
        3: _format_four_averages(q3),
        4: _format_average(q4),
        5: _format_percentage(q5),
        6: _format_average(q6),
        7: f"{q7:,}",
        8: f"{q8:,}",
        9: f"Original-field count: {q8:,}; LLM-field count: {q9:,}; Difference: {q9 - q8:+d}",
        10: _format_percentage(q10),
        11: _format_top_universities(q11),
    }

    return [
        {
            "number": number,
            "question": WEB_QUESTIONS[number],
            "result": formatted[number],
            "explanation": WEB_EXPLANATIONS[number],
        }
        for number in range(1, 12)
    ]


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
    print("Q8. How many original-field Fall 2026 accepted PhD Computer Science records are at Georgetown, MIT, Stanford, or Carnegie Mellon?")
    print(f"Result: {results[8]}")
    print()
    print("Q9. Repeat Q8 using the LLM-generated program and university fields.")
    print(f"Result: original={original_count}; LLM={llm_count}; difference={difference:+d}")
    print()
    print("Q10. Own question: What percentage of all records with a usable status are accepted?")
    print(f"Result: {_format_percentage(results[10])}")


if __name__ == "__main__":
    main()
