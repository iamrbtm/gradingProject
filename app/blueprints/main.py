from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    jsonify,
    session,
)
from flask_login import login_required, current_user
import time
from collections import defaultdict
from app.models import db, Term, Assignment, TodoItem, Course, GradeCategory, AuditLog
from app.utils import (
    check_term_editable,
    require_assignment_owner,
    require_course_owner,
    require_term_editable,
    require_category_course_owner,
    calculate_assignment_percentage,
)
from app.utils.helpers import categorize_assignments, get_comparison_date
from app.services.grade_calculator import GradeCalculatorService
from datetime import datetime, timedelta
from app.term_date_calculator import get_term_dates
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    """Home page route."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("auth.login"))


@main_bp.route("/login")
def login_redirect():
    """Redirect /login to /auth/login for convenience."""
    return redirect(url_for("auth.login"))


@main_bp.route("/dashboard")
@login_required
def dashboard():
    """Main dashboard showing user's terms."""
    try:
        all_user_terms = (
            Term.query.filter_by(user_id=current_user.id)
            .options(
                joinedload(Term.courses).joinedload(Course.assignments),
                joinedload(Term.courses).joinedload(Course.grade_categories),
            )
            .order_by(Term.year.desc(), Term.season)
            .all()
        )

        active_terms = [
            term for term in all_user_terms if getattr(term, "active", True)
        ]
        inactive_terms = [
            term for term in all_user_terms if not getattr(term, "active", True)
        ]

        # Calculate analytics for each term
        for term in active_terms + inactive_terms:
            term.gpa = GradeCalculatorService.calculate_term_gpa(term)
            term.total_courses = len(term.courses)
            term.total_credits = sum(course.credits for course in term.courses)

        schools = [
            s[0]
            for s in db.session.query(Term.school_name)
            .filter_by(user_id=current_user.id)
            .distinct()
            .all()
        ]

        return render_template(
            "dashboard.html",
            active_terms=active_terms,
            inactive_terms=inactive_terms,
            schools=schools,
        )
    except Exception as e:
        flash("An error occurred while loading the dashboard.", "danger")
        return render_template(
            "dashboard.html", active_terms=[], inactive_terms=[], schools=[]
        )


@main_bp.route("/term/<int:term_id>")
@login_required
def view_term(term_id):
    """View detailed term information."""
    try:
        # Step 1: Get the term
        term = Term.query.filter_by(id=term_id, user_id=current_user.id).first_or_404()
        flash(f"✓ Found term: {term.nickname}", "success")

        # Step 2: Get courses without eager loading first
        courses = Course.query.filter_by(term_id=term.id).order_by(Course.name).all()
        flash(f"✓ Found {len(courses)} courses", "success")

        # Step 3: Test imports
        from app.services.grade_calculator import GradeCalculatorService
        from app.utils.helpers import categorize_assignments

        flash("✓ Imports successful", "success")

        # Step 4: Calculate term GPA safely
        try:
            grade_calculator = GradeCalculatorService()
            term_gpa = grade_calculator.calculate_term_gpa(term)
            # Ensure term_gpa is a valid number
            if term_gpa is None or not isinstance(term_gpa, (int, float)):
                term_gpa = 0.0
        except Exception as gpa_error:
            flash(f"Warning: Could not calculate term GPA: {str(gpa_error)}", "warning")
            term_gpa = 0.0

        # Step 5: Ensure all course grade percentages are safe
        for course in courses:
            if (
                not hasattr(course, "overall_grade_percentage")
                or course.overall_grade_percentage is None
            ):
                course.overall_grade_percentage = None
            elif not isinstance(course.overall_grade_percentage, (int, float)):
                course.overall_grade_percentage = None

        # Step 6: Calculate course statistics for display
        from datetime import datetime, timedelta

        now = datetime.now()
        week_from_now = now + timedelta(days=7)

        for course in courses:
            # Missing assignments: assignments marked as missing
            course.missing_count = sum(
                1 for assignment in course.assignments if assignment.is_missing
            )

            # Due this week: assignments due within 7 days that are not completed
            course.due_this_week_count = sum(
                1
                for assignment in course.assignments
                if assignment.due_date
                and now <= assignment.due_date <= week_from_now
                and not assignment.completed
            )

            # Awaiting grade: submitted assignments without scores
            course.awaiting_grade_count = sum(
                1
                for assignment in course.assignments
                if assignment.is_submitted and assignment.score is None
            )

        # Step 7: Template render
        return render_template(
            "view_term.html", term=term, courses=courses, term_gpa=term_gpa
        )
    except Exception as e:
        import logging

        logging.error(f"ERROR in view_term: {str(e)}", exc_info=True)
        flash(f"Error in view_term: {str(e)}", "danger")
        return redirect(url_for("main.dashboard"))


