#!/usr/bin/env python3
"""
Test script to verify the toggle assignment completion endpoint
"""
import requests
import json

def test_toggle_endpoint():
    """Test the toggle assignment completion endpoint."""

    base_url = "http://localhost:12345"

    # First, let's try to access the todo page to see if we get redirected to login
    print("Testing todo page access...")
    response = requests.get(f"{base_url}/todo")
    print(f"Status: {response.status_code}")
    print(f"URL: {response.url}")

    if response.status_code == 302:
        print("Redirected to login - user not authenticated")
        return

    # If we get here, user might be logged in
    print("User appears to be logged in")

    # Try to toggle an assignment
    print("\nTesting assignment toggle...")
    assignment_id = 1

    # We need CSRF token, but for testing purposes, let's see what happens
    response = requests.post(
        f"{base_url}/toggle_assignment_completion/{assignment_id}",
        data={'csrf_token': 'dummy_token'},
        allow_redirects=False
    )

    print(f"Toggle response status: {response.status_code}")
    print(f"Response: {response.text}")

if __name__ == "__main__":
    test_toggle_endpoint()