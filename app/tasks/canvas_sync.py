"""
Canvas Sync Celery Tasks
========================

High-performance, scalable Canvas sync tasks using Celery for background processing.
Provides real-time progress updates, streaming data processing, and robust error handling.

Features:
- Async background processing with Celery
- Real-time progress via Server-Sent Events
- Streaming/chunked data processing for large datasets
- Intelligent retry and error recovery
- Memory-efficient processing
- Rate limiting and API optimization

Author: Canvas Integration Team
Date: 2024-12-20
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)

# Import canvas sync logging utilities
try:
    from app.logging_config import (
        log_canvas_sync_event,
        log_canvas_api_call,
        log_canvas_db_operation,
        log_canvas_progress,
        log_canvas_error,
    )
except ImportError:
    # Fallback if logging config not available
    def log_canvas_sync_event(*args, **kwargs):
        pass

    def log_canvas_api_call(*args, **kwargs):
        pass

    def log_canvas_db_operation(*args, **kwargs):
        pass

    def log_canvas_progress(*args, **kwargs):
        pass

    def log_canvas_error(*args, **kwargs):
        pass


class CanvasTaskError(Exception):
    """Custom exception for Canvas task errors"""

    pass


def get_redis_client():
    """Get Redis client for progress tracking"""
    try:
        import redis
        from app.redis_config import RedisConfig
        import os

        logger.debug("Initializing Redis client for progress tracking")
        environment = os.environ.get("FLASK_ENV", "production")
        redis_config = RedisConfig(environment)
        redis_client = redis.Redis(**redis_config.config)
        logger.debug("Redis client initialized successfully")
        return redis_client
    except ImportError:
        logger.warning("Redis not available, using in-memory progress tracking")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Redis client: {e}")
        log_canvas_error(f"Redis initialization failed: {e}", operation="redis_init")
        return None


def publish_progress(
    task_id: str,
    user_id: int,
    progress_data: Dict[str, Any],
    cache_key: Optional[str] = None,
) -> None:
    """
    Publish progress update for real-time notifications

    Args:
        task_id: Celery task ID
        user_id: User ID for the sync
        progress_data: Progress information
        cache_key: Optional Redis cache key for SSE
    """
    try:
        redis_client = get_redis_client()
        if not redis_client:
            logger.debug("Redis not available, skipping progress publishing")
            return

        # Store in Redis for Server-Sent Events
        if cache_key is None:
            cache_key = f"canvas_sync_progress:{user_id}"

        progress_data.update(
            {
                "task_id": task_id,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Store in Redis with 1 hour expiration
        redis_client.setex(
            cache_key,
            3600,  # 1 hour
            json.dumps(progress_data),
        )

        # Publish to SSE channel for real-time updates
        sse_channel = f"canvas_sync:{user_id}"
        redis_client.publish(sse_channel, json.dumps(progress_data))

        logger.debug(
            f"Published progress for user {user_id}: {progress_data.get('progress_percent', 0)}%"
        )
        log_canvas_progress(
            task_id=task_id,
            user_id=user_id,
            progress_percent=progress_data.get("progress_percent", 0),
            current_item=progress_data.get("current_item", ""),
            total_items=progress_data.get("total_items", 0),
        )

    except Exception as e:
        logger.warning(f"Failed to publish progress: {e}")
        log_canvas_error(
            f"Progress publishing failed: {e}",
            user_id=user_id,
            operation="publish_progress",
        )


def get_sync_checkpoint(user_id: int, sync_type: str) -> Dict[str, Any]:
    """
    Get checkpoint data for resuming failed syncs

    Args:
        user_id: User ID
        sync_type: Type of sync (all, term, course)

    Returns:
        Dict with checkpoint data
    """
    try:
        redis_client = get_redis_client()
        if not redis_client:
            logger.debug("Redis not available for checkpoint retrieval")
            return {}

        checkpoint_key = f"canvas_sync_checkpoint:{user_id}:{sync_type}"
        checkpoint_data = redis_client.get(checkpoint_key)

        if checkpoint_data:
            checkpoint = json.loads(checkpoint_data)
            logger.info(
                f"Retrieved checkpoint for user {user_id} sync_type {sync_type}: {checkpoint}"
            )
            log_canvas_sync_event(
                "checkpoint_retrieved",
                user_id=user_id,
                sync_type=sync_type,
                checkpoint=checkpoint,
            )
            return checkpoint
        logger.debug(f"No checkpoint found for user {user_id} sync_type {sync_type}")
        return {}

    except Exception as e:
        logger.warning(f"Failed to get checkpoint: {e}")
        log_canvas_error(
            f"Checkpoint retrieval failed: {e}",
            user_id=user_id,
            operation="get_checkpoint",
        )
        return {}


def save_sync_checkpoint(
    user_id: int, sync_type: str, checkpoint_data: Dict[str, Any]
) -> None:
    """
    Save checkpoint data for resuming failed syncs

    Args:
        user_id: User ID
        sync_type: Type of sync
        checkpoint_data: Checkpoint information
    """
    try:
        redis_client = get_redis_client()
        if not redis_client:
            logger.debug("Redis not available for checkpoint saving")
            return

        checkpoint_key = f"canvas_sync_checkpoint:{user_id}:{sync_type}"

        # Store checkpoint with 24 hour expiration
        redis_client.setex(
            checkpoint_key,
            86400,  # 24 hours
            json.dumps(checkpoint_data),
        )

        logger.debug(
            f"Saved checkpoint for user {user_id} sync_type {sync_type}: {checkpoint_data}"
        )
        log_canvas_sync_event(
            "checkpoint_saved",
            user_id=user_id,
            sync_type=sync_type,
            checkpoint=checkpoint_data,
        )

    except Exception as e:
        logger.warning(f"Failed to save checkpoint: {e}")
        log_canvas_error(
            f"Checkpoint saving failed: {e}",
            user_id=user_id,
            operation="save_checkpoint",
        )


def clear_sync_checkpoint(user_id: int, sync_type: str) -> None:
    """Clear checkpoint after successful sync"""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            logger.debug("Redis not available for checkpoint clearing")
            return

        checkpoint_key = f"canvas_sync_checkpoint:{user_id}:{sync_type}"
        redis_client.delete(checkpoint_key)

        logger.debug(f"Cleared checkpoint for user {user_id} sync_type {sync_type}")
        log_canvas_sync_event(
            "checkpoint_cleared", user_id=user_id, sync_type=sync_type
        )

    except Exception as e:
        logger.warning(f"Failed to clear checkpoint: {e}")
        log_canvas_error(
            f"Checkpoint clearing failed: {e}",
            user_id=user_id,
            operation="clear_checkpoint",
        )


# Store active sync tasks in memory for simple progress tracking
_active_syncs = {}


def sync_canvas_data_task(
    user_id: int,
    sync_type: str = "all",
    target_id: Optional[int] = None,
    chunk_size: int = 10,
    use_incremental: bool = True,
) -> Dict[str, Any]:
    """
    Enhanced Canvas data synchronization with streaming processing

    This is the main sync function that can be called directly or wrapped by Celery

    Args:
        user_id: User ID to sync for
        sync_type: Type of sync ("all", "term", "course")
        target_id: Target ID for term/course sync
        chunk_size: Number of courses to process per chunk
        use_incremental: Whether to use incremental sync

    Returns:
        Dict with sync results
    """
    # Generate task ID for tracking
    task_id = f"canvas_sync_{user_id}_{int(time.time())}"
    start_time = time.time()

    # Store in active syncs for tracking
    _active_syncs[user_id] = {
        "task_id": task_id,
        "start_time": start_time,
        "progress": 0,
    }

    logger.info(
        f"Starting Canvas sync {task_id} for user {user_id} (type: {sync_type})"
    )
    log_canvas_sync_event(
        "sync_started",
        user_id=user_id,
        task_id=task_id,
        sync_type=sync_type,
        target_id=target_id,
        chunk_size=chunk_size,
        use_incremental=use_incremental,
    )

    try:
        # Initialize progress
        progress_data = {
            "progress_percent": 0,
            "completed_items": 0,
            "total_items": 0,
            "current_operation": "Initializing Canvas sync...",
            "current_item": "",
            "elapsed_time": 0,
            "errors": [],
            "is_complete": False,
            "sync_type": sync_type,
            "target_id": target_id,
            "estimated_remaining": None,
        }
        publish_progress(task_id, user_id, progress_data)

        # Get user and validate credentials
        from app.models import db, User

        logger.debug(f"Fetching user {user_id} from database")
        user = db.session.get(User, user_id)

        if not user:
            error_msg = f"User {user_id} not found"
            logger.error(error_msg)
            log_canvas_error(error_msg, user_id=user_id, operation="user_lookup")
            raise CanvasTaskError(error_msg)

        if not user.canvas_base_url or not user.canvas_access_token:
            error_msg = "Canvas credentials not configured"
            logger.error(f"User {user_id}: {error_msg}")
            log_canvas_error(error_msg, user_id=user_id, operation="credential_check")
            raise CanvasTaskError(error_msg)

        logger.info(f"User {user_id} credentials validated successfully")

        # Initialize Canvas sync service
        from app.services.canvas_sync_service import create_canvas_sync_service

        def progress_callback(sync_progress_data):
            """Enhanced progress callback with time estimation"""
            nonlocal start_time

            elapsed = time.time() - start_time
            progress = sync_progress_data.get("progress_percent", 0)

            # Update active syncs tracking
            if user_id in _active_syncs:
                _active_syncs[user_id]["progress"] = progress

            # Estimate remaining time
            estimated_remaining = None
            if progress > 5:  # Only estimate after 5% complete
                estimated_total = elapsed / (progress / 100)
                estimated_remaining = max(0, estimated_total - elapsed)

            enhanced_progress = {
                **sync_progress_data,
                "elapsed_time": round(elapsed, 1),
                "estimated_remaining": round(estimated_remaining, 1)
                if estimated_remaining
                else None,
                "sync_type": sync_type,
                "target_id": target_id,
            }

            publish_progress(task_id, user_id, enhanced_progress)
            log_canvas_progress(
                task_id=task_id,
                user_id=user_id,
                progress_percent=progress,
                current_item=sync_progress_data.get("current_item", ""),
                total_items=sync_progress_data.get("total_items", 0),
            )

        logger.info(f"Creating Canvas sync service for user {user_id}")
        sync_service = create_canvas_sync_service(user, progress_callback)

        # Test connection
        logger.info("Testing Canvas API connection...")
        progress_data.update(
            {
                "progress_percent": 5,
                "current_operation": "Testing Canvas connection...",
                "elapsed_time": time.time() - start_time,
            }
        )
        publish_progress(task_id, user_id, progress_data)

        connection_result = sync_service.test_connection()
        if not connection_result.get("success"):
            error_msg = f"Canvas connection failed: {connection_result.get('error', 'Unknown error')}"
            logger.error(error_msg)
            log_canvas_error(error_msg, user_id=user_id, operation="connection_test")
            raise CanvasTaskError(error_msg)

        logger.info("Canvas connection test successful")

        # Check for existing checkpoint
        checkpoint = get_sync_checkpoint(user_id, sync_type)
        if checkpoint:
            logger.info(f"Resuming sync from checkpoint: {checkpoint}")
            log_canvas_sync_event(
                "checkpoint_resumed",
                user_id=user_id,
                task_id=task_id,
                checkpoint_data=checkpoint,
            )
            progress_data.update(
                {
                    "current_operation": "Resuming from previous checkpoint...",
                    "progress_percent": checkpoint.get("progress_percent", 10),
                }
            )
            publish_progress(task_id, user_id, progress_data)

        # Perform sync based on type with streaming
        logger.info(f"Starting {sync_type} sync with streaming processing")
        log_canvas_sync_event(
            "sync_type_started", user_id=user_id, task_id=task_id, sync_type=sync_type
        )

        if sync_type == "term" and target_id:
            logger.info(f"Syncing term {target_id}")
            result = _sync_term_streaming(
                sync_service, target_id, task_id, user_id, chunk_size, checkpoint
            )
        elif sync_type == "course" and target_id:
            logger.info(f"Syncing course {target_id}")
            result = _sync_course_streaming(
                sync_service, target_id, task_id, user_id, checkpoint
            )
        else:
            logger.info("Syncing all courses")
            result = _sync_all_streaming(
                sync_service, task_id, user_id, chunk_size, use_incremental, checkpoint
            )

        # Clear checkpoint on success
        clear_sync_checkpoint(user_id, sync_type)

        # Final success notification
        elapsed_time = time.time() - start_time
        success_data = {
            "progress_percent": 100,
            "completed_items": result.get("courses_processed", 0),
            "total_items": result.get("courses_processed", 0),
            "current_operation": "Canvas sync completed successfully! 🎉",
            "current_item": f"Synced {result.get('assignments_processed', 0)} assignments",
            "elapsed_time": round(elapsed_time, 1),
            "errors": result.get("errors", []),
            "is_complete": True,
            "sync_type": sync_type,
            "target_id": target_id,
            "result_summary": {
                "courses": result.get("courses_processed", 0),
                "assignments": result.get("assignments_processed", 0),
                "categories": result.get("categories_created", 0),
            },
        }
        publish_progress(task_id, user_id, success_data)

        logger.info(
            f"Canvas sync {task_id} completed successfully in {elapsed_time:.1f}s"
        )
        log_canvas_sync_event(
            "sync_completed",
            user_id=user_id,
            task_id=task_id,
            elapsed_seconds=round(elapsed_time, 1),
            result_summary=success_data["result_summary"],
        )
        return result

    except Exception as exc:
        elapsed_time = time.time() - start_time
        error_msg = str(exc)

        logger.error(
            f"Canvas sync {task_id} failed after {elapsed_time:.1f}s: {error_msg}"
        )
        log_canvas_error(
            error_msg,
            user_id=user_id,
            operation="sync_task",
            task_id=task_id,
            elapsed_seconds=round(elapsed_time, 1),
        )

        # Publish error notification
        error_data = {
            "progress_percent": 0,
            "completed_items": 0,
            "total_items": 0,
            "current_operation": "Canvas sync failed ❌",
            "current_item": error_msg,
            "elapsed_time": round(elapsed_time, 1),
            "errors": [error_msg],
            "is_complete": True,
            "sync_type": sync_type,
            "target_id": target_id,
        }
        publish_progress(task_id, user_id, error_data)

        raise CanvasTaskError(f"Canvas sync failed: {error_msg}")

    finally:
        # Clean up active sync tracking
        if user_id in _active_syncs:
            logger.debug(f"Cleaning up active sync tracking for user {user_id}")
            del _active_syncs[user_id]


def _sync_all_streaming(
    sync_service,
    task_id: str,
    user_id: int,
    chunk_size: int,
    use_incremental: bool,
    checkpoint: Dict[str, Any],
) -> Dict[str, Any]:
    """Stream processing for full Canvas sync"""

    logger.info(f"Starting full Canvas sync for user {user_id}")
    log_canvas_sync_event("full_sync_started", user_id=user_id, task_id=task_id)

    # Fetch courses list
    progress_data = {
        "progress_percent": 10,
        "current_operation": "Fetching courses from Canvas...",
        "current_item": "",
    }
    publish_progress(task_id, user_id, progress_data)

    logger.info("Fetching courses list from Canvas")
    since = None
    if use_incremental:
        from app.models import User

        user = User.query.get(user_id)
        if user and user.canvas_last_sync:
            since = user.canvas_last_sync
            logger.info(f"Using incremental sync since {since}")

    canvas_courses = sync_service.canvas_api.get_courses(since=since)
    total_courses = len(canvas_courses)
    logger.info(f"Fetched {total_courses} courses from Canvas")
    log_canvas_api_call(
        "GET", "/courses", user_id=user_id, response_status=200, count=total_courses
    )

    # Resume from checkpoint if available
    processed_courses = checkpoint.get("processed_courses", 0)
    completed_course_ids = set(checkpoint.get("completed_course_ids", []))

    result = {
        "courses_processed": processed_courses,
        "courses_created": checkpoint.get("courses_created", 0),
        "courses_updated": checkpoint.get("courses_updated", 0),
        "assignments_processed": checkpoint.get("assignments_processed", 0),
        "assignments_created": checkpoint.get("assignments_created", 0),
        "assignments_updated": checkpoint.get("assignments_updated", 0),
        "categories_created": checkpoint.get("categories_created", 0),
        "errors": checkpoint.get("errors", []),
    }

    # Process courses in chunks
    logger.info(f"Processing {total_courses} courses in chunks of {chunk_size}")
    for i in range(processed_courses, total_courses, chunk_size):
        chunk = canvas_courses[i : i + chunk_size]
        logger.debug(
            f"Processing chunk starting at index {i}, chunk size: {len(chunk)}"
        )

        for j, canvas_course in enumerate(chunk):
            canvas_course_id = str(canvas_course["id"])

            # Skip if already processed
            if canvas_course_id in completed_course_ids:
                logger.debug(f"Skipping already processed course {canvas_course_id}")
                continue

            try:
                course_name = canvas_course.get("name", "Unnamed Course")
                current_index = i + j + 1

                progress_data = {
                    "progress_percent": int((current_index / total_courses) * 90) + 10,
                    "completed_items": current_index - 1,
                    "total_items": total_courses,
                    "current_operation": f"Syncing course {current_index}/{total_courses}",
                    "current_item": course_name,
                }
                publish_progress(task_id, user_id, progress_data)

                logger.info(
                    f"[{current_index}/{total_courses}] Syncing course: {course_name}"
                )

                # Auto-determine term or use default
                canvas_term = canvas_course.get("term")
                season, year = sync_service._parse_canvas_term(canvas_term)
                logger.debug(f"Parsed canvas term for {course_name}: {season} {year}")
                course_term_id = sync_service._find_or_create_term(season, year)
                logger.debug(f"Term ID for {course_name}: {course_term_id}")

                course_result = sync_service._sync_course(canvas_course, course_term_id)

                # Update results
                result["courses_processed"] += 1
                if course_result["created"]:
                    result["courses_created"] += 1
                    logger.info(f"✓ Course created: {course_name}")
                else:
                    result["courses_updated"] += 1
                    logger.info(f"✓ Course updated: {course_name}")

                result["assignments_processed"] += course_result[
                    "assignments_processed"
                ]
                result["assignments_created"] += course_result["assignments_created"]
                result["assignments_updated"] += course_result["assignments_updated"]
                result["categories_created"] += course_result["categories_created"]

                completed_course_ids.add(canvas_course_id)

                log_canvas_db_operation(
                    "sync",
                    "Course",
                    count=1,
                    course_id=course_result.get("id"),
                    created=course_result["created"],
                )

            except Exception as e:
                error_msg = (
                    f"Failed to sync course {canvas_course.get('name', 'Unknown')}: {e}"
                )
                logger.error(error_msg)
                result["errors"].append(error_msg)
                log_canvas_error(
                    error_msg,
                    user_id=user_id,
                    course_id=canvas_course.get("id"),
                    operation="sync_course",
                )

        # Save checkpoint after each chunk
        checkpoint_data = {
            **result,
            "processed_courses": min(i + chunk_size, total_courses),
            "completed_course_ids": list(completed_course_ids),
            "progress_percent": int(((i + chunk_size) / total_courses) * 90) + 10,
        }
        save_sync_checkpoint(user_id, "all", checkpoint_data)

        # Brief pause to prevent overwhelming Canvas API
        logger.debug("Waiting 0.5s before processing next chunk")
        time.sleep(0.5)

    # Update user's last sync timestamp
    from app.models import db, User

    logger.debug("Updating user last sync timestamp")
    user = User.query.get(user_id)
    if user:
        user.canvas_last_sync = datetime.utcnow()
        db.session.commit()
        logger.info(f"Updated last sync timestamp for user {user_id}")

    logger.info(f"Full sync completed: {result}")
    log_canvas_sync_event(
        "full_sync_completed",
        user_id=user_id,
        task_id=task_id,
        result=result,
    )
    return result


def _sync_term_streaming(
    sync_service,
    term_id: int,
    task_id: str,
    user_id: int,
    chunk_size: int,
    checkpoint: Dict[str, Any],
) -> Dict[str, Any]:
    """Stream processing for term-specific sync"""

    logger.info(f"Starting term sync for user {user_id}, term {term_id}")
    log_canvas_sync_event(
        "term_sync_started", user_id=user_id, task_id=task_id, term_id=term_id
    )

    result = sync_service.sync_term_data(term_id, force_full_sync=True)

    logger.info(f"Term sync completed: {result}")
    log_canvas_sync_event(
        "term_sync_completed",
        user_id=user_id,
        task_id=task_id,
        term_id=term_id,
        result=result,
    )
    return result


def _sync_course_streaming(
    sync_service, course_id: int, task_id: str, user_id: int, checkpoint: Dict[str, Any]
) -> Dict[str, Any]:
    """Stream processing for course-specific sync"""

    logger.info(f"Starting course sync for user {user_id}, course {course_id}")
    log_canvas_sync_event(
        "course_sync_started", user_id=user_id, task_id=task_id, course_id=course_id
    )

    result = sync_service.sync_course_data(course_id)

    logger.info(f"Course sync completed: {result}")
    log_canvas_sync_event(
        "course_sync_completed",
        user_id=user_id,
        task_id=task_id,
        course_id=course_id,
        result=result,
    )
    return result


def get_sync_progress(user_id: int) -> Dict[str, Any]:
    """
    Get current sync progress for a user

    Args:
        user_id: User ID

    Returns:
        Dict with current progress or None if no active sync
    """
    try:
        redis_client = get_redis_client()
        if redis_client:
            cache_key = f"canvas_sync_progress:{user_id}"
            progress_data = redis_client.get(cache_key)

            if progress_data:
                progress = json.loads(progress_data)
                logger.debug(f"Retrieved progress for user {user_id}: {progress}")
                return progress

        # Fallback to in-memory tracking
        if user_id in _active_syncs:
            progress = {
                "progress_percent": _active_syncs[user_id]["progress"],
                "is_complete": False,
                "current_operation": "Syncing in progress...",
            }
            logger.debug(f"Retrieved in-memory progress for user {user_id}: {progress}")
            return progress

        logger.debug(f"No progress found for user {user_id}")
        return None

    except Exception as e:
        logger.error(f"Failed to get sync progress: {e}")
        log_canvas_error(
            f"Progress retrieval failed: {e}",
            user_id=user_id,
            operation="get_progress",
        )
        return None


def cleanup_old_sync_data(days: int = 30) -> Dict[str, Any]:
    """
    Cleanup old sync progress and checkpoint data

    Args:
        days: Number of days to keep data

    Returns:
        Dict with cleanup results
    """
    try:
        redis_client = get_redis_client()
        from app.models import db, SyncProgress
        from datetime import timedelta

        logger.info(f"Starting cleanup of sync data older than {days} days")

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Clean up database records
        deleted_count = SyncProgress.query.filter(
            SyncProgress.created_at < cutoff_date
        ).delete()

        db.session.commit()

        logger.info(f"Cleaned up {deleted_count} old sync progress records")
        log_canvas_sync_event(
            "cleanup_completed",
            deleted_records=deleted_count,
            cutoff_date=cutoff_date.isoformat(),
        )

        # Clean up Redis keys (if available)
        if redis_client:
            logger.debug("Cleaning up Redis sync data")
            # This is a simple cleanup - in production you'd want more sophisticated Redis key management
            pass

        return {
            "success": True,
            "deleted_records": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
        }

    except Exception as e:
        logger.error(f"Sync data cleanup failed: {e}")
        log_canvas_error(f"Cleanup failed: {e}", operation="cleanup_old_sync_data")
        return {"success": False, "error": str(e)}


# Try to create Celery task if Celery is available
try:
    from celery_app import celery

    @celery.task(bind=True, max_retries=3, default_retry_delay=60)
    def sync_canvas_data_celery(
        self,
        user_id: int,
        sync_type: str = "all",
        target_id: Optional[int] = None,
        chunk_size: int = 10,
        use_incremental: bool = True,
    ) -> Dict[str, Any]:
        """
        Celery wrapper for Canvas sync task
        """
        logger.info(
            f"Celery task sync_canvas_data_celery started - user_id: {user_id}, sync_type: {sync_type}"
        )
        log_canvas_sync_event(
            "celery_task_started",
            user_id=user_id,
            sync_type=sync_type,
            target_id=target_id,
        )
        try:
            result = sync_canvas_data_task(
                user_id=user_id,
                sync_type=sync_type,
                target_id=target_id,
                chunk_size=chunk_size,
                use_incremental=use_incremental,
            )
            logger.info(f"Celery task sync_canvas_data_celery completed successfully")
            return result
        except Exception as exc:
            # Retry logic for Celery
            if self.request.retries < self.max_retries:
                retry_delay = 60 * (2**self.request.retries)  # Exponential backoff
                logger.info(
                    f"Retrying sync task in {retry_delay}s (attempt {self.request.retries + 1})"
                )
                log_canvas_error(
                    f"Retry attempt {self.request.retries + 1}/{self.max_retries}",
                    user_id=user_id,
                    operation="celery_retry",
                )
                raise self.retry(countdown=retry_delay, exc=exc)

            # Max retries exceeded
            error_msg = (
                f"Canvas sync failed after {self.max_retries} retries: {str(exc)}"
            )
            logger.error(error_msg)
            log_canvas_error(error_msg, user_id=user_id, operation="celery_max_retries")
            raise CanvasTaskError(error_msg)

    @celery.task
    def cleanup_old_sync_data_celery(days: int = 30) -> Dict[str, Any]:
        """Celery wrapper for cleanup task"""
        logger.info(f"Starting Celery cleanup task for data older than {days} days")
        result = cleanup_old_sync_data(days)
        logger.info(f"Celery cleanup task completed: {result}")
        return result

    logger.info("Celery Canvas sync tasks registered successfully")

except ImportError:
    logger.info("Celery not available, using direct function calls")
    sync_canvas_data_celery = sync_canvas_data_task
    cleanup_old_sync_data_celery = cleanup_old_sync_data
