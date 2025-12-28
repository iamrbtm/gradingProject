#!/usr/bin/env python3
"""
Test Canvas sync with enhanced logging to see where it fails
"""

import requests
import time
import json


def test_canvas_sync_with_logging():
    """Test Canvas sync and monitor logs"""

    # Test the Canvas sync start endpoint
    base_url = "http://127.0.0.1:5001"

    try:
        # We can't easily login through requests, so let's call the endpoint directly
        # and see what happens in the logs

        session = requests.Session()

        # Try to trigger sync directly (this will fail due to authentication, but should show logs)
        print(
            "🔧 Attempting to trigger Canvas sync (expect auth error, but should show logs)..."
        )

        response = session.post(
            f"{base_url}/sync/canvas/start", data={"sync_type": "all"}, timeout=10
        )

        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text}")

        # Give background thread time to run
        print("⏳ Waiting for background thread to process...")
        time.sleep(5)

        print("✅ Check the Flask logs to see if background sync thread started")

    except Exception as e:
        print(f"❌ Request failed: {e}")


if __name__ == "__main__":
    test_canvas_sync_with_logging()
