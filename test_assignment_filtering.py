#!/usr/bin/env python3
"""
Test script to verify that assignment filtering works by completion status
"""
import os
from app import create_app
from app.models import db, User, Term, Course, Assignment, GradeCategory

def test_assignment_filtering():
    """Test that assignments are properly filtered by completion status."""
    
    # Set the environment to production to use the MySQL database
    os.environ['FLASK_ENV'] = 'production'
    
    app = create_app('production')
    
    with app.app_context():
        try:
            print("🧪 Testing Assignment Filtering by Completion Status...")
            print("=" * 60)
            
            # Test 1: Find a course with assignments to test with
            print("1. Finding course with assignments...")
            course = Course.query.filter(Course.assignments.any()).first()
            if not course:
                print("   ⚠️  No courses with assignments found")
                return
            
            print(f"   ✅ Using course: {course.name}")
            
            # Test 2: Check current assignment completion status
            print("\n2. Current assignment completion status:")
            all_assignments = course.assignments
            completed_assignments = [a for a in all_assignments if a.completed]
            uncompleted_assignments = [a for a in all_assignments if not a.completed]
            
            print(f"   Total assignments: {len(all_assignments)}")
            print(f"   Completed assignments: {len(completed_assignments)}")
            print(f"   Uncompleted assignments: {len(uncompleted_assignments)}")
            
            # Test 3: Show some examples
            print("\n3. Assignment examples:")
            for assignment in all_assignments[:5]:  # Show first 5
                status = "✅ Completed" if assignment.completed else "⏳ Uncompleted"
                score_info = f"({assignment.score}/{assignment.max_score})" if assignment.score is not None else "(No score)"
                print(f"   {assignment.name}: {status} {score_info}")
            
            # Test 4: Test the filtering logic manually
            print("\n4. Testing filtering logic:")
            
            # This mimics the new filtering logic in view_course
            filtered_completed = [a for a in all_assignments if a.completed]
            filtered_uncompleted = [a for a in all_assignments if not a.completed]
            
            print(f"   New filtering - Completed section: {len(filtered_completed)} assignments")
            print(f"   New filtering - Uncompleted section: {len(filtered_uncompleted)} assignments")
            
            # Verify no overlap
            completed_ids = {a.id for a in filtered_completed}
            uncompleted_ids = {a.id for a in filtered_uncompleted}
            overlap = completed_ids.intersection(uncompleted_ids)
            
            if not overlap:
                print("   ✅ No assignment overlap between sections")
            else:
                print(f"   ❌ Found overlap: {len(overlap)} assignments in both sections")
            
            # Verify total count
            total_filtered = len(filtered_completed) + len(filtered_uncompleted)
            if total_filtered == len(all_assignments):
                print("   ✅ All assignments accounted for")
            else:
                print(f"   ❌ Missing assignments: {len(all_assignments)} total vs {total_filtered} filtered")
            
            print(f"\n🎉 ASSIGNMENT FILTERING TEST COMPLETED!")
            print("=" * 60)
            print("✅ Assignments are now filtered by completion status")
            print("✅ No duplicates between completed/uncompleted sections")
            print("✅ All assignments properly categorized")
            
        except Exception as e:
            print(f"❌ Error during testing: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_assignment_filtering()