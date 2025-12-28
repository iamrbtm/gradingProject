#!/usr/bin/env python3
"""
Test script to debug sync issues
"""
import os
import sys
import subprocess
sys.path.append('.')

def test_applescript_basic():
    """Test basic AppleScript functionality."""
    print("Testing basic AppleScript...")
    
    try:
        # Test simple AppleScript
        result = subprocess.run(
            ['osascript', '-e', 'tell application "System Events" to return name of processes'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✓ AppleScript is working")
            return True
        else:
            print(f"✗ AppleScript failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ AppleScript test failed: {e}")
        return False

def test_reminders_app():
    """Test if Reminders app is accessible."""
    print("Testing Reminders app access...")
    
    try:
        # Test accessing Reminders app
        applescript = '''
        tell application "Reminders"
            return count of lists
        end tell
        '''
        
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"✓ Reminders app accessible, found {result.stdout.strip()} lists")
            return True
        else:
            print(f"✗ Reminders app failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Reminders app test failed: {e}")
        return False

def test_create_homework_list():
    """Test creating the Homework list."""
    print("Testing Homework list creation...")
    
    try:
        applescript = '''
        tell application "Reminders"
            if not (exists list "Homework") then
                make new list with properties {name:"Homework"}
                return "created"
            else
                return "exists"
            end if
        end tell
        '''
        
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"✓ Homework list {result.stdout.strip()}")
            return True
        else:
            print(f"✗ Homework list creation failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Homework list test failed: {e}")
        return False

def test_create_simple_reminder():
    """Test creating a simple reminder."""
    print("Testing simple reminder creation...")
    
    try:
        applescript = '''
        tell application "Reminders"
            set targetList to list "Homework"
            set newReminder to make new reminder in targetList with properties {name:"Test Assignment"}
            return id of newReminder
        end tell
        '''
        
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            reminder_id = result.stdout.strip()
            print(f"✓ Created test reminder with ID: {reminder_id}")
            
            # Clean up - delete the test reminder
            cleanup_script = f'''
            tell application "Reminders"
                delete reminder id "{reminder_id}"
            end tell
            '''
            subprocess.run(['osascript', '-e', cleanup_script], capture_output=True)
            print("✓ Cleaned up test reminder")
            return True
        else:
            print(f"✗ Simple reminder creation failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Simple reminder test failed: {e}")
        return False

def main():
    """Run all sync debug tests."""
    print("=== Sync Debug Tests ===\n")
    
    tests = [
        test_applescript_basic,
        test_reminders_app,
        test_create_homework_list,
        test_create_simple_reminder
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"=== Results: {passed}/{total} debug tests passed ===")
    
    if passed == total:
        print("🎉 All tests passed! Sync environment is working.")
        return True
    else:
        print("❌ Some tests failed. Check permissions and macOS settings.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)