@main_bp.route("/add_term", methods=["POST"])
@login_required
def add_term():
    """Add a new academic term."""
    try:
        nickname = request.form.get("nickname", "").strip()
        season = request.form.get("season", "").strip()
        year = request.form.get("year", "").strip()
        school_name = request.form.get("school_name", "").strip()

        # Validation
        if not all([nickname, season, year, school_name]):
            flash("All fields are required.", "danger")
            return redirect(url_for("main.dashboard"))

        year = int(year)
        if year < 1900 or year > 2100:
            flash("Please enter a valid year between 1900 and 2100.", "danger")
            return redirect(url_for("main.dashboard"))

        # Check for duplicate terms
        existing_term = Term.query.filter_by(
            user_id=current_user.id, season=season, year=year, school_name=school_name
        ).first()

        if existing_term:
            flash(f"A {season} {year} term at {school_name} already exists.", "warning")
            return redirect(url_for("main.dashboard"))

        start_date, end_date = get_term_dates(season, year)

        new_term = Term(
            nickname=nickname,
            season=season,
            year=year,
            school_name=school_name,
            start_date=start_date,
            end_date=end_date,
            user_id=current_user.id,
        )

        db.session.add(new_term)
        db.session.commit()

        flash(
            f'Term "{nickname}" ({season} {year}) at {school_name} added successfully!',
            "success",
        )

    except ValueError:
        flash("Year must be a valid number.", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Error creating term: {str(e)}", "danger")

    return redirect(url_for("main.dashboard"))


@main_bp.route("/assignment/<int:assignment_id>/update_field", methods=["POST"])
@login_required
@require_assignment_owner
def update_assignment_field(assignment_id):
    """Update assignment field via inline editing."""
    assignment = Assignment.query.get_or_404(assignment_id)

    # Handle both JSON and form data
    if request.is_json:
        data = request.get_json()
        field = data.get("field")
        value = data.get("value")
    else:
        field = request.form.get("field")
        value = request.form.get("value")

    if field not in ["name", "due_date", "score", "max_score"]:
        return jsonify({"success": False, "message": "Invalid field"}), 400

    try:
        # Capture old values before making changes for audit logging
        old_value = getattr(assignment, field)

        if field == "name":
            if not value or value.strip() == "":
                return jsonify(
                    {"success": False, "message": "Assignment name cannot be empty"}
                ), 400
            assignment.name = value.strip()

        elif field == "due_date":
            if value and value.strip():
                try:
                    assignment.due_date = datetime.strptime(
                        value.strip(), "%Y-%m-%d"
                    ).date()
                except ValueError:
                    return jsonify(
                        {"success": False, "message": "Invalid date format"}
                    ), 400
            else:
                assignment.due_date = None

        elif field == "score":
            if value and value.strip():
                try:
                    score_val = float(value.strip())
                    assignment.score = score_val
                except ValueError:
                    return jsonify(
                        {"success": False, "message": "Invalid score format"}
                    ), 400
            else:
                assignment.score = None

        elif field == "max_score":
            if not value or value.strip() == "":
                return jsonify(
                    {"success": False, "message": "Max score cannot be empty"}
                ), 400
            try:
                max_score_val = float(value.strip())
                if max_score_val < 0:
                    return jsonify(
                        {"success": False, "message": "Max score cannot be negative"}
                    ), 400
                elif max_score_val == 0:
                    # If max score is 0, automatically set as extra credit
                    assignment.is_extra_credit = True
                    assignment.max_score = max_score_val
                else:  # max_score_val > 0
                    # If changing from 0 to positive value, unset extra credit flag
                    if old_value == 0:
                        assignment.is_extra_credit = False
                    assignment.max_score = max_score_val
            except ValueError:
                return jsonify(
                    {"success": False, "message": "Invalid max score format"}
                ), 400

        # Log the change before committing
        new_value = getattr(assignment, field)
        if old_value != new_value:
            action = f"updated_{field}"
            log_assignment_change(assignment, field, old_value, new_value, action)

        db.session.commit()

        # Calculate updated course grade
        course = assignment.course
        overall = GradeCalculatorService.calculate_course_grade(course)
        gpa_contrib = GradeCalculatorService.calculate_gpa_contribution(course, overall)

        if request.is_json:
            return jsonify(
                {
                    "success": True,
                    "assignment_id": assignment.id,
                    "field": field,
                    "value": value,
                    "score": assignment.score,
                    "max_score": assignment.max_score,
                    "overall_grade_percentage": overall,
                    "gpa_contribution": gpa_contrib,
                }
            )
        else:
            flash(f"Assignment {field} updated successfully!", "success")
            return redirect(url_for("main.view_course", course_id=assignment.course_id))

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@main_bp.route("/assignment/<int:assignment_id>/update_score", methods=["POST"])
@login_required
@require_assignment_owner
@require_term_editable
def update_assignment_score(assignment_id):
    """Update assignment score."""
    assignment = Assignment.query.get_or_404(assignment_id)

    score_str = request.form.get("score")
    try:
        # Capture old value for audit logging
        old_score = assignment.score

        if score_str is not None and score_str != "":
            score = float(score_str)
            if score < 0 or score > assignment.max_score:
                return jsonify(
                    {
                        "success": False,
                        "message": f"Score must be between 0 and {assignment.max_score}.",
                    }
                ), 400
            assignment.score = score
        else:
            assignment.score = None  # Allow setting score to None (ungraded)

        # Log the change if score changed
        if old_score != assignment.score:
            action = "updated_score"
            log_assignment_change(
                assignment, "score", old_score, assignment.score, action
            )

        db.session.commit()

        course = assignment.course
        overall = GradeCalculatorService.calculate_course_grade(course)
        gpa_contrib = GradeCalculatorService.calculate_gpa_contribution(course, overall)
        return jsonify(
            {
                "success": True,
                "message": f'Score for "{assignment.name}" updated successfully!',
                "overall_grade_percentage": overall,
                "gpa_contribution": gpa_contrib,
            }
        )
    except ValueError:
        return jsonify(
            {"success": False, "message": "Score must be a valid number."}
        ), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@main_bp.route("/course/<int:course_id>/categories", methods=["POST"])
@login_required
def create_category(course_id):
    """Create a new grade category for a course."""
    course = Course.query.get_or_404(course_id)
    if course.term.user_id != current_user.id:
        if request.is_json:
            return jsonify({"success": False, "message": "Unauthorized"}), 403
        flash("Unauthorized.", "danger")
        return redirect(url_for("main.dashboard"))

    # Handle both JSON and form data
    if request.is_json:
        data = request.get_json()
        name = data.get("name", "").strip()
        weight_str = data.get("weight")
    else:
        name = request.form.get("name", "").strip()
        weight_str = request.form.get("weight")

    if not name:
        if request.is_json:
            return jsonify(
                {"success": False, "message": "Category name is required"}
            ), 400
        flash("Category name is required.", "danger")
        return redirect(url_for("main.view_course", course_id=course.id))

    # Enforce uniqueness per course
    existing = GradeCategory.query.filter_by(course_id=course.id, name=name).first()
    if existing:
        if request.is_json:
            return jsonify(
                {"success": False, "message": "Category name must be unique per course"}
            ), 400
        flash("Category name must be unique per course.", "danger")
        return redirect(url_for("main.view_course", course_id=course.id))

    weight = 0.0
    if course.is_weighted:
        try:
            weight_val = float(weight_str)
            if not (0 <= weight_val <= 100):
                raise ValueError
            weight = weight_val / 100.0
        except (TypeError, ValueError):
            if request.is_json:
                return jsonify(
                    {
                        "success": False,
                        "message": "Weight must be a number between 0 and 100",
                    }
                ), 400
            flash("Weight must be a number between 0 and 100.", "danger")
            return redirect(url_for("main.view_course", course_id=course.id))

    try:
        new_cat = GradeCategory(name=name, weight=weight, course_id=course.id)
        db.session.add(new_cat)
        db.session.commit()

        if request.is_json:
            return jsonify(
                {"success": True, "message": "Category created successfully"}
            )
        else:
            flash("Category created.", "success")
            return redirect(url_for("main.view_course", course_id=course.id))
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({"success": False, "message": str(e)}), 500
        else:
            flash("Error creating category.", "danger")
            return redirect(url_for("main.view_course", course_id=course.id))


@main_bp.route(
    "/course/<int:course_id>/categories/<int:category_id>/update", methods=["POST"]
)
@login_required
def update_category(course_id, category_id):
    """Update a grade category."""
    course = Course.query.get_or_404(course_id)
    category = GradeCategory.query.get_or_404(category_id)
    if course.id != category.course_id or course.term.user_id != current_user.id:
        if request.is_json:
            return jsonify({"success": False, "message": "Unauthorized"}), 403
        flash("Unauthorized.", "danger")
        return redirect(url_for("main.dashboard"))

    # Handle both JSON and form data
    if request.is_json:
        data = request.get_json()
        # For weight updates, we only update the weight, not the name
        weight_str = data.get("weight")
        if weight_str is not None:
            if course.is_weighted:
                try:
                    weight_val = float(weight_str)
                    if not (0 <= weight_val <= 100):
                        return jsonify(
                            {
                                "success": False,
                                "message": "Weight must be between 0 and 100",
                            }
                        ), 400
                    category.weight = weight_val / 100.0
                    db.session.commit()
                    return jsonify(
                        {"success": True, "message": "Weight updated successfully"}
                    )
                except (TypeError, ValueError):
                    return jsonify(
                        {"success": False, "message": "Weight must be a valid number"}
                    ), 400
            else:
                return jsonify(
                    {"success": False, "message": "Course is not weighted"}
                ), 400
        else:
            return jsonify({"success": False, "message": "Weight is required"}), 400
    else:
        # Original form-based logic for full category updates
        name = request.form.get("name", "").strip()
        weight_str = request.form.get("weight")

        if not name:
            flash("Category name is required.", "danger")
            return redirect(url_for("main.view_course", course_id=course.id))

        # Uniqueness per course excluding self
        existing = GradeCategory.query.filter(
            GradeCategory.course_id == course.id,
            GradeCategory.name == name,
            GradeCategory.id != category.id,
        ).first()
        if existing:
            flash("Category name must be unique per course.", "danger")
            return redirect(url_for("main.view_course", course_id=course.id))

        category.name = name
        if course.is_weighted:
            try:
                weight_val = float(weight_str)
                if not (0 <= weight_val <= 100):
                    raise ValueError
                category.weight = weight_val / 100.0
            except (TypeError, ValueError):
                flash("Weight must be a number between 0 and 100.", "danger")
    return redirect(url_for("main.view_course", course_id=course.id))


# Audit logging helper function
def log_assignment_change(assignment, field_changed, old_value, new_value, action):
    """Log assignment changes to audit trail."""
    try:
        audit_log = AuditLog(
            assignment_id=assignment.id,
            assignment_name=assignment.name,
            course_id=assignment.course_id,
            action=action,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
            field_changed=field_changed,
        )
        db.session.add(audit_log)
        db.session.commit()
    except Exception as e:
        print(f"Error logging audit change: {e}")


@main_bp.route("/assignment/<int:assignment_id>/update_completed", methods=["POST"])
@login_required
def update_assignment_completed(assignment_id):
    """Update assignment completed status."""
    assignment = Assignment.query.get_or_404(assignment_id)
    if assignment.course.term.user_id != current_user.id:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    data = request.get_json(silent=True) or {}
    completed = data.get("completed", False)

    try:
        old_value = assignment.completed
        assignment.completed = completed

        # Log the change
        action = "marked_completed" if completed else "marked_incomplete"
        log_assignment_change(assignment, "completed", old_value, completed, action)

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "assignment_id": assignment.id,
                "completed": assignment.completed,
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@main_bp.route("/course/<int:course_id>/audit_trail")
@login_required
def audit_trail(course_id):
    """View audit trail for a course."""
    course = Course.query.get_or_404(course_id)
    if course.term.user_id != current_user.id:
        flash("You do not have permission to view this audit trail.", "danger")
        return redirect(url_for("main.dashboard"))

    # Get audit logs for all assignments in this course
    audit_logs = (
        AuditLog.query.filter_by(course_id=course.id)
        .order_by(AuditLog.timestamp.desc())
        .all()
    )

    return render_template("audit_trail.html", course=course, audit_logs=audit_logs)


@main_bp.route(
    "/course/<int:course_id>/categories/<int:category_id>/delete", methods=["POST"]
)
@login_required
def delete_category(course_id, category_id):
    """Delete a grade category."""
    course = Course.query.get_or_404(course_id)
    category = GradeCategory.query.get_or_404(category_id)
    if course.id != category.course_id or course.term.user_id != current_user.id:
        if request.is_json:
            return jsonify({"success": False, "message": "Unauthorized"}), 403
        flash("Unauthorized.", "danger")
        return redirect(url_for("main.dashboard"))

    # Check if term is active before allowing modifications
    if not check_term_editable(course.term):
        if request.is_json:
            return jsonify(
                {"success": False, "message": "Cannot modify inactive terms"}
            ), 400
        flash("Cannot modify inactive terms.", "warning")
        return redirect(url_for("main.view_course", course_id=course.id))

    try:
        category_name = category.name
        db.session.delete(category)
        db.session.commit()

        if request.is_json:
            return jsonify(
                {
                    "success": True,
                    "message": f'Category "{category_name}" deleted successfully',
                }
            )
        else:
            flash(f'Category "{category_name}" deleted successfully!', "success")
            return redirect(url_for("main.view_course", course_id=course.id))
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({"success": False, "message": str(e)}), 500
        else:
            flash("Error deleting category.", "danger")
            return redirect(url_for("main.view_course", course_id=course.id))


@main_bp.route("/course/<int:course_id>/import_assignments", methods=["POST"])
@login_required
def import_assignments(course_id):
    """Import assignments from CSV file."""
    course = Course.query.get_or_404(course_id)
    if course.term.user_id != current_user.id:
        flash("Unauthorized.", "danger")
        return redirect(url_for("main.dashboard"))

    # Check if term is active before allowing modifications
    if not check_term_editable(course.term):
        flash("Cannot modify inactive terms.", "warning")
        return redirect(url_for("main.view_course", course_id=course.id))

    import csv
    from io import StringIO

    if "file" not in request.files:
        flash("No file selected.", "danger")
        return redirect(url_for("main.view_course", course_id=course.id))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected.", "danger")
        return redirect(url_for("main.view_course", course_id=course.id))

    if not file.filename.endswith(".csv"):
        flash("Please upload a CSV file.", "danger")
        return redirect(url_for("main.view_course", course_id=course.id))

    try:
        # Read the file content
        stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)

        added_count = 0
        for row in csv_input:
            name = row.get("name", "").strip()
            score_str = row.get("score", "").strip()
            max_score_str = row.get("max_score", "").strip()
            category_name = row.get("category", "").strip()
            due_date_str = row.get("due_date", "").strip()

            if not name or not max_score_str:
                continue  # Skip invalid rows

            # Check if assignment with this name already exists in the course
            existing_assignment = Assignment.query.filter_by(
                course_id=course.id, name=name
            ).first()
            if existing_assignment:
                continue  # Skip duplicate assignment

            try:
                max_score = float(max_score_str)
                score = float(score_str) if score_str else None

                # Find or create category by name if provided
                category_id = None
                if category_name:
                    category = GradeCategory.query.filter_by(
                        course_id=course.id, name=category_name
                    ).first()
                    if not category:
                        # Create new category with default weight
                        category = GradeCategory(
                            name=category_name,
                            weight=10.0,  # Default weight
                            course_id=course.id,
                        )
                        db.session.add(category)
                        db.session.flush()  # Get the ID before committing
                    category_id = category.id

                # Parse due date if provided
                due_date = None
                if due_date_str:
                    try:
                        due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
                    except ValueError:
                        pass  # Skip invalid dates

                assignment = Assignment(
                    name=name,
                    score=score,
                    max_score=max_score,
                    course_id=course.id,
                    category_id=category_id,
                    due_date=due_date,
                )
                db.session.add(assignment)
                added_count += 1

            except ValueError:
                continue  # Skip rows with invalid numbers

        db.session.commit()
        flash(f"Successfully imported {added_count} assignments!", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error converting course: {str(e)}", "danger")

    return redirect(url_for("main.view_course", course_id=course.id))


@main_bp.route("/notifications")
@login_required
def notifications():
    """Notifications center page."""
    return render_template("notifications.html", title="Notifications")


@main_bp.route("/download_assignment_template")
@login_required
def download_assignment_template():
    """Download CSV template for assignment import."""
    from flask import Response
    import csv
    from io import StringIO

    output = StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(["name", "score", "max_score", "category", "due_date"])

    # Write sample data
    writer.writerow(["Homework 1", "85", "100", "Homework", "2024-01-15"])
    writer.writerow(["Quiz 1", "", "25", "Quizzes", "2024-01-20"])
    writer.writerow(["Midterm Exam", "92", "100", "Exams", "2024-02-15"])

    output.seek(0)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=assignment_template.csv"},
    )


