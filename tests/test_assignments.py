import pytest
from app import app, db
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


def seed_course(user, is_category=True):
    term = Term(nickname='T', season='Fall', year=2025, school_name='X', start_date=datetime(2025,9,1), end_date=datetime(2025,12,15), user_id=user.id)
    db.session.add(term)
    db.session.commit()
    course = Course(name='C', credits=3.0, term_id=term.id, is_category=is_category)
    db.session.add(course)
    db.session.commit()
    return term, course


def test_move_category_success(client, user_login):
    _, course = seed_course(user_login)
    cat1 = GradeCategory(name='Lab', course_id=course.id)
    cat2 = GradeCategory(name='Quiz', course_id=course.id)
    db.session.add_all([cat1, cat2])
    db.session.commit()
    a = Assignment(name='A1', max_score=10, course_id=course.id, category_id=cat1.id)
    db.session.add(a)
    db.session.commit()

    resp = client.post(f"/assignment/{a.id}/move_category", json={"category_id": cat2.id})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('success') is True
    db.session.refresh(a)
    assert a.category_id == cat2.id


def test_move_category_to_uncategorized(client, user_login):
    _, course = seed_course(user_login)
    cat1 = GradeCategory(name='Lab', course_id=course.id)
    db.session.add(cat1)
    db.session.commit()
    a = Assignment(name='A1', max_score=10, course_id=course.id, category_id=cat1.id)
    db.session.add(a)
    db.session.commit()

    resp = client.post(f"/assignment/{a.id}/move_category", json={"category_id": None})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('success') is True
    db.session.refresh(a)
    assert a.category_id is None


def test_move_category_wrong_course_forbidden(client, user_login):
    # course 1 with user
    _, course1 = seed_course(user_login)
    a = Assignment(name='A1', max_score=10, course_id=course1.id)
    db.session.add(a)
    db.session.commit()

    # different user and course
    u2 = User(username='u2'); u2.set_password('pw2')
    db.session.add(u2); db.session.commit()
    t2 = Term(nickname='T2', season='Spring', year=2026, school_name='X', start_date=datetime(2026,1,10), end_date=datetime(2026,5,20), user_id=u2.id)
    db.session.add(t2); db.session.commit()
    course2 = Course(name='Other', credits=3.0, term_id=t2.id, is_category=True)
    db.session.add(course2); db.session.commit()
    cat_other = GradeCategory(name='OtherCat', course_id=course2.id)
    db.session.add(cat_other); db.session.commit()

    # logged in as user_login; moving to other user's category should fail server-side (ownership check)
    resp = client.post(f"/assignment/{a.id}/move_category", json={"category_id": cat_other.id})
    assert resp.status_code in (400, 403, 404)
    data = resp.get_json()
    assert not data.get('success')


def test_update_score_json_and_banner_fields(client, user_login):
    _, course = seed_course(user_login)
    a = Assignment(name='A1', max_score=20, course_id=course.id)
    db.session.add(a); db.session.commit()

    resp = client.post(f"/assignment/{a.id}/update_score", data={"score": "18"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('success') is True
    # Optional fields returned should exist (float or null); do not assert exact numbers
    assert 'overall_grade_percentage' in data
    assert 'gpa_contribution' in data
