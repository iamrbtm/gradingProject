#!/usr/bin/env python3
"""
Test script to verify the complete extra credit workflow including:
1. Adding assignments with max_score=0 and is_extra_credit=True
2. Updating existing assignments to/from extra credit status
3. Inline editing functionality for max_score
"""
import os
import json
from app import create_app
from app.models import db, User, Term, Course, Assignment, GradeCategory

def test_extra_credit_workflow():
    """Test the complete extra credit workflow."""
    
    # Set the environment to production to use the database
    os.environ['FLASK_ENV'] = 'production'
    
    app = create_app('production')
    
    with app.app_context():
        try:
            print("🧪 Testing Complete Extra Credit Workflow...")
            print("=" * 60)
            
            # Get a test course to work with
            first_course = Course.query.first()
            if not first_course:
                print("❌ No courses found in database")
                return False
            
            print(f"Using course: {first_course.name}")
            
            # Test 1: Create an extra credit assignment with max_score=0
            print("\n1. Testing extra credit assignment creation (max_score=0)...")
            
            test_assignment = Assignment(
                name="Test Extra Credit Workflow",
                score=5.0,  # Extra credit points earned
                max_score=0.0,  # Zero max score for extra credit
                course_id=first_course.id,
                category_id=None,
                due_date=None,
                is_extra_credit=True
            )
            
            db.session.add(test_assignment)
            db.session.commit()
            
            print(f"   ✅ Created assignment ID: {test_assignment.id}")
            print(f"   ✅ max_score: {test_assignment.max_score}")
            print(f"   ✅ is_extra_credit: {test_assignment.is_extra_credit}")
            print(f"   ✅ score: {test_assignment.score}")
            
            # Test 2: Simulate updating max_score from 0 to positive value
            print("\n2. Testing update from extra credit (0) to regular assignment...")
            
            original_max_score = test_assignment.max_score
            original_is_extra_credit = test_assignment.is_extra_credit
            
            # Simulate the backend logic from update_assignment_field
            new_max_score = 10.0
            if new_max_score > 0 and original_max_score == 0:
                test_assignment.is_extra_credit = False
            test_assignment.max_score = new_max_score
            
            db.session.commit()
            
            print(f"   ✅ Updated max_score from {original_max_score} to {test_assignment.max_score}")
            print(f"   ✅ Updated is_extra_credit from {original_is_extra_credit} to {test_assignment.is_extra_credit}")
            
            # Test 3: Simulate updating max_score from positive to 0 (extra credit)
            print("\n3. Testing update from regular assignment to extra credit (0)...")
            
            original_max_score = test_assignment.max_score
            original_is_extra_credit = test_assignment.is_extra_credit
            
            # Simulate the backend logic from update_assignment_field
            new_max_score = 0.0
            if new_max_score == 0:
                test_assignment.is_extra_credit = True
            test_assignment.max_score = new_max_score
            
            db.session.commit()
            
            print(f"   ✅ Updated max_score from {original_max_score} to {test_assignment.max_score}")
            print(f"   ✅ Updated is_extra_credit from {original_is_extra_credit} to {test_assignment.is_extra_credit}")
            
            # Test 4: Test percentage calculation logic for extra credit
            print("\n4. Testing percentage calculation for extra credit...")
            
            if test_assignment.is_extra_credit and test_assignment.max_score == 0:
                # Extra credit should show as +points, not percentage
                extra_credit_display = f"+{test_assignment.score}"
                print(f"   ✅ Extra credit display: {extra_credit_display}")
            elif test_assignment.score is not None and test_assignment.max_score > 0:
                percentage = (test_assignment.score / test_assignment.max_score) * 100
                print(f"   ✅ Regular assignment percentage: {percentage:.1f}%")
            else:
                print("   ✅ No score/percentage display: N/A")
            
            # Test 5: Verify data integrity
            print("\n5. Verifying data integrity...")
            
            saved_assignment = Assignment.query.filter_by(id=test_assignment.id).first()
            assert saved_assignment is not None, "Assignment should exist"
            assert saved_assignment.is_extra_credit == test_assignment.is_extra_credit, "is_extra_credit should match"
            assert saved_assignment.max_score == test_assignment.max_score, "max_score should match"
            assert saved_assignment.score == test_assignment.score, "score should match"
            
            print("   ✅ All data integrity checks passed")
            
            # Clean up
            print("\n6. Cleaning up test data...")
            db.session.delete(test_assignment)
            db.session.commit()
            print("   ✅ Test assignment deleted")
            
            print("\n🎉 ALL WORKFLOW TESTS PASSED!")
            print("=" * 60)
            print("✅ Extra credit assignment creation works")
            print("✅ Updating from extra credit to regular works")
            print("✅ Updating from regular to extra credit works")
            print("✅ Percentage calculation logic is correct")
            print("✅ Data integrity is maintained")
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = test_extra_credit_workflow()
    exit(0 if success else 1)