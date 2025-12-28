"""
Enhanced Canvas Sync Routes with Real-Time Progress
===================================================

Provides improved Canvas sync functionality with:
- Celery background tasks for non-blocking sync
- Server-Sent Events (SSE) for real-time progress
- Alert-based user notifications
- Better error handling and recovery

Author: Canvas Integration Team
Date: 2024-12-20
"""

from flask import Blueprint, request, jsonify, Response, stream_template, current_app
from flask_login import login_required, current_user
from app.models import db, SyncProgress
import json
import time
import logging

# Create blueprint for enhanced Canvas sync routes
enhanced_canvas_bp = Blueprint("canvas_sync_enhanced", __name__)

logger = logging.getLogger(__name__)


@enhanced_canvas_bp.route("/sync/canvas/start_enhanced", methods=["POST"])
@login_required
def start_enhanced_canvas_sync():
    """Start Canvas sync with Celery background task and real-time progress"""
    try:
        data = request.get_json() or {}
        sync_type = data.get("sync_type", "all")  # 'all', 'term', or 'course'
        target_id = data.get("target_id")  # term_id or course_id for specific syncs
        chunk_size = data.get("chunk_size", 10)  # Courses per chunk
        use_incremental = data.get("use_incremental", True)  # Incremental sync

        # Check if Canvas credentials are configured
        if not current_user.canvas_base_url or not current_user.canvas_access_token:
            return jsonify(
                {
                    "success": False,
                    "message": "Canvas credentials not configured. Please update your settings first.",
                    "error_type": "credentials_missing",
                }
            )

        # Check for existing active sync
        from app.tasks.canvas_sync import get_sync_progress

        existing_progress = get_sync_progress(current_user.id)

        if existing_progress and not existing_progress.get("is_complete", True):
            return jsonify(
                {
                    "success": False,
                    "message": "Canvas sync already in progress. Please wait for it to complete.",
                    "error_type": "sync_in_progress",
                    "current_progress": existing_progress,
                }
            )

        # Clean up any old incomplete progress records
        SyncProgress.query.filter_by(
            user_id=current_user.id,
            sync_type=f"canvas_{sync_type}" if sync_type != "all" else "canvas",
            is_complete=False,
        ).delete()
        db.session.commit()

        # Try to use Celery if available, fallback to direct execution
        try:
            from app.tasks.canvas_sync import sync_canvas_data_celery

            # Start Celery task
            task = sync_canvas_data_celery.delay(
                user_id=current_user.id,
                sync_type=sync_type,
                target_id=target_id,
                chunk_size=chunk_size,
                use_incremental=use_incremental,
            )

            return jsonify(
                {
                    "success": True,
                    "message": "Canvas sync started successfully! 🚀",
                    "task_id": task.id,
                    "sync_type": sync_type,
                    "use_background_task": True,
                    "sse_endpoint": f"/sync/canvas/progress_stream?user_id={current_user.id}",
                    "progress_endpoint": f"/sync/canvas/progress_enhanced?user_id={current_user.id}",
                }
            )

        except ImportError:
            # Celery not available, use direct execution in thread
            logger.warning("Celery not available, falling back to thread execution")

            import threading
            from app.tasks.canvas_sync import sync_canvas_data_task

            def background_sync():
                try:
                    sync_canvas_data_task(
                        user_id=current_user.id,
                        sync_type=sync_type,
                        target_id=target_id,
                        chunk_size=chunk_size,
                        use_incremental=use_incremental,
                    )
                except Exception as e:
                    logger.error(f"Background sync failed: {e}")

            sync_thread = threading.Thread(target=background_sync)
            sync_thread.daemon = True
            sync_thread.start()

            return jsonify(
                {
                    "success": True,
                    "message": "Canvas sync started successfully! 🚀",
                    "task_id": f"thread_sync_{current_user.id}_{int(time.time())}",
                    "sync_type": sync_type,
                    "use_background_task": False,
                    "sse_endpoint": f"/sync/canvas/progress_stream?user_id={current_user.id}",
                    "progress_endpoint": f"/sync/canvas/progress_enhanced?user_id={current_user.id}",
                }
            )

    except Exception as e:
        logger.error(f"Error starting enhanced Canvas sync: {e}")
        return jsonify(
            {
                "success": False,
                "message": f"Failed to start Canvas sync: {str(e)}",
                "error_type": "internal_error",
            }
        )


