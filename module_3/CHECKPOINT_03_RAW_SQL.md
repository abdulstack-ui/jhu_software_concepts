# Checkpoint 03 - Raw SQL analysis

This checkpoint implements the eleven required raw-SQL analyses in `query_data.py`: assignment questions Q1-Q9 plus two student-defined questions. The implementation uses psycopg and executable PostgreSQL `SELECT` statements only; SQLAlchemy is intentionally reserved for Checkpoint 04.

## Missing-data rule

The current 30,011-row source-backed dataset has zero non-NULL values for `term`, `us_or_international`, `gpa`, `gre`, `gre_v`, and `gre_aw`. The SQL therefore does not impute or infer any of those values. Count questions over an unavailable category can correctly return `0`; percentages with no usable denominator and averages with no usable observations return SQL `NULL` and are displayed as `N/A`. This distinction avoids falsely reporting `0.00%` or `0.00` when the data needed to compute the statistic do not exist.

## Run

With PostgreSQL environment variables set:

```powershell
python checkpoint_03_audit.py
python query_data.py
python query_data.py --show-sql
python checkpoint_03_audit.py --database
```

`python query_data.py` is the concise terminal output to use for the required raw-SQL screenshot. `--show-sql` prints the same results together with every executable SQL statement and is useful when preparing `query_results.pdf` later.

## Own questions

Q10 asks what percentage of records with a usable status are accepted. Q11 asks which five LLM-standardized universities have the most application records. These questions were chosen because they are meaningful with the fields actually present in the scraped dataset rather than relying on unavailable term/GPA/GRE information.
