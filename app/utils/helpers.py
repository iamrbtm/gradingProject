"""
Utility functions for Grade Tracker application
"""

from datetime import datetime, timedelta
from flask import flash


def serialize_model(obj):
    """Convert SQLAlchemy model to dict, excluding private attributes and metadata."""
    return {
        column.name: getattr(obj, column.name)
        for column in obj.__table__.columns
    }


def is_term_active(term):
    """Check if a term is active and can be edited."""
    return getattr(term, 'active', True)


def check_term_editable(term):
    """Check if a term can be edited, show flash message if not."""
    if not is_term_active(term):
        flash(f'Term "{term.nickname}" is inactive and cannot be edited.', 'warning')
        return False
    return True


def calculate_assignment_percentage(assignment):
    if assignment.max_score == 0 or assignment.score is None:
        return None, False  # Not graded or cannot contribute a percentage
    return (assignment.score / assignment.max_score) * 100, True


def calculate_category_average(grade_category, all_assignments_for_course):
    total_earned_points_in_category = 0.0
    total_possible_points_in_category = 0.0

    # Filter assignments belonging to this category
    category_assignments = [a for a in all_assignments_for_course if a.category_id == grade_category.id]

    for assignment in category_assignments:
        percentage, is_graded = calculate_assignment_percentage(assignment)
        if is_graded:
            total_earned_points_in_category += assignment.score
            total_possible_points_in_category += assignment.max_score

    if total_possible_points_in_category > 0.0:
        average_percentage = (total_earned_points_in_category / total_possible_points_in_category) * 100
        return average_percentage, True  # Category is active
    else:
        return None, False  # Category is inactive (no graded assignments)


def calculate_course_grade(course):
    if course.is_weighted:
        weighted_sum_of_category_percentages = 0.0
        total_active_category_weight = 0.0

        for category in course.grade_categories:
            average_percentage, is_active = calculate_category_average(category, course.assignments)
            if is_active:
                category_decimal_average = average_percentage / 100
                weighted_sum_of_category_percentages += (category_decimal_average * category.weight)
                total_active_category_weight += category.weight

        if total_active_category_weight > 0.0:
            return (weighted_sum_of_category_percentages / total_active_category_weight) * 100
        else:
            return 0.0  # No graded assignments in any category
    else:
        # Traditional unweighted grading
        all_assignments = course.assignments
        if all_assignments:
            total_score = sum(a.score for a in all_assignments if a.score is not None)
            total_max_score = sum(a.max_score for a in all_assignments if a.max_score is not None and a.score is not None)
            return (total_score / total_max_score) * 100 if total_max_score > 0 else 0.0
        else:
            return 0.0  # No assignments yet


def get_comparison_date(assignment):
    """
    Helper function to get date for comparison from assignment.
    
    Args:
        assignment: Assignment object with due_date attribute
        
    Returns:
        date object or None
    """
    if assignment.due_date is None:
        return None
    if isinstance(assignment.due_date, datetime):
        return assignment.due_date.date()
    return assignment.due_date


def categorize_assignment(assignment):
    """
    Categorize an assignment based on the standardized business logic.
    
    Business Logic:
    1. If is_missing is True → Missing
    2. If is_submitted and completed are True AND no score → Waiting for Grading
    3. If due date falls between Monday and Sunday of this week → Due This Week
    4. If due date falls between Monday and Sunday of next week → Due Next Week
    5. If due date is in the future (beyond next week) → Future
    6. If completed and is_submitted are True AND has a score → Completed
    7. Default → Future (for assignments without due dates)
    
    Args:
        assignment: Assignment object
        
    Returns:
        str: Category name - 'missing', 'waiting_grading', 'due_this_week', 
             'due_next_week', 'future', or 'completed'
    """
    from datetime import datetime, timedelta
    
    # Priority 1: Missing assignments
    if assignment.is_missing:
        return 'missing'
    
    # Priority 2: Completed with score
    if assignment.completed and assignment.is_submitted and assignment.score is not None:
        return 'completed'
    
    # Priority 3: Waiting for grading (submitted and completed but no score)
    if assignment.is_submitted and assignment.completed and assignment.score is None:
        return 'waiting_grading'
    
    # Get due date for time-based categorization
    due_date = get_comparison_date(assignment)
    
    # If no due date, put in Future
    if not due_date:
        return 'future'
    
    # Calculate week boundaries (Monday to Sunday)
    today = datetime.now().date()
    current_monday = today - timedelta(days=today.weekday())  # Monday of current week
    this_week_end = current_monday + timedelta(days=6)  # Sunday of current week
    next_monday = current_monday + timedelta(days=7)  # Monday of next week
    next_week_end = next_monday + timedelta(days=6)  # Sunday of next week
    
    # Priority 4: Due this week (Monday to Sunday)
    if current_monday <= due_date <= this_week_end:
        return 'due_this_week'
    
    # Priority 5: Due next week (Monday to Sunday)
    if next_monday <= due_date <= next_week_end:
        return 'due_next_week'
    
    # Priority 6: Future (beyond next week)
    if due_date > next_week_end:
        return 'future'
    
    # Edge case: past due but not marked as missing (shouldn't happen with triggers)
    # Put it in future to be safe
    return 'future'


def categorize_assignments(assignments):
    """
    Categorize a list of assignments into sections based on business logic.
    
    Args:
        assignments: List of Assignment objects
        
    Returns:
        dict: Dictionary with keys 'missing', 'waiting_grading', 'due_this_week',
              'due_next_week', 'future', 'completed', each containing a list of assignments
    """
    categories = {
        'missing': [],
        'waiting_grading': [],
        'due_this_week': [],
        'due_next_week': [],
        'future': [],
        'completed': []
    }
    
    for assignment in assignments:
        category = categorize_assignment(assignment)
        categories[category].append(assignment)
    
    # Sort each category by due date (None values last)
    def sort_by_due_date(assignment_list):
        return sorted(assignment_list, key=lambda x: (x.due_date is None, x.due_date))
    
    for category in categories:
        categories[category] = sort_by_due_date(categories[category])
    
    return categories