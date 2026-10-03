"""Packaging configuration for Module 5."""

from setuptools import setup


RUNTIME_REQUIREMENTS = [
    "beautifulsoup4>=4.12",
    "selenium>=4.20",
    "psycopg[binary]>=3.2,<4",
    "SQLAlchemy>=2,<3",
    "Flask>=3,<4",
]


setup(
    name="jhu-software-concepts-module5",
    version="0.1.0",
    description="JHU Modern Software Concepts Module 5 application",
    package_dir={"": "src"},
    py_modules=[
        "app",
        "capture",
        "clean",
        "load_data",
        "models",
        "orm_queries",
        "pull_data",
        "query_data",
        "scrape",
    ],
    install_requires=RUNTIME_REQUIREMENTS,
    python_requires=">=3.11",
)
