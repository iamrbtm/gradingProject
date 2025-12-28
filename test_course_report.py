#!/usr/bin/env python3
"""
Test script to debug the course report 500 error by simulating authentication
"""
import requests
from requests.sessions import Session
import json

# Create a session to maintain cookies
session = Session()

# Base URL
BASE_URL = "http://localhost:12345"

def test_course_report():
    print("Testing course report route...")
    
    # First, try to login (you'll need to check what the actual login process is)
    # For now, let's just try to access the route directly and see what happens
    
    # Try accessing the course report
    response = session.get(f"{BASE_URL}/course/1/report")
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    if response.status_code == 302:
        print("Redirected to login - this is expected without authentication")
        print(f"Redirect location: {response.headers.get('Location', 'Unknown')}")
        return
    
    if response.status_code == 500:
        print("500 Error detected!")
        print("Response content:")
        print(response.text[:2000])  # First 2000 chars
        return
    
    print("Response content:")
    print(response.text[:500])  # First 500 chars

if __name__ == "__main__":
    test_course_report()