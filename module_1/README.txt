Module 1 - Personal Developer Website
EN.605.256 - Modern Concepts in Python
Johns Hopkins University - Whiting School of Engineering
Fall 2026

Author: Abdul Sarwar


PROJECT DESCRIPTION

This project is a personal developer website built using Python, Flask,
HTML, and CSS.

The website contains three main pages:

1. Home
   - Includes my name, position, biography, and profile photo.

2. Projects
   - Describes the Module 1 personal website project.
   - Includes a link to the GitHub repository.

3. Contact
   - Includes my email address and LinkedIn profile.

The application also uses Flask Blueprints, HTML templates, CSS styling,
and a navigation bar that highlights the currently selected page.


REQUIREMENTS

- Python 3.10 or newer
- Flask

The required Python packages are listed in requirements.txt.


INSTALLATION

1. Open a terminal or PowerShell window.

2. Navigate to the module_1 directory.

3. Install the required packages with:

   python -m pip install -r requirements.txt


RUNNING THE WEBSITE

From inside the module_1 directory, run:

   python run.py

The Flask development server will start on port 8080.

Open a web browser and go to:

   http://localhost:8080


PROJECT STRUCTURE

module_1/
    run.py
    pages.py
    requirements.txt
    README.txt

    static/
        style.css
        profile.jpg

    templates/
        base.html
        home.html
        projects.html
        contact.html


GITHUB REPOSITORY

git@github.com:abdulstack-ui/jhu_software_concepts.git