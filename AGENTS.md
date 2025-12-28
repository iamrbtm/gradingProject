# AGENTS.md

This file provides guidelines for agentic coding agents operating in this repository.

## General Instructions

* This is a Flask application using SQLAlchemy for database interactions.
* Follow the existing code structure and conventions.

## Code Style Guidelines

* **Imports:** Use absolute imports.
* **Formatting:** Follow PEP 8 guidelines.
* **Types:** Use type hints for function signatures and variables.
* **Naming Conventions:** Use descriptive names for variables, functions, and classes.
* **Error Handling:** Use try-except blocks to handle potential exceptions gracefully.

## Build/Lint/Test Commands

* **Build:** Run the application using `python app.py`.
* **Lint:** Use `flake8` or `pylint` to check for code style issues.
* **Test:** Use `pytest` or `unittest` for testing.
  - To run a single test with `pytest`, use: `pytest path/to/test_file.py::test_name`.

## Database

* The database is MySQL, hosted remotely.
* Use SQLAlchemy for all database interactions.
* Database configuration is in `config.py` with environment variable `DATABASE_URL`
* Test database: Use environment variable `TEST_DATABASE_URL`