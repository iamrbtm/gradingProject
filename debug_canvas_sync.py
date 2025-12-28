#!/usr/bin/env python3
"""
Direct Canvas sync simulation to debug the exact failure point
"""

from app import create_app
from app.models import User, SyncProgress, db
from flask_login import login_user
import threading
import time


def simulate_canvas_sync():
    """Directly simulate the Canvas sync process to find where it fails"""

    app = create_app()

    with app.app_context():
        # Get a user with Canvas URL
        user = User.query.filter(User.canvas_base_url.isnot(None)).first()
        if not user:
            print("❌ No user with Canvas URL found")
            return

        print(f"📋 Simulating Canvas sync for user {user.id} ({user.username})")
        print(f"   Canvas URL: {user.canvas_base_url}")
        print(f"   Access Token: {'Set' if user.canvas_access_token else 'NOT SET'}")

        # Clear any existing sync progress
        existing_progress = SyncProgress.query.filter_by(user_id=user.id).all()
        for prog in existing_progress:
            db.session.delete(prog)
        db.session.commit()

        # Create the sync progress record (like the /sync/canvas/start endpoint does)
        sync_progress = SyncProgress(
            user_id=user.id,
            sync_type="canvas",
            target_id=None,
            total_items=0,
            completed_items=0,
            progress_percent=0,
            current_operation="Initializing sync...",
            current_item="",
            is_complete=False,
        )
        db.session.add(sync_progress)
        db.session.commit()

        print(f"✅ Created SyncProgress record with ID {sync_progress.id}")

        # Now simulate the background sync function step by step
        user_id = user.id
        sync_type = "all"
        target_id = None
        sync_type_str = "canvas"

        def progress_callback(progress_data):
            """Update progress in database"""
            try:
                with app.app_context():
                    print(f"📊 Progress callback: {progress_data}")

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
                        print(f"✅ Updated SyncProgress: {sync_prog.current_operation}")
                    else:
                        print(f"❌ No sync progress record found")
            except Exception as e:
                print(f"❌ Error in progress callback: {e}")

        def background_sync():
            try:
                print("🚀 Background sync thread started")

                with app.app_context():
                    from app.models import db, User
                    from app.services.canvas_sync_service import (
                        create_canvas_sync_service,
                    )

                    print("📂 In app context, fetching user")

                    # Re-fetch user in the new context (using fixed SQLAlchemy syntax)
                    user = db.session.get(User, user_id)
                    if not user:
                        error_msg = f"User {user_id} not found for background sync"
                        print(f"❌ {error_msg}")

                        # Update progress with error
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

                    print(f"✅ User found: {user.username}")

                    # Check Canvas credentials
                    print(f"🔑 Checking Canvas credentials...")
                    print(f"   Canvas URL: {repr(user.canvas_base_url)}")
                    print(
                        f"   Access Token: {'Set' if user.canvas_access_token else 'NOT SET'}"
                    )

                    if not user.canvas_base_url or not user.canvas_access_token:
                        error_msg = (
                            f"Canvas credentials not configured for user {user_id}"
                        )
                        print(f"❌ {error_msg}")

                        # Update progress with error
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
                            print("✅ Updated SyncProgress with credential error")
                        return

                    print("🔧 Attempting to initialize Canvas sync service...")

                    # Initialize sync service with progress callback
                    try:
                        sync_service = create_canvas_sync_service(
                            user, progress_callback
                        )
                        print("✅ Canvas sync service created successfully")
                    except Exception as e:
                        error_msg = f"Failed to initialize Canvas sync service: {e}"
                        print(f"❌ {error_msg}")

                        # Update progress with error
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
                            print("✅ Updated SyncProgress with service creation error")
                        return

                    print("🔍 Testing Canvas connection...")

                    # Test connection first
                    try:
                        connection_result = sync_service.test_connection()
                        if not connection_result.get("success"):
                            error_msg = f"Canvas connection test failed: {connection_result.get('error', 'Unknown error')}"
                            print(f"❌ {error_msg}")

                            # Update progress with connection error
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
                                print("✅ Updated SyncProgress with connection error")
                            return
                        print("✅ Canvas connection test passed")
                    except Exception as e:
                        error_msg = f"Canvas connection test exception: {e}"
                        print(f"❌ {error_msg}")

                        # Update progress with connection error
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
                            print("✅ Updated SyncProgress with connection exception")
                        return

                    print("🎯 Starting actual sync process...")

                    # Perform sync based on type
                    if sync_type == "term" and target_id:
                        result = sync_service.sync_term_data(target_id)
                    elif sync_type == "course" and target_id:
                        result = sync_service.sync_course_data(target_id)
                    else:
                        result = sync_service.sync_all_data()

                    print(f"✅ Canvas sync completed with result: {result}")

                    # Mark as complete in database
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

                    print(f"🎉 Canvas sync completed successfully!")

            except Exception as e:
                print(f"💥 Background Canvas sync failed: {e}")
                import traceback

                print(f"Traceback: {traceback.format_exc()}")

                # Mark as failed in database
                try:
                    with app.app_context():
                        from app.models import db, SyncProgress

                        sync_prog = SyncProgress.query.filter_by(
                            user_id=user_id,
                            sync_type=sync_type_str,
                            target_id=target_id,
                            is_complete=False,
                        ).first()

                        if sync_prog:
                            sync_prog.current_operation = "Sync failed"
                            sync_prog.current_item = f"Error: {str(e)}"
                            sync_prog.set_errors([str(e)])
                            sync_prog.is_complete = True
                            db.session.commit()
                            print("✅ Updated SyncProgress with general error")
                except Exception as db_error:
                    print(f"❌ Failed to update database: {db_error}")

        # Start background thread (like the real endpoint does)
        print("🧵 Starting background thread...")
        sync_thread = threading.Thread(target=background_sync)
        sync_thread.daemon = True
        sync_thread.start()

        # Wait for thread to complete
        print("⏳ Waiting for background thread to complete...")
        sync_thread.join(timeout=30)  # Wait up to 30 seconds

        if sync_thread.is_alive():
            print("⚠️ Background thread is still running after 30 seconds")
        else:
            print("✅ Background thread completed")

        # Check final sync progress
        final_progress = SyncProgress.query.filter_by(user_id=user.id).first()
        if final_progress:
            print(f"\n📊 Final Sync Progress:")
            print(f"   Is Complete: {final_progress.is_complete}")
            print(f"   Current Operation: {final_progress.current_operation}")
            print(f"   Current Item: {final_progress.current_item}")
            print(f"   Progress: {final_progress.progress_percent}%")
            errors = final_progress.get_errors()
            if errors:
                print(f"   Errors: {errors}")


if __name__ == "__main__":
    simulate_canvas_sync()
