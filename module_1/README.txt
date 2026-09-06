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
   - Includes my name, position, biography, academic interests, and
     profile photograph.

2. Projects
   - Describes my Module 1 personal developer website project.
   - Lists the technologies used to create the project.
   - Includes a link to the Module 1 GitHub source code.

3. Contact
   - Includes my Johns Hopkins email address.
   - Includes a link to my LinkedIn profile.

The application uses Flask Blueprints to organize page routes, reusable
Jinja HTML templates for page structure, CSS for styling and responsive
layout, and Git/GitHub for version control.


REQUIREMENTS

- Python 3.10 or newer
- Flask 3.1.3

The required Python package is listed in requirements.txt.


INSTALLATION

1. Open a terminal or PowerShell window.

2. Navigate to the module_1 directory.

3. Install the required packages:

   python -m pip install -r requirements.txt


RUNNING THE WEBSITE

From inside the module_1 directory, run:

   python run.py

The Flask development server will start on port 8080.

Open a web browser and navigate to:

   http://localhost:8080


WEBSITE ROUTES

Home:
   http://localhost:8080/

Projects:
   http://localhost:8080/projects

Contact:
   http://localhost:8080/contact


PROJECT STRUCTURE

module_1/
    run.py
    pages.py
    requirements.txt
    README.txt
    Module_1_Screenshots.pdf

    static/
        style.css
        profile.jpg

    templates/
        base.html
        home.html
        projects.html
        contact.html


GITHUB REPOSITORY

SSH:
git@github.com:abdulstack-ui/jhu_software_concepts.git

Module 1:
https://github.com/abdulstack-ui/jhu_software_concepts/tree/main/module_1


NOTES

The application is intended to be started using:

   python run.py

The Flask development server runs on localhost port 8080 as required by
the Module 1 assignment.