@main_bp.route("/course/<int:course_id>/report")
@login_required
def course_report(course_id):
    """Generate course report."""
    course = Course.query.get_or_404(course_id)
    if course.term.user_id != current_user.id:
        flash("You do not have permission to view this course.", "danger")
        return redirect(url_for("main.dashboard"))

    # Order assignments with null due_dates last (MariaDB compatible)
    assignments = (
        Assignment.query.filter_by(course_id=course.id)
        .order_by(
            db.case((Assignment.due_date.is_(None), 1), else_=0),
            Assignment.due_date.asc(),
        )
        .all()
    )
    grade_categories = (
        GradeCategory.query.filter_by(course_id=course.id)
        .order_by(GradeCategory.weight.desc())
        .all()
    )

    # Calculate category averages
    category_averages = {}
    for category in grade_categories:
        average, is_active = GradeCalculatorService.calculate_category_average(
            category, assignments
        )
        if is_active:
            category_averages[category.id] = average

    # Helper function to handle mixed date types in sorting
    def get_sort_date(assignment):
        if assignment.due_date is None:
            return datetime.max.date()
        if isinstance(assignment.due_date, datetime):
            return assignment.due_date.date()
        return assignment.due_date

    # Group assignments by category
    assignments_by_category = {}
    for category in grade_categories:
        assignments_by_category[category.id] = sorted(
            [a for a in assignments if a.category_id == category.id], key=get_sort_date
        )

    uncategorized_assignments = sorted(
        [a for a in assignments if a.category_id is None], key=get_sort_date
    )

    # Calculate overall course grade
    overall_grade_percentage = GradeCalculatorService.calculate_course_grade(course)
    gpa_contribution = GradeCalculatorService.calculate_gpa_contribution(
        course, overall_grade_percentage
    )

    return render_template(
        "course_report.html",
        course=course,
        assignments=assignments,
        grade_categories=grade_categories,
        assignments_by_category=assignments_by_category,
        uncategorized_assignments=uncategorized_assignments,
        category_averages=category_averages,
        overall_grade_percentage=overall_grade_percentage,
        gpa_contribution=gpa_contribution,
    )


@main_bp.route("/add_todo_item", methods=["POST"])
@login_required
def add_todo_item():
    """Add a new todo item."""
    description = request.form.get("description")
    due_date_str = request.form.get("due_date")
    course_id = request.form.get("course_id")

    if not description:
        flash("Description is required.", "danger")
        return redirect(url_for("main.todo"))

    due_date = None
    if due_date_str:
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
        except ValueError:
            flash("Invalid due date format. Please use YYYY-MM-DD.", "danger")
            return redirect(url_for("main.todo"))

    # Convert empty string to None for course_id
    if course_id == "":
        course_id = None

    new_todo = TodoItem(description=description, due_date=due_date, course_id=course_id)
    db.session.add(new_todo)
    db.session.commit()
    flash("ToDo item added successfully!", "success")
    return redirect(url_for("main.todo"))


@main_bp.route("/import_todo_items", methods=["POST"])
@login_required
def import_todo_items():
    """Import multiple todo items from a bullet point list."""
    bullet_list = request.form.get("bullet_list")
    due_date_str = request.form.get("due_date")
    course_id = request.form.get("course_id")

    if not bullet_list:
        flash("Bullet list is required.", "danger")
        return redirect(url_for("main.todo"))

    due_date = None
    if due_date_str:
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
        except ValueError:
            flash("Invalid due date format. Please use YYYY-MM-DD.", "danger")
            return redirect(url_for("main.todo"))

    # Convert empty string to None for course_id
    if course_id == "":
        course_id = None

    # Parse bullet points
    lines = bullet_list.strip().split("\n")
    imported_count = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Remove common bullet point prefixes
        description = line.lstrip("-•* ").strip()

        if description:  # Only add if there's actual content
            new_todo = TodoItem(
                description=description, due_date=due_date, course_id=course_id
            )
            db.session.add(new_todo)
            imported_count += 1

    if imported_count > 0:
        db.session.commit()
        flash(f"Successfully imported {imported_count} ToDo items!", "success")
    else:
        flash("No valid tasks found in the list.", "warning")

    return redirect(url_for("main.todo"))


@main_bp.route("/course/<int:course_id>/convert_to_unweighted", methods=["POST"])
@login_required
def convert_course_to_unweighted(course_id):
    """Convert a weighted course to unweighted (category-only) course."""
    course = Course.query.get_or_404(course_id)
    if course.term.user_id != current_user.id:
        flash("You do not have permission to modify this course.", "danger")
        return redirect(url_for("main.dashboard"))

    # Check if term is active before allowing modifications
    if not check_term_editable(course.term):
        flash("Cannot modify inactive terms.", "warning")
        return redirect(url_for("main.view_course", course_id=course.id))

    # Validate that the course is currently weighted
    if not course.is_weighted:
        flash("This course is already unweighted.", "warning")
        return redirect(url_for("main.view_course", course_id=course.id))

    try:
        # Convert the course to unweighted
        course.is_weighted = False

        # Keep the categories but zero out their weights to preserve the data
        # This allows for potential future conversion back to weighted if needed
        for category in course.grade_categories:
            category.weight = 0.0

        db.session.commit()
        flash(
            f'Course "{course.name}" successfully converted to unweighted! Categories are preserved but weights are removed.',
            "success",
        )

    except Exception as e:
        db.session.rollback()
        flash(f"Error converting course: {str(e)}", "danger")

    return redirect(url_for("main.view_course", course_id=course.id))


# Sync Status and Management Routes


@main_bp.route("/sync")
@login_required
def sync_status():
    """Display sync status and management page."""
    from app.google_tasks_sync import GoogleTasksSyncManager
    from app.google_auth import setup_google_credentials_instructions

    try:
        sync_manager = GoogleTasksSyncManager()

        # Check if Google credentials are set up
        if not sync_manager.auth_manager.has_credentials_file():
            instructions = setup_google_credentials_instructions()
            return render_template(
                "sync.html",
                setup_required=True,
                setup_instructions=instructions,
                total_assignments=0,
                synced_tasks=0,
                needs_sync=0,
                assignments=[],
                is_authenticated=False,
            )

        # Check if user is authenticated
        is_authenticated = sync_manager.is_authenticated()
        if not is_authenticated:
            auth_url = sync_manager.get_auth_url()
            return render_template(
                "sync.html",
                auth_required=True,
                auth_url=auth_url,
                total_assignments=0,
                synced_tasks=0,
                needs_sync=0,
                assignments=[],
                is_authenticated=False,
            )

        # Get all assignments for the current user's active terms
        active_terms = (
            Term.query.filter_by(user_id=current_user.id, active=True)
            .options(joinedload(Term.courses).joinedload(Course.assignments))
            .all()
        )
        all_assignments = []
        for term in active_terms:
            for course in term.courses:
                all_assignments.extend(course.assignments)

        # Filter ungraded assignments
        ungraded_assignments = [a for a in all_assignments if a.score is None]

        # Calculate statistics with improved sync logic
        total_assignments = len(all_assignments)
        synced_assignments = [
            a
            for a in all_assignments
            if hasattr(a, "google_task_id") and a.google_task_id is not None
        ]

        # Count assignments that actually need sync
        needs_sync_assignments = []
        for assignment in all_assignments:
            has_task_id = (
                hasattr(assignment, "google_task_id")
                and assignment.google_task_id is not None
            )
            is_ungraded = assignment.score is None
            # Assignment needs sync if it's ungraded AND doesn't have a Google Task ID
            if is_ungraded and not has_task_id:
                needs_sync_assignments.append(assignment)

        needs_sync_count = len(needs_sync_assignments)

        # Prepare assignment data with sync status
        assignment_data = []
        for assignment in all_assignments:
            has_task_id = (
                hasattr(assignment, "google_task_id")
                and assignment.google_task_id is not None
            )
            is_ungraded = assignment.score is None
            # Assignment needs sync if it's ungraded AND doesn't have a Google Task ID
            needs_sync = is_ungraded and not has_task_id

            # Get course name safely
            course_name = "Unknown Course"
            try:
                course = Course.query.get(assignment.course_id)
                if course:
                    course_name = course.name
            except Exception:
                pass

            assignment_data.append(
                {
                    "id": assignment.id,
                    "name": assignment.name,
                    "course_name": course_name,
                    "due_date": assignment.due_date,
                    "last_synced_tasks": getattr(assignment, "last_synced_tasks", None),
                    "last_modified": assignment.last_modified,
                    "needs_sync": needs_sync,
                    "has_task_id": has_task_id,
                    "is_graded": assignment.score is not None,
                }
            )

        # Sort by sync priority (needs sync first, then by due date)
        assignment_data.sort(
            key=lambda x: (not x["needs_sync"], x["due_date"] or datetime.max)
        )

        return render_template(
            "sync.html",
            total_assignments=total_assignments,
            synced_tasks=len(synced_assignments),
            needs_sync=needs_sync_count,
            assignments=assignment_data,
            is_authenticated=True,
        )

    except Exception as e:
        flash(f"Error loading sync status: {str(e)}", "danger")
        return render_template(
            "sync.html",
            total_assignments=0,
            synced_tasks=0,
            needs_sync=0,
            assignments=[],
            is_authenticated=False,
        )


