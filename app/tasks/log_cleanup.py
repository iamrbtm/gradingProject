"""
Canvas Sync Log Cleanup Task

This module provides automated log cleanup and archival functions for Canvas sync logs.
Old logs are compressed and archived to preserve disk space.
"""

import os
import logging
import tarfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

try:
    from celery import shared_task
except ImportError:

    def shared_task(func=None, **kwargs):
        """Fallback if Celery not available."""
        if func is None:
            return lambda f: f
        return func


try:
    from app.logging_config import log_canvas_sync_event
except ImportError:

    def log_canvas_sync_event(*args, **kwargs):
        """Fallback if logging config not available."""
        pass


logger = logging.getLogger(__name__)


def get_log_directory() -> Path:
    """Get the canvas sync log directory."""
    return Path("./logs/canvas_sync")


def archive_log_file(log_file: Path, archive_dir: Path) -> bool:
    """
    Archive a single log file with timestamp.

    Args:
        log_file: Path to the log file to archive
        archive_dir: Directory to store archives

    Returns:
        True if successful, False otherwise
    """
    try:
        if not log_file.exists():
            return False

        archive_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"{log_file.stem}_{timestamp}.tar.gz"
        archive_path = archive_dir / archive_name

        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(log_file, arcname=log_file.name)

        logger.info(f"Archived {log_file.name} to {archive_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to archive {log_file}: {str(e)}")
        return False


def cleanup_log_file(log_file: Path, max_lines: int = 10000) -> int:
    """
    Clean up a log file by keeping only recent lines.

    Args:
        log_file: Path to the log file
        max_lines: Maximum lines to keep

    Returns:
        Number of lines removed
    """
    try:
        if not log_file.exists():
            return 0

        with open(log_file, "r") as f:
            lines = f.readlines()

        original_count = len(lines)

        if original_count <= max_lines:
            return 0

        # Keep only the most recent lines
        lines_to_keep = lines[-max_lines:]

        with open(log_file, "w") as f:
            f.writelines(lines_to_keep)

        removed = original_count - len(lines_to_keep)
        logger.info(f"Cleaned up {log_file.name}: removed {removed} lines")
        return removed

    except Exception as e:
        logger.error(f"Failed to cleanup {log_file}: {str(e)}")
        return 0


def get_old_files(directory: Path, days_old: int = 7) -> list[Path]:
    """
    Find files older than specified days.

    Args:
        directory: Directory to search
        days_old: Age threshold in days

    Returns:
        List of old file paths
    """
    cutoff_time = datetime.now() - timedelta(days=days_old)
    old_files = []

    if not directory.exists():
        return old_files

    for file in directory.glob("*.tar.gz"):
        modification_time = datetime.fromtimestamp(file.stat().st_mtime)
        if modification_time < cutoff_time:
            old_files.append(file)

    return old_files


def delete_old_archives(archive_dir: Path, days_old: int = 30) -> int:
    """
    Delete archived logs older than specified days.

    Args:
        archive_dir: Directory containing archives
        days_old: Age threshold in days

    Returns:
        Number of files deleted
    """
    old_files = get_old_files(archive_dir, days_old)
    deleted_count = 0

    for file in old_files:
        try:
            file.unlink()
            logger.info(f"Deleted old archive: {file.name}")
            deleted_count += 1
        except Exception as e:
            logger.error(f"Failed to delete {file}: {str(e)}")

    return deleted_count


