from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    jsonify,
    current_app,
    session,
)
from flask_login import login_required, current_user, login_user, logout_user
from app.models import (
    db,
    TodoItem,
    User,
    Term,
    Course,
    GradeCategory,
    Assignment,
    Settings,
)
from app.utils import serialize_model
from app.services.notification_service import NotificationService
from datetime import datetime
from app.term_date_calculator import get_term_dates

# Create a Blueprint for routes
routes = Blueprint("routes", __name__, template_folder="templates")


@routes.route("/send_reminders")
@login_required
def send_reminders():
    """Send email reminders for current user."""
    success = NotificationService.send_reminders(current_user.id)
    if success:
        flash("Reminders sent successfully!", "success")
    else:
        flash("Failed to send reminders. Check email configuration.", "danger")
    return redirect(url_for("main.dashboard"))


@routes.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """User settings page."""
    if request.method == "POST":
        # Get or create settings
        settings = Settings.query.first()
        if not settings:
            settings = Settings()
            db.session.add(settings)

        # Update settings from form
        settings.mail_server = request.form.get("smtp_server")
        settings.mail_port = int(request.form.get("smtp_port", 587))
        settings.mail_username = request.form.get("smtp_username")
        settings.mail_password = request.form.get("smtp_password")
        settings.mail_use_tls = "smtp_tls" in request.form
        settings.email_reminders = "email_reminders" in request.form
        settings.dashboard_notifications = "dashboard_notifications" in request.form

        # Update Canvas credentials for current user
        canvas_base_url = request.form.get("canvas_base_url", "").strip()
        canvas_access_token = request.form.get("canvas_access_token", "").strip()

        current_user.canvas_base_url = canvas_base_url if canvas_base_url else None
        current_user.canvas_access_token = (
            canvas_access_token if canvas_access_token else None
        )

        db.session.commit()
        flash("Settings saved successfully!", "success")
        return redirect(url_for("routes.settings"))

    # Get settings from DB, fallback to config
    settings = Settings.query.first()
    if settings:
        mail_server = settings.mail_server or current_app.config.get("MAIL_SERVER", "")
        mail_port = settings.mail_port or current_app.config.get("MAIL_PORT", 587)
        mail_username = settings.mail_username or current_app.config.get(
            "MAIL_USERNAME", ""
        )
        mail_password = settings.mail_password or current_app.config.get(
            "MAIL_PASSWORD", ""
        )
        mail_use_tls = (
            settings.mail_use_tls
            if settings.mail_use_tls is not None
            else current_app.config.get("MAIL_USE_TLS", True)
        )
        email_reminders = (
            settings.email_reminders if settings.email_reminders is not None else True
        )
        dashboard_notifications = (
            settings.dashboard_notifications
            if settings.dashboard_notifications is not None
            else True
        )
    else:
        mail_server = current_app.config.get("MAIL_SERVER", "")
        mail_port = current_app.config.get("MAIL_PORT", 587)
        mail_username = current_app.config.get("MAIL_USERNAME", "")
        mail_password = current_app.config.get("MAIL_PASSWORD", "")
        mail_use_tls = current_app.config.get("MAIL_USE_TLS", True)
        email_reminders = True
        dashboard_notifications = True

    return render_template(
        "settings.html",
        mail_server=mail_server,
        mail_port=mail_port,
        mail_username=mail_username,
        mail_password=mail_password,
        mail_use_tls=mail_use_tls,
        email_reminders=email_reminders,
        dashboard_notifications=dashboard_notifications,
        canvas_base_url=current_user.canvas_base_url or "",
        canvas_access_token=current_user.canvas_access_token or "",
        canvas_last_sync=current_user.canvas_last_sync,
    )