@main_bp.route("/sync/individual/<int:assignment_id>", methods=["POST"])
@login_required
def sync_individual_assignment(assignment_id):
    """Sync a single assignment to Google Tasks."""
    from app.google_tasks_sync import GoogleTasksSyncManager

    assignment = Assignment.query.get_or_404(assignment_id)

    # Check permission
    course = Course.query.get(assignment.course_id)
    if not course or course.term.user_id != current_user.id:
        return jsonify({"success": False, "message": "Permission denied"}), 403

    try:
        sync_manager = GoogleTasksSyncManager()

        if not sync_manager.is_authenticated():
            return jsonify(
                {"success": False, "message": "Not authenticated with Google Tasks"}
            ), 401

        result = sync_manager.sync_assignment(assignment)

        if result["success"]:
            return jsonify(
                {
                    "success": True,
                    "message": result["message"],
                    "assignment_id": assignment_id,
                    "task_id": result.get("task_id"),
                }
            )
        else:
            return jsonify({"success": False, "message": result["message"]}), 500

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@main_bp.route("/sync/bulk", methods=["POST"])
@login_required
def sync_bulk_assignments():
    """Sync multiple selected assignments to Google Tasks."""
    from app.google_tasks_sync import GoogleTasksSyncManager

    try:
        data = request.get_json()
        assignment_ids = data.get("assignment_ids", [])

        if not assignment_ids:
            return jsonify(
                {"success": False, "message": "No assignments selected"}
            ), 400

        sync_manager = GoogleTasksSyncManager()

        if not sync_manager.is_authenticated():
            return jsonify(
                {"success": False, "message": "Not authenticated with Google Tasks"}
            ), 401

        # Get assignments and verify permissions
        assignments = Assignment.query.filter(Assignment.id.in_(assignment_ids)).all()

        # Check permissions for all assignments
        for assignment in assignments:
            course = Course.query.get(assignment.course_id)
            if not course or course.term.user_id != current_user.id:
                return jsonify(
                    {
                        "success": False,
                        "message": "Permission denied for one or more assignments",
                    }
                ), 403

        # Execute bulk sync
        result = sync_manager.sync_assignments(assignments)

        return jsonify(
            {
                "success": result["success"],
                "message": result["message"],
                "total": result["total"],
                "synced": result["synced"],
                "failed": result["failed"],
            }
        )

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@main_bp.route("/sync/all", methods=["POST"])
@login_required
def sync_all_assignments():
    """Sync all ungraded assignments to Google Tasks."""
    from app.google_tasks_sync import GoogleTasksSyncManager

    try:
        sync_manager = GoogleTasksSyncManager()

        if not sync_manager.is_authenticated():
            return jsonify(
                {"success": False, "message": "Not authenticated with Google Tasks"}
            ), 401

        # Get all ungraded assignments for the current user's active terms
        active_terms = (
            Term.query.filter_by(user_id=current_user.id, active=True)
            .options(joinedload(Term.courses).joinedload(Course.assignments))
            .all()
        )
        user_assignments = []
        for term in active_terms:
            for course in term.courses:
                # Only sync ungraded assignments
                ungraded = [a for a in course.assignments if a.score is None]
                user_assignments.extend(ungraded)

        if not user_assignments:
            return jsonify({"success": True, "message": "No assignments need syncing"})

        # Execute sync all
        result = sync_manager.sync_assignments(user_assignments)

        return jsonify(
            {
                "success": result["success"],
                "message": result["message"],
                "total": result["total"],
                "synced": result["synced"],
                "failed": result["failed"],
            }
        )

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@main_bp.route("/sync/progress")
@login_required
def get_sync_progress():
    """Get current Google Tasks sync progress."""
    from app.google_tasks_sync import GoogleTasksSyncManager
    import time

    try:
        sync_manager = GoogleTasksSyncManager()
        progress = sync_manager.get_progress()

        # Calculate progress percentage
        if progress["total"] > 0:
            progress_percent = round((progress["current"] / progress["total"]) * 100)
        else:
            progress_percent = 100 if progress["status"] == "completed" else 0

        # Calculate elapsed time (basic implementation)
        start_time = getattr(sync_manager, "start_time", None)
        if start_time is not None:
            elapsed_time = round(time.time() - start_time, 1)
        else:
            elapsed_time = 0

        return jsonify(
            {
                "progress_percent": progress_percent,
                "completed_items": progress["current"],
                "total_items": progress["total"],
                "current_operation": progress["message"],
                "status": progress["status"],
                "is_complete": progress["status"] in ["completed", "ready"],
                "elapsed_time": elapsed_time,
                "errors": [],  # GoogleTasksSyncManager doesn't currently track errors separately
            }
        )

    except Exception as e:
        return jsonify(
            {
                "progress_percent": 0,
                "completed_items": 0,
                "total_items": 0,
                "current_operation": f"Error: {str(e)}",
                "status": "error",
                "is_complete": True,
                "elapsed_time": 0,
                "errors": [str(e)],
            }
        )


@main_bp.route("/sync/execute", methods=["POST"])
@login_required
def execute_sync():
    """Execute the actual sync operation with progress updates."""
    from app.google_tasks_sync import GoogleTasksSyncManager

    try:
        data = request.get_json()
        sync_type = data.get("sync_type", "all")
        assignment_ids = data.get("assignment_ids", [])

        sync_manager = GoogleTasksSyncManager()

        # Check authentication
        if not sync_manager.is_authenticated():
            return jsonify(
                {"success": False, "message": "Not authenticated with Google Tasks"}
            ), 401

        # Get assignments to sync
        if sync_type == "bulk" and assignment_ids:
            assignments = Assignment.query.filter(
                Assignment.id.in_(assignment_ids)
            ).all()
            # Filter to user's assignments only
            user_assignments = []
            for assignment in assignments:
                course = Course.query.get(assignment.course_id)
                if course and course.term.user_id == current_user.id:
                    user_assignments.append(assignment)
            assignments = user_assignments
        else:
            # Get all ungraded assignments for the current user's active terms
            active_terms = (
                Term.query.filter_by(user_id=current_user.id, active=True)
                .options(joinedload(Term.courses).joinedload(Course.assignments))
                .all()
            )
            assignments = []
            for term in active_terms:
                for course in term.courses:
                    # Only sync ungraded assignments
                    ungraded = [a for a in course.assignments if a.score is None]
                    assignments.extend(ungraded)

        if not assignments:
            return jsonify({"success": True, "message": "No assignments to sync"})

        # Execute the sync using GoogleTasksSyncManager
        result = sync_manager.sync_assignments(assignments)

        return jsonify(
            {
                "success": result["success"],
                "message": result["message"],
                "total": result["total"],
                "synced": result["synced"],
                "failed": result["failed"],
            }
        )

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@main_bp.route("/sync/clear_all", methods=["POST"])
@login_required
def clear_all_synced():
    """Clear all synced assignments from Google Tasks."""
    from app.google_tasks_sync import GoogleTasksSyncManager

    try:
        sync_manager = GoogleTasksSyncManager()

        if not sync_manager.is_authenticated():
            return jsonify(
                {"success": False, "message": "Not authenticated with Google Tasks"}
            ), 401

        # Get all assignments for the current user's active terms
        active_terms = (
            Term.query.filter_by(user_id=current_user.id, active=True)
            .options(joinedload(Term.courses).joinedload(Course.assignments))
            .all()
        )
        all_assignments = []
        for term in active_terms:
            for course in term.courses:
                all_assignments.extend(course.assignments)

        if not all_assignments:
            return jsonify({"success": True, "message": "No assignments found"})

        # Execute clear all synced
        result = sync_manager.clear_all_synced_assignments(all_assignments)

        return jsonify(
            {
                "success": result["success"],
                "message": result["message"],
                "total": result["total"],
                "cleared": result["cleared"],
                "failed": result["failed"],
            }
        )

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@main_bp.route("/google_auth_callback")
@login_required
def google_auth_callback():
    """Handle Google OAuth2 callback and store credentials."""
    from app.google_auth import GoogleAuthManager

    try:
        auth_manager = GoogleAuthManager()

        # Get the authorization code from the callback
        code = request.args.get("code")
        state = request.args.get("state")
        error = request.args.get("error")

        if error:
            flash(f"Google authorization failed: {error}", "danger")
            return redirect(url_for("main.sync_status"))

        if not code:
            flash("Authorization code not received from Google", "danger")
            return redirect(url_for("main.sync_status"))

        # Exchange authorization code for credentials
        success, message = auth_manager.handle_auth_callback(code, state)

        if success:
            flash("Successfully connected to Google Tasks!", "success")
        else:
            flash(f"Failed to connect to Google Tasks: {message}", "danger")

    except Exception as e:
        flash(f"Error during Google authentication: {str(e)}", "danger")

    return redirect(url_for("main.sync_status"))


