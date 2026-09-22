"""SQLAlchemy model and connection helpers for the GradCafe database.

The application maps the existing ``public.applicants`` table created by
``load_data.py``.  Connection details come from ``DATABASE_URL`` when it is
set; otherwise the standard PostgreSQL ``PG*`` environment variables are used.
No credentials are hard-coded in source code.
"""

from __future__ import annotations

import os
from datetime import date
from typing import Optional

from sqlalchemy import Date, Float, Integer, Text, URL, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    """Base class for SQLAlchemy ORM mappings."""


def _database_url(database_url: str | URL | None = None) -> URL:
    """Return the SQLAlchemy URL used by the application.

    ``DATABASE_URL`` is the preferred portable configuration used by Module 4
    and CI.  If it is absent, the Module 3 ``PGHOST``/``PGPORT``/``PGDATABASE``/
    ``PGUSER``/``PGPASSWORD`` variables remain supported for backwards
    compatibility.
    """

    raw_url = database_url or os.getenv("DATABASE_URL")
    if raw_url:
        url = make_url(str(raw_url))
        if url.drivername == "postgresql":
            url = url.set(drivername="postgresql+psycopg")
        return url

    raw_port = os.getenv("PGPORT")
    port = int(raw_port) if raw_port else None
    return URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        host=os.getenv("PGHOST"),
        port=port,
        database=os.getenv("PGDATABASE"),
    )


def make_session_factory(database_url: str | URL | None = None):
    """Create a SQLAlchemy session factory without opening a DB connection yet."""

    db_engine = create_engine(_database_url(database_url), pool_pre_ping=True)
    return sessionmaker(
        bind=db_engine,
        class_=Session,
        expire_on_commit=False,
    )


class Applicant(Base):
    """ORM mapping for the existing ``applicants`` table."""

    __tablename__ = "applicants"

    p_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program: Mapped[Optional[str]] = mapped_column(Text)
    comments: Mapped[Optional[str]] = mapped_column(Text)
    date_added: Mapped[Optional[date]] = mapped_column(Date)
    url: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[Optional[str]] = mapped_column(Text)
    term: Mapped[Optional[str]] = mapped_column(Text)
    us_or_international: Mapped[Optional[str]] = mapped_column(Text)
    gpa: Mapped[Optional[float]] = mapped_column(Float)
    gre: Mapped[Optional[float]] = mapped_column(Float)
    gre_v: Mapped[Optional[float]] = mapped_column(Float)
    gre_aw: Mapped[Optional[float]] = mapped_column(Float)
    degree: Mapped[Optional[str]] = mapped_column(Text)
    llm_generated_program: Mapped[Optional[str]] = mapped_column(Text)
    llm_generated_university: Mapped[Optional[str]] = mapped_column(Text)


# Module 3 entry points still import SessionLocal directly.  Creating an engine
# does not connect to PostgreSQL, so keeping this alias is safe and preserves
# backwards compatibility while Module 4's app factory can create an override.
SessionLocal = make_session_factory()
