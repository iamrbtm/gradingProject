"""
Advanced Logging Configuration for Analytics System
Provides structured, production-ready logging with analytics-specific loggers.
"""

import logging
import logging.handlers
import os
import json
from datetime import datetime
from typing import Optional
from flask import Flask, has_request_context, request, g


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request context if available
        if has_request_context():
            log_record.update(
                {
                    "request_id": getattr(g, "request_id", None),
                    "user_id": getattr(g, "user_id", None),
                    "ip_address": request.remote_addr,
                    "method": request.method,
                    "url": request.url,
                    "endpoint": request.endpoint,
                    "user_agent": request.headers.get("User-Agent"),
                }
            )

        # Add exception info if present
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        # Add extra fields from the record
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
            ]:
                if not key.startswith("_"):
                    log_record[f"extra_{key}"] = value

        return json.dumps(log_record, default=str)


class AnalyticsFilter(logging.Filter):
    """Filter for analytics-specific log entries."""

    def filter(self, record):
        # Add analytics context to log records
        if hasattr(record, "analytics_event"):
            setattr(record, "extra_analytics_event", getattr(record, "analytics_event"))

        if hasattr(record, "user_id"):
            setattr(record, "extra_user_id", getattr(record, "user_id"))

        if hasattr(record, "course_id"):
            setattr(record, "extra_course_id", getattr(record, "course_id"))

        return True


def setup_comprehensive_logging(app: Flask):
    """Setup comprehensive logging configuration for production analytics system."""

    # Don't setup logging if already configured or in testing
    if app.logger.hasHandlers() and not app.config.get("FORCE_LOGGING_SETUP", False):
        return

    # Clear existing handlers in case of reconfiguration
    app.logger.handlers.clear()

    # Create logs directory structure
    log_dirs = ["logs", "logs/analytics", "logs/ml", "logs/exports", "logs/celery"]
    for log_dir in log_dirs:
        os.makedirs(log_dir, exist_ok=True)

    # Get log level from environment
    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO").upper())

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Application logger setup
    app.logger.setLevel(log_level)

    if app.config.get("TESTING"):
        # Simple console logging for tests
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        app.logger.addHandler(handler)
        return

    # Production vs Development logging setup
    use_json_logging = app.config.get("JSON_LOGGING", not app.debug)

    # Console handler for all environments
    console_handler = logging.StreamHandler()
    if use_json_logging:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s [%(filename)s:%(lineno)d]"
            )
        )
    console_handler.setLevel(logging.WARNING if not app.debug else logging.DEBUG)
    app.logger.addHandler(console_handler)

    if not app.debug:
        # Main application log with rotation
        app_handler = logging.handlers.RotatingFileHandler(
            "logs/application.log",
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=10,
            encoding="utf-8",
        )

        if use_json_logging:
            app_handler.setFormatter(JSONFormatter())
        else:
            app_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(name)s: %(message)s [%(filename)s:%(lineno)d]"
                )
            )

        app_handler.setLevel(logging.INFO)
        app.logger.addHandler(app_handler)

        # Error-specific log
        error_handler = logging.handlers.RotatingFileHandler(
            "logs/errors.log",
            maxBytes=25 * 1024 * 1024,  # 25MB
            backupCount=5,
            encoding="utf-8",
        )
        error_handler.setFormatter(
            JSONFormatter()
            if use_json_logging
            else logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s [%(filename)s:%(lineno)d]"
            )
        )
        error_handler.setLevel(logging.ERROR)
        app.logger.addHandler(error_handler)

    # Analytics-specific loggers
    setup_analytics_loggers(use_json_logging, log_level)

    # Performance monitoring logger
    setup_performance_logger(use_json_logging, log_level)

    # Security events logger
    setup_security_logger(use_json_logging, log_level)

    # ML operations logger
    setup_ml_logger(use_json_logging, log_level)

    # Export operations logger
    setup_export_logger(use_json_logging, log_level)

    # Celery task logger
    setup_celery_logger(use_json_logging, log_level)

    # Canvas Sync logger
    setup_canvas_sync_logger(use_json_logging, log_level)

    app.logger.info(
        f"Comprehensive logging configured - JSON: {use_json_logging}, Level: {logging.getLevelName(log_level)}"
    )