@main_bp.route("/delete_term/<int:term_id>", methods=["POST"])
@login_required
def delete_term(term_id):
    """Delete a term and all associated data."""
    term = Term.query.filter_by(id=term_id, user_id=current_user.id).first()
    if term:
        db.session.delete(term)
        db.session.commit()
        flash(
            f'Term "{term.nickname}" and all its associated data deleted successfully!',
            "success",
        )
    else:
        flash("Term not found or you do not have permission to delete it.", "danger")
    return redirect(url_for("main.dashboard"))


@main_bp.route("/toggle_term_active/<int:term_id>", methods=["POST"])
@login_required
def toggle_term_active(term_id):
    """Toggle term activation status."""
    term = Term.query.filter_by(id=term_id, user_id=current_user.id).first()
    if term:
        term.active = not term.active
        db.session.commit()
        status = "activated" if term.active else "deactivated"
        flash(f'Term "{term.nickname}" has been {status} successfully!', "success")
    else:
        flash("Term not found or you do not have permission to modify it.", "danger")
    return redirect(url_for("main.dashboard"))


@main_bp.route("/term/<int:term_id>/add_course", methods=["POST"])
@login_required
def add_course(term_id):
    """Add a new course to a term."""
    term = Term.query.filter_by(id=term_id, user_id=current_user.id).first_or_404()

    # Check if term is active before allowing modifications
    if not check_term_editable(term):
        return redirect(url_for("main.view_term", term_id=term.id))

    course_name = request.form.get("course_name")
    credits = request.form.get("credits")
    is_weighted = request.form.get("is_weighted") == "True"
    is_category = request.form.get("is_category") == "True"

    if not course_name or not credits:
        flash("Course name and credits are required.", "danger")
    else:
        try:
            credits = float(credits)
            if credits <= 0:
                flash("Credits must be a positive number.", "danger")
            else:
                new_course = Course(
                    name=course_name,
                    credits=credits,
                    term_id=term.id,
                    is_weighted=is_weighted,
                    is_category=is_category,
                )
                db.session.add(new_course)
                db.session.commit()

                if is_weighted:
                    category_names = request.form.getlist("category_names[]")
                    category_weights = request.form.getlist("category_weights[]")

                    for name, weight_str in zip(category_names, category_weights):
                        try:
                            weight = float(weight_str)
                            if 0 < weight <= 100:
                                new_category = GradeCategory(
                                    name=name,
                                    weight=weight / 100,
                                    course_id=new_course.id,
                                )
                                db.session.add(new_category)
                            else:
                                flash(
                                    f"Invalid weight for category {name}. Must be between 0 and 100.",
                                    "warning",
                                )
                        except ValueError:
                            flash(
                                f"Invalid weight format for category {name}. Must be a number.",
                                "warning",
                            )
                    db.session.commit()

                elif is_category:
                    category_names = request.form.getlist("category_names[]")

                    for name in category_names:
                        if name.strip():
                            new_category = GradeCategory(
                                name=name, weight=0, course_id=new_course.id
                            )
                            db.session.add(new_category)
                    db.session.commit()

                flash(
                    f'Course "{course_name}" added successfully to {term.nickname}!',
                    "success",
                )
        except ValueError:
            flash("Credits must be a valid number.", "danger")
    return redirect(url_for("main.view_term", term_id=term.id))


