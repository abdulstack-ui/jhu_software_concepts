"""Page routes for the Module 1 personal developer website.

This module defines a Flask Blueprint containing the routes for the
Home, Projects, and Contact pages.
"""

from flask import Blueprint, render_template


# A Blueprint keeps the page routes separate from application startup logic.
pages = Blueprint("pages", __name__)


@pages.route("/")
def home():
    """Render the website homepage.

    Returns:
        str: Rendered HTML for the homepage.
    """
    return render_template("home.html")


@pages.route("/projects")
def projects():
    """Render the projects page.

    Returns:
        str: Rendered HTML describing completed course projects.
    """
    return render_template("projects.html")


@pages.route("/contact")
def contact():
    """Render the contact page.

    Returns:
        str: Rendered HTML containing contact information.
    """
    return render_template("contact.html")