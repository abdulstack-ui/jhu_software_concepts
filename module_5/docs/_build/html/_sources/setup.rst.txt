Setup and Configuration
=======================

Requirements
------------

Install the project dependencies from the repository root::

   python -m pip install -r module_4/requirements.txt

PostgreSQL configuration
------------------------

``DATABASE_URL`` is the preferred Module 4 database setting. Example::

   $env:DATABASE_URL = "postgresql://postgres:YOUR_PASSWORD@localhost:5432/gradcafe"

The inherited Module 3 PostgreSQL variables are also supported::

   $env:PGHOST = "localhost"
   $env:PGPORT = "5432"
   $env:PGDATABASE = "gradcafe"
   $env:PGUSER = "postgres"
   $env:PGPASSWORD = "YOUR_PASSWORD"

Do not commit passwords or ``.env`` files. GitHub Actions supplies its own
ephemeral PostgreSQL service and test connection string.

Run the Flask app
-----------------

From the repository root::

   python module_4/src/app.py

The canonical analysis route is ``/analysis``. The root route remains as a
compatibility redirect.

Build the documentation
-----------------------

Generate local Sphinx HTML with::

   python -m sphinx -W --keep-going -b html module_4/docs module_4/docs/_build/html

Open ``module_4/docs/_build/html/index.html`` in a browser to inspect the
result.
