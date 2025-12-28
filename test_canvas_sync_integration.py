#!/usr/bin/env python3
"""
Simple Canvas sync test - directly tests the sync functionality
"""

import requests
import time
import json
from app import create_app
from app.models import User, SyncProgress, db


def simulate_canvas_sync_request():
    """Simulate Canvas sync request to test error handling"""

    app = create_app()

    with app.test_client() as client:
        # Get a user with Canvas URL
        with app.app_context():
            user = User.query.filter(User.canvas_base_url.isnot(None)).first()
            if not user:
                print("❌ No user with Canvas URL found")
                return False

            print(f"📋 Testing Canvas sync for user {user.id} ({user.username})")
            print(f"   Canvas URL: {user.canvas_base_url}")
            print(
                f"   Access Token: {'Set' if user.canvas_access_token else 'NOT SET'}"
            )

            # Clear any existing sync progress
            existing_progress = SyncProgress.query.filter_by(user_id=user.id).all()
            for prog in existing_progress:
                db.session.delete(prog)
            db.session.commit()

        # Mock a logged in session by directly calling the sync start route
        with app.app_context():
            from flask_login import login_user

            login_user(user)

            # Import the sync route function directly
            from app.routes import start_canvas_sync
            from flask import request
            import flask

            # Create a mock request context
            with app.test_request_context(
                "/sync/canvas/start", method="POST", data={"sync_type": "all"}
            ):
                try:
                    response = start_canvas_sync()
                    print(f"✅ Canvas sync started successfully")
                    print(f"   Response: {response}")

                    # Wait a moment for background sync to run
                    time.sleep(2)

                    # Check the sync progress
                    sync_prog = SyncProgress.query.filter_by(
                        user_id=user.id, sync_type="canvas"
                    ).first()

                    if sync_prog:
                        print(f"📊 Sync Progress Status:")
                        print(f"   Is Complete: {sync_prog.is_complete}")
                        print(f"   Current Operation: {sync_prog.current_operation}")
                        print(f"   Current Item: {sync_prog.current_item}")
                        print(f"   Progress: {sync_prog.progress_percent}%")

                        if sync_prog.is_complete:
                            errors = sync_prog.get_errors()
                            if errors:
                                print(f"   Errors: {errors}")
                                print(
                                    "✅ Error handling working - sync properly failed with error message"
                                )
                                return True
                            else:
                                print("❓ Sync completed without errors (unexpected)")
                                return False
                        else:
                            print("❓ Sync still in progress or stuck")
                            return False
                    else:
                        print("❌ No sync progress record found")
                        return False

                except Exception as e:
                    print(f"❌ Exception during sync: {e}")
                    return False

    return False


if __name__ == "__main__":
    success = simulate_canvas_sync_request()
    if success:
        print("🎉 Canvas sync error handling test PASSED!")
    else:
        print("❌ Canvas sync error handling test FAILED!")
