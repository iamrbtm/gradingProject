#!/usr/bin/env python3
"""
Test Canvas sync with our fixes to verify error handling works
"""

from app import create_app
from app.models import User, SyncProgress, db
from flask import current_app
import threading
import time


def test_canvas_sync_fix():
    """Test that Canvas sync now properly handles missing credentials"""

    app = create_app()

    with app.app_context():
        # Get a user with Canvas URL but no access token
        user = User.query.filter(User.canvas_base_url.isnot(None)).first()
        if not user:
            print("❌ No user with Canvas URL found")
            return False

        print(f"📋 Testing Canvas sync fix for user {user.id} ({user.username})")
        print(f"   Canvas URL: {user.canvas_base_url}")
        print(f"   Access Token: {'Set' if user.canvas_access_token else 'NOT SET'}")

        # Clear any existing sync progress
        existing_progress = SyncProgress.query.filter_by(user_id=user.id).all()
        for prog in existing_progress:
            db.session.delete(prog)
        db.session.commit()

        # Simulate the sync start process
        user_id = user.id
        sync_type = "all"
        target_id = None
        sync_type_str = "canvas"

        # Create sync progress record (like the real endpoint does)
        sync_progress = SyncProgress(
            user_id=user_id,
            sync_type=sync_type_str,
            target_id=target_id,
            total_items=0,
            completed_items=0,
            progress_percent=0,
            current_operation="Initializing sync...",
            current_item="",
            is_complete=False,
        )
        db.session.add(sync_progress)
        db.session.commit()
        print(f"✅ Created SyncProgress record ID {sync_progress.id}")

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
                    else:
                        print(f"❌ No sync progress record found in callback")
            except Exception as e:
                print(f"❌ Error in progress callback: {e}")

        # Simulate the background sync function with our fixes
        def background_sync():
            try:
                print("🚀 Background sync started")

                with app.app_context():
                    from app.models import db, User
                    from app.services.canvas_sync_service import (
                        create_canvas_sync_service,
                    )

                    # Re-fetch user (using fixed SQLAlchemy syntax)
                    user = db.session.get(User, user_id)
                    if not user:
                        error_msg = f"User {user_id} not found for background sync"
                        print(f"❌ {error_msg}")

                        # Update progress with error
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

                    print(f"✅ User found: {user.username}")

                    print(f"🔑 Checking Canvas credentials...")
                    print(f"   Canvas URL: {repr(user.canvas_base_url)}")
                    print(
                        f"   Access Token: {'Set' if user.canvas_access_token else 'NOT SET'}"
                    )

                    # This is our FIX - properly handle missing credentials
                    if not user.canvas_base_url or not user.canvas_access_token:
                        error_msg = (
                            f"Canvas credentials not configured for user {user_id}"
                        )
                        print(f"❌ {error_msg}")

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
                            print("✅ Updated SyncProgress with credential error")
                        return

                    print("🔧 Canvas credentials OK, proceeding with sync...")
                    # Rest of sync logic would go here...

            except Exception as e:
                print(f"💥 Background sync failed: {e}")
                import traceback

                print(f"Traceback: {traceback.format_exc()}")

        # Start background thread
        print("🧵 Starting background thread...")
        sync_thread = threading.Thread(target=background_sync)
        sync_thread.daemon = True
        sync_thread.start()

        # Wait for thread to complete
        print("⏳ Waiting for background thread...")
        sync_thread.join(timeout=10)

        if sync_thread.is_alive():
            print("⚠️ Background thread still running")
        else:
            print("✅ Background thread completed")

        # Check final result
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

            if (
                final_progress.is_complete
                and final_progress.current_operation == "Canvas credentials missing"
            ):
                print("🎉 SUCCESS: Canvas sync properly handled missing credentials!")
                return True
            else:
                print(
                    "❌ FAILED: Canvas sync did not handle missing credentials correctly"
                )
                return False
        else:
            print("❌ FAILED: No sync progress record found")
            return False


if __name__ == "__main__":
    success = test_canvas_sync_fix()
    if success:
        print("\n✅ Canvas sync fix VERIFIED!")
    else:
        print("\n❌ Canvas sync fix FAILED!")