def setup_analytics_loggers(use_json_logging: bool, log_level: int):
    """Setup analytics-specific loggers."""

    # Analytics events logger
    analytics_logger = logging.getLogger("analytics")
    analytics_logger.setLevel(log_level)

    analytics_handler = logging.handlers.RotatingFileHandler(
        "logs/analytics/events.log",
        maxBytes=25 * 1024 * 1024,
        backupCount=7,
        encoding="utf-8",
    )

    formatter = (
        JSONFormatter()
        if use_json_logging
        else logging.Formatter("%(asctime)s [%(levelname)s] Analytics: %(message)s")
    )
    analytics_handler.setFormatter(formatter)
    analytics_handler.addFilter(AnalyticsFilter())
    analytics_logger.addHandler(analytics_handler)

    # Predictions logger
    predictions_logger = logging.getLogger("analytics.predictions")
    predictions_logger.setLevel(log_level)

    predictions_handler = logging.handlers.RotatingFileHandler(
        "logs/analytics/predictions.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    predictions_handler.setFormatter(formatter)
    predictions_logger.addHandler(predictions_handler)

    # Notifications logger
    notifications_logger = logging.getLogger("analytics.notifications")
    notifications_logger.setLevel(log_level)

    notifications_handler = logging.handlers.RotatingFileHandler(
        "logs/analytics/notifications.log",
        maxBytes=15 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    notifications_handler.setFormatter(formatter)
    notifications_logger.addHandler(notifications_handler)


def setup_performance_logger(use_json_logging: bool, log_level: int):
    """Setup performance monitoring logger."""

    perf_logger = logging.getLogger("performance")
    perf_logger.setLevel(log_level)

    perf_handler = logging.handlers.RotatingFileHandler(
        "logs/performance.log",
        maxBytes=20 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )

    formatter = (
        JSONFormatter()
        if use_json_logging
        else logging.Formatter("%(asctime)s [PERF] %(message)s")
    )
    perf_handler.setFormatter(formatter)
    perf_logger.addHandler(perf_handler)


def setup_security_logger(use_json_logging: bool, log_level: int):
    """Setup security events logger."""

    security_logger = logging.getLogger("security")
    security_logger.setLevel(logging.WARNING)  # Only log warnings and errors

    security_handler = logging.handlers.RotatingFileHandler(
        "logs/security.log",
        maxBytes=25 * 1024 * 1024,
        backupCount=10,  # Keep more security logs
        encoding="utf-8",
    )

    formatter = (
        JSONFormatter()
        if use_json_logging
        else logging.Formatter("%(asctime)s [SECURITY] %(levelname)s: %(message)s")
    )
    security_handler.setFormatter(formatter)
    security_logger.addHandler(security_handler)


def setup_ml_logger(use_json_logging: bool, log_level: int):
    """Setup ML operations logger."""

    ml_logger = logging.getLogger("ml")
    ml_logger.setLevel(log_level)

    ml_handler = logging.handlers.RotatingFileHandler(
        "logs/ml/operations.log",
        maxBytes=30 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )

    formatter = (
        JSONFormatter()
        if use_json_logging
        else logging.Formatter(
            "%(asctime)s [ML] %(levelname)s: %(message)s [%(filename)s:%(lineno)d]"
        )
    )
    ml_handler.setFormatter(formatter)
    ml_logger.addHandler(ml_handler)


def setup_export_logger(use_json_logging: bool, log_level: int):
    """Setup export operations logger."""

    export_logger = logging.getLogger("exports")
    export_logger.setLevel(log_level)

    export_handler = logging.handlers.RotatingFileHandler(
        "logs/exports/operations.log",
        maxBytes=15 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )

    formatter = (
        JSONFormatter()
        if use_json_logging
        else logging.Formatter("%(asctime)s [EXPORT] %(levelname)s: %(message)s")
    )
    export_handler.setFormatter(formatter)
    export_logger.addHandler(export_handler)


def setup_celery_logger(use_json_logging: bool, log_level: int):
    """Setup Celery task logger."""

    celery_logger = logging.getLogger("celery")
    celery_logger.setLevel(log_level)

    celery_handler = logging.handlers.RotatingFileHandler(
        "logs/celery/tasks.log",
        maxBytes=25 * 1024 * 1024,
        backupCount=7,
        encoding="utf-8",
    )

    formatter = (
        JSONFormatter()
        if use_json_logging
        else logging.Formatter("%(asctime)s [CELERY] %(levelname)s: %(message)s")
    )
    celery_handler.setFormatter(formatter)
    celery_logger.addHandler(celery_handler)


def setup_canvas_sync_logger(use_json_logging: bool, log_level: int):
    """Setup Canvas Sync logger with detailed operational logging."""

    # Create canvas_sync directory if it doesn't exist
    os.makedirs("logs/canvas_sync", exist_ok=True)

    # Main Canvas Sync operations logger
    canvas_sync_logger = logging.getLogger("canvas_sync")
    canvas_sync_logger.setLevel(log_level)
    canvas_sync_logger.propagate = False

    # Main operations log with detailed information
    canvas_sync_handler = logging.handlers.RotatingFileHandler(
        "logs/canvas_sync/operations.log",
        maxBytes=50 * 1024 * 1024,  # 50MB - larger for detailed logs
        backupCount=10,  # Keep more backups for debugging
        encoding="utf-8",
    )

    formatter = (
        JSONFormatter()
        if use_json_logging
        else logging.Formatter(
            "%(asctime)s [CANVAS_SYNC] %(levelname)s [%(funcName)s:%(lineno)d]: %(message)s"
        )
    )
    canvas_sync_handler.setFormatter(formatter)
    canvas_sync_logger.addHandler(canvas_sync_handler)

    # API calls logger
    api_logger = logging.getLogger("canvas_sync.api")
    api_logger.setLevel(log_level)
    api_logger.propagate = False

    api_handler = logging.handlers.RotatingFileHandler(
        "logs/canvas_sync/api_calls.log",
        maxBytes=30 * 1024 * 1024,
        backupCount=8,
        encoding="utf-8",
    )
    api_handler.setFormatter(formatter)
    api_logger.addHandler(api_handler)

    # Database operations logger
    db_logger = logging.getLogger("canvas_sync.db")
    db_logger.setLevel(log_level)
    db_logger.propagate = False

    db_handler = logging.handlers.RotatingFileHandler(
        "logs/canvas_sync/database.log",
        maxBytes=30 * 1024 * 1024,
        backupCount=8,
        encoding="utf-8",
    )
    db_handler.setFormatter(formatter)
    db_logger.addHandler(db_handler)

    # Error logger (all errors in Canvas sync)
    error_logger = logging.getLogger("canvas_sync.errors")
    error_logger.setLevel(logging.ERROR)
    error_logger.propagate = False

    error_handler = logging.handlers.RotatingFileHandler(
        "logs/canvas_sync/errors.log",
        maxBytes=20 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8",
    )
    error_handler.setFormatter(formatter)
    error_logger.addHandler(error_handler)

    # Progress tracking logger
    progress_logger = logging.getLogger("canvas_sync.progress")
    progress_logger.setLevel(log_level)
    progress_logger.propagate = False

    progress_handler = logging.handlers.RotatingFileHandler(
        "logs/canvas_sync/progress.log",
        maxBytes=25 * 1024 * 1024,
        backupCount=7,
        encoding="utf-8",
    )
    progress_handler.setFormatter(formatter)
    progress_logger.addHandler(progress_handler)


# Context managers for structured logging
class LogContext:
    """Context manager for adding structured context to log records."""

    def __init__(self, **context):
        self.context = context
        self.old_context = {}

    def __enter__(self):
        if has_request_context():
            for key, value in self.context.items():
                self.old_context[key] = getattr(g, key, None)
                setattr(g, key, value)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if has_request_context():
            for key in self.context.keys():
                if key in self.old_context:
                    if self.old_context[key] is not None:
                        setattr(g, key, self.old_context[key])
                    else:
                        delattr(g, key)


# Utility functions for analytics logging
def log_analytics_event(event_type: str, user_id: Optional[int] = None, **kwargs):
    """Log an analytics event with structured data."""
    logger = logging.getLogger("analytics")

    event_data = {
        "event_type": event_type,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat(),
        **kwargs,
    }

    logger.info(f"Analytics event: {event_type}", extra=event_data)


def log_prediction_event(
    model_type: str,
    user_id: Optional[int] = None,
    accuracy: Optional[float] = None,
    **kwargs,
):
    """Log a prediction event."""
    logger = logging.getLogger("analytics.predictions")

    event_data = {
        "model_type": model_type,
        "user_id": user_id,
        "accuracy": accuracy,
        **kwargs,
    }

    logger.info(f"Prediction generated: {model_type}", extra=event_data)


def log_notification_event(
    notification_type: str,
    user_id: Optional[int] = None,
    delivered: bool = False,
    **kwargs,
):
    """Log a notification event."""
    logger = logging.getLogger("analytics.notifications")

    event_data = {
        "notification_type": notification_type,
        "user_id": user_id,
        "delivered": delivered,
        **kwargs,
    }

    logger.info(
        f"Notification {notification_type}: {'delivered' if delivered else 'failed'}",
        extra=event_data,
    )


def log_performance_metric(
    metric_name: str, value: float, unit: Optional[str] = None, **kwargs
):
    """Log a performance metric."""
    logger = logging.getLogger("performance")

    metric_data = {"metric": metric_name, "value": value, "unit": unit, **kwargs}

    logger.info(
        f"Performance metric: {metric_name} = {value} {unit or ''}", extra=metric_data
    )


def log_security_event(event_type: str, severity: str = "WARNING", **kwargs):
    """Log a security event."""
    logger = logging.getLogger("security")

    event_data = {"security_event": event_type, "severity": severity, **kwargs}

    level = getattr(logging, severity.upper(), logging.WARNING)
    logger.log(level, f"Security event: {event_type}", extra=event_data)


def log_canvas_sync_event(
    event_type: str,
    user_id: Optional[int] = None,
    course_id: Optional[int] = None,
    detail_level: str = "INFO",
    **kwargs,
):
    """
    Log a Canvas sync event with detailed context.

    Args:
        event_type: Type of event (start, progress, complete, error, etc.)
        user_id: User ID performing the sync
        course_id: Course ID being synced (if applicable)
        detail_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        **kwargs: Additional context data to log
    """
    logger = logging.getLogger("canvas_sync")

    event_data = {
        "event_type": event_type,
        "user_id": user_id,
        "course_id": course_id,
        "timestamp": datetime.utcnow().isoformat(),
        **kwargs,
    }

    level = getattr(logging, detail_level.upper(), logging.INFO)
    logger.log(level, f"Canvas sync event: {event_type}", extra=event_data)


def log_canvas_api_call(
    method: str,
    endpoint: str,
    user_id: Optional[int] = None,
    response_status: Optional[int] = None,
    duration_ms: Optional[float] = None,
    **kwargs,
):
    """
    Log Canvas API calls with detailed information.

    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint being called
        user_id: User making the call
        response_status: HTTP response status code
        duration_ms: Request duration in milliseconds
        **kwargs: Additional context
    """
    logger = logging.getLogger("canvas_sync.api")

    api_data = {
        "method": method,
        "endpoint": endpoint,
        "user_id": user_id,
        "response_status": response_status,
        "duration_ms": duration_ms,
        "timestamp": datetime.utcnow().isoformat(),
        **kwargs,
    }

    logger.debug(
        f"Canvas API call: {method} {endpoint} - Status: {response_status}",
        extra=api_data,
    )


def log_canvas_db_operation(
    operation_type: str,
    entity_type: str,
    count: Optional[int] = None,
    course_id: Optional[int] = None,
    **kwargs,
):
    """
    Log Canvas database operations.

    Args:
        operation_type: Type of operation (create, update, delete, fetch)
        entity_type: Type of entity (Course, Assignment, Category, etc.)
        count: Number of entities affected
        course_id: Course ID (if applicable)
        **kwargs: Additional context
    """
    logger = logging.getLogger("canvas_sync.db")

    db_data = {
        "operation": operation_type,
        "entity_type": entity_type,
        "count": count,
        "course_id": course_id,
        "timestamp": datetime.utcnow().isoformat(),
        **kwargs,
    }

    logger.debug(
        f"Database {operation_type}: {entity_type} (count: {count})",
        extra=db_data,
    )


def log_canvas_progress(
    task_id: str,
    user_id: Optional[int] = None,
    progress_percent: Optional[int] = None,
    current_item: Optional[str] = None,
    total_items: Optional[int] = None,
    **kwargs,
):
    """
    Log Canvas sync progress updates.

    Args:
        task_id: Unique task ID for this sync
        user_id: User ID
        progress_percent: Progress as percentage (0-100)
        current_item: Current item being processed
        total_items: Total items to process
        **kwargs: Additional context
    """
    logger = logging.getLogger("canvas_sync.progress")

    progress_data = {
        "task_id": task_id,
        "user_id": user_id,
        "progress_percent": progress_percent,
        "current_item": current_item,
        "total_items": total_items,
        "timestamp": datetime.utcnow().isoformat(),
        **kwargs,
    }

    logger.info(
        f"Sync progress: {progress_percent}% - {current_item}",
        extra=progress_data,
    )


def log_canvas_error(
    error_msg: str,
    user_id: Optional[int] = None,
    course_id: Optional[int] = None,
    operation: Optional[str] = None,
    **kwargs,
):
    """
    Log Canvas sync errors.

    Args:
        error_msg: Error message
        user_id: User ID
        course_id: Course ID (if applicable)
        operation: Operation that failed
        **kwargs: Additional context
    """
    logger = logging.getLogger("canvas_sync.errors")

    error_data = {
        "error_message": error_msg,
        "user_id": user_id,
        "course_id": course_id,
        "operation": operation,
        "timestamp": datetime.utcnow().isoformat(),
        **kwargs,
    }

    logger.error(
        f"Canvas sync error in {operation}: {error_msg}",
        extra=error_data,
    )
