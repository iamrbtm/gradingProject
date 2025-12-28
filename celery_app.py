#!/usr/bin/env python3
"""
Celery Application Configuration
===============================

This module configures Celery for background task processing including:
- Scheduled ML model training
- Analytics data updates
- Notification delivery
- Report generation

Usage:
    # Start Celery worker
    celery -A celery_app.celery worker --loglevel=info

    # Start Celery beat scheduler
    celery -A celery_app.celery beat --loglevel=info

    # Monitor tasks
    celery -A celery_app.celery flower

Author: Analytics Team
Date: 2024-12-19
"""

import os
from celery import Celery
from celery.schedules import crontab


def make_celery(app):
    """Create Celery instance with Flask app context."""
    celery = Celery(
        app.import_name,
        backend=app.config.get("CELERY_RESULT_BACKEND", "redis://redis:6379/1"),
        broker=app.config.get("CELERY_BROKER_URL", "redis://redis:6379/0"),
    )

    # Configure Celery with Flask config
    celery.conf.update(
        # Basic configuration
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        # Connection settings
        broker_connection_retry_on_startup=True,
        # Task routing
        task_routes={
            "app.tasks.ml.*": {"queue": "ml_tasks"},
            "app.tasks.analytics.*": {"queue": "analytics"},
            "app.tasks.exports.*": {"queue": "exports"},
            "app.tasks.notifications.*": {"queue": "notifications"},
        },
        # Scheduled tasks
        beat_schedule={
            # Traditional ML model training - daily at 2 AM
            "train-ml-models": {
                "task": "app.tasks.ml.train_all_models",
                "schedule": crontab(hour=2, minute=0),
                "options": {"queue": "ml_tasks"},
            },
            # ADVANCED ML TASKS
            # External data collection - every 6 hours
            "collect-external-data": {
                "task": "app.tasks.ml.collect_external_data",
                "schedule": crontab(minute=0, hour="*/6"),
                "options": {"queue": "ml_tasks"},
            },
            # Advanced ML model training - daily at 3 AM
            "train-advanced-ml-models": {
                "task": "app.tasks.ml.train_advanced_ml_models",
                "schedule": crontab(hour=3, minute=0),
                "options": {"queue": "ml_tasks"},
            },
            # Model performance monitoring - every 2 hours
            "monitor-model-performance": {
                "task": "app.tasks.ml.monitor_model_performance",
                "schedule": crontab(minute=0, hour="*/2"),
                "options": {"queue": "ml_tasks"},
            },
            # A/B test management - every 4 hours
            "manage-ab-tests": {
                "task": "app.tasks.ml.manage_ab_tests",
                "schedule": crontab(minute=0, hour="*/4"),
                "options": {"queue": "ml_tasks"},
            },
            # Time series forecasting - daily at 1 AM
            "generate-forecasts": {
                "task": "app.tasks.ml.generate_time_series_forecasts",
                "schedule": crontab(hour=1, minute=0),
                "options": {"queue": "ml_tasks"},
            },
            # Update model explanations - daily at 4 AM
            "update-explanations": {
                "task": "app.tasks.ml.update_model_explanations",
                "schedule": crontab(hour=4, minute=0),
                "options": {"queue": "ml_tasks"},
            },
            # Comprehensive ML maintenance - weekly on Sunday at 5 AM
            "comprehensive-ml-maintenance": {
                "task": "app.tasks.ml.comprehensive_ml_maintenance",
                "schedule": crontab(hour=5, minute=0, day_of_week=0),
                "options": {"queue": "ml_tasks"},
            },
            # EXISTING ANALYTICS TASKS
            # Analytics updates - every 4 hours
            "update-analytics": {
                "task": "app.tasks.analytics.update_all_analytics",
                "schedule": crontab(minute=0, hour="*/4"),
                "options": {"queue": "analytics"},
            },
            # Performance metrics - every hour
            "update-performance-metrics": {
                "task": "app.tasks.analytics.update_performance_metrics",
                "schedule": crontab(minute=0),
                "options": {"queue": "analytics"},
            },
            # Notification delivery - every 15 minutes
            "deliver-notifications": {
                "task": "app.tasks.notifications.deliver_scheduled_notifications",
                "schedule": crontab(minute="*/15"),
                "options": {"queue": "notifications"},
            },
            # Cleanup old data - daily at 6 AM (after ML maintenance)
            "cleanup-old-data": {
                "task": "app.tasks.maintenance.cleanup_old_analytics_data",
                "schedule": crontab(hour=6, minute=0),
                "options": {"queue": "maintenance"},
            },
            # ML model cleanup - weekly on Sunday at 7 AM
            "cleanup-old-ml-models": {
                "task": "app.tasks.ml.cleanup_old_models",
                "schedule": crontab(hour=7, minute=0, day_of_week=0),
                "options": {"queue": "maintenance"},
            },
        },
        # Worker configuration
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        worker_max_tasks_per_child=1000,
        # Error handling
        task_reject_on_worker_lost=True,
        task_ignore_result=False,
        result_expires=3600,  # 1 hour
    )

    # Ensure tasks run in Flask app context
    class ContextTask(celery.Task):
        """Make celery tasks work with Flask app context."""

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


