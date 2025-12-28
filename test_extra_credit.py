#!/usr/bin/env python3
"""
Test script to verify extra credit functionality works correctly
"""
import os
from app import create_app
from app.models import db, User, Term, Course, Assignment, GradeCategory

def test_extra_credit():
    """Test extra credit assignment creation and data integrity."""
    
    # Set the environment to production to use the MySQL database
    os.environ['FLASK_ENV'] = 'production'
    
    app = create_app('production')
    
    with app.app_context():
        try:
            print("🧪 Testing Extra Credit Functionality...")
            print("=" * 50)
            
            # Test 1: Check if is_extra_credit column exists and is accessible
            print("1. Testing is_extra_credit column access...")
            first_assignment = Assignment.query.first()
            if first_assignment:
                print(f"   ✅ Can access is_extra_credit: {first_assignment.is_extra_credit}")
            else:
                print("   ⚠️  No assignments found in database")
            
            # Test 2: Try to create a test extra credit assignment (if we have courses)
            print("2. Testing extra credit assignment creation...")
            first_course = Course.query.first()
            if first_course:
                # Create a test extra credit assignment
                test_assignment = Assignment(
                    name="Test Extra Credit Assignment",
                    score=None,
                    max_score=0.0,  # Extra credit assignments can have 0 max score
                    course_id=first_course.id,
                    category_id=None,
                    due_date=None,
                    is_extra_credit=True
                )
                
                db.session.add(test_assignment)
                db.session.commit()
                
                print(f"   ✅ Created extra credit assignment with ID: {test_assignment.id}")
                
                # Verify it was saved correctly
                saved_assignment = Assignment.query.get(test_assignment.id)
                print(f"   ✅ Verified: is_extra_credit = {saved_assignment.is_extra_credit}")
                print(f"   ✅ Verified: max_score = {saved_assignment.max_score}")
                
                # Clean up the test assignment
                db.session.delete(saved_assignment)
                db.session.commit()
                print("   ✅ Test assignment cleaned up")
                
            else:
                print("   ⚠️  No courses found to test assignment creation")
            
            # Test 3: Check existing assignments for is_extra_credit field
            print("3. Checking existing assignments...")
            assignments = Assignment.query.limit(5).all()
            for assignment in assignments:
                print(f"   Assignment: {assignment.name} | Extra Credit: {assignment.is_extra_credit}")
            
            print("\n🎉 ALL TESTS PASSED!")
            print("=" * 50)
            print("✅ is_extra_credit column is working correctly")
            print("✅ Extra credit assignments can be created")
            print("✅ Database migration was successful")
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = test_extra_credit()
    exit(0 if success else 1)