from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models import db, Course, GradeCategory, Assignment, AuditLog, Term
from app.services.grade_calculator import GradeCalculatorService
from app.utils import check_term_editable
from datetime import datetime
from sqlalchemy.orm import joinedload

courses_bp = Blueprint('courses', __name__, url_prefix='/course')


@courses_bp.route('/<int:course_id>')
@login_required
def course_detail(course_id):
    """Display detailed view of a specific course."""
    course = Course.query.join(Term).filter(Course.id == course_id, Term.user_id == current_user.id).options(
        joinedload('assignments'),
        joinedload('grade_categories')
    ).first_or_404()

    # Calculate course grade
    course.grade = GradeCalculatorService.calculate_course_grade(course)

    # Sort categories by weight
    sorted_categories = sorted(course.categories, key=lambda c: c.weight, reverse=True)

    # Get assignments by category
    assignments_by_category = {}
    for category in sorted_categories:
        assignments_by_category[category.id] = sorted(
            [a for a in course.assignments if a.category_id == category.id],
            key=lambda a: a.due_date or datetime.max
        )

    return render_template('course_detail.html',
                         course=course,
                         categories=sorted_categories,
                         assignments_by_category=assignments_by_category)


@courses_bp.route('/<int:course_id>/categories', methods=['POST'])
@login_required
def add_category(course_id):
    """Add a new grade category to a course."""
    course = Course.query.join(Term).filter(Course.id == course_id, Term.user_id == current_user.id).options(
        joinedload('assignments'),
        joinedload('grade_categories')
    ).first_or_404()
    term = Term.query.get(course.term_id)

    if not check_term_editable(term):
        flash('Cannot modify categories for past terms.', 'error')
        return redirect(url_for('courses.course_detail', course_id=course_id))

    try:
        category_name = request.form.get('category_name')
        weight = float(request.form.get('weight', 0))

        if not category_name or weight <= 0:
            flash('Category name and positive weight are required.', 'error')
            return redirect(url_for('courses.course_detail', course_id=course_id))

        # Check if total weight would exceed 100%
        current_total_weight = sum(c.weight for c in course.categories)
        if current_total_weight + weight > 100:
            flash('Total category weights cannot exceed 100%.', 'error')
            return redirect(url_for('courses.course_detail', course_id=course_id))

        new_category = GradeCategory(
            name=category_name,
            weight=weight,
            course_id=course_id
        )

        db.session.add(new_category)
        db.session.commit()

        flash(f'Category "{category_name}" added successfully!', 'success')
        return redirect(url_for('courses.course_detail', course_id=course_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error adding category: {str(e)}', 'error')
        return redirect(url_for('courses.course_detail', course_id=course_id))


@courses_bp.route('/<int:course_id>/categories/<int:category_id>/update', methods=['POST'])
@login_required
def update_category(course_id, category_id):
    """Update an existing grade category."""
    course = Course.query.join(Term).filter(Course.id == course_id, Term.user_id == current_user.id).options(
        joinedload('assignments'),
        joinedload('grade_categories')
    ).first_or_404()
    category = GradeCategory.query.filter_by(id=category_id, course_id=course_id).first_or_404()
    term = Term.query.get(course.term_id)

    if not check_term_editable(term):
        flash('Cannot modify categories for past terms.', 'error')
        return redirect(url_for('courses.course_detail', course_id=course_id))

    try:
        new_name = request.form.get('category_name')
        new_weight = float(request.form.get('weight', 0))

        if not new_name or new_weight <= 0:
            flash('Category name and positive weight are required.', 'error')
            return redirect(url_for('courses.course_detail', course_id=course_id))

        # Check if total weight would exceed 100%
        other_categories_weight = sum(c.weight for c in course.categories if c.id != category_id)
        if other_categories_weight + new_weight > 100:
            flash('Total category weights cannot exceed 100%.', 'error')
            return redirect(url_for('courses.course_detail', course_id=course_id))

        category.name = new_name
        category.weight = new_weight
        db.session.commit()

        flash(f'Category "{new_name}" updated successfully!', 'success')
        return redirect(url_for('courses.course_detail', course_id=course_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error updating category: {str(e)}', 'error')
        return redirect(url_for('courses.course_detail', course_id=course_id))


@courses_bp.route('/<int:course_id>/categories/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_category(course_id, category_id):
    """Delete a grade category."""
    course = Course.query.join(Term).filter(Course.id == course_id, Term.user_id == current_user.id).options(
        joinedload('assignments'),
        joinedload('grade_categories')
    ).first_or_404()
    category = GradeCategory.query.filter_by(id=category_id, course_id=course_id).first_or_404()
    term = Term.query.get(course.term_id)

    if not check_term_editable(term):
        flash('Cannot delete categories for past terms.', 'error')
        return redirect(url_for('courses.course_detail', course_id=course_id))

    try:
        # Check if category has assignments
        if category.assignments:
            flash('Cannot delete category with existing assignments.', 'error')
            return redirect(url_for('courses.course_detail', course_id=course_id))

        db.session.delete(category)
        db.session.commit()

        flash(f'Category "{category.name}" deleted successfully.', 'success')
        return redirect(url_for('courses.course_detail', course_id=course_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting category: {str(e)}', 'error')
        return redirect(url_for('courses.course_detail', course_id=course_id))


@courses_bp.route('/<int:course_id>/audit_trail')
@login_required
def audit_trail(course_id):
    """Display audit trail for a course."""
    course = Course.query.join(Term).filter(Course.id == course_id, Term.user_id == current_user.id).options(
        joinedload('assignments'),
        joinedload('grade_categories')
    ).first_or_404()

    # Get audit logs for this course
    audit_logs = AuditLog.query.filter_by(course_id=course_id).order_by(AuditLog.timestamp.desc()).all()

    return render_template('audit_trail.html', course=course, audit_logs=audit_logs)


@courses_bp.route('/<int:course_id>/report')
@login_required
def course_report(course_id):
    """Generate a detailed report for a course."""
    course = Course.query.join(Term).filter(Course.id == course_id, Term.user_id == current_user.id).options(
        joinedload('assignments'),
        joinedload('grade_categories')
    ).first_or_404()

    # Calculate detailed statistics
    course.grade = GradeCalculatorService.calculate_course_grade(course)

    # Category breakdown
    category_breakdown = []
    for category in course.grade_categories:
        category_avg, _ = GradeCalculatorService.calculate_category_average(category, course.assignments)
        category_breakdown.append({
            'name': category.name,
            'weight': category.weight,
            'average': category_avg,
            'weighted_score': (category_avg * category.weight / 100) if category_avg else 0
        })

    # Assignment statistics
    completed_assignments = [a for a in course.assignments if a.score is not None]
    total_assignments = len(course.assignments)
    completed_count = len(completed_assignments)

    if completed_assignments:
        avg_score = sum(a.score for a in completed_assignments) / len(completed_assignments)
        avg_max_score = sum(a.max_score for a in completed_assignments) / len(completed_assignments)
        avg_percentage = (avg_score / avg_max_score * 100) if avg_max_score > 0 else 0
    else:
        avg_score = avg_max_score = avg_percentage = 0

    return render_template('course_report.html',
                         course=course,
                         category_breakdown=category_breakdown,
                         total_assignments=total_assignments,
                         completed_count=completed_count,
                         avg_percentage=avg_percentage)