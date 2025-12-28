"""
Error handling service for consistent error and success message patterns.
Consolidates flash message and error response handling across the application.
"""
from flask import flash, jsonify, redirect, url_for, request
from typing import Optional, Any, Tuple


class ErrorHandler:
    """Service class for standardized error and success message handling."""

    # Common error messages
    UNAUTHORIZED = "Unauthorized access"
    TERM_INACTIVE = "This term is inactive and cannot be edited"
    VALIDATION_ERROR = "Please check your input and try again"
    DATABASE_ERROR = "A database error occurred"
    FILE_ERROR = "File processing error"
    NETWORK_ERROR = "Network connection error"

    # Common success messages
    CREATED_SUCCESS = "Item created successfully"
    UPDATED_SUCCESS = "Item updated successfully"
    DELETED_SUCCESS = "Item deleted successfully"
    IMPORTED_SUCCESS = "Data imported successfully"

    @staticmethod
    def flash_error(message: str, category: str = 'danger') -> None:
        """Standardized flash error message."""
        flash(message, category)

    @staticmethod
    def flash_success(message: str, category: str = 'success') -> None:
        """Standardized flash success message."""
        flash(message, category)

    @staticmethod
    def flash_validation_error(message: str) -> None:
        """Flash a validation error message."""
        ErrorHandler.flash_error(message, 'danger')

    @staticmethod
    def flash_unauthorized() -> None:
        """Flash an unauthorized access message."""
        ErrorHandler.flash_error(ErrorHandler.UNAUTHORIZED, 'danger')

    @staticmethod
    def flash_term_inactive() -> None:
        """Flash a term inactive message."""
        ErrorHandler.flash_error(ErrorHandler.TERM_INACTIVE, 'danger')

    @staticmethod
    def handle_database_error(error: Exception, operation: str = "operation") -> None:
        """Handle database errors consistently."""
        error_msg = f"Error during {operation}: {str(error)}"
        ErrorHandler.flash_error(error_msg, 'danger')

    @staticmethod
    def handle_import_error(error: Exception, source: str = "data") -> None:
        """Handle import errors consistently."""
        error_msg = f"Error importing {source}: {str(error)}"
        ErrorHandler.flash_error(error_msg, 'danger')

    @staticmethod
    def handle_file_error(error: Exception, operation: str = "file operation") -> None:
        """Handle file operation errors consistently."""
        error_msg = f"Error during {operation}: {str(error)}"
        ErrorHandler.flash_error(error_msg, 'danger')

    @staticmethod
    def handle_network_error(error: Exception, service: str = "service") -> None:
        """Handle network errors consistently."""
        error_msg = f"Error connecting to {service}: {str(error)}"
        ErrorHandler.flash_error(error_msg, 'danger')

    @staticmethod
    def handle_generic_error(error: Exception, context: str = "operation") -> None:
        """Handle generic errors consistently."""
        error_msg = f"An error occurred during {context}: {str(error)}"
        ErrorHandler.flash_error(error_msg, 'danger')

    @staticmethod
    def handle_success(operation: str, item_name: str = "item") -> None:
        """Handle success messages consistently."""
        message = f"{item_name.title()} {operation} successfully"
        ErrorHandler.flash_success(message)

    @staticmethod
    def handle_create_success(item_name: str) -> None:
        """Handle creation success messages."""
        ErrorHandler.handle_success("created", item_name)

    @staticmethod
    def handle_update_success(item_name: str) -> None:
        """Handle update success messages."""
        ErrorHandler.handle_success("updated", item_name)

    @staticmethod
    def handle_delete_success(item_name: str) -> None:
        """Handle deletion success messages."""
        ErrorHandler.handle_success("deleted", item_name)

    @staticmethod
    def handle_import_success(count: int, item_type: str = "items") -> None:
        """Handle import success messages."""
        message = f"Successfully imported {count} {item_type}"
        ErrorHandler.flash_success(message)

    @staticmethod
    def handle_conversion_success(item_name: str, conversion_type: str) -> None:
        """Handle conversion success messages."""
        message = f"{item_name} successfully converted to {conversion_type}"
        ErrorHandler.flash_success(message)

    @staticmethod
    def handle_auth_success(action: str = "authenticated") -> None:
        """Handle authentication success messages."""
        message = f"Successfully {action}"
        ErrorHandler.flash_success(message)

    @staticmethod
    def handle_settings_success() -> None:
        """Handle settings update success messages."""
        ErrorHandler.flash_success("Settings saved successfully")

    @staticmethod
    def handle_reminder_success() -> None:
        """Handle reminder sending success messages."""
        ErrorHandler.flash_success("Reminders sent successfully")

    @staticmethod
    def json_error(message: str, status_code: int = 400) -> Tuple[Any, int]:
        """Return a JSON error response."""
        return jsonify({'success': False, 'message': message}), status_code

    @staticmethod
    def json_unauthorized() -> Tuple[Any, int]:
        """Return a JSON unauthorized response."""
        return ErrorHandler.json_error(ErrorHandler.UNAUTHORIZED, 403)

    @staticmethod
    def json_validation_error(message: str) -> Tuple[Any, int]:
        """Return a JSON validation error response."""
        return ErrorHandler.json_error(message, 400)

    @staticmethod
    def json_term_inactive() -> Tuple[Any, int]:
        """Return a JSON term inactive response."""
        return ErrorHandler.json_error(ErrorHandler.TERM_INACTIVE, 403)

    @staticmethod
    def json_success(message: str = "Operation completed successfully") -> Any:
        """Return a JSON success response."""
        return jsonify({'success': True, 'message': message})

    @staticmethod
    def json_created(item_name: str) -> Any:
        """Return a JSON creation success response."""
        return ErrorHandler.json_success(f"{item_name} created successfully")

    @staticmethod
    def json_updated(item_name: str) -> Any:
        """Return a JSON update success response."""
        return ErrorHandler.json_success(f"{item_name} updated successfully")

    @staticmethod
    def json_deleted(item_name: str) -> Any:
        """Return a JSON deletion success response."""
        return ErrorHandler.json_success(f"{item_name} deleted successfully")

    @staticmethod
    def redirect_with_error(url: str, message: str, category: str = 'danger') -> Any:
        """Redirect with an error message."""
        flash(message, category)
        return redirect(url)

    @staticmethod
    def redirect_with_success(url: str, message: str, category: str = 'success') -> Any:
        """Redirect with a success message."""
        flash(message, category)
        return redirect(url)

    @staticmethod
    def redirect_unauthorized(fallback_url: str = 'main.dashboard') -> Any:
        """Redirect with unauthorized message."""
        return ErrorHandler.redirect_with_error(url_for(fallback_url), ErrorHandler.UNAUTHORIZED)

    @staticmethod
    def redirect_term_inactive(fallback_url: str = 'main.dashboard') -> Any:
        """Redirect with term inactive message."""
        return ErrorHandler.redirect_with_error(url_for(fallback_url), ErrorHandler.TERM_INACTIVE)

    @staticmethod
    def handle_exception(error: Exception, context: str = "operation", is_json: bool = False) -> Any:
        """Handle exceptions consistently based on request type."""
        ErrorHandler.handle_generic_error(error, context)

        if is_json:
            return ErrorHandler.json_error(f"An error occurred during {context}")

        return redirect(url_for('main.dashboard'))

    @staticmethod
    def handle_validation_exception(error: Exception, field_name: str, is_json: bool = False) -> Any:
        """Handle validation exceptions consistently."""
        message = f"Invalid {field_name}: {str(error)}"
        ErrorHandler.flash_validation_error(message)

        if is_json:
            return ErrorHandler.json_validation_error(message)

        return redirect(request.referrer or url_for('main.dashboard'))