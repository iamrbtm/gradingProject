#!/usr/bin/env python3
"""
Test script to verify the checkbox toggle functionality works correctly.
"""

import requests
import json
import time

def test_checkbox_toggle():
    """
    Test the todo and assignment checkbox toggle functionality.
    This script assumes the Flask app is running on localhost:5000
    """
    
    base_url = "http://localhost:5000"
    
    # Test data
    test_cases = [
        {
            "type": "todo",
            "endpoint": "/toggle_todo/1",
            "description": "Test todo toggle"
        },
        {
            "type": "assignment", 
            "endpoint": "/toggle_assignment_completion/1",
            "description": "Test assignment toggle"
        }
    ]
    
    print("Testing checkbox toggle functionality...")
    print("=" * 50)
    
    for test_case in test_cases:
        print(f"\nTesting {test_case['description']}")
        print("-" * 30)
        
        # Test multiple rapid toggles
        for i in range(3):
            try:
                print(f"Toggle attempt {i+1}...")
                
                response = requests.post(
                    base_url + test_case["endpoint"],
                    data={
                        'csrf_token': 'test-token'  # In real app, get from meta tag
                    },
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        status = data.get('is_completed') if test_case['type'] == 'todo' else data.get('completed')
                        print(f"  ✓ Success: Status = {status}")
                    else:
                        print(f"  ✗ Failed: {data.get('error', 'Unknown error')}")
                else:
                    print(f"  ✗ HTTP Error: {response.status_code}")
                    
                # Small delay between requests
                time.sleep(0.1)
                
            except requests.exceptions.RequestException as e:
                print(f"  ✗ Request failed: {e}")
        
        print(f"Completed testing {test_case['description']}")
    
    print("\n" + "=" * 50)
    print("Checkbox toggle test completed!")
    print("\nKey improvements made:")
    print("1. Removed complex delay logic that caused race conditions")
    print("2. Added request deduplication to prevent double-clicking issues")
    print("3. Added proper error handling and user feedback")
    print("4. Ensured checkbox state always matches server response")
    print("5. Added user authorization checks in backend routes")

if __name__ == "__main__":
    print("Note: This test requires the Flask app to be running.")
    print("Start the app with: python app.py")
    print("Then run this test script.")
    print("\nPress Enter to continue or Ctrl+C to cancel...")
    try:
        input()
        test_checkbox_toggle()
    except KeyboardInterrupt:
        print("\nTest cancelled.")