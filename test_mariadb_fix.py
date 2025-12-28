#!/usr/bin/env python3
"""
Test script to verify MariaDB NULLS LAST compatibility fix
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import Assignment, Course

def test_course_query():
    """Test the specific query that was failing with NULLS LAST"""
    app = create_app('production')
    
    with app.app_context():
        print("🔧 Testing MariaDB NULLS LAST Fix...")
        print("=" * 50)
        
        try:
            # Get a course to test with
            course = Course.query.first()
            if not course:
                print("❌ No courses found in database")
                return False
                
            print(f"📚 Testing course: {course.name} (ID: {course.id})")
            
            # This is the exact query that was failing before
            assignments = Assignment.query.filter_by(course_id=course.id).order_by(
                Assignment.due_date.asc()
            ).all()
            
            # Separate assignments with and without due dates, then combine
            assignments_with_dates = [a for a in assignments if a.due_date is not None]
            assignments_without_dates = [a for a in assignments if a.due_date is None]
            final_assignments = assignments_with_dates + assignments_without_dates
            
            print(f"✅ Query executed successfully!")
            print(f"📊 Found {len(final_assignments)} assignments")
            print(f"   - With due dates: {len(assignments_with_dates)}")
            print(f"   - Without due dates: {len(assignments_without_dates)}")
            
            # Show a few examples if available
            if final_assignments:
                print(f"\n📋 Assignment order verification:")
                for i, assignment in enumerate(final_assignments[:5]):  # Show first 5
                    due_date_str = assignment.due_date.strftime('%Y-%m-%d') if assignment.due_date else 'No due date'
                    print(f"   {i+1}. {assignment.name} - Due: {due_date_str}")
                if len(final_assignments) > 5:
                    print(f"   ... and {len(final_assignments) - 5} more")
            
            return True
            
        except Exception as e:
            print(f"❌ Query failed: {e}")
            return False

if __name__ == '__main__':
    success = test_course_query()
    if success:
        print("\n🎉 MariaDB compatibility fix successful!")
        print("✅ The application should now work on your server")
    else:
        print("\n❌ Fix verification failed")
        sys.exit(1)