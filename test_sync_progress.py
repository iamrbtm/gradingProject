#!/usr/bin/env python3
"""Test script to verify sync progress functionality"""

import requests
import json
import time
from bs4 import BeautifulSoup

BASE_URL = "http://127.0.0.1:12345"


def login_and_get_session():
    """Login and get authenticated session"""
    session = requests.Session()

    # Get login page to get CSRF token
    response = session.get(f"{BASE_URL}/auth/login")
    soup = BeautifulSoup(response.text, "html.parser")
    csrf_token = None
    for input_tag in soup.find_all("input"):
        if input_tag.get("name") == "csrf_token":
            csrf_token = input_tag.get("value")
            break

    if not csrf_token:
        print("Could not find CSRF token")
        return None

    # Login
    login_data = {"username": "test", "password": "test123", "csrf_token": csrf_token}

    response = session.post(f"{BASE_URL}/auth/login", data=login_data)

    if response.status_code == 200 and "dashboard" in response.url:
        print("Login successful!")
        return session
    else:
        print(f"Login failed: {response.status_code}")
        return None


def test_sync_progress():
    """Test the sync progress functionality"""

    # Login first
    session = login_and_get_session()
    if not session:
        return

    # First, let's check if we can access the progress endpoint
    print("\nTesting sync progress endpoint...")

    # Get initial progress
    response = session.get(f"{BASE_URL}/sync/canvas/progress")
    print(f"Initial progress response: {response.status_code}")

    if response.status_code == 200:
        try:
            progress_data = response.json()
            print(f"Initial progress data: {json.dumps(progress_data, indent=2)}")
        except:
            print(f"Response is not JSON. Raw response: {response.text[:500]}")
    else:
        print(f"Error getting initial progress: {response.text}")
        return

    # Get CSRF token from dashboard page
    response = session.get(f"{BASE_URL}/dashboard")
    soup = BeautifulSoup(response.text, "html.parser")
    csrf_token = None
    for meta_tag in soup.find_all("meta"):
        if meta_tag.get("name") == "csrf-token":
            csrf_token = meta_tag.get("content")
            break

    if not csrf_token:
        print("Could not find CSRF token for POST request")
        return

    # Try to start a sync (this will likely fail without proper Canvas credentials)
    print("\nAttempting to start sync...")
    sync_data = {"sync_type": "all", "target_id": None}

    response = session.post(
        f"{BASE_URL}/sync/canvas/start",
        json=sync_data,
        headers={"Content-Type": "application/json", "X-CSRFToken": csrf_token},
    )
    print(f"Start sync response: {response.status_code}")

    if response.status_code == 200:
        try:
            result = response.json()
            print(f"Start sync response: {json.dumps(result, indent=2)}")
        except:
            print(f"Start sync returned non-JSON: {response.text[:500]}")
            return

        if result.get("success"):
            print("\nPolling for progress...")
            for i in range(10):
                response = session.get(f"{BASE_URL}/sync/canvas/progress")
                if response.status_code == 200:
                    progress_data = response.json()
                    print(
                        f"Progress update {i + 1}: {progress_data.get('current_operation', 'N/A')} - {progress_data.get('progress_percent', 0)}%"
                    )

                    if progress_data.get("is_complete"):
                        print("Sync completed!")
                        break
                else:
                    print(f"Error getting progress: {response.text}")

                time.sleep(1)
        else:
            print(f"Sync failed to start: {result.get('message', 'Unknown error')}")
    else:
        print(f"Start sync failed: {response.text[:500]}")


if __name__ == "__main__":
    test_sync_progress()
