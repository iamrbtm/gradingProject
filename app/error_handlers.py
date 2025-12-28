import logging
from flask import render_template, request, current_app, flash, redirect, url_for
from werkzeug.exceptions import HTTPException


def init_error_handlers(app):
    """Initialize centralized error handlers for the Flask app."""

    @app.errorhandler(400)
    def bad_request_error(error):
        """Handle 400 Bad Request errors (including CSRF failures)."""
        # Check if this is a CSRF error
        error_msg = str(error)
        if "CSRF" in error_msg or "csrf" in error_msg.lower():
            app.logger.warning(f"CSRF validation failed: {request.url}")
            flash("Security token expired or missing. Please try again.", "warning")
            # Redirect back to the referring page or login
            return redirect(request.referrer or url_for("auth.login"))

        app.logger.warning(f"400 error: {request.url}, Error: {error_msg}")
        return render_template("errors/400.html") if app.config.get("DEBUG") else (
            "Bad Request",
            400,
        ), 400

    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors."""
        app.logger.warning(f"404 error: {request.url}")
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        app.logger.error(f"500 error: {request.url}, Error: {str(error)}")
        # Rollback any pending database transactions
        try:
            from app.models import db

            db.session.rollback()
        except:
            pass
        return render_template("errors/500.html"), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 errors."""
        app.logger.warning(f"403 error: {request.url}")
        return render_template("errors/403.html"), 403

    @app.errorhandler(Exception)
    def handle_exception(e):
        """Handle all other exceptions."""
        # Pass through HTTP errors
        if isinstance(e, HTTPException):
            return e

        # Log the exception
        app.logger.error(f"Unhandled exception: {request.url}", exc_info=True)

        # Rollback any pending database transactions
        try:
            from app.models import db

            db.session.rollback()
        except:
            pass

        # Return a generic 500 page for non-HTTP exceptions
        return render_template("errors/500.html"), 500


def setup_logging(app):
    """Setup structured logging for the application."""
    try:
        # Use comprehensive logging configuration if available
        from .logging_config import setup_comprehensive_logging

        setup_comprehensive_logging(app)
        app.logger.info("Comprehensive logging configured successfully")
        return
    except ImportError:
        app.logger.warning("Comprehensive logging not available, using basic setup")

    import logging.handlers
    import os

    if not app.debug and not app.testing:
        # Production logging setup

        # Create logs directory if it doesn't exist
        if not os.path.exists("logs"):
            os.mkdir("logs")

        # File handler for application logs
        file_handler = logging.handlers.RotatingFileHandler(
            "logs/grade_tracker.log", maxBytes=10240000, backupCount=10
        )

        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
            )
        )

        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info("Grade Tracker startup")

    else:
        # Development logging setup
        app.logger.setLevel(logging.DEBUG)

        # Console handler for development
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
        )
        app.logger.addHandler(console_handler)
