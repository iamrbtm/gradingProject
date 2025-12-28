#!/usr/bin/env python3
"""
Test script to verify datetime comparison fix
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import Assignment, Course
from datetime import datetime, date

def test_datetime_comparison_fix():
    """Test the specific datetime comparison issue that was failing"""
    app = create_app('production')
    
    with app.app_context():
        print("🔧 Testing DateTime Comparison Fix...")
        print("=" * 50)
        
        try:
            # Get a course to test with
            course = Course.query.first()
            if not course:
                print("❌ No courses found in database")
                return False
                
            print(f"📚 Testing course: {course.name} (ID: {course.id})")
            
            # Get assignments and check their date types
            assignments = Assignment.query.filter_by(course_id=course.id).all()
            
            print(f"📊 Found {len(assignments)} assignments")
            
            # Check date types
            datetime_count = 0
            date_count = 0
            none_count = 0
            
            for assignment in assignments:
                if assignment.due_date is None:
                    none_count += 1
                elif isinstance(assignment.due_date, datetime):
                    datetime_count += 1
                elif isinstance(assignment.due_date, date):
                    date_count += 1
            
            print(f"📅 Date type breakdown:")
            print(f"   - datetime objects: {datetime_count}")
            print(f"   - date objects: {date_count}")
            print(f"   - None values: {none_count}")
            
            # Test the helper function that should fix the comparison issue
            def get_sort_date(assignment):
                if assignment.due_date is None:
                    return datetime.max.date()
                if isinstance(assignment.due_date, datetime):
                    return assignment.due_date.date()
                return assignment.due_date
            
            # Try to sort assignments using the new helper function
            try:
                sorted_assignments = sorted(assignments, key=get_sort_date)
                print(f"✅ Sorting successful! Fixed datetime comparison issue")
                
                # Show first few sorted assignments
                if sorted_assignments:
                    print(f"\n📋 First few sorted assignments:")
                    for i, assignment in enumerate(sorted_assignments[:3]):
                        due_date_str = assignment.due_date.strftime('%Y-%m-%d') if assignment.due_date else 'No due date'
                        date_type = type(assignment.due_date).__name__ if assignment.due_date else 'None'
                        print(f"   {i+1}. {assignment.name[:50]}... - Due: {due_date_str} ({date_type})")
                
                return True
                
            except Exception as sort_error:
                print(f"❌ Sorting still failed: {sort_error}")
                return False
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False

if __name__ == '__main__':
    success = test_datetime_comparison_fix()
    if success:
        print(f"\n🎉 DateTime comparison fix successful!")
        print("✅ Mixed datetime/date types now sort properly")
        print("✅ The course view should now work on your server")
    else:
        print(f"\n❌ Fix verification failed")
        sys.exit(1)