@enhanced_canvas_bp.route("/sync/canvas/progress_enhanced")
@login_required
def get_enhanced_canvas_progress():
    """Get current Canvas sync progress with enhanced info"""
    try:
        user_id = request.args.get("user_id", current_user.id, type=int)

        # Security check
        if user_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403

        from app.tasks.canvas_sync import get_sync_progress

        progress = get_sync_progress(user_id)

        if progress:
            return jsonify({"success": True, "progress": progress})
        else:
            # Check database for latest progress
            sync_progress = (
                SyncProgress.query.filter_by(user_id=user_id)
                .filter(SyncProgress.sync_type.like("canvas%"))
                .order_by(SyncProgress.created_at.desc())
                .first()
            )

            if sync_progress:
                return jsonify({"success": True, "progress": sync_progress.to_dict()})
            else:
                return jsonify(
                    {
                        "success": True,
                        "progress": {
                            "progress_percent": 0,
                            "completed_items": 0,
                            "total_items": 0,
                            "current_operation": "Ready to sync",
                            "current_item": "",
                            "elapsed_time": 0,
                            "errors": [],
                            "is_complete": True,
                        },
                    }
                )

    except Exception as e:
        logger.error(f"Error getting enhanced Canvas sync progress: {e}")
        return jsonify({"success": False, "error": str(e)})


@enhanced_canvas_bp.route("/sync/canvas/progress_stream")
@login_required
def canvas_sync_progress_stream():
    """Server-Sent Events endpoint for real-time Canvas sync progress"""

    # Use current_user.id directly since we're authenticated
    user_id = current_user.id

    def event_stream():
        """Generate Server-Sent Events for real-time progress"""
        try:
            from app.tasks.canvas_sync import get_redis_client

            redis_client = get_redis_client()
            if not redis_client:
                # Fallback to polling without Redis
                logger.warning("Redis not available, using polling fallback for SSE")

                for i in range(600):  # 10 minutes max
                    from app.tasks.canvas_sync import get_sync_progress

                    progress = get_sync_progress(user_id)

                    if progress:
                        yield f"data: {json.dumps(progress)}\\n\\n"

                        if progress.get("is_complete", False):
                            break
                    else:
                        yield f"data: {json.dumps({'status': 'no_sync_active'})}\\n\\n"

                    time.sleep(1)  # Poll every second
                return

            # Redis-based real-time updates with timeout handling
            sse_channel = f"canvas_sync:{user_id}"
            pubsub = redis_client.pubsub()
            pubsub.subscribe(sse_channel)

            # Send initial progress if available
            cache_key = f"canvas_sync_progress:{user_id}"
            initial_progress = redis_client.get(cache_key)
            if initial_progress:
                yield f"data: {initial_progress}\\n\\n"

            # Listen for real-time updates with proper timeout
            start_time = time.time()
            max_duration = 600  # 10 minutes max
            last_heartbeat = time.time()
            heartbeat_interval = 30  # Send heartbeat every 30 seconds

            while True:
                elapsed = time.time() - start_time
                if elapsed > max_duration:
                    yield f"data: {json.dumps({'status': 'timeout', 'message': 'Connection timeout after 10 minutes'})}\\n\\n"
                    break

                # Send heartbeat to keep connection alive
                if time.time() - last_heartbeat > heartbeat_interval:
                    yield f"data: {json.dumps({'status': 'heartbeat', 'timestamp': time.time()})}\\n\\n"
                    last_heartbeat = time.time()

                # Non-blocking Redis message check with error handling
                try:
                    message = pubsub.get_message(timeout=1.0)
                    if message and message["type"] == "message":
                        try:
                            progress_data = json.loads(message["data"])
                            yield f"data: {json.dumps(progress_data)}\\n\\n"

                            # Stop streaming if sync is complete
                            if progress_data.get("is_complete", False):
                                break

                        except (json.JSONDecodeError, KeyError) as e:
                            logger.warning(f"Invalid progress data received: {e}")
                            continue

                except Exception as redis_error:
                    logger.warning(f"Redis connection error in SSE: {redis_error}")
                    # Fall back to polling if Redis fails
                    from app.tasks.canvas_sync import get_sync_progress

                    progress = get_sync_progress(user_id)
                    if progress:
                        yield f"data: {json.dumps(progress)}\\n\\n"
                        if progress.get("is_complete", False):
                            break

                # Small sleep to prevent tight loop
                time.sleep(0.1)

            pubsub.unsubscribe(sse_channel)
            pubsub.close()

        except Exception as e:
            logger.error(f"SSE stream error for user {user_id}: {e}")
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\\n\\n"

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        },
    )


