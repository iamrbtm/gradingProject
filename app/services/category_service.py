"""
Category service for handling grade category CRUD operations.
Consolidates common logic used across different blueprints.
"""
from flask import flash, jsonify, redirect, url_for, request
from flask_login import current_user
from app.models import db, Course, GradeCategory, Term
from app.utils.helpers import check_term_editable


class CategoryService:
    """Service class for category operations."""

    @staticmethod
    def validate_category_data(name, weight, course):
        """Validate category name and weight. Returns (is_valid, weight_value)"""
        if not name or not name.strip():
            return False, 0.0

        if course.is_weighted:
            try:
                weight_val = float(weight)
                if not (0 <= weight_val <= 100):
                    return False, 0.0
                return True, weight_val
            except (TypeError, ValueError):
                return False, 0.0
        else:
            return True, 0.0

    @staticmethod
    def check_weight_total(course, category_id=None, new_weight=0.0):
        """Check if adding/updating category would exceed 100% weight."""
        current_total = sum(c.weight * 100 for c in course.categories if c.id != (category_id or 0))
        if current_total + new_weight > 100:
            return False, f"Total category weights cannot exceed 100%. Current total: {current_total}%"
        return True, None

    @staticmethod
    def create_category(course_id, name, weight, is_json=False):
        """Create a new category for a course."""
        course = Course.query.get_or_404(course_id)

        # Check authorization
        if course.term.user_id != current_user.id:
            if is_json:
                return jsonify({'success': False, 'message': 'Unauthorized'}), 403
            flash('Unauthorized.', 'danger')
            return redirect(url_for('main.dashboard')), None

        # Check if term is editable
        if not check_term_editable(course.term):
            error_msg = 'This term is inactive and cannot be edited.'
            if is_json:
                return jsonify({'success': False, 'message': error_msg}), 403
            flash(error_msg or "An error occurred", 'danger')
            return redirect(url_for('main.dashboard')), None

        # Validate data
        is_valid, weight_val = CategoryService.validate_category_data(name, weight, course)
        if not is_valid:
            error_msg = "Invalid category data"
            if is_json:
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg or "An error occurred", 'danger')
            return redirect(url_for('main.view_course', course_id=course.id)), None

        # Check weight total
        is_valid, error_msg = CategoryService.check_weight_total(course, new_weight=weight_val if course.is_weighted else 0.0)
        if not is_valid:
            error_message = error_msg or "Weight validation failed"
            if is_json:
                return jsonify({'success': False, 'message': error_message}), 400
            flash(error_message, 'danger')
            return redirect(url_for('main.view_course', course_id=course.id)), None

        # Check uniqueness
        existing = GradeCategory.query.filter_by(course_id=course.id, name=name.strip()).first()
        if existing:
            if is_json:
                return jsonify({'success': False, 'message': 'Category name must be unique per course'}), 400
            flash('Category name must be unique per course.', 'danger')
            return redirect(url_for('main.view_course', course_id=course.id)), None

        try:
            weight_decimal = weight_val / 100.0 if course.is_weighted else 0.0
            new_category = GradeCategory(name=name.strip(), weight=weight_decimal, course_id=course.id)
            db.session.add(new_category)
            db.session.commit()

            if is_json:
                return jsonify({'success': True, 'message': 'Category created successfully'}), None
            flash('Category created.', 'success')
            return redirect(url_for('main.view_course', course_id=course.id)), new_category

        except Exception as e:
            db.session.rollback()
            if is_json:
                return jsonify({'success': False, 'message': f'Error creating category: {str(e)}'}), 500
            flash(f'Error creating category: {str(e)}', 'danger')
            return redirect(url_for('main.view_course', course_id=course.id)), None

    @staticmethod
    def update_category(course_id, category_id, name=None, weight=None, is_json=False):
        """Update an existing category."""
        course = Course.query.get_or_404(course_id)
        category = GradeCategory.query.get_or_404(category_id)

        # Check authorization
        if course.id != category.course_id or course.term.user_id != current_user.id:
            if is_json:
                return jsonify({'success': False, 'message': 'Unauthorized'}), 403
            flash('Unauthorized.', 'danger')
            return redirect(url_for('main.dashboard')), None

        # Check if term is editable
        if not check_term_editable(course.term):
            error_msg = 'This term is inactive and cannot be edited.'
            if is_json:
                return jsonify({'success': False, 'message': error_msg}), 403
            flash(error_msg or "An error occurred", 'danger')
            return redirect(url_for('main.dashboard')), None

        # Handle weight-only updates (for JSON API)
        if name is None and weight is not None:
            if course.is_weighted:
                try:
                    weight_val = float(weight)
                    if not (0 <= weight_val <= 100):
                        if is_json:
                            return jsonify({'success': False, 'message': 'Weight must be between 0 and 100'}), 400
                        flash('Weight must be between 0 and 100.', 'danger')
                        return redirect(url_for('main.view_course', course_id=course.id)), None

                    # Check weight total
                    is_valid, error_msg = CategoryService.check_weight_total(course, category_id, weight_val)
                    if not is_valid:
                        if is_json:
                            return jsonify({'success': False, 'message': error_msg}), 400
                        flash(error_msg or "An error occurred", 'danger')
                        return redirect(url_for('main.view_course', course_id=course.id)), None

                    category.weight = weight_val / 100.0
                    db.session.commit()

                    if is_json:
                        return jsonify({'success': True, 'message': 'Weight updated successfully'}), None
                    flash('Weight updated successfully.', 'success')
                    return redirect(url_for('main.view_course', course_id=course.id)), None

                except (TypeError, ValueError):
                    if is_json:
                        return jsonify({'success': False, 'message': 'Weight must be a valid number'}), 400
                    flash('Weight must be a valid number.', 'danger')
                    return redirect(url_for('main.view_course', course_id=course.id)), None
            else:
                if is_json:
                    return jsonify({'success': False, 'message': 'Course is not weighted'}), 400
                flash('Course is not weighted.', 'danger')
                return redirect(url_for('main.view_course', course_id=course.id)), None

        # Handle full updates (name and/or weight)
        if name is not None:
            if not name.strip():
                if is_json:
                    return jsonify({'success': False, 'message': 'Category name is required'}), 400
                flash('Category name is required.', 'danger')
                return redirect(url_for('main.view_course', course_id=course.id)), None

            # Check uniqueness if name changed
            if name.strip() != category.name:
                existing = GradeCategory.query.filter_by(course_id=course.id, name=name.strip()).first()
                if existing:
                    if is_json:
                        return jsonify({'success': False, 'message': 'Category name must be unique per course'}), 400
                    flash('Category name must be unique per course.', 'danger')
                    return redirect(url_for('main.view_course', course_id=course.id)), None

            category.name = name.strip()

        if weight is not None and course.is_weighted:
            try:
                weight_val = float(weight)
                if not (0 <= weight_val <= 100):
                    if is_json:
                        return jsonify({'success': False, 'message': 'Weight must be between 0 and 100'}), 400
                    flash('Weight must be between 0 and 100.', 'danger')
                    return redirect(url_for('main.view_course', course_id=course.id)), None

                # Check weight total
                is_valid, error_msg = CategoryService.check_weight_total(course, category_id, weight_val)
                if not is_valid:
                    if is_json:
                        return jsonify({'success': False, 'message': error_msg}), 400
                    flash(error_msg or "An error occurred", 'danger')
                    return redirect(url_for('main.view_course', course_id=course.id)), None

                category.weight = weight_val / 100.0

            except (TypeError, ValueError):
                if is_json:
                    return jsonify({'success': False, 'message': 'Weight must be a valid number'}), 400
                flash('Weight must be a valid number.', 'danger')
                return redirect(url_for('main.view_course', course_id=course.id)), None

        try:
            db.session.commit()
            if is_json:
                return jsonify({'success': True, 'message': 'Category updated successfully'}), None
            flash('Category updated successfully.', 'success')
            return redirect(url_for('main.view_course', course_id=course.id)), None

        except Exception as e:
            db.session.rollback()
            if is_json:
                return jsonify({'success': False, 'message': f'Error updating category: {str(e)}'}), 500
            flash(f'Error updating category: {str(e)}', 'danger')
            return redirect(url_for('main.view_course', course_id=course.id)), None

    @staticmethod
    def delete_category(course_id, category_id, is_json=False):
        """Delete a category."""
        course = Course.query.get_or_404(course_id)
        category = GradeCategory.query.get_or_404(category_id)

        # Check authorization
        if course.id != category.course_id or course.term.user_id != current_user.id:
            if is_json:
                return jsonify({'success': False, 'message': 'Unauthorized'}), 403
            flash('Unauthorized.', 'danger')
            return redirect(url_for('main.dashboard')), False

        # Check if term is editable
        if not check_term_editable(course.term):
            error_msg = 'This term is inactive and cannot be edited.'
            if is_json:
                return jsonify({'success': False, 'message': error_msg}), 403
            flash(error_msg or "An error occurred", 'danger')
            return redirect(url_for('main.dashboard')), False

        # Check if category has assignments
        if category.assignments:
            if is_json:
                return jsonify({'success': False, 'message': 'Cannot delete category with assignments. Move or delete assignments first.'}), 400
            flash('Cannot delete category with assignments. Move or delete assignments first.', 'danger')
            return redirect(url_for('main.view_course', course_id=course.id)), False

        try:
            db.session.delete(category)
            db.session.commit()

            if is_json:
                return jsonify({'success': True, 'message': 'Category deleted successfully'}), True
            flash('Category deleted successfully.', 'success')
            return redirect(url_for('main.view_course', course_id=course.id)), True

        except Exception as e:
            db.session.rollback()
            if is_json:
                return jsonify({'success': False, 'message': f'Error deleting category: {str(e)}'}), 500
            flash(f'Error deleting category: {str(e)}', 'danger')
            return redirect(url_for('main.view_course', course_id=course.id)), False