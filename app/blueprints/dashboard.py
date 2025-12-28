from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from app.models import db, Term, Course
from app.services.grade_calculator import GradeCalculatorService

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
@login_required
def dashboard():
    """Main dashboard showing user's terms."""
    try:
        all_user_terms = (
            Term.query.filter_by(user_id=current_user.id)
            .order_by(Term.year.desc(), Term.season)
            .options(
                joinedload(Term.courses).joinedload(Course.assignments),
                joinedload(Term.courses).joinedload(Course.grade_categories),
            )
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
        flash(f"Error loading dashboard: {str(e)}", "error")
        return render_template(
            "dashboard.html", active_terms=[], inactive_terms=[], schools=[]
        )


@dashboard_bp.route("/term/<int:term_id>")
@login_required
def term_detail(term_id):
    """Display detailed view of a specific term."""
    term = Term.query.filter_by(id=term_id, user_id=current_user.id).first_or_404()

    # Get courses for this term
    courses = (
        Course.query.filter_by(term_id=term.id)
        .options(joinedload(Course.assignments), joinedload(Course.grade_categories))
        .order_by(Course.name)
        .all()
    )

    # Calculate GPA and other metrics
    term_gpa = GradeCalculatorService.calculate_term_gpa(term)

    # Use the same template as the main blueprint
    return render_template(
        "view_term.html", term=term, courses=courses, term_gpa=term_gpa
    )


@dashboard_bp.route("/add_term", methods=["POST"])
@login_required
def add_term():
    """Add a new term for the user."""
    try:
        term_name = request.form.get("term_name")
        school_name = request.form.get("school_name")
        year = int(request.form.get("year"))
        season = request.form.get("season")

        if not all([term_name, school_name, year, season]):
            flash("All fields are required.", "error")
            return redirect(url_for("dashboard.dashboard"))

        new_term = Term(
            name=term_name,
            school_name=school_name,
            year=year,
            season=season,
            user_id=current_user.id,
            active=True,
        )

        db.session.add(new_term)
        db.session.commit()

        flash(f'Term "{term_name}" added successfully!', "success")
        return redirect(url_for("dashboard.term_detail", term_id=new_term.id))

    except Exception as e:
        db.session.rollback()
        flash(f"Error adding term: {str(e)}", "error")
        return redirect(url_for("dashboard.dashboard"))


@dashboard_bp.route("/delete_term/<int:term_id>", methods=["POST"])
@login_required
def delete_term(term_id):
    """Delete a term and all associated data."""
    term = Term.query.filter_by(id=term_id, user_id=current_user.id).first_or_404()

    try:
        # Delete associated courses and assignments will cascade
        db.session.delete(term)
        db.session.commit()
        flash(f'Term "{term.name}" deleted successfully.', "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting term: {str(e)}", "error")

    return redirect(url_for("dashboard.dashboard"))


@dashboard_bp.route("/toggle_term_active/<int:term_id>", methods=["POST"])
@login_required
def toggle_term_active(term_id):
    """Toggle a term's active status."""
    term = Term.query.filter_by(id=term_id, user_id=current_user.id).first_or_404()

    try:
        term.active = not term.active
        db.session.commit()
        status = "activated" if term.active else "deactivated"
        flash(f'Term "{term.name}" {status}.', "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating term: {str(e)}", "error")

    return redirect(url_for("dashboard.dashboard"))