@enhanced_canvas_bp.route("/sync/canvas/cancel", methods=["POST"])
@login_required
def cancel_canvas_sync():
    """Cancel ongoing Canvas sync"""
    try:
        # Try to revoke Celery task if available
        try:
            from celery_app import celery
            from app.tasks.canvas_sync import get_sync_progress

            progress = get_sync_progress(current_user.id)
            if progress and progress.get("task_id"):
                celery.control.revoke(progress["task_id"], terminate=True)

        except ImportError:
            pass  # Celery not available

        # Clear progress and checkpoints
        SyncProgress.query.filter_by(user_id=current_user.id, is_complete=False).update(
            {"is_complete": True, "current_operation": "Sync cancelled by user"}
        )
        db.session.commit()

        # Clear Redis data
        try:
            from app.tasks.canvas_sync import get_redis_client

            redis_client = get_redis_client()
            if redis_client:
                cache_key = f"canvas_sync_progress:{current_user.id}"
                redis_client.delete(cache_key)

                # Clear checkpoints
                checkpoint_pattern = f"canvas_sync_checkpoint:{current_user.id}:*"
                for key in redis_client.scan_iter(match=checkpoint_pattern):
                    redis_client.delete(key)

        except Exception as e:
            logger.warning(f"Failed to clear Redis data: {e}")

        return jsonify(
            {"success": True, "message": "Canvas sync cancelled successfully"}
        )

    except Exception as e:
        logger.error(f"Error cancelling Canvas sync: {e}")
        return jsonify(
            {"success": False, "message": f"Failed to cancel sync: {str(e)}"}
        )


@enhanced_canvas_bp.route("/sync/canvas/retry", methods=["POST"])
@login_required
def retry_canvas_sync():
    """Retry failed Canvas sync from checkpoint"""
    try:
        data = request.get_json() or {}
        sync_type = data.get("sync_type", "all")
        target_id = data.get("target_id")

        # Check for existing checkpoint
        from app.tasks.canvas_sync import get_sync_checkpoint

        checkpoint = get_sync_checkpoint(current_user.id, sync_type)

        if not checkpoint:
            return jsonify(
                {
                    "success": False,
                    "message": "No checkpoint found for retry. Please start a new sync.",
                }
            )

        # Start retry with checkpoint
        try:
            from app.tasks.canvas_sync import sync_canvas_data_celery

            task = sync_canvas_data_celery.delay(
                user_id=current_user.id,
                sync_type=sync_type,
                target_id=target_id,
                chunk_size=data.get("chunk_size", 10),
                use_incremental=False,  # Don't use incremental for retry
            )

            return jsonify(
                {
                    "success": True,
                    "message": "Canvas sync retry started from checkpoint! 🔄",
                    "task_id": task.id,
                    "checkpoint_progress": checkpoint.get("progress_percent", 0),
                }
            )

        except ImportError:
            return jsonify(
                {
                    "success": False,
                    "message": "Background task system not available for retry",
                }
            )

    except Exception as e:
        logger.error(f"Error retrying Canvas sync: {e}")
        return jsonify({"success": False, "message": f"Failed to retry sync: {str(e)}"})


