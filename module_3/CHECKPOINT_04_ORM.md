# Checkpoint 04 - SQLAlchemy ORM

This checkpoint implements the assignment's SQLAlchemy 2.x portion against the
same PostgreSQL `applicants` table loaded by `load_data.py`.

- `models.py` maps all 15 existing database columns to the `Applicant` model.
- `p_id` is the ORM primary key.
- PostgreSQL connection settings remain outside source code in the standard
  `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, and `PGPASSWORD` environment
  variables.
- `orm_queries.py` repeats Questions 1, 4, 5, 8, 9, and original Question 10
  with SQLAlchemy expressions and `Session` objects.
- The ORM code does not use `text("SELECT ...")`, a psycopg cursor, or a second
  copy of the applicants table.
- ORM output uses the same whole-number, two-decimal average, and two-decimal
  percentage formatting as the raw-SQL portion.

Run:

```powershell
python orm_queries.py
python checkpoint_04_audit.py
```

For the checkpoint dataset, ORM results should match the raw SQL results:
Q1 = 29,534; Q4 = 3.78; Q5 = 43.88%; Q8 = 25; Q9 = 25 vs. 25 (difference +0);
and Q10 = 36.36%.
