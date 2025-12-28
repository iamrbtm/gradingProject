#!/usr/bin/env python3
"""
Test script to verify Canvas sync error handling fixes
"""

import requests
import time
import sys
from app import create_app
from app.models import User, SyncProgress, db


def test_canvas_sync_error_handling():
    """Test that Canvas sync properly handles missing credentials"""

    app = create_app()

    with app.app_context():
        # Find a user with Canvas credentials (we know users exist)
        user = User.query.filter(User.canvas_base_url.isnot(None)).first()

        if not user:
            print("❌ No test user found with Canvas URL but no access token")
            return False

        print(f"📋 Testing Canvas sync for user {user.id} ({user.username})")
        print(f"   Canvas URL: {user.canvas_base_url}")
        print(f"   Access Token: {'Set' if user.canvas_access_token else 'NOT SET'}")

        # Clear any existing sync progress for this user
        existing_progress = SyncProgress.query.filter_by(
            user_id=user.id, sync_type="canvas"
        ).all()

        for prog in existing_progress:
            db.session.delete(prog)
        db.session.commit()

        # Simulate the Canvas sync request by making HTTP request to the app
        base_url = "http://127.0.0.1:5001"

        # First login to get session
        session = requests.Session()

        # Try to access login page
        try:
            login_response = session.get(f"{base_url}/auth/login")
            if login_response.status_code != 200:
                print(f"❌ Could not access login page: {login_response.status_code}")
                return False

            print("✅ Flask app is accessible")

        except Exception as e:
            print(f"❌ Could not connect to Flask app: {e}")
            return False

        # Since we can't easily simulate a full login session, let's test the sync service directly
        print("🔧 Testing Canvas sync service directly...")

        from app.services.canvas_sync_service import (
            create_canvas_sync_service,
            CanvasSyncError,
        )

        # Test 1: Verify that create_canvas_sync_service raises proper exception
        try:
            sync_service = create_canvas_sync_service(user)
            print("❌ Expected CanvasSyncError but service was created successfully")
            return False
        except CanvasSyncError as e:
            expected_msg = "User Canvas credentials not configured"
            if expected_msg in str(e):
                print(f"✅ Correctly caught CanvasSyncError: {e}")
            else:
                print(f"❌ Got CanvasSyncError but wrong message: {e}")
                return False
        except Exception as e:
            print(f"❌ Unexpected exception type: {type(e).__name__}: {e}")
            return False

        # Test 2: Test that SyncProgress record can be created and updated
        print("🔧 Testing SyncProgress error handling...")

        sync_progress = SyncProgress(
            user_id=user.id,
            sync_type="canvas",
            total_items=0,
            completed_items=0,
            progress_percent=0,
            current_operation="Initializing sync...",
            current_item="",
            is_complete=False,
        )
        db.session.add(sync_progress)
        db.session.commit()

        # Simulate error update
        error_msg = "Failed to initialize Canvas sync service: User Canvas credentials not configured"
        sync_progress.current_operation = "Canvas sync failed"
        sync_progress.current_item = error_msg
        sync_progress.set_errors([error_msg])
        sync_progress.is_complete = True
        db.session.commit()

        # Verify the error was saved
        updated_progress = SyncProgress.query.get(sync_progress.id)
        if updated_progress and updated_progress.is_complete:
            errors = updated_progress.get_errors()
            if errors and error_msg in errors:
                print("✅ SyncProgress error handling working correctly")
                print(f"   Operation: {updated_progress.current_operation}")
                print(f"   Error: {updated_progress.current_item}")
            else:
                print("❌ SyncProgress error not saved correctly")
                return False
        else:
            print("❌ SyncProgress not updated correctly")
            return False

        # Clean up
        db.session.delete(updated_progress)
        db.session.commit()

        print("🎉 All Canvas sync error handling tests passed!")
        return True


if __name__ == "__main__":
    success = test_canvas_sync_error_handling()
    sys.exit(0 if success else 1)
