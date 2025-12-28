from flask import Blueprint, request, current_app
from flask_login import current_user, login_required
from app.models import db, Term, Course, Assignment, GradeCategory, User
from sqlalchemy import desc

try:
    from flask_restx import Api, Resource, fields
    api_bp = Blueprint('api', __name__, url_prefix='/api/v1')
    api = Api(api_bp, title='Grade Tracker API', version='1.0', description='API for Grade Tracker application')

    # Models for documentation
    term_model = api.model('Term', {
        'id': fields.Integer,
        'nickname': fields.String,
        'season': fields.String,
        'year': fields.Integer,
        'active': fields.Boolean,
        'school_name': fields.String
    })

    course_model = api.model('Course', {
        'id': fields.Integer,
        'name': fields.String,
        'credits': fields.Float,
        'is_weighted': fields.Boolean
    })

    assignment_model = api.model('Assignment', {
        'id': fields.Integer,
        'name': fields.String,
        'score': fields.Float,
        'max_score': fields.Float,
        'due_date': fields.DateTime,
        'category_id': fields.Integer,
        'is_completed': fields.Boolean
    })

    category_model = api.model('Category', {
        'id': fields.Integer,
        'name': fields.String,
        'weight': fields.Float
    })

    course_detail_model = api.model('CourseDetail', {
        'id': fields.Integer,
        'name': fields.String,
        'credits': fields.Float,
        'is_weighted': fields.Boolean,
        'assignments': fields.List(fields.Nested(assignment_model)),
        'categories': fields.List(fields.Nested(category_model))
    })

    grade_model = api.model('Grade', {
        'course_id': fields.Integer,
        'grade': fields.Float,
        'assignments_count': fields.Integer
    })

    @api.route('/health')
    class Health(Resource):
        def get(self):
            """API health check."""
            return {'status': 'ok', 'version': '1.0'}

    @api.route('/terms')
    class Terms(Resource):
        @api.marshal_list_with(term_model)
        @login_required
        def get(self):
            """Get all terms for current user."""
            terms = Term.query.filter_by(user_id=current_user.id).order_by(desc(Term.year), desc(Term.season)).all()
            return terms

    @api.route('/terms/<int:term_id>/courses')
    class TermCourses(Resource):
        @api.marshal_list_with(course_model)
        @login_required
        def get(self, term_id):
            """Get courses for a term."""
            term = Term.query.filter_by(id=term_id, user_id=current_user.id).first_or_404()
            courses = Course.query.filter_by(term_id=term_id).all()
            return courses

    @api.route('/courses/<int:course_id>')
    class CourseDetail(Resource):
        @api.marshal_with(course_detail_model)
        @login_required
        def get(self, course_id):
            """Get course details with assignments."""
            course = Course.query.filter_by(id=course_id).join(Term).filter(Term.user_id == current_user.id).first_or_404()
            assignments = Assignment.query.filter_by(course_id=course_id).order_by(Assignment.due_date).all()
            categories = GradeCategory.query.filter_by(course_id=course_id).all()
            
            course.assignments = assignments
            course.categories = categories
            return course

    @api.route('/courses/<int:course_id>/grade')
    class CourseGrade(Resource):
        @api.marshal_with(grade_model)
        @login_required
        def get(self, course_id):
            """Get current grade for course."""
            from app.services.grade_calculator import GradeCalculatorService
            course = Course.query.filter_by(id=course_id).join(Term).filter(Term.user_id == current_user.id).first_or_404()
            assignments = Assignment.query.filter_by(course_id=course_id).all()
            
            grade = GradeCalculatorService.calculate_course_grade(course)
            return {
                'course_id': course_id,
                'grade': grade,
                'assignments_count': len(assignments)
            }
except ImportError:
    api_bp = None