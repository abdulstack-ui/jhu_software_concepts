"""SQLAlchemy 2.x model for the existing Module 3 PostgreSQL database.

The assignment already creates and loads ``public.applicants`` through
``load_data.py``.  This module maps that same table to an ``Applicant`` Python
class; it does not create a second table or copy any data.

Connection settings come from the standard PostgreSQL environment variables:
PGHOST, PGPORT, PGDATABASE, PGUSER, and PGPASSWORD.
"""

from __future__ import annotations

import os
from datetime import date
from typing import Optional

from sqlalchemy import Date, Float, Integer, Text, URL, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    """Base class for SQLAlchemy ORM mappings."""


def _database_url() -> URL:
    """Build a psycopg SQLAlchemy URL without embedding credentials in code.

    Parameters omitted from the URL remain available to psycopg/libpq through
    the standard PostgreSQL environment variables.
    """

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


# Creating an Engine does not create tables or open a connection immediately.
# It simply configures SQLAlchemy to use the same PostgreSQL database.
engine = create_engine(_database_url(), pool_pre_ping=True)

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    expire_on_commit=False,
)
