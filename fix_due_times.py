#!/usr/bin/env python3
"""
Fix due times in reminders_sync.py to be 11:59 PM instead of midnight.
"""

import re

def fix_due_times():
    """Fix the due time formatting in reminders_sync.py"""
    
    # Read the current file
    with open('/Users/rbtm2006/Downloads/gradingProject/app/reminders_sync.py', 'r') as f:
        content = f.read()
    
    # Fix the _create_reminder_pure method
    pattern1 = r"(\s+)# Adjust due date to 11:59 PM if it exists\n(\s+)due_date_adjusted = None\n(\s+)if assignment\.due_date:\n(\s+)from datetime import datetime, time\n(\s+)due_date_adjusted = datetime\.combine\(assignment\.due_date\.date\(\), time\(23, 59, 59\)\)\n(\s+)\n(\s+)data = \{\n(\s+)'assignment_id': assignment\.id,\n(\s+)'name': assignment\.name,\n(\s+)'course_name': assignment\.course\.name,\n(\s+)'max_score': assignment\.max_score,\n(\s+)'due_date': due_date_adjusted,"
    
    # Fix the AppleScript date formatting in _create_reminder_pure
    old_pattern = r"set dueDateValue to \(date \"' \+ data\['due_date'\]\.strftime\('%m/%d/%Y'\) \+ '\"\)"
    new_pattern = r"set dueDateValue to (date \"' + data['due_date'].strftime('%m/%d/%Y %I:%M:%S %p') + '\")"
    
    if old_pattern in content:
        content = content.replace(old_pattern, new_pattern)
        print("Fixed AppleScript date formatting in _create_reminder_pure")
    
    # Also fix in _update_reminder_pure if it exists
    old_pattern2 = r"set dueDateValue to \(date \"' \+ data\['due_date'\]\.strftime\('%m/%d/%Y'\) \+ '\"\)"
    if old_pattern2 in content:
        content = content.replace(old_pattern2, new_pattern)
        print("Fixed AppleScript date formatting in _update_reminder_pure")
    
    # Write the fixed content
    with open('/Users/rbtm2006/Downloads/gradingProject/app/reminders_sync.py', 'w') as f:
        f.write(content)
    
    print("Due time fixes applied successfully!")

if __name__ == '__main__':
    fix_due_times()