# Create standalone Celery app for command line usage
def create_celery_app():
    """Create Celery app for standalone usage."""
    from app import create_app

    # Load Flask app configuration
    flask_app = create_app(os.environ.get("FLASK_ENV", "production"))

    # Try to use Redis configuration
    try:
        from app.redis_config import get_celery_redis_config

        redis_config = get_celery_redis_config()
        broker_url = redis_config["broker_url"]
        result_backend = redis_config["result_backend"]
    except ImportError:
        # Fallback to environment variables
        broker_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        result_backend = os.environ.get("REDIS_URL", "redis://redis:6379/1")

    # Add Celery-specific configuration
    flask_app.config.update(
        CELERY_BROKER_URL=broker_url,
        CELERY_RESULT_BACKEND=result_backend,
        # Redis connection settings
        CELERY_REDIS_MAX_CONNECTIONS=20,
        CELERY_REDIS_RETRY_ON_TIMEOUT=True,
        # Task timeouts - increased for advanced ML tasks
        CELERY_TASK_SOFT_TIME_LIMIT=1800,  # 30 minutes soft limit for ML tasks
        CELERY_TASK_TIME_LIMIT=3600,  # 1 hour hard limit for complex ML operations
        # Advanced ML task specific timeouts
        CELERY_TASK_TIME_LIMITS={
            "app.tasks.ml.train_advanced_ml_models": 7200,  # 2 hours for model training
            "app.tasks.ml.generate_time_series_forecasts": 3600,  # 1 hour for forecasting
            "app.tasks.ml.comprehensive_ml_maintenance": 10800,  # 3 hours for full maintenance
        },
        # Performance settings
        CELERY_WORKER_CONCURRENCY=4,
        CELERY_WORKER_MAX_MEMORY_PER_CHILD=200000,  # 200MB
    )

    return make_celery(flask_app)


# Create the Celery instance
celery = create_celery_app()


if __name__ == "__main__":
    # Command line interface for Celery management
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "worker":
            # Start worker
            celery.start(["worker", "--loglevel=info"])

        elif command == "beat":
            # Start scheduler
            celery.start(["beat", "--loglevel=info"])

        elif command == "flower":
            # Start monitoring
            celery.start(["flower"])

        elif command == "status":
            # Show status
            celery.control.inspect().stats()

        else:
            print("Usage: python celery_app.py [worker|beat|flower|status]")
    else:
        print("Celery application configured successfully!")
        print("Available commands:")
        print("  python celery_app.py worker  - Start worker")
        print("  python celery_app.py beat    - Start scheduler")
        print("  python celery_app.py flower  - Start monitoring")
        print("  python celery_app.py status  - Show status")
