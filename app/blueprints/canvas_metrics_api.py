"""
Canvas Sync Metrics API Blueprint

Provides REST API endpoints for accessing Canvas sync metrics and logs.
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from app.models import db, CanvasSyncMetrics
from app.services.canvas_sync_metrics import (
    get_sync_metrics_summary,
    get_all_sync_metrics_summary,
)
from app.tasks.log_cleanup import get_cleanup_status
import logging

logger = logging.getLogger(__name__)

canvas_metrics_bp = Blueprint(
    "canvas_metrics", __name__, url_prefix="/api/canvas/metrics"
)


@canvas_metrics_bp.route("/sync/<int:sync_id>", methods=["GET"])
def get_sync_metrics(sync_id: int):
    """
    Get metrics for a specific sync operation.

    Args:
        sync_id: Sync record ID

    Returns:
        JSON with sync metrics or 404 if not found
    """
    sync = CanvasSyncMetrics.query.get(sync_id)

    if not sync:
        return jsonify({"error": "Sync metrics not found"}), 404

    return jsonify(sync.to_dict())


@canvas_metrics_bp.route("/sync/task/<task_id>", methods=["GET"])
def get_sync_by_task(task_id: str):
    """
    Get metrics for a specific sync by Celery task ID.

    Args:
        task_id: Celery task ID

    Returns:
        JSON with sync metrics or 404 if not found
    """
    sync = CanvasSyncMetrics.query.filter_by(sync_task_id=task_id).first()

    if not sync:
        return jsonify({"error": "Sync metrics not found"}), 404

    return jsonify(sync.to_dict())


@canvas_metrics_bp.route("/user/<int:user_id>/summary", methods=["GET"])
def get_user_summary(user_id: int):
    """
    Get summary metrics for a specific user.

    Args:
        user_id: User ID

    Query Parameters:
        days: Number of days to look back (default: 7)

    Returns:
        JSON with user sync summary
    """
    days = request.args.get("days", 7, type=int)
    summary = get_sync_metrics_summary(user_id, days=days)
    return jsonify(summary)


@canvas_metrics_bp.route("/user/<int:user_id>/syncs", methods=["GET"])
def get_user_syncs(user_id: int):
    """
    Get all syncs for a specific user.

    Args:
        user_id: User ID

    Query Parameters:
        limit: Maximum number of results (default: 50)
        status: Filter by status (completed, failed, in_progress, partial)

    Returns:
        JSON list of sync metrics
    """
    limit = request.args.get("limit", 50, type=int)
    status = request.args.get("status", type=str)

    query = CanvasSyncMetrics.query.filter_by(user_id=user_id).order_by(
        CanvasSyncMetrics.sync_start_time.desc()
    )

    if status:
        query = query.filter_by(sync_status=status)

    syncs = query.limit(limit).all()

    return jsonify(
        {
            "user_id": user_id,
            "count": len(syncs),
            "syncs": [s.to_dict() for s in syncs],
        }
    )


@canvas_metrics_bp.route("/summary", methods=["GET"])
def get_global_summary():
    """
    Get global Canvas sync summary across all users.

    Query Parameters:
        days: Number of days to look back (default: 7)

    Returns:
        JSON with global sync summary
    """
    days = request.args.get("days", 7, type=int)
    summary = get_all_sync_metrics_summary(days=days)
    return jsonify(summary)


@canvas_metrics_bp.route("/recent", methods=["GET"])
def get_recent_syncs():
    """
    Get the most recent Canvas sync operations.

    Query Parameters:
        limit: Maximum number of results (default: 20)

    Returns:
        JSON list of recent sync metrics
    """
    limit = request.args.get("limit", 20, type=int)

    syncs = (
        CanvasSyncMetrics.query.order_by(CanvasSyncMetrics.sync_start_time.desc())
        .limit(limit)
        .all()
    )

    return jsonify(
        {
            "count": len(syncs),
            "syncs": [s.to_dict() for s in syncs],
        }
    )


@canvas_metrics_bp.route("/failed", methods=["GET"])
def get_failed_syncs():
    """
    Get failed Canvas sync operations.

    Query Parameters:
        limit: Maximum number of results (default: 20)
        days: Only include failures from last N days (default: 7)

    Returns:
        JSON list of failed sync metrics
    """
    limit = request.args.get("limit", 20, type=int)
    days = request.args.get("days", 7, type=int)

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    syncs = (
        CanvasSyncMetrics.query.filter(
            CanvasSyncMetrics.sync_status == "failed",
            CanvasSyncMetrics.sync_start_time >= cutoff_date,
        )
        .order_by(CanvasSyncMetrics.sync_start_time.desc())
        .limit(limit)
        .all()
    )

    return jsonify(
        {
            "count": len(syncs),
            "period_days": days,
            "syncs": [s.to_dict() for s in syncs],
        }
    )


@canvas_metrics_bp.route("/performance", methods=["GET"])
def get_performance_stats():
    """
    Get performance statistics for Canvas syncs.

    Query Parameters:
        days: Number of days to look back (default: 30)

    Returns:
        JSON with performance statistics
    """
    days = request.args.get("days", 30, type=int)

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    syncs = CanvasSyncMetrics.query.filter(
        CanvasSyncMetrics.sync_start_time >= cutoff_date,
        CanvasSyncMetrics.sync_status == "completed",
    ).all()

    if not syncs:
        return jsonify(
            {
                "period_days": days,
                "sync_count": 0,
                "message": "No completed syncs found",
            }
        )

    durations = [s.total_duration_seconds for s in syncs if s.total_duration_seconds]
    api_calls = [s.api_calls_made for s in syncs if s.api_calls_made]
    db_ops = [s.db_operations for s in syncs if s.db_operations]

    stats = {
        "period_days": days,
        "sync_count": len(syncs),
        "duration": {
            "min_seconds": min(durations) if durations else 0,
            "max_seconds": max(durations) if durations else 0,
            "avg_seconds": sum(durations) / len(durations) if durations else 0,
            "total_seconds": sum(durations) if durations else 0,
        },
        "api_calls": {
            "total": sum(api_calls) if api_calls else 0,
            "avg_per_sync": sum(api_calls) / len(api_calls) if api_calls else 0,
        },
        "database": {
            "total_operations": sum(db_ops) if db_ops else 0,
            "avg_per_sync": sum(db_ops) / len(db_ops) if db_ops else 0,
        },
        "items_processed": {
            "total_courses": sum(s.courses_processed or 0 for s in syncs),
            "total_assignments": sum(s.assignments_processed or 0 for s in syncs),
            "total_submissions": sum(s.submissions_processed or 0 for s in syncs),
        },
    }

    return jsonify(stats)


@canvas_metrics_bp.route("/logs/cleanup-status", methods=["GET"])
def get_logs_cleanup_status():
    """
    Get information about log files and archives.

    Returns:
        JSON with log and archive statistics
    """
    status = get_cleanup_status()
    return jsonify(status)


@canvas_metrics_bp.route("/logs/cleanup", methods=["POST"])
def trigger_cleanup():
    """
    Manually trigger log cleanup task.

    Query Parameters:
        max_lines: Maximum lines to keep per log file (default: 10000)
        archive_days: Age at which to archive files (default: 7)
        delete_days: Age at which to delete archives (default: 30)

    Returns:
        JSON with cleanup task status
    """
    try:
        from app.tasks.log_cleanup import cleanup_canvas_sync_logs

        max_lines = request.args.get("max_lines", 10000, type=int)
        archive_days = request.args.get("archive_days", 7, type=int)
        delete_days = request.args.get("delete_days", 30, type=int)

        task = cleanup_canvas_sync_logs.delay(
            max_log_lines=max_lines,
            archive_age_days=archive_days,
            delete_age_days=delete_days,
        )

        return jsonify(
            {
                "status": "started",
                "task_id": task.id,
                "message": "Log cleanup task triggered",
            }
        )

    except Exception as e:
        logger.error(f"Failed to trigger cleanup: {str(e)}")
        return jsonify(
            {
                "error": str(e),
                "message": "Failed to trigger cleanup task",
            }
        ), 500


@canvas_metrics_bp.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint for Canvas sync metrics system.

    Returns:
        JSON with system health status
    """
    try:
        # Check database connection
        from sqlalchemy import text

        db.session.execute(text("SELECT 1"))
        db_healthy = True
    except Exception as e:
        db_healthy = False
        logger.error(f"Database health check failed: {str(e)}")

    # Check logs directory
    from pathlib import Path

    logs_dir = Path("./logs/canvas_sync")
    logs_healthy = logs_dir.exists()

    health = {
        "timestamp": datetime.utcnow().isoformat(),
        "status": "healthy" if db_healthy and logs_healthy else "degraded",
        "database": "healthy" if db_healthy else "unhealthy",
        "logs_directory": "present" if logs_healthy else "missing",
    }

    return jsonify(health)


def register_canvas_metrics_api(app):
    """
    Register the Canvas metrics API blueprint with the Flask app.

    Args:
        app: Flask application instance
    """
    app.register_blueprint(canvas_metrics_bp)
    logger.info("Canvas metrics API endpoints registered")
