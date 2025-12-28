#!/usr/bin/env python3
"""
Debug script to test analytics routes directly
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from flask import Flask
import traceback


def test_analytics_route():
    """Test analytics route directly"""
    try:
        app = create_app()

        with app.test_client() as client:
            print("🔍 Testing analytics health endpoint...")

            # Test health endpoint
            response = client.get("/api/analytics/health")
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")

            if response.status_code == 200:
                print(f"✅ Success! Response: {response.get_json()}")
            else:
                print(
                    f"❌ Failed. Response data: {response.get_data(as_text=True)[:500]}"
                )

            # Test notifications endpoint
            print("\n🔍 Testing analytics notifications endpoint...")
            response = client.get("/api/analytics/notifications")
            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                print(f"✅ Success! Response: {response.get_json()}")
            elif response.status_code == 302:
                print(
                    f"↗️  Redirect (expected for protected route): {response.headers.get('Location')}"
                )
            else:
                print(f"❌ Failed. Response: {response.get_data(as_text=True)[:500]}")

    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    test_analytics_route()