@routes.route("/sync_canvas", methods=["POST"])
@login_required
def sync_canvas():
    """Sync data from Canvas."""
    try:
        # Check if Canvas credentials are configured
        if not current_user.canvas_base_url or not current_user.canvas_access_token:
            flash(
                "Canvas credentials not configured. Please update your settings first.",
                "error",
            )
            return redirect(url_for("routes.settings"))

        # Dynamic import to avoid circular imports
        try:
            import importlib

            canvas_sync_module = importlib.import_module(
                "app.services.canvas_sync_service"
            )
            canvas_api_module = importlib.import_module(
                "app.services.canvas_api_service"
            )
            CanvasSyncService = getattr(canvas_sync_module, "CanvasSyncService")
            CanvasAPIService = getattr(canvas_api_module, "CanvasAPIService")
        except (ImportError, AttributeError) as e:
            flash(f"Canvas sync service not available: {str(e)}", "error")
            return redirect(url_for("main.dashboard"))

        # Initialize Canvas API service with user's credentials
        canvas_api_service = CanvasAPIService(
            current_user.canvas_base_url, current_user.canvas_access_token
        )

        # Initialize sync service with user and API service
        sync_service = CanvasSyncService(current_user, canvas_api_service)

        # Sync all data - the service will auto-create terms from Canvas data
        result = sync_service.sync_all_data()

        # Update last sync time
        current_user.canvas_last_sync = datetime.utcnow()
        db.session.commit()

        # Show success message with sync statistics
        courses_msg = (
            f"{result['courses_created']} created, {result['courses_updated']} updated"
        )
        assignments_msg = f"{result['assignments_created']} created, {result['assignments_updated']} updated"

        flash(
            f"Canvas sync completed! Courses: {courses_msg}. Assignments: {assignments_msg}. "
            f"Categories created: {result['categories_created']}.",
            "success",
        )

        if result["errors"]:
            flash(
                f"Some errors occurred during sync: {'; '.join(result['errors'][:3])}",
                "warning",
            )

    except Exception as e:
        flash(f"Canvas sync failed: {str(e)}", "error")

    return redirect(url_for("main.dashboard"))


@routes.route("/sync_canvas_term/<int:term_id>", methods=["POST"])
@login_required
def sync_canvas_term(term_id):
    """
    Sync Canvas data for a specific term (async background processing)
    """
    if not current_user.canvas_base_url or not current_user.canvas_access_token:
        flash(
            "Canvas credentials not configured. Please update your settings first.",
            "error",
        )
        return redirect(url_for("main.view_term", term_id=term_id))

    # Dynamic import to avoid circular imports
    try:
        import importlib
        import threading
        from flask import current_app

        canvas_sync_module = importlib.import_module("app.services.canvas_sync_service")
        canvas_api_module = importlib.import_module("app.services.canvas_api_service")
        CanvasSyncService = getattr(canvas_sync_module, "CanvasSyncService")
        CanvasAPIService = getattr(canvas_api_module, "CanvasAPIService")
    except (ImportError, AttributeError) as e:
        flash(f"Canvas sync service not available: {str(e)}", "error")
        return redirect(url_for("main.view_term", term_id=term_id))

    # Start sync in background thread
    def background_sync():
        try:
            # Create new app context for the background thread
            with current_app.app_context():
                from app.models import db, User

                # Re-fetch user in the new context
                user = User.query.get(current_user.id)
                if not user:
                    return

                # Update sync status
                if hasattr(user, "canvas_sync_status"):
                    user.canvas_sync_status = "running"
                db.session.commit()

                try:
                    # Initialize services
                    canvas_api_service = CanvasAPIService(
                        user.canvas_base_url, user.canvas_access_token
                    )
                    sync_service = CanvasSyncService(user, canvas_api_service)

                    # Perform sync
                    result = sync_service.sync_term_data(term_id)

                    # Update last sync time and results
                    user.canvas_last_sync = datetime.utcnow()
                    if hasattr(user, "canvas_last_sync_courses"):
                        user.canvas_last_sync_courses = result["courses_processed"]
                        user.canvas_last_sync_assignments = result[
                            "assignments_processed"
                        ]
                        user.canvas_last_sync_categories = result["categories_created"]
                        user.canvas_sync_status = "completed"
                    db.session.commit()

                    # Log completion
                    current_app.logger.info(
                        f"Background Canvas term sync completed for user {user.id}, term {term_id}: {result}"
                    )

                except Exception as sync_error:
                    if hasattr(user, "canvas_sync_status"):
                        user.canvas_sync_status = "failed"
                    db.session.commit()
                    current_app.logger.error(
                        f"Background Canvas term sync failed for user {current_user.id}, term {term_id}: {sync_error}"
                    )
                    raise

        except Exception as e:
            current_app.logger.error(
                f"Background Canvas term sync thread error for user {current_user.id}, term {term_id}: {e}"
            )

    # Start the background thread
    sync_thread = threading.Thread(target=background_sync)
    sync_thread.daemon = True
    sync_thread.start()

    # Return immediately with progress message
    flash(
        "Canvas term sync started in the background. This may take a few minutes. Please refresh the page later to see updated data.",
        "info",
    )

    return redirect(url_for("main.view_term", term_id=term_id))


