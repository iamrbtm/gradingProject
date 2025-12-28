import pytest
from app import app
from app import db
from app.models import User, Term, Course, GradeCategory, Assignment
from datetime import datetime

@pytest.fixture(autouse=True)
def app_context():
    # Store original config
    original_db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    
    app.config['TESTING'] = True
    # Use a test database on the same MySQL server
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://onlymyli:Braces4me%23%23@jeremyguill.com:3306/onlymyli_grades_test'
    
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        # Clean up test data instead of dropping all tables
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
    
    # Restore original config
    if original_db_uri:
        app.config['SQLALCHEMY_DATABASE_URI'] = original_db_uri

@pytest.fixture
def client():
    return app.test_client()

@pytest.fixture
def user_login(client):
    u = User(username='u1')
    u.set_password('pw')
    db.session.add(u)
    db.session.commit()
    with client.session_transaction() as sess:
        sess['_user_id'] = str(u.id)
    return u


def create_term_course(user, weighted=False, category=False):
    term = Term(nickname='T1', season='Fall', year=2025, school_name='X', start_date=datetime(2025,9,1), end_date=datetime(2025,12,15), user_id=user.id)
    db.session.add(term)
    db.session.commit()
    course = Course(name='C1', credits=3.0, term_id=term.id, is_weighted=weighted, is_category=category)
    db.session.add(course)
    db.session.commit()
    return term, course


def test_create_update_delete_category_weighted(client, user_login):
    _, course = create_term_course(user_login, weighted=True)

    # create
    resp = client.post(f"/course/{course.id}/categories", data={"name": "Homework", "weight": "40"}, follow_redirects=True)
    assert resp.status_code == 200
    cat = GradeCategory.query.filter_by(course_id=course.id, name='Homework').first()
    assert cat and abs(cat.weight - 0.4) < 1e-6

    # uniqueness
    resp = client.post(f"/course/{course.id}/categories", data={"name": "Homework", "weight": "10"}, follow_redirects=True)
    assert resp.status_code == 200
    assert GradeCategory.query.filter_by(course_id=course.id, name='Homework').count() == 1

    # update
    resp = client.post(f"/course/{course.id}/categories/{cat.id}/update", data={"name": "HW", "weight": "50"}, follow_redirects=True)
    assert resp.status_code == 200
    cat = GradeCategory.query.get(cat.id)
    assert cat.name == 'HW' and abs(cat.weight - 0.5) < 1e-6

    # delete
    a = Assignment(name='A1', max_score=10, course_id=course.id, category_id=cat.id)
    db.session.add(a)
    db.session.commit()
    resp = client.post(f"/course/{course.id}/categories/{cat.id}/delete", follow_redirects=True)
    assert resp.status_code == 200
    db.session.refresh(a)
    assert Assignment.query.get(a.id).category_id is None


def test_total_weight_indicator_in_template(client, user_login):
    _, course = create_term_course(user_login, weighted=True)
    # Two categories totaling 90%
    db.session.add_all([
        GradeCategory(name='Exams', weight=0.5, course_id=course.id),
        GradeCategory(name='HW', weight=0.4, course_id=course.id),
    ])
    db.session.commit()

    r = client.get(f"/course/{course.id}")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'Total weight' in html
    assert '90.0%' in html or '90%' in html
    assert 'Weights total less than 100%' in html


def test_category_course_create_names_only(client, user_login):
    _, course = create_term_course(user_login, weighted=False, category=True)
    resp = client.post(f"/course/{course.id}/categories", data={"name": "Lab"}, follow_redirects=True)
    assert resp.status_code == 200
    cat = GradeCategory.query.filter_by(course_id=course.id, name='Lab').first()
    assert cat and abs(cat.weight - 0.0) < 1e-6
