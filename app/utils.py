
# Import utilities from the centralized helpers module
from app.utils.helpers import (
    serialize_model,
    is_term_active,
    check_term_editable,
    calculate_assignment_percentage,
    calculate_category_average,
    calculate_course_grade
)

# Re-export for backward compatibility
__all__ = [
    'serialize_model',
    'is_term_active', 
    'check_term_editable',
    'calculate_assignment_percentage',
    'calculate_category_average',
    'calculate_course_grade'
]