@main_bp.route("/course/<int:course_id>/rename", methods=["POST"])
@login_required
def rename_course(course_id):
    """Rename a course and update its credits."""
    course = Course.query.get_or_404(course_id)
    if course.term.user_id != current_user.id:
        flash("You do not have permission to edit this course.", "danger")
        return redirect(url_for("main.dashboard"))

    # Check if term is active before allowing modifications
    if not check_term_editable(course.term):
        flash("Cannot modify inactive terms.", "warning")
        return redirect(url_for("main.view_course", course_id=course.id))

    new_name = request.form.get("name", "").strip()
    new_credits = request.form.get("credits", "").strip()

    if not new_name or not new_credits:
        flash("Course name and credits are required.", "danger")
        return redirect(url_for("main.view_course", course_id=course.id))

    try:
        credits = float(new_credits)
        if credits < 0 or credits > 20:
            flash("Credits must be between 0 and 20.", "danger")
            return redirect(url_for("main.view_course", course_id=course.id))

        old_name = course.name
        old_credits = course.credits
        course.name = new_name
        course.credits = credits
        db.session.commit()

        # Show informative message about what changed
        if old_name != new_name and old_credits != credits:
            flash(
                f'Course renamed from "{old_name}" to "{new_name}" and credits updated from {old_credits} to {credits}!',
                "success",
            )
        elif old_name != new_name:
            flash(f'Course renamed from "{old_name}" to "{new_name}"!', "success")
        elif old_credits != credits:
            flash(f"Course credits updated from {old_credits} to {credits}!", "success")
        else:
            flash("No changes made.", "info")

    except ValueError:
        flash("Credits must be a valid number.", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating course: {str(e)}", "danger")

    return redirect(url_for("main.view_course", course_id=course.id))


@main_bp.route("/course/<int:course_id>/delete", methods=["POST"])
@login_required
def delete_course(course_id):
    """Delete a course and all associated data."""
    course = Course.query.get_or_404(course_id)
    if course.term.user_id != current_user.id:
        flash("You do not have permission to delete this course.", "danger")
        return redirect(url_for("main.dashboard"))

    term_id = course.term_id
    db.session.delete(course)
    db.session.commit()
    flash(
        f'Course "{course.name}" and all its associated data deleted successfully!',
        "success",
    )
    return redirect(url_for("main.view_term", term_id=term_id))


@main_bp.route("/course/<int:course_id>")
@login_required
def view_course(course_id):
    """View detailed course information with assignments and categories."""
    course = Course.query.get_or_404(course_id)
    if course.term.user_id != current_user.id:
        flash("You do not have permission to view this course.", "danger")
        return redirect(url_for("main.dashboard"))

    # Order assignments with null due_dates last (MariaDB compatible)
    assignments = (
        Assignment.query.filter_by(course_id=course_id)
        .order_by(Assignment.due_date.asc())
        .all()
    )
    # Separate assignments with and without due dates, then combine
    assignments_with_dates = [a for a in assignments if a.due_date is not None]
    assignments_without_dates = [a for a in assignments if a.due_date is None]
    assignments = assignments_with_dates + assignments_without_dates

    # Add percentage calculation to each assignment
    for assignment in assignments:
        percentage, is_graded = calculate_assignment_percentage(assignment)
        assignment.percentage = percentage if is_graded else None
    grade_categories = (
        GradeCategory.query.filter_by(course_id=course.id)
        .order_by(GradeCategory.weight.desc())
        .all()
    )

    # Calculate category averages
    category_averages = {}
    for category in grade_categories:
        average, is_active = GradeCalculatorService.calculate_category_average(
            category, assignments
        )
        if is_active:
            category_averages[category.id] = average

    # Helper function to handle mixed date types in sorting
    def get_sort_date(assignment):
        if assignment.due_date is None:
            return datetime.max.date()
        if isinstance(assignment.due_date, datetime):
            return assignment.due_date.date()
        return assignment.due_date

    assignments_by_category = {}
    for category in grade_categories:
        assignments_by_category[category.id] = sorted(
            [a for a in assignments if a.category_id == category.id], key=get_sort_date
        )

    uncategorized_assignments = sorted(
        [a for a in assignments if a.category_id is None], key=get_sort_date
    )

    # Calculate overall course grade
    overall_grade_percentage = GradeCalculatorService.calculate_course_grade(course)
    gpa_contribution = GradeCalculatorService.calculate_gpa_contribution(
        course, overall_grade_percentage
    )

    term_courses = (
        Course.query.filter_by(term_id=course.term_id).order_by(Course.name).all()
    )

    # Total weight for weighted courses
    total_weight_pct = None
    if course.is_weighted:
        total_weight_pct = round(
            sum((c.weight or 0.0) for c in grade_categories) * 100, 2
        )

    # Function to determine assignment due date status
    def get_assignment_status(assignment):
        if not assignment.due_date:
            return None

        # Convert due_date to date object if it's a datetime
        if isinstance(assignment.due_date, datetime):
            due_date = assignment.due_date.date()
        else:
            due_date = assignment.due_date

        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        week_from_today = today + timedelta(days=7)

        if due_date < today:
            return "overdue"
        elif due_date == today:
            return "due-today"
        elif due_date == tomorrow:
            return "due-tomorrow"
        elif due_date <= week_from_today:
            return "due-this-week"
        else:
            return None

    # Add status to all assignments
    assignment_statuses = {}
    for assignment in assignments:
        assignment_statuses[assignment.id] = get_assignment_status(assignment)

    # Separate graded and ungraded assignments based on score field
    graded_assignments = [a for a in assignments if a.score is not None]
    ungraded_assignments = [a for a in assignments if a.score is None]

    # Split assignments by category for both completed and uncompleted
    graded_assignments_by_category = {}
    ungraded_assignments_by_category = {}

    for category in grade_categories:
        graded_assignments_by_category[category.id] = sorted(
            [a for a in graded_assignments if a.category_id == category.id],
            key=get_sort_date,
        )
        ungraded_assignments_by_category[category.id] = sorted(
            [a for a in ungraded_assignments if a.category_id == category.id],
            key=get_sort_date,
        )

    # Uncategorized assignments split by completed/uncompleted
    graded_uncategorized = sorted(
        [a for a in graded_assignments if a.category_id is None], key=get_sort_date
    )
    ungraded_uncategorized = sorted(
        [a for a in ungraded_assignments if a.category_id is None], key=get_sort_date
    )

    # Use centralized categorization utility
    categorized = categorize_assignments(assignments)

    # Extract categorized assignments (note: due_this_week and due_next_week combined into "current")
    missing_assignments = categorized["missing"]
    current_assignments = (
        categorized["due_this_week"] + categorized["due_next_week"]
    )  # Combine both weeks for course view
    awaiting_grading_assignments = categorized["waiting_grading"]
    future_assignments = categorized["future"]
    complete_assignments = categorized["completed"]

    # Sort all sections by due date
    current_assignments = sorted(current_assignments, key=get_sort_date)

    # Create category-split versions for each section
    def split_by_category(assignment_list):
        by_category = {}
        for category in grade_categories:
            by_category[category.id] = [
                a for a in assignment_list if a.category_id == category.id
            ]
        uncategorized = [a for a in assignment_list if a.category_id is None]
        return by_category, uncategorized

    missing_by_category, missing_uncategorized = split_by_category(missing_assignments)
    current_by_category, current_uncategorized = split_by_category(current_assignments)
    awaiting_by_category, awaiting_uncategorized = split_by_category(
        awaiting_grading_assignments
    )
    future_by_category, future_uncategorized = split_by_category(future_assignments)
    complete_by_category, complete_uncategorized = split_by_category(
        complete_assignments
    )

    # Calculate counts for statistics
    completed_count = len(complete_assignments)
    pending_count = len(current_assignments) + len(awaiting_grading_assignments)

    return render_template(
        "view_course.html",
        course=course,
        assignments=assignments,
        grade_categories=grade_categories,
        assignments_by_category=assignments_by_category,
        uncategorized_assignments=uncategorized_assignments,
        graded_assignments=graded_assignments,
        ungraded_assignments=ungraded_assignments,
        graded_assignments_by_category=graded_assignments_by_category,
        ungraded_assignments_by_category=ungraded_assignments_by_category,
        graded_uncategorized=graded_uncategorized,
        ungraded_uncategorized=ungraded_uncategorized,
        category_averages=category_averages,
        overall_grade_percentage=overall_grade_percentage,
        gpa_contribution=gpa_contribution,
        is_weighted=course.is_weighted,
        term_courses=term_courses,
        total_weight_pct=total_weight_pct,
        assignment_statuses=assignment_statuses,
        # New 5-section data
        missing_assignments=missing_assignments,
        current_assignments=current_assignments,
        awaiting_grading_assignments=awaiting_grading_assignments,
        future_assignments=future_assignments,
        complete_assignments=complete_assignments,
        missing_by_category=missing_by_category,
        missing_uncategorized=missing_uncategorized,
        current_by_category=current_by_category,
        current_uncategorized=current_uncategorized,
        awaiting_by_category=awaiting_by_category,
        awaiting_uncategorized=awaiting_uncategorized,
        future_by_category=future_by_category,
        future_uncategorized=future_uncategorized,
        complete_by_category=complete_by_category,
        complete_uncategorized=complete_uncategorized,
        completed_count=completed_count,
        pending_count=pending_count,
    )


@main_bp.route("/course/<int:course_id>/add_assignment", methods=["POST"])
@login_required
def add_assignment(course_id):
    """Add a new assignment to a course."""
    course = Course.query.get_or_404(course_id)
    if course.term.user_id != current_user.id:
        flash("You do not have permission to add assignments to this course.", "danger")
        return redirect(url_for("main.dashboard"))

    # Check if term is active before allowing modifications
    if not check_term_editable(course.term):
        return redirect(url_for("main.view_course", course_id=course_id))

    name = request.form.get("name")
    score_str = request.form.get("score")
    max_score_str = request.form.get("max_score")
    category_id = request.form.get("category_id")
    due_date_str = request.form.get("due_date")
    is_extra_credit = request.form.get("is_extra_credit") == "on"

    if not name or not max_score_str:
        flash("Assignment name and max score are required.", "danger")
    else:
        try:
            max_score = float(max_score_str)
            # Allow max_score = 0 for extra credit assignments
            if max_score <= 0 and not is_extra_credit:
                flash("Max Score must be a positive number.", "danger")
            elif max_score < 0:
                flash("Max Score cannot be negative.", "danger")
            else:
                score = float(score_str) if score_str else None
                due_date = None
                if due_date_str:
                    try:
                        due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
                    except ValueError:
                        flash(
                            "Invalid due date format. Please use YYYY-MM-DD.", "danger"
                        )
                new_assignment = Assignment(
                    name=name,
                    score=score,
                    max_score=max_score,
                    course_id=course.id,
                    category_id=category_id,
                    due_date=due_date,
                    is_extra_credit=is_extra_credit,
                )
                db.session.add(new_assignment)
                db.session.commit()

                flash(f'Assignment "{name}" added successfully!', "success")
        except ValueError:
            flash("Invalid number format for score or max score.", "danger")
    return redirect(url_for("main.view_course", course_id=course.id))


@main_bp.route("/course/<int:course_id>/import_canvas_grades", methods=["POST"])
@login_required
def import_canvas_grades(course_id):
    """Import assignments from Canvas grade text."""
    course = Course.query.get_or_404(course_id)
    if course.term.user_id != current_user.id:
        flash("Unauthorized.", "danger")
        return redirect(url_for("main.dashboard"))

    # Check if term is active before allowing modifications
    if not check_term_editable(course.term):
        flash("Cannot modify inactive terms.", "warning")
        return redirect(url_for("main.view_course", course_id=course.id))

    try:
        from app.utils.canvas_parser import parse_canvas_grades, validate_canvas_data
        import json

        canvas_text = request.form.get("canvas_text", "").strip()
        year_hint = request.form.get("year_hint")

        if not canvas_text:
            flash("Please paste Canvas grade text.", "danger")
            return redirect(url_for("main.view_course", course_id=course.id))

        # Parse year hint if provided
        year = None
        if year_hint:
            try:
                year = int(year_hint)
            except ValueError:
                pass

        # Parse the Canvas text using our parser
        df = parse_canvas_grades(canvas_text, year_hint=year)

        if df.empty:
            flash("No assignments found in the Canvas text.", "warning")
            return redirect(url_for("main.view_course", course_id=course.id))

        # Validate the parsed data
        validation_results = validate_canvas_data(df)

        if not validation_results["is_complete"]:
            # Data is incomplete, redirect to completion form
            assignments_data = [(idx, row) for idx, row in df.iterrows()]
            return render_template(
                "complete_canvas_import.html",
                course=course,
                assignments_data=assignments_data,
                validation_results=validation_results,
                canvas_data_json=json.dumps(df.to_dict("records")),
            )

        # Data is complete, proceed with direct import
        added_count = 0
        skipped_count = 0
        for _, row in df.iterrows():
            name = str(row.get("name", "")).strip()
            score = row.get("score")
            max_score = row.get("max_score")
            category_name = (
                str(row.get("category", "")).strip() if row.get("category") else None
            )
            due_date_str = (
                str(row.get("due_date", "")).strip() if row.get("due_date") else None
            )

            if not name or max_score is None:
                continue  # Skip invalid rows

            try:
                # Check if assignment with this name already exists in the course
                existing_assignment = Assignment.query.filter_by(
                    course_id=course.id, name=name
                ).first()
                if existing_assignment:
                    skipped_count += 1
                    continue  # Skip duplicate assignment

                # Find or create category by name if provided
                category_id = None
                if category_name:
                    category = GradeCategory.query.filter_by(
                        course_id=course.id, name=category_name
                    ).first()
                    if not category:
                        # Create new category with default weight
                        category = GradeCategory(
                            name=category_name,
                            weight=10.0,  # Default weight
                            course_id=course.id,
                        )
                        db.session.add(category)
                        db.session.flush()  # Get the ID before committing
                    category_id = category.id

                # Parse due date if provided (can be YYYY-MM-DD or YYYY-MM-DD HH:MM:SS format from parser)
                due_date = None
                if due_date_str and due_date_str != "nan":
                    try:
                        # Try parsing with time first
                        due_date = datetime.strptime(due_date_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        try:
                            # Fall back to date-only format for backwards compatibility
                            due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
                        except ValueError:
                            pass  # Skip invalid dates

                assignment = Assignment(
                    name=name,
                    score=score if score is not None and str(score) != "nan" else None,
                    max_score=float(max_score),
                    course_id=course.id,
                    category_id=category_id,
                    due_date=due_date,
                )
                db.session.add(assignment)
                added_count += 1

            except (ValueError, TypeError):
                continue  # Skip rows with invalid data

        db.session.commit()

        if skipped_count > 0:
            flash(
                f"Successfully imported {added_count} assignments from Canvas! ({skipped_count} duplicates skipped)",
                "success",
            )
        else:
            flash(
                f"Successfully imported {added_count} assignments from Canvas!",
                "success",
            )

    except Exception as e:
        db.session.rollback()
        flash(f"Error importing Canvas grades: {str(e)}", "danger")

    return redirect(url_for("main.view_course", course_id=course.id))


@main_bp.route(
    "/course/<int:course_id>/complete_canvas_import", methods=["GET", "POST"]
)
@login_required
def complete_canvas_import(course_id):
    """Complete Canvas import by filling in missing data."""
    course = Course.query.get_or_404(course_id)
    if course.term.user_id != current_user.id:
        flash("Unauthorized.", "danger")
        return redirect(url_for("main.dashboard"))

    # Check if term is active before allowing modifications
    if not check_term_editable(course.term):
        flash("Cannot modify inactive terms.", "warning")
        return redirect(url_for("main.view_course", course_id=course.id))

    if request.method == "GET":
        # This should only be accessed via POST with canvas_data
        flash("Invalid access to completion form.", "danger")
        return redirect(url_for("main.view_course", course_id=course.id))

    try:
        from app.utils.canvas_parser import validate_canvas_data
        import json

        # Get canvas data from form
        canvas_data_json = request.form.get("canvas_data")
        if not canvas_data_json:
            flash("Missing canvas data.", "danger")
            return redirect(url_for("main.view_course", course_id=course.id))

        canvas_data = json.loads(canvas_data_json)

        # Reconstruct DataFrame from JSON data
        import pandas as pd

        df = pd.DataFrame(canvas_data)

        # Check if this is a completion submission
        if "name_0" in request.form:
            # Process the completed data
            for idx in range(len(df)):
                # Update data with form values
                name = request.form.get(f"name_{idx}", "").strip()
                category = request.form.get(f"category_{idx}", "").strip()
                score = request.form.get(f"score_{idx}", "").strip()
                max_score = request.form.get(f"max_score_{idx}", "").strip()
                due_date = request.form.get(f"due_date_{idx}", "").strip()

                if name:
                    df.at[idx, "name"] = name
                if category:
                    df.at[idx, "category"] = category
                if score:
                    try:
                        df.at[idx, "score"] = float(score)
                    except ValueError:
                        df.at[idx, "score"] = None
                if max_score:
                    try:
                        df.at[idx, "max_score"] = float(max_score)
                    except ValueError:
                        pass
                if due_date:
                    df.at[idx, "due_date"] = due_date

        # Validate the updated data
        validation_results = validate_canvas_data(df)

        if not validation_results["is_complete"]:
            # Still incomplete, show form again
            assignments_data = [(idx, row) for idx, row in df.iterrows()]
            return render_template(
                "complete_canvas_import.html",
                course=course,
                assignments_data=assignments_data,
                validation_results=validation_results,
                canvas_data_json=json.dumps(df.to_dict("records")),
            )

        # Data is complete, proceed with import
        added_count = 0
        skipped_count = 0
        for _, row in df.iterrows():
            name = str(row.get("name", "")).strip()
            score = row.get("score")
            max_score = row.get("max_score")
            category_name = (
                str(row.get("category", "")).strip() if row.get("category") else None
            )
            due_date_str = (
                str(row.get("due_date", "")).strip() if row.get("due_date") else None
            )

            if not name or max_score is None:
                continue  # Skip invalid rows

            try:
                # Check if assignment with this name already exists in the course
                existing_assignment = Assignment.query.filter_by(
                    course_id=course.id, name=name
                ).first()
                if existing_assignment:
                    skipped_count += 1
                    continue  # Skip duplicate assignment

                # Find or create category by name if provided
                category_id = None
                if category_name:
                    category = GradeCategory.query.filter_by(
                        course_id=course.id, name=category_name
                    ).first()
                    if not category:
                        # Create new category with default weight
                        category = GradeCategory(
                            name=category_name,
                            weight=10.0,  # Default weight
                            course_id=course.id,
                        )
                        db.session.add(category)
                        db.session.flush()  # Get the ID before committing
                    category_id = category.id

                # Parse due date
                due_date = None
                if due_date_str and due_date_str != "nan":
                    try:
                        due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
                    except ValueError:
                        pass  # Skip invalid dates

                assignment = Assignment(
                    name=name,
                    score=score if score is not None and str(score) != "nan" else None,
                    max_score=float(max_score),
                    course_id=course.id,
                    category_id=category_id,
                    due_date=due_date,
                )
                db.session.add(assignment)
                added_count += 1

            except (ValueError, TypeError):
                continue  # Skip rows with invalid data

        db.session.commit()

        if skipped_count > 0:
            flash(
                f"Successfully imported {added_count} assignments from Canvas! ({skipped_count} duplicates skipped)",
                "success",
            )
        else:
            flash(
                f"Successfully imported {added_count} assignments from Canvas!",
                "success",
            )

    except Exception as e:
        db.session.rollback()
        flash(f"Error completing Canvas import: {str(e)}", "danger")

    return redirect(url_for("main.view_course", course_id=course.id))


@main_bp.route("/assignment/<int:assignment_id>/delete", methods=["POST"])
@login_required
def delete_assignment(assignment_id):
    """Delete an assignment."""
    assignment = Assignment.query.get_or_404(assignment_id)
    course_id = assignment.course_id
    if assignment.course.term.user_id != current_user.id:
        flash("You do not have permission to delete this assignment.", "danger")
        return redirect(url_for("main.dashboard"))

    db.session.delete(assignment)
    db.session.commit()
    flash(f'Assignment "{assignment.name}" deleted successfully!', "success")
    return redirect(url_for("main.view_course", course_id=course_id))


@main_bp.route("/assignment/<int:assignment_id>/duplicate", methods=["POST"])
@login_required
def duplicate_assignment(assignment_id):
    """Duplicate an assignment."""
    assignment = Assignment.query.get_or_404(assignment_id)
    course_id = assignment.course_id
    if assignment.course.term.user_id != current_user.id:
        flash("You do not have permission to duplicate this assignment.", "danger")
        return redirect(url_for("main.dashboard"))

    # Create a copy of the assignment
    new_assignment = Assignment(
        name=f"{assignment.name} (Copy)",
        score=None,  # Reset score for the duplicate
        max_score=assignment.max_score,
        course_id=assignment.course_id,
        category_id=assignment.category_id,
        due_date=assignment.due_date,
        completed=False,
        is_submitted=False,
        is_extra_credit=assignment.is_extra_credit,
        is_missing=False,
        estimated_difficulty=assignment.estimated_difficulty,
        time_investment_hours=assignment.time_investment_hours,
        submission_method=None,  # Reset for the duplicate
        late_submission=False,
        performance_impact=None,  # Will be recalculated
    )

    db.session.add(new_assignment)
    db.session.commit()
    flash(f'Assignment "{assignment.name}" duplicated successfully!', "success")
    return redirect(url_for("main.view_course", course_id=course_id))


@main_bp.route("/assignment/<int:assignment_id>/move_category", methods=["POST"])
@login_required
def move_assignment_category(assignment_id):
    """Move assignment to different category via drag and drop."""
    assignment = Assignment.query.get_or_404(assignment_id)
    if assignment.course.term.user_id != current_user.id:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    data = request.get_json(silent=True) or {}
    category_id = data.get("category_id", None)

    # Capture old value for audit logging
    old_category_id = assignment.category_id

    # Allow null to uncategorize
    if category_id in (None, "null", ""):
        assignment.category_id = None
    else:
        try:
            new_cat_id = int(category_id)
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "Invalid category_id"}), 400
        new_cat = GradeCategory.query.get_or_404(new_cat_id)
        if new_cat.course_id != assignment.course_id:
            return jsonify(
                {"success": False, "message": "Category must belong to the same course"}
            ), 400
        assignment.category_id = new_cat.id

    try:
        # Log the change if category changed
        if old_category_id != assignment.category_id:
            old_cat_name = None
            new_cat_name = None
            if old_category_id:
                old_cat = GradeCategory.query.get(old_category_id)
                old_cat_name = old_cat.name if old_cat else None
            if assignment.category_id:
                new_cat = GradeCategory.query.get(assignment.category_id)
                new_cat_name = new_cat.name if new_cat else None

            action = "moved_category"
            log_assignment_change(
                assignment, "category", old_cat_name, new_cat_name, action
            )

        db.session.commit()
        course = assignment.course
        overall = GradeCalculatorService.calculate_course_grade(course)
        gpa_contrib = GradeCalculatorService.calculate_gpa_contribution(course, overall)
        return jsonify(
            {
                "success": True,
                "assignment_id": assignment.id,
                "category_id": assignment.category_id,
                "overall_grade_percentage": overall,
                "gpa_contribution": gpa_contrib,
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@main_bp.route("/analytics/export")
@login_required
def export_analytics():
    """Export analytics data as CSV."""
    try:
        import pandas as pd
        from io import StringIO

        # Get all user's terms and courses
        terms = (
            Term.query.filter_by(user_id=current_user.id)
            .order_by(Term.year.asc(), Term.season)
            .all()
        )

        # Prepare data for export
        export_data = []
        for term in terms:
            term_gpa = GradeCalculatorService.calculate_term_gpa(term)
            for course in term.courses:
                course_grade = GradeCalculatorService.calculate_course_grade(course)
                export_data.append(
                    {
                        "Term": f"{term.season} {term.year}",
                        "Term_Nickname": term.nickname,
                        "Course": course.name,
                        "Credits": course.credits,
                        "Course_Grade": course_grade if course_grade else 0,
                        "Term_GPA": term_gpa if term_gpa else 0,
                    }
                )

        if not export_data:
            flash("No data to export.", "warning")
            return redirect(url_for("main.analytics"))

        # Create DataFrame and export to CSV
        df = pd.DataFrame(export_data)
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)

        from flask import Response

        response = Response(
            csv_buffer.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=grade_analytics.csv"},
        )
        return response

    except ImportError:
        flash("Data export requires pandas. Please install pandas.", "error")
        return redirect(url_for("main.analytics"))
    except Exception as e:
        flash(f"Error exporting data: {str(e)}", "error")
        return redirect(url_for("main.analytics"))


@main_bp.route("/calendar")
@login_required
def calendar_view():
    """Calendar view of all assignments."""
    try:
        # Get all assignments for the user with due dates
        assignments = (
            Assignment.query.join(Course)
            .join(Term)
            .filter(Term.user_id == current_user.id, Assignment.due_date.isnot(None))
            .order_by(Assignment.due_date)
            .all()
        )

        # Group assignments by date
        assignments_by_date = {}
        for assignment in assignments:
            date_key = assignment.due_date.strftime("%Y-%m-%d")
            if date_key not in assignments_by_date:
                assignments_by_date[date_key] = []
            assignments_by_date[date_key].append(
                {
                    "id": assignment.id,
                    "name": assignment.name,
                    "course": assignment.course.name,
                    "score": assignment.score,
                    "max_score": assignment.max_score,
                    "completed": assignment.completed,
                    "is_overdue": assignment.due_date < datetime.now()
                    and assignment.score is None,
                }
            )

        return render_template("calendar.html", assignments_by_date=assignments_by_date)

    except Exception as e:
        flash(f"Error loading calendar: {str(e)}", "error")
        return redirect(url_for("main.dashboard"))


@main_bp.route("/analytics")
@login_required
def analytics():
    """Analytics page showing grade statistics and trends."""
    try:
        # Get all user's terms and courses
        terms = (
            Term.query.filter_by(user_id=current_user.id)
            .order_by(Term.year.asc(), Term.season)
            .all()
        )

        # Calculate term statistics
        term_stats = []
        gpa_trend = []
        credit_distribution = {"Fall": 0, "Spring": 0, "Summer": 0, "Winter": 0}

        for term in terms:
            term_gpa = GradeCalculatorService.calculate_term_gpa(term)
            total_courses = len(term.courses)
            total_credits = sum(course.credits for course in term.courses)

            term_stat = {
                "nickname": term.nickname,
                "name": f"{term.season} {term.year}",
                "gpa": term_gpa if term_gpa is not None else 0.0,
                "credits": total_credits,
                "courses": total_courses,
            }
            term_stats.append(term_stat)

            # Add to GPA trend
            if term_gpa is not None:
                gpa_trend.append(
                    {"term": f"{term.season} {term.year}", "gpa": term_gpa}
                )

            # Add to credit distribution
            if term.season in credit_distribution:
                credit_distribution[term.season] += total_credits

        # Calculate overall GPA across all terms
        total_credits = sum(stat["credits"] for stat in term_stats)
        weighted_gpa_sum = sum(
            stat["gpa"] * stat["credits"] for stat in term_stats if stat["gpa"] > 0
        )
        overall_gpa = weighted_gpa_sum / total_credits if total_credits > 0 else 0.0

        # Create data object for template
        data = {
            "overall_gpa": overall_gpa,
            "total_credits": total_credits,
            "terms": term_stats,
            "gpa_trend": gpa_trend,
            "credit_distribution": credit_distribution,
        }

        return render_template("analytics.html", data=data)
    except Exception as e:
        flash(f"An error occurred while loading analytics: {str(e)}", "danger")
        return redirect(url_for("main.dashboard"))


@main_bp.route("/todo")
@login_required
def todo():
    """Todo page showing user's todo items."""
    try:
        # Get all todos for now (since the current schema doesn't link todos to users)
        # In a multi-user environment, this should be improved to filter by user
        todos = TodoItem.query.order_by(TodoItem.due_date.asc()).all()

        # Get all assignments from user's courses (not just ungraded ones)
        assignments = (
            Assignment.query.join(Course)
            .join(Term)
            .filter(Term.user_id == current_user.id)
            .order_by(Assignment.due_date.asc())
            .all()
        )

        # Get courses for dropdown
        courses = Course.query.join(Term).filter(Term.user_id == current_user.id).all()

        # Use centralized categorization utility for assignments
        categorized = categorize_assignments(assignments)

        # Group each category by course
        def group_by_course(assignment_list):
            grouped = defaultdict(list)
            for assignment in assignment_list:
                course_name = assignment.course.name if assignment.course else "General"
                grouped[course_name].append(assignment)
            return dict(grouped)

        missing_assignments = group_by_course(categorized["missing"])
        waiting_grading = group_by_course(categorized["waiting_grading"])
        due_this_week = group_by_course(categorized["due_this_week"])
        due_next_week = group_by_course(categorized["due_next_week"])
        future = group_by_course(categorized["future"])
        completed_assignments = group_by_course(categorized["completed"])

        # Process TodoItems and add them to the appropriate categories
        today = datetime.now().date()
        current_monday = today - timedelta(days=today.weekday())
        this_week_end = current_monday + timedelta(days=6)
        next_monday = current_monday + timedelta(days=7)
        next_week_end = next_monday + timedelta(days=6)

        for todo in todos:
            # Add template-expected attributes
            todo.todo_table = True
            todo.assignment_table = False

            course_name = todo.course.name if todo.course else "General"

            if todo.due_date:
                todo_date = (
                    todo.due_date.date()
                    if isinstance(todo.due_date, datetime)
                    else todo.due_date
                )

                # Categorize todo items by due date
                if current_monday <= todo_date <= this_week_end:
                    if course_name not in due_this_week:
                        due_this_week[course_name] = []
                    due_this_week[course_name].append(todo)
                elif next_monday <= todo_date <= next_week_end:
                    if course_name not in due_next_week:
                        due_next_week[course_name] = []
                    due_next_week[course_name].append(todo)
                else:
                    if course_name not in future:
                        future[course_name] = []
                    future[course_name].append(todo)
            else:
                # No due date - put in future
                if course_name not in future:
                    future[course_name] = []
                future[course_name].append(todo)

        # Add template-expected attributes to assignments
        for assignment in assignments:
            assignment.assignment_table = True
            assignment.todo_table = False
            assignment.is_completed = assignment.completed

        # Sort items within each course group by due date
        def sort_items_by_date(items):
            return sorted(items, key=lambda x: (x.due_date is None, x.due_date))

        for category in [
            missing_assignments,
            waiting_grading,
            due_this_week,
            due_next_week,
            future,
            completed_assignments,
        ]:
            for course_name in category:
                category[course_name] = sort_items_by_date(category[course_name])

        return render_template(
            "todo.html",
            missing_assignments=missing_assignments,
            waiting_grading=waiting_grading,
            due_this_week=due_this_week,
            due_next_week=due_next_week,
            future=future,
            completed_assignments=completed_assignments,
            courses=courses,
            all_todos=todos,
            assignments=assignments,
            # Legacy support (in case template still uses these)
            overdue={},
        )
    except Exception as e:
        flash(f"An error occurred while loading todos: {str(e)}", "danger")
        return redirect(url_for("main.dashboard"))


@main_bp.route("/delete_todo_item/<int:todo_id>", methods=["POST"])
@login_required
def delete_todo_item(todo_id):
    """Delete a todo item."""
    try:
        todo = TodoItem.query.get_or_404(todo_id)
        todo_description = todo.description
        db.session.delete(todo)
        db.session.commit()
        flash(f'ToDo item "{todo_description}" deleted successfully!', "success")

    except Exception as e:
        db.session.rollback()
        flash("An error occurred while deleting the todo item.", "danger")

    return redirect(url_for("main.todo"))


@main_bp.route("/toggle_todo/<int:todo_id>", methods=["POST"])
@login_required
def toggle_todo(todo_id):
    """Toggle completion status of a todo item."""
    try:
        # Both routes now use FormData, so no need to get JSON data
        todo = TodoItem.query.get_or_404(todo_id)

        # Check if user owns this todo item (via course ownership)
        if todo.course_id:
            if todo.course.term.user_id != current_user.id:
                return jsonify({"success": False, "error": "Permission denied"}), 403

        todo.is_completed = not todo.is_completed
        db.session.commit()
        return jsonify({"success": True, "is_completed": todo.is_completed})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@main_bp.route("/toggle_assignment_completion/<int:assignment_id>", methods=["POST"])
@login_required
def toggle_assignment_completion(assignment_id):
    """Toggle completion status of an assignment."""
    try:
        assignment = Assignment.query.get_or_404(assignment_id)

        # Check if user owns this assignment
        if assignment.course.term.user_id != current_user.id:
            return jsonify({"success": False, "error": "Permission denied"}), 403

        assignment.completed = not assignment.completed
        db.session.commit()
        return jsonify({"success": True, "completed": assignment.completed})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@main_bp.route("/course/<int:course_id>/convert_to_weighted", methods=["POST"])
@login_required
def convert_course_to_weighted(course_id):
    """Convert an unweighted course to weighted course."""
    course = Course.query.get_or_404(course_id)
    if course.term.user_id != current_user.id:
        flash("You do not have permission to modify this course.", "danger")
        return redirect(url_for("main.dashboard"))

    # Check if term is active before allowing modifications
    if not check_term_editable(course.term):
        flash("Cannot modify inactive terms.", "warning")
        return redirect(url_for("main.view_course", course_id=course.id))

    # Validate that the course is currently unweighted
    if course.is_weighted:
        flash("This course is already weighted.", "warning")
        return redirect(url_for("main.view_course", course_id=course.id))

    try:
        # Check if course has categories
        categories = GradeCategory.query.filter_by(course_id=course.id).all()

        if not categories:
            flash(
                "Cannot convert to weighted course: no categories found. Please create categories first.",
                "warning",
            )
            return redirect(url_for("main.view_course", course_id=course.id))

        # Convert the course to weighted
        course.is_weighted = True
        course.is_category = False  # Ensure it's not marked as category-only

        # Assign default equal weights to all categories
        default_weight = 1.0 / len(categories)  # Equal distribution

        for category in categories:
            category.weight = default_weight

        db.session.commit()

        flash(
            f'Course "{course.name}" successfully converted to weighted! All {len(categories)} categories have been assigned equal weights ({default_weight * 100:.1f}% each). You can adjust individual weights as needed.',
            "success",
        )

    except Exception as e:
        db.session.rollback()
        flash(f"Error converting course: {str(e)}", "danger")

    return redirect(url_for("main.view_course", course_id=course.id))