@shared_task(bind=True, max_retries=3)
def cleanup_canvas_sync_logs(
    self,
    max_log_lines: int = 10000,
    archive_age_days: int = 7,
    delete_age_days: int = 30,
) -> dict:
    """
    Celery task to cleanup Canvas sync logs.

    This task:
    1. Archives old log files to compressed archives
    2. Cleans up log files to keep only recent entries
    3. Deletes very old archives

    Args:
        max_log_lines: Maximum lines to keep in each log file
        archive_age_days: Age at which to archive files
        delete_age_days: Age at which to delete archives

    Returns:
        Dictionary with cleanup statistics
    """
    try:
        log_dir = get_log_directory()
        archive_dir = log_dir / "archives"

        stats = {
            "task_id": self.request.id,
            "timestamp": datetime.now().isoformat(),
            "archived_files": 0,
            "cleaned_up_files": 0,
            "total_lines_removed": 0,
            "deleted_archives": 0,
            "errors": [],
        }

        log_canvas_sync_event(
            event_type="cleanup_started",
            detail_level="INFO",
            task_id=self.request.id,
            max_log_lines=max_log_lines,
        )

        if not log_dir.exists():
            logger.warning(f"Log directory does not exist: {log_dir}")
            return stats

        # Process each log file
        log_files = list(log_dir.glob("*.log"))

        for log_file in log_files:
            # Archive the file
            if archive_log_file(log_file, archive_dir):
                stats["archived_files"] += 1

            # Clean up the file
            removed = cleanup_log_file(log_file, max_log_lines)
            if removed > 0:
                stats["cleaned_up_files"] += 1
                stats["total_lines_removed"] += removed

        # Delete very old archives
        deleted = delete_old_archives(archive_dir, delete_age_days)
        stats["deleted_archives"] = deleted

        log_canvas_sync_event(
            event_type="cleanup_completed",
            detail_level="INFO",
            task_id=self.request.id,
            **stats,
        )

        logger.info(f"Canvas sync log cleanup completed: {stats}")
        return stats

    except Exception as exc:
        logger.error(f"Canvas sync log cleanup failed: {str(exc)}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=min(2**self.request.retries, 600))


def get_cleanup_status() -> dict:
    """
    Get information about log files and archives.

    Returns:
        Dictionary with log and archive statistics
    """
    log_dir = get_log_directory()
    archive_dir = log_dir / "archives"

    status = {
        "timestamp": datetime.now().isoformat(),
        "log_files": [],
        "archives": [],
        "total_log_size_mb": 0,
        "total_archive_size_mb": 0,
    }

    # Get log file info
    if log_dir.exists():
        for log_file in log_dir.glob("*.log"):
            size_mb = log_file.stat().st_size / (1024 * 1024)
            status["log_files"].append(
                {
                    "name": log_file.name,
                    "size_mb": round(size_mb, 2),
                    "modified": datetime.fromtimestamp(
                        log_file.stat().st_mtime
                    ).isoformat(),
                }
            )
            status["total_log_size_mb"] += size_mb

    # Get archive info
    if archive_dir.exists():
        for archive in archive_dir.glob("*.tar.gz"):
            size_mb = archive.stat().st_size / (1024 * 1024)
            status["archives"].append(
                {
                    "name": archive.name,
                    "size_mb": round(size_mb, 2),
                    "created": datetime.fromtimestamp(
                        archive.stat().st_mtime
                    ).isoformat(),
                }
            )
            status["total_archive_size_mb"] += size_mb

    status["total_log_size_mb"] = round(status["total_log_size_mb"], 2)
    status["total_archive_size_mb"] = round(status["total_archive_size_mb"], 2)

    return status


def register_cleanup_schedule(celery_app) -> None:
    """
    Register the cleanup task to run on a schedule.

    Args:
        celery_app: The Celery application instance
    """
    try:
        from celery.schedules import crontab
    except ImportError:
        logger.warning("Celery not available, skipping schedule registration")
        return

    # Run cleanup daily at 2 AM
    celery_app.conf.beat_schedule["cleanup-canvas-sync-logs"] = {
        "task": "app.tasks.log_cleanup.cleanup_canvas_sync_logs",
        "schedule": crontab(hour=2, minute=0),
        "kwargs": {
            "max_log_lines": 10000,
            "archive_age_days": 7,
            "delete_age_days": 30,
        },
    }

    logger.info("Canvas sync log cleanup scheduled for 2:00 AM daily")
