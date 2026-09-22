"""Static audit for Module 4 Sphinx/Read the Docs deliverables."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
DOCS = ROOT / "docs"

checks: list[tuple[str, bool]] = []


def add(label: str, condition: bool) -> None:
    checks.append((label, bool(condition)))


required_files = [
    DOCS / "conf.py",
    DOCS / "index.rst",
    DOCS / "overview.rst",
    DOCS / "setup.rst",
    DOCS / "architecture.rst",
    DOCS / "api.rst",
    DOCS / "testing.rst",
    DOCS / "operations.rst",
    REPO / ".readthedocs.yaml",
]
for path in required_files:
    add(f"exists: {path.relative_to(REPO)}", path.exists())

conf = (DOCS / "conf.py").read_text(encoding="utf-8")
api = (DOCS / "api.rst").read_text(encoding="utf-8")
setup = (DOCS / "setup.rst").read_text(encoding="utf-8")
arch = (DOCS / "architecture.rst").read_text(encoding="utf-8")
testing = (DOCS / "testing.rst").read_text(encoding="utf-8")
ops = (DOCS / "operations.rst").read_text(encoding="utf-8")
rtd = (REPO / ".readthedocs.yaml").read_text(encoding="utf-8")
reqs = (ROOT / "requirements.txt").read_text(encoding="utf-8")

add("Sphinx autodoc enabled", "sphinx.ext.autodoc" in conf)
add("Read the Docs theme configured", "sphinx_rtd_theme" in conf)
for module in ["app", "scrape", "clean", "load_data", "query_data"]:
    add(f"autodoc module: {module}", f".. automodule:: {module}" in api)
add("DATABASE_URL documented", "DATABASE_URL" in setup)
add("PG fallback variables documented", "PGHOST" in setup and "PGPASSWORD" in setup)
add("web architecture documented", "Web layer" in arch)
add("ETL architecture documented", "ETL layer" in arch)
add("database architecture documented", "Database and analysis layer" in arch)
add("markers documented", all(m in testing for m in ["web", "buttons", "analysis", "db", "integration"]))
add("100 percent coverage documented", "100 percent" in testing)
add("troubleshooting documented", "Troubleshooting" in ops)
add("Read the Docs config points at conf.py", "module_4/docs/conf.py" in rtd)
add("Sphinx dependency", "Sphinx" in reqs)
add("RTD theme dependency", "sphinx-rtd-theme" in reqs)

print("CHECKPOINT 07 STATIC AUDIT")
for label, ok in checks:
    print(f"  {'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("CHECKPOINT 07 STATIC AUDIT: FAIL")
print("CHECKPOINT 07 STATIC AUDIT: PASS")