@enhanced_canvas_bp.route("/sync/canvas/status")
@login_required
def get_canvas_sync_status():
    """Get comprehensive Canvas sync status and history"""
    try:
        # Get recent sync history
        recent_syncs = (
            SyncProgress.query.filter_by(user_id=current_user.id)
            .filter(SyncProgress.sync_type.like("canvas%"))
            .order_by(SyncProgress.created_at.desc())
            .limit(5)
            .all()
        )

        # Get current active sync
        from app.tasks.canvas_sync import get_sync_progress

        current_sync = get_sync_progress(current_user.id)

        # Check for available checkpoints
        checkpoints = {}
        for sync_type in ["all", "term", "course"]:
            from app.tasks.canvas_sync import get_sync_checkpoint

            checkpoint = get_sync_checkpoint(current_user.id, sync_type)
            if checkpoint:
                checkpoints[sync_type] = {
                    "progress": checkpoint.get("progress_percent", 0),
                    "completed_courses": checkpoint.get("processed_courses", 0),
                }

        return jsonify(
            {
                "success": True,
                "current_sync": current_sync,
                "recent_syncs": [sync.to_dict() for sync in recent_syncs],
                "available_checkpoints": checkpoints,
                "canvas_configured": bool(
                    current_user.canvas_base_url and current_user.canvas_access_token
                ),
                "last_successful_sync": current_user.canvas_last_sync.isoformat()
                if current_user.canvas_last_sync
                else None,
            }
        )

    except Exception as e:
        logger.error(f"Error getting Canvas sync status: {e}")
        return jsonify({"success": False, "error": str(e)})


# Additional utility routes for enhanced Canvas sync


@enhanced_canvas_bp.route("/sync/canvas/test_connection", methods=["POST"])
@login_required
def test_canvas_connection():
    """Test Canvas API connection without starting sync"""
    try:
        if not current_user.canvas_base_url or not current_user.canvas_access_token:
            return jsonify(
                {"success": False, "message": "Canvas credentials not configured"}
            )

        from app.services.canvas_sync_service import create_canvas_sync_service

        sync_service = create_canvas_sync_service(current_user)

        result = sync_service.test_connection()

        return jsonify(result)

    except Exception as e:
        logger.error(f"Canvas connection test failed: {e}")
        return jsonify(
            {"success": False, "message": f"Connection test failed: {str(e)}"}
        )


@enhanced_canvas_bp.route("/sync/canvas/preview", methods=["POST"])
@login_required
def preview_canvas_data():
    """Preview what data would be synced without actually syncing"""
    try:
        data = request.get_json() or {}
        use_incremental = data.get("use_incremental", True)

        if not current_user.canvas_base_url or not current_user.canvas_access_token:
            return jsonify(
                {"success": False, "message": "Canvas credentials not configured"}
            )

        from app.services.canvas_sync_service import create_canvas_sync_service

        sync_service = create_canvas_sync_service(current_user)

        # Test connection first
        connection_result = sync_service.test_connection()
        if not connection_result.get("success"):
            return jsonify(connection_result)

        # Get courses list for preview
        since = None
        if use_incremental and current_user.canvas_last_sync:
            since = current_user.canvas_last_sync

        canvas_courses = sync_service.canvas_api.get_courses(since=since)

        # Preview first few courses for sample data
        preview_courses = []
        for course in canvas_courses[:5]:  # Preview first 5 courses
            try:
                assignments = sync_service.canvas_api.get_assignments(str(course["id"]))
                preview_courses.append(
                    {
                        "name": course.get("name", "Unnamed Course"),
                        "id": course["id"],
                        "assignment_count": len(assignments),
                        "term": course.get("term", {}).get("name", "Unknown Term"),
                    }
                )
            except Exception:
                preview_courses.append(
                    {
                        "name": course.get("name", "Unnamed Course"),
                        "id": course["id"],
                        "assignment_count": "Error loading",
                        "term": course.get("term", {}).get("name", "Unknown Term"),
                    }
                )

        return jsonify(
            {
                "success": True,
                "total_courses": len(canvas_courses),
                "incremental_sync": use_incremental and since is not None,
                "last_sync": current_user.canvas_last_sync.isoformat()
                if current_user.canvas_last_sync
                else None,
                "preview_courses": preview_courses,
                "estimated_time": f"{max(1, len(canvas_courses) // 10)} - {max(2, len(canvas_courses) // 5)} minutes",
            }
        )

    except Exception as e:
        logger.error(f"Canvas preview failed: {e}")
        return jsonify({"success": False, "message": f"Preview failed: {str(e)}"})
