"""Entry point for the Module 1 personal developer website.

This module creates the Flask application, registers the page blueprint,
and starts the development server on localhost port 8080.
"""

from flask import Flask

from pages import pages


# Create the Flask application and register the site's routes.
app = Flask(__name__)
app.register_blueprint(pages)


if __name__ == "__main__":
    # Run the application on the port required by the assignment.
    app.run(host="localhost", port=8080, debug=True)