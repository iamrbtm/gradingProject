"""
Canvas Sync Metrics Tracking Module

Provides utilities to track and log Canvas sync performance metrics.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from app.models import db, CanvasSyncMetrics
import logging

logger = logging.getLogger(__name__)


class CanvasSyncMetricsTracker:
    """Track Canvas sync operation metrics."""

    def __init__(self, task_id: str, user_id: int, sync_type: str = "all"):
        """
        Initialize metrics tracker.

        Args:
            task_id: Celery task ID
            user_id: User ID performing sync
            sync_type: Type of sync (all, courses, assignments, etc.)
        """
        self.task_id = task_id
        self.user_id = user_id
        self.sync_type = sync_type
        self.metrics = CanvasSyncMetrics(
            sync_task_id=task_id,
            user_id=user_id,
            sync_type=sync_type,
        )
        self.start_time = datetime.utcnow()

    def record_course(self, created: bool = False, updated: bool = False) -> None:
        """Record a course processed."""
        self.metrics.courses_processed += 1
        if created:
            self.metrics.courses_created += 1
        elif updated:
            self.metrics.courses_updated += 1

    def record_assignment(self, created: bool = False, updated: bool = False) -> None:
        """Record an assignment processed."""
        self.metrics.assignments_processed += 1
        if created:
            self.metrics.assignments_created += 1
        elif updated:
            self.metrics.assignments_updated += 1

    def record_submission(self, created: bool = False, updated: bool = False) -> None:
        """Record a submission processed."""
        self.metrics.submissions_processed += 1
        if created:
            self.metrics.submissions_created += 1
        elif updated:
            self.metrics.submissions_updated += 1

    def record_grade(self, updated: bool = False) -> None:
        """Record a grade processed."""
        self.metrics.grades_processed += 1
        if updated:
            self.metrics.grades_updated += 1

    def record_api_call(self, duration_ms: float, failed: bool = False) -> None:
        """Record an API call."""
        self.metrics.api_calls_made += 1
        self.metrics.total_api_duration_ms += duration_ms
        if failed:
            self.metrics.api_calls_failed += 1

    def record_api_rate_limit(self) -> None:
        """Record an API rate limit hit."""
        self.metrics.api_rate_limit_hits += 1

    def record_db_operation(self, duration_ms: float) -> None:
        """Record a database operation."""
        self.metrics.db_operations += 1
        self.metrics.db_duration_ms += duration_ms

    def set_target_course(self, course_id: int) -> None:
        """Set the target course for sync."""
        self.metrics.target_course_id = course_id

    def set_incremental(self, incremental: bool) -> None:
        """Set whether sync is incremental."""
        self.metrics.incremental_sync = incremental

    def set_chunk_size(self, chunk_size: int) -> None:
        """Set the chunk size used."""
        self.metrics.chunk_size = chunk_size

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the sync."""
        if self.metrics.sync_metadata is None:
            self.metrics.sync_metadata = {}
        self.metrics.sync_metadata[key] = value

    def complete_success(self) -> CanvasSyncMetrics:
        """Mark sync as completed successfully."""
        self.metrics.sync_status = "completed"
        self.metrics.sync_end_time = datetime.utcnow()
        self.metrics.total_duration_seconds = (
            self.metrics.sync_end_time - self.start_time
        ).total_seconds()
        self.save()
        return self.metrics

    def complete_failure(self, error_message: str) -> CanvasSyncMetrics:
        """Mark sync as failed."""
        self.metrics.sync_status = "failed"
        self.metrics.error_message = error_message
        self.metrics.sync_end_time = datetime.utcnow()
        self.metrics.total_duration_seconds = (
            self.metrics.sync_end_time - self.start_time
        ).total_seconds()
        self.save()
        return self.metrics

    def save(self) -> CanvasSyncMetrics:
        """Save metrics to database."""
        try:
            db.session.merge(self.metrics)
            db.session.commit()
            logger.info(f"Saved Canvas sync metrics for task {self.task_id[:8]}...")
            return self.metrics
        except Exception as e:
            logger.error(f"Failed to save Canvas sync metrics: {str(e)}")
            db.session.rollback()
            raise

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return self.metrics.to_dict()


def get_sync_metrics_summary(user_id: int, days: int = 7) -> Dict[str, Any]:
    """
    Get summary of Canvas sync metrics for a user over specified days.

    Args:
        user_id: User ID
        days: Number of days to look back

    Returns:
        Dictionary with summary statistics
    """
    from datetime import timedelta

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    metrics = CanvasSyncMetrics.query.filter(
        CanvasSyncMetrics.user_id == user_id,
        CanvasSyncMetrics.sync_start_time >= cutoff_date,
    ).all()

    if not metrics:
        return {
            "user_id": user_id,
            "period_days": days,
            "total_syncs": 0,
            "successful_syncs": 0,
            "failed_syncs": 0,
        }

    successful = [m for m in metrics if m.sync_status == "completed"]
    failed = [m for m in metrics if m.sync_status == "failed"]

    total_duration = sum(m.total_duration_seconds or 0 for m in metrics)
    avg_duration = total_duration / len(metrics) if metrics else 0

    summary = {
        "user_id": user_id,
        "period_days": days,
        "total_syncs": len(metrics),
        "successful_syncs": len(successful),
        "failed_syncs": len(failed),
        "success_rate": len(successful) / len(metrics) * 100 if metrics else 0,
        "total_duration_seconds": total_duration,
        "average_duration_seconds": avg_duration,
        "total_courses_processed": sum(m.courses_processed or 0 for m in metrics),
        "total_assignments_processed": sum(
            m.assignments_processed or 0 for m in metrics
        ),
        "total_api_calls": sum(m.api_calls_made or 0 for m in metrics),
        "total_api_failures": sum(m.api_calls_failed or 0 for m in metrics),
        "recent_error": failed[0].error_message if failed else None,
    }

    return summary


def get_all_sync_metrics_summary(days: int = 7) -> Dict[str, Any]:
    """
    Get summary of all Canvas sync metrics over specified days.

    Args:
        days: Number of days to look back

    Returns:
        Dictionary with summary statistics across all users
    """
    from datetime import timedelta

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    metrics = CanvasSyncMetrics.query.filter(
        CanvasSyncMetrics.sync_start_time >= cutoff_date,
    ).all()

    if not metrics:
        return {
            "period_days": days,
            "total_syncs": 0,
        }

    successful = [m for m in metrics if m.sync_status == "completed"]
    failed = [m for m in metrics if m.sync_status == "failed"]

    total_duration = sum(m.total_duration_seconds or 0 for m in metrics)
    avg_duration = total_duration / len(metrics) if metrics else 0

    summary = {
        "period_days": days,
        "total_syncs": len(metrics),
        "successful_syncs": len(successful),
        "failed_syncs": len(failed),
        "success_rate": len(successful) / len(metrics) * 100 if metrics else 0,
        "total_duration_seconds": total_duration,
        "average_duration_seconds": avg_duration,
        "total_courses_processed": sum(m.courses_processed or 0 for m in metrics),
        "total_assignments_processed": sum(
            m.assignments_processed or 0 for m in metrics
        ),
        "total_api_calls": sum(m.api_calls_made or 0 for m in metrics),
        "total_api_failures": sum(m.api_calls_failed or 0 for m in metrics),
        "average_api_call_duration_ms": (
            sum(m.total_api_duration_ms or 0 for m in metrics)
            / sum(m.api_calls_made or 1 for m in metrics)
        )
        if metrics
        else 0,
        "unique_users": len(set(m.user_id for m in metrics if m.user_id)),
    }

    return summary
