"""
Authorization decorators for Flask routes to eliminate code duplication.
"""
from functools import wraps
from flask import jsonify
from flask_login import login_required, current_user
from app.models import Assignment, Course, Term, GradeCategory


def require_course_owner(f):
    """
    Decorator to ensure the current user owns the course.
    Checks if course.term.user_id == current_user.id
    """
    @wraps(f)
    def decorated_function(course_id, *args, **kwargs):
        course = Course.query.get_or_404(course_id)
        if course.term.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        return f(course_id, *args, **kwargs)
    return decorated_function


def require_assignment_owner(f):
    """
    Decorator to ensure the current user owns the assignment's course.
    Checks if assignment.course.term.user_id == current_user.id
    """
    @wraps(f)
    def decorated_function(assignment_id, *args, **kwargs):
        assignment = Assignment.query.get_or_404(assignment_id)
        if assignment.course.term.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        return f(assignment_id, *args, **kwargs)
    return decorated_function


def require_term_editable(f):
    """
    Decorator to ensure the term is editable.
    Checks if check_term_editable(term) returns True
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if any of the common term identifiers are in kwargs
        term_id = kwargs.get('term_id')
        course_id = kwargs.get('course_id')
        assignment_id = kwargs.get('assignment_id')
        category_id = kwargs.get('category_id')

        # Determine which term to check based on the ID provided
        if term_id:
            term = Term.query.get_or_404(term_id)
        elif course_id:
            course = Course.query.get_or_404(course_id)
            term = course.term
        elif assignment_id:
            assignment = Assignment.query.get_or_404(assignment_id)
            term = assignment.course.term
        elif category_id:
            category = GradeCategory.query.get_or_404(category_id)
            term = category.course.term
        else:
            return jsonify({'success': False, 'message': 'Term identifier required'}), 400

        from app.utils.helpers import check_term_editable
        if not check_term_editable(term):
            return jsonify({'success': False, 'message': 'This term is inactive and cannot be edited.'}), 403

        return f(*args, **kwargs)
    return decorated_function


def require_category_course_owner(f):
    """
    Decorator to ensure the current user owns the category's course.
    Checks if category.course.term.user_id == current_user.id
    """
    @wraps(f)
    def decorated_function(category_id, *args, **kwargs):
        category = GradeCategory.query.get_or_404(category_id)
        if category.course.term.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        return f(category_id, *args, **kwargs)
    return decorated_function


def combine_decorators(*decorators):
    """
    Helper function to combine multiple decorators.
    """
    def decorator(f):
        for dec in reversed(decorators):
            f = dec(f)
        return f
    return decorator