@routes.route("/sync_canvas_course/<int:course_id>", methods=["POST"])
@login_required
def sync_canvas_course(course_id):
    """
    Sync Canvas data for a specific course
    """
    if not current_user.canvas_base_url or not current_user.canvas_access_token:
        flash(
            "Canvas credentials not configured. Please update your settings first.",
            "error",
        )
        return redirect(url_for("main.view_course", course_id=course_id))

    # Dynamic import to avoid circular imports
    try:
        import importlib

        canvas_sync_module = importlib.import_module("app.services.canvas_sync_service")
        canvas_api_module = importlib.import_module("app.services.canvas_api_service")
        CanvasSyncService = getattr(canvas_sync_module, "CanvasSyncService")
        CanvasAPIService = getattr(canvas_api_module, "CanvasAPIService")
    except (ImportError, AttributeError) as e:
        flash(f"Canvas sync service not available: {str(e)}", "error")
        return redirect(url_for("main.view_course", course_id=course_id))

    # Initialize Canvas API service with user's credentials
    canvas_api_service = CanvasAPIService(
        current_user.canvas_base_url, current_user.canvas_access_token
    )

    # Initialize sync service with user and API service
    sync_service = CanvasSyncService(current_user, canvas_api_service)

    try:
        # Sync course-specific data
        result = sync_service.sync_course_data(course_id)

        # Show success message with sync statistics
        assignments_msg = f"{result['assignments_created']} created, {result['assignments_updated']} updated"

        flash(
            f"Canvas course sync completed! Assignments: {assignments_msg}. "
            f"Categories created: {result['categories_created']}.",
            "success",
        )

        if result["errors"]:
            flash(
                f"Some errors occurred during sync: {'; '.join(result['errors'][:3])}",
                "warning",
            )

    except Exception as e:
        flash(f"Canvas course sync failed: {str(e)}", "error")

    return redirect(url_for("main.view_course", course_id=course_id))


# Canvas Sync Progress Routes
@routes.route("/sync/canvas/progress")
@login_required
def get_canvas_sync_progress():
    """Get current Canvas sync progress"""
    try:
        # Get progress from database
        from app.models import SyncProgress

        # Look for the most recent incomplete sync, or the most recent completed sync
        sync_progress = (
            SyncProgress.query.filter_by(user_id=current_user.id)
            .filter(SyncProgress.sync_type.like("canvas%"))
            .order_by(SyncProgress.created_at.desc())
            .first()
        )

        if sync_progress:
            return jsonify(sync_progress.to_dict())
        else:
            # Return default progress if no sync found
            return jsonify(
                {
                    "progress_percent": 0,
                    "completed_items": 0,
                    "total_items": 0,
                    "current_operation": "Ready",
                    "current_item": "",
                    "elapsed_time": 0,
                    "errors": [],
                    "is_complete": False,
                }
            )

    except Exception as e:
        current_app.logger.error(f"Error getting Canvas sync progress: {e}")
        return jsonify(
            {
                "progress_percent": 0,
                "completed_items": 0,
                "total_items": 0,
                "current_operation": "Error",
                "current_item": "",
                "elapsed_time": 0,
                "errors": [str(e)],
                "is_complete": False,
            }
        )


@routes.route("/sync/canvas/start", methods=["POST"])
@login_required
def start_canvas_sync():
    """Start Canvas sync with progress tracking"""
    try:
        data = request.get_json() or {}
        sync_type = data.get("sync_type", "all")  # 'all', 'term', or 'course'
        target_id = data.get("target_id")  # term_id or course_id for specific syncs

        # Check if Canvas credentials are configured
        if not current_user.canvas_base_url or not current_user.canvas_access_token:
            return jsonify(
                {
                    "success": False,
                    "message": "Canvas credentials not configured. Please update your settings first.",
                }
            )

        # Initialize progress in database
        from app.models import SyncProgress

        # Clean up any existing incomplete progress for this user
        SyncProgress.query.filter_by(
            user_id=current_user.id,
            sync_type=f"canvas_{sync_type}" if sync_type != "all" else "canvas",
            is_complete=False,
        ).delete()

        # Capture variables for background thread
        user_id = current_user.id
        sync_type_str = f"canvas_{sync_type}" if sync_type != "all" else "canvas"

        sync_progress = SyncProgress(
            user_id=user_id,
            sync_type=sync_type_str,
            target_id=target_id,
            progress_percent=0,
            completed_items=0,
            total_items=0,
            current_operation="Initializing sync...",
            current_item="",
            elapsed_time=0,
            is_complete=False,
        )
        db.session.add(sync_progress)
        db.session.commit()

        # Define progress callback function
        def progress_callback(progress_data):
            """Update progress in database"""
            try:
                with current_app.app_context():
                    from app.models import db, SyncProgress

                    # Log progress updates for debugging
                    current_app.logger.debug(
                        f"Progress update: {progress_data.get('progress_percent', 0)}% - {progress_data.get('current_operation', '')}"
                    )

                    # Update progress in database
                    sync_prog = SyncProgress.query.filter_by(
                        user_id=user_id,
                        sync_type=sync_type_str,
                        target_id=target_id,
                        is_complete=False,
                    ).first()

                    if sync_prog:
                        sync_prog.progress_percent = progress_data.get(
                            "progress_percent", 0
                        )
                        sync_prog.completed_items = progress_data.get(
                            "completed_items", 0
                        )
                        sync_prog.total_items = progress_data.get("total_items", 0)
                        sync_prog.current_operation = progress_data.get(
                            "current_operation", ""
                        )
                        sync_prog.current_item = progress_data.get("current_item", "")
                        sync_prog.elapsed_time = progress_data.get("elapsed_time", 0)
                        sync_prog.set_errors(progress_data.get("errors", []))
                        db.session.commit()
                    else:
                        current_app.logger.warning(
                            f"No sync progress record found for user {user_id}, type {sync_type_str}"
                        )
            except Exception as e:
                current_app.logger.error(f"Error updating progress: {e}")
                import traceback

                current_app.logger.error(
                    f"Progress callback traceback: {traceback.format_exc()}"
                )

        # Start sync in background thread
        def background_sync():
            try:
                current_app.logger.info(
                    f"Background sync thread started for user {user_id}"
                )

                with current_app.app_context():
                    from app.models import db, User
                    from app.services.canvas_sync_service import (
                        create_canvas_sync_service,
                    )

                    current_app.logger.info(
                        f"Background sync: In app context, fetching user {user_id}"
                    )

                    # Re-fetch user in the new context (fix deprecated SQLAlchemy syntax)
                    user = db.session.get(User, user_id)
                    if not user:
                        error_msg = f"User {user_id} not found for background sync"
                        current_app.logger.error(error_msg)

                        # Update progress with user not found error
                        from app.models import SyncProgress

                        sync_prog = SyncProgress.query.filter_by(
                            user_id=user_id,
                            sync_type=sync_type_str,
                            target_id=target_id,
                            is_complete=False,
                        ).first()

                        if sync_prog:
                            sync_prog.current_operation = "Sync failed"
                            sync_prog.current_item = error_msg
                            sync_prog.set_errors([error_msg])
                            sync_prog.is_complete = True
                            db.session.commit()
                        return

                    current_app.logger.info(
                        f"Background sync: User {user.username} found, checking credentials"
                    )

                    current_app.logger.info(
                        f"Starting background Canvas {sync_type} sync for user {user_id}"
                    )

                    # Check Canvas credentials
                    if not user.canvas_base_url or not user.canvas_access_token:
                        error_msg = (
                            f"Canvas credentials not configured for user {user_id}"
                        )
                        current_app.logger.error(error_msg)

                        # Update progress with credential error
                        from app.models import SyncProgress

                        sync_prog = SyncProgress.query.filter_by(
                            user_id=user_id,
                            sync_type=sync_type_str,
                            target_id=target_id,
                            is_complete=False,
                        ).first()

                        if sync_prog:
                            sync_prog.current_operation = "Canvas credentials missing"
                            sync_prog.current_item = "Please configure Canvas URL and access token in settings"
                            sync_prog.set_errors([error_msg])
                            sync_prog.is_complete = True
                            db.session.commit()
                        return

                    # Initialize sync service with progress callback
                    try:
                        sync_service = create_canvas_sync_service(
                            user, progress_callback
                        )
                    except Exception as e:
                        error_msg = f"Failed to initialize Canvas sync service: {e}"
                        current_app.logger.error(error_msg)

                        # Update progress with error
                        from app.models import SyncProgress

                        sync_prog = SyncProgress.query.filter_by(
                            user_id=user_id,
                            sync_type=sync_type_str,
                            target_id=target_id,
                            is_complete=False,
                        ).first()

                        if sync_prog:
                            sync_prog.current_operation = "Canvas sync failed"
                            sync_prog.current_item = error_msg
                            sync_prog.set_errors([error_msg])
                            sync_prog.is_complete = True
                            db.session.commit()
                        return

                    # Test connection first
                    try:
                        connection_result = sync_service.test_connection()
                        if not connection_result.get("success"):
                            error_msg = f"Canvas connection test failed: {connection_result.get('error', 'Unknown error')}"
                            current_app.logger.error(error_msg)

                            # Update progress with connection error
                            from app.models import SyncProgress

                            sync_prog = SyncProgress.query.filter_by(
                                user_id=user_id,
                                sync_type=sync_type_str,
                                target_id=target_id,
                                is_complete=False,
                            ).first()

                            if sync_prog:
                                sync_prog.current_operation = "Canvas connection failed"
                                sync_prog.current_item = error_msg
                                sync_prog.set_errors([error_msg])
                                sync_prog.is_complete = True
                                db.session.commit()
                            return
                        current_app.logger.info("Canvas connection test passed")
                    except Exception as e:
                        error_msg = f"Canvas connection test exception: {e}"
                        current_app.logger.error(error_msg)

                        # Update progress with connection error
                        from app.models import SyncProgress

                        sync_prog = SyncProgress.query.filter_by(
                            user_id=user_id,
                            sync_type=sync_type_str,
                            target_id=target_id,
                            is_complete=False,
                        ).first()

                        if sync_prog:
                            sync_prog.current_operation = "Canvas connection failed"
                            sync_prog.current_item = error_msg
                            sync_prog.set_errors([error_msg])
                            sync_prog.is_complete = True
                            db.session.commit()
                        return

                    # Perform sync based on type
                    current_app.logger.info(
                        f"Starting {sync_type} sync with target_id={target_id}"
                    )
                    if sync_type == "term" and target_id:
                        result = sync_service.sync_term_data(target_id)
                    elif sync_type == "course" and target_id:
                        result = sync_service.sync_course_data(target_id)
                    else:
                        result = sync_service.sync_all_data()

                    current_app.logger.info(
                        f"Canvas {sync_type} sync completed with result: {result}"
                    )

                    # Mark as complete in database
                    from app.models import SyncProgress

                    sync_prog = SyncProgress.query.filter_by(
                        user_id=user_id,
                        sync_type=sync_type_str,
                        target_id=target_id,
                        is_complete=False,
                    ).first()

                    if sync_prog:
                        sync_prog.progress_percent = 100
                        sync_prog.completed_items = sync_prog.total_items
                        sync_prog.current_operation = "Sync completed successfully!"
                        sync_prog.current_item = ""
                        sync_prog.set_errors(result.get("errors", []))
                        sync_prog.is_complete = True
                        db.session.commit()

                    current_app.logger.info(
                        f"Canvas {sync_type} sync completed for user {user.id}"
                    )

            except Exception as e:
                current_app.logger.error(f"Background Canvas sync failed: {e}")
                # Mark as failed in database
                from app.models import db, SyncProgress

                sync_prog = SyncProgress.query.filter_by(
                    user_id=user_id,
                    sync_type=sync_type_str,  # Use consistent sync_type_str
                    target_id=target_id,
                    is_complete=False,
                ).first()

                if sync_prog:
                    sync_prog.current_operation = "Sync failed"
                    sync_prog.current_item = f"Error: {str(e)}"
                    sync_prog.set_errors([str(e)])
                    sync_prog.is_complete = True
                    db.session.commit()

        # Start background thread
        import threading

        sync_thread = threading.Thread(target=background_sync)
        sync_thread.daemon = True
        sync_thread.start()

        return jsonify({"success": True, "message": "Canvas sync started"})

    except Exception as e:
        current_app.logger.error(f"Error starting Canvas sync: {e}")
        return jsonify(
            {"success": False, "message": f"Failed to start Canvas sync: {str(e)}"}
        )


# Add more routes here following the same pattern...
