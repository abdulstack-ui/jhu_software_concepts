"""Sphinx configuration for Module 4 documentation."""

from __future__ import annotations

import os
import sys
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent
MODULE_DIR = DOCS_DIR.parent
SRC_DIR = MODULE_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

# Autodoc imports app.py. Creating the SQLAlchemy engine is lazy, but providing
# a valid URL keeps documentation builds deterministic and independent of the
# developer's local PG* environment variables.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/gradcafe",
)

project = "GradCafe Analytics - Module 4"
author = "Muhammad Abdullah Sarwar"
release = "1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

autodoc_typehints = "description"
autodoc_member_order = "bysource"

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_title = "GradCafe Analytics - Module 4"
