"""
Validation service for common form validation patterns.
Consolidates validation logic used across different blueprints.
"""
from flask import request, flash, jsonify
from typing import Optional, Union, Tuple, Any
import re


class ValidationService:
    """Service class for form validation operations."""

    # Security patterns
    SQL_INJECTION_PATTERNS = [
        r';\s*--',  # SQL comment
        r';\s*/\*',  # SQL comment block
        r'union\s+select',  # UNION attack
        r'/\*.*\*/',  # Comment blocks
    ]

    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',  # JavaScript URLs
        r'on\w+\s*=',  # Event handlers
        r'<iframe[^>]*>',  # Iframe tags
    ]

    @staticmethod
    def sanitize_string(value: str, max_length: int = 255) -> str:
        """Sanitize string input for security."""
        if not value:
            return ""

        # Remove null bytes and control characters
        value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)

        # Truncate to max length
        if len(value) > max_length:
            value = value[:max_length]

        return value.strip()

    @staticmethod
    def validate_no_sql_injection(value: str) -> Tuple[bool, str]:
        """Check for potential SQL injection patterns."""
        if not value:
            return True, ""

        for pattern in ValidationService.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return False, "Invalid input detected"

        return True, ""

    @staticmethod
    def validate_no_xss(value: str) -> Tuple[bool, str]:
        """Check for potential XSS patterns."""
        if not value:
            return True, ""

        for pattern in ValidationService.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return False, "Invalid input detected"

        return True, ""

    @staticmethod
    def validate_safe_string(value: str, field_name: str, max_length: int = 255) -> Tuple[bool, str]:
        """Comprehensive string validation with security checks."""
        if not value:
            return False, f"{field_name} is required"

        # Sanitize
        value = ValidationService.sanitize_string(value, max_length)

        # Check for SQL injection
        is_safe, error_msg = ValidationService.validate_no_sql_injection(value)
        if not is_safe:
            return False, f"Invalid {field_name.lower()}"

        # Check for XSS
        is_safe, error_msg = ValidationService.validate_no_xss(value)
        if not is_safe:
            return False, f"Invalid {field_name.lower()}"

        # Check length
        if len(value) > max_length:
            return False, f"{field_name} is too long (max {max_length} characters)"

        return True, value

    @staticmethod
    def get_required_string(field_name: str, default: str = '') -> str:
        """Get a required string field from form data."""
        value = request.form.get(field_name, default).strip()
        return value

    @staticmethod
    def get_optional_string(field_name: str, default: str = '') -> str:
        """Get an optional string field from form data."""
        return request.form.get(field_name, default).strip()

    @staticmethod
    def get_required_int(field_name: str, default: int = 0) -> int:
        """Get a required integer field from form data."""
        try:
            return int(request.form.get(field_name, default))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def get_optional_int(field_name: str, default: int = 0) -> int:
        """Get an optional integer field from form data."""
        value = request.form.get(field_name)
        if value is None or value == '':
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def get_required_float(field_name: str, default: float = 0.0) -> float:
        """Get a required float field from form data."""
        try:
            return float(request.form.get(field_name, default))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def get_optional_float(field_name: str, default: float = 0.0) -> float:
        """Get an optional float field from form data."""
        value = request.form.get(field_name)
        if value is None or value == '':
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def get_boolean_field(field_name: str, default: bool = False) -> bool:
        """Get a boolean field from form data (checkbox)."""
        return request.form.get(field_name) == 'on' or request.form.get(field_name) == 'True'

    @staticmethod
    def validate_required_field(value: str, field_name: str) -> Tuple[bool, str]:
        """Validate that a required field is not empty."""
        if not value or not value.strip():
            return False, f"{field_name} is required"
        return True, ""

    @staticmethod
    def validate_year_range(year: int, min_year: int = 1900, max_year: int = 2100) -> Tuple[bool, str]:
        """Validate that a year is within a valid range."""
        if not (min_year <= year <= max_year):
            return False, f"Please enter a valid year between {min_year} and {max_year}"
        return True, ""

    @staticmethod
    def validate_weight_range(weight: float, min_weight: float = 0.0, max_weight: float = 100.0) -> Tuple[bool, str]:
        """Validate that a weight is within a valid range."""
        if not (min_weight <= weight <= max_weight):
            return False, f"Weight must be between {min_weight} and {max_weight}"
        return True, ""

    @staticmethod
    def validate_term_data(nickname: str, season: str, year: int, school_name: str) -> Tuple[bool, str]:
        """Validate term creation data."""
        # Check required fields
        is_valid, error_msg = ValidationService.validate_required_field(nickname, "Nickname")
        if not is_valid:
            return False, error_msg

        is_valid, error_msg = ValidationService.validate_required_field(season, "Season")
        if not is_valid:
            return False, error_msg

        is_valid, error_msg = ValidationService.validate_required_field(school_name, "School name")
        if not is_valid:
            return False, error_msg

        # Validate year
        is_valid, error_msg = ValidationService.validate_year_range(year)
        if not is_valid:
            return False, error_msg

        return True, ""

    @staticmethod
    def validate_category_data(name: str, weight: float, is_weighted: bool = True) -> Tuple[bool, str]:
        """Validate category creation/update data."""
        # Check required fields
        is_valid, error_msg = ValidationService.validate_required_field(name, "Category name")
        if not is_valid:
            return False, error_msg

        if is_weighted:
            # Validate weight
            is_valid, error_msg = ValidationService.validate_weight_range(weight)
            if not is_valid:
                return False, error_msg

        return True, ""

    @staticmethod
    def validate_assignment_data(name: str, score: float, max_score: float, category_id: Optional[int] = None) -> Tuple[bool, str]:
        """Validate assignment creation/update data."""
        # Check required fields
        is_valid, error_msg = ValidationService.validate_required_field(name, "Assignment name")
        if not is_valid:
            return False, error_msg

        # Validate scores
        if score < 0:
            return False, "Score cannot be negative"

        if max_score <= 0:
            return False, "Maximum score must be greater than 0"

        if score > max_score:
            return False, "Score cannot exceed maximum score"

        return True, ""

    @staticmethod
    def handle_validation_error(error_msg: str, is_json: bool = False) -> Any:
        """Handle validation errors consistently."""
        if is_json:
            return jsonify({'success': False, 'message': error_msg}), 400
        flash(error_msg, 'danger')
        return None

    @staticmethod
    def handle_success_message(message: str, is_json: bool = False) -> Any:
        """Handle success messages consistently."""
        if is_json:
            return jsonify({'success': True, 'message': message})
        flash(message, 'success')
        return None