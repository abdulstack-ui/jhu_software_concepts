# Checkpoint 05 - Dynamic Flask Analysis Page

This checkpoint adds the single dynamic Flask analysis page required by Module 3.

- `app.py` opens SQLAlchemy sessions through the existing `models.py` configuration.
- `orm_queries.py` now exposes all eleven analyses for the webpage while retaining the six required standalone ORM queries.
- `templates/index.html` renders Questions 1-11 dynamically from PostgreSQL.
- `static/styles.css` provides responsive page styling.
- `Update Analysis` re-queries PostgreSQL without starting a scraper.

The Pull Data/scraping workflow and active-scrape coordination are intentionally handled in the next checkpoint so they can be tested separately.
