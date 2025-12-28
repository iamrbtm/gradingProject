import os
import tempfile
import json
import csv
import pytest
from app.import_assignments import AssignmentImporter
from app import db
from app.models import Assignment
from flask import Flask
from datetime import datetime

# --- Setup a minimal Flask app and test database context ---
@pytest.fixture(scope="function")
def test_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://onlymyli:Braces4me%23%23@jeremyguill.com:3306/onlymyli_grades_test'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        # Clean up test data instead of dropping all tables
        db.session.execute(db.text('DELETE FROM assignments'))
        db.session.execute(db.text('DELETE FROM courses'))
        db.session.execute(db.text('DELETE FROM terms'))
        db.session.execute(db.text('DELETE FROM users'))
        db.session.commit()

@pytest.fixture
def importer():
    return AssignmentImporter()

@pytest.fixture
def course_id(test_app):
    # Insert a dummy course
    from app.models import Course, Term, User
    user = User(username="testuser", password_hash="x")
    db.session.add(user)
    db.session.commit()
    term = Term(nickname="Fall", season="Fall", year=2025, school_name="Test School", user_id=user.id)
    db.session.add(term)
    db.session.commit()
    course = Course(name="Math", credits=3, term_id=term.id)
    db.session.add(course)
    db.session.commit()
    return course.id

def test_import_csv_success(importer, course_id, test_app):
    csv_content = "name,max_score,due_date\nAssignment 1,100,2025-09-01T12:00:00\nAssignment 2,50,2025-09-10T12:00:00\n"
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False) as f:
        f.write(csv_content)
        f.flush()
        file_path = f.name
    with test_app.app_context():
        result = importer.import_assignments(file_path, course_id)
        assert result['success']
        assert len(result['inserted']) == 2
        assert not result['errors']
        assignments = Assignment.query.filter_by(course_id=course_id).all()
        assert len(assignments) == 2
    os.remove(file_path)

def test_import_json_success(importer, course_id, test_app):
    json_content = [
        {"name": "Assignment 3", "max_score": 75, "due_date": "2025-09-15T12:00:00"},
        {"name": "Assignment 4", "max_score": 80, "due_date": "2025-09-20T12:00:00"}
    ]
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as f:
        json.dump(json_content, f)
        f.flush()
        file_path = f.name
    with test_app.app_context():
        result = importer.import_assignments(file_path, course_id)
        assert result['success']
        assert len(result['inserted']) == 2
        assert not result['errors']
        assignments = Assignment.query.filter_by(course_id=course_id).all()
        assert len(assignments) == 2
    os.remove(file_path)

def test_import_invalid_file(importer, course_id, test_app):
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as f:
        f.write("not a valid file")
        f.flush()
        file_path = f.name
    with test_app.app_context():
        result = importer.import_assignments(file_path, course_id)
        assert not result['success']
        assert 'Unsupported file type.' in result['errors'][0]
    os.remove(file_path)

def test_import_missing_fields(importer, course_id, test_app):
    csv_content = "name,max_score\nAssignment 5,100\n"
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False) as f:
        f.write(csv_content)
        f.flush()
        file_path = f.name
    with test_app.app_context():
        result = importer.import_assignments(file_path, course_id)
        assert not result['success']
        assert any('missing fields' in e for e in result['errors'])
    os.remove(file_path)
