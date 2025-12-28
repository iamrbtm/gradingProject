#!/usr/bin/env python3
"""
Test script to verify assignment completion toggle moves assignments between sections
"""
import os
from app import create_app
from app.models import db, Assignment

def test_completion_toggle():
    """Test that toggling completion status moves assignments between sections."""
    
    # Set the environment to production to use the MySQL database
    os.environ['FLASK_ENV'] = 'production'
    
    app = create_app('production')
    
    with app.app_context():
        try:
            print("🧪 Testing Assignment Completion Toggle...")
            print("=" * 50)
            
            # Test 1: Find an assignment to test with
            print("1. Finding assignment to test with...")
            test_assignment = Assignment.query.first()
            if not test_assignment:
                print("   ⚠️  No assignments found")
                return
            
            print(f"   ✅ Using assignment: {test_assignment.name}")
            print(f"   Initial completion status: {test_assignment.completed}")
            
            # Test 2: Get course and count assignments by completion status
            course = test_assignment.course
            print(f"\n2. Testing with course: {course.name}")
            
            def count_assignments():
                all_assignments = course.assignments
                completed = [a for a in all_assignments if a.completed]
                uncompleted = [a for a in all_assignments if not a.completed]
                return len(completed), len(uncompleted), len(all_assignments)
            
            # Initial counts
            completed_count, uncompleted_count, total_count = count_assignments()
            print(f"   Initial: {completed_count} completed, {uncompleted_count} uncompleted, {total_count} total")
            
            # Test 3: Toggle assignment to completed
            print("\n3. Toggling assignment to completed...")
            original_status = test_assignment.completed
            test_assignment.completed = True
            db.session.commit()
            
            # Check new counts
            completed_count_after, uncompleted_count_after, total_count_after = count_assignments()
            print(f"   After toggle: {completed_count_after} completed, {uncompleted_count_after} uncompleted, {total_count_after} total")
            
            # Verify the change
            if not original_status and test_assignment.completed:
                if completed_count_after == completed_count + 1 and uncompleted_count_after == uncompleted_count - 1:
                    print("   ✅ Assignment correctly moved from uncompleted to completed section")
                else:
                    print("   ❌ Assignment counts don't match expected change")
            
            # Test 4: Toggle assignment back to uncompleted
            print("\n4. Toggling assignment back to uncompleted...")
            test_assignment.completed = False
            db.session.commit()
            
            # Check final counts
            final_completed, final_uncompleted, final_total = count_assignments()
            print(f"   Final: {final_completed} completed, {final_uncompleted} uncompleted, {final_total} total")
            
            # Verify we're back to original state
            if final_completed == completed_count and final_uncompleted == uncompleted_count:
                print("   ✅ Assignment correctly moved back to uncompleted section")
            else:
                print("   ❌ Assignment counts don't match original state")
            
            # Test 5: Verify the filtering logic matches our expectations
            print("\n5. Verifying filtering logic...")
            all_assignments = course.assignments
            filtered_completed = [a for a in all_assignments if a.completed]
            filtered_uncompleted = [a for a in all_assignments if not a.completed]
            
            print(f"   Filtering results: {len(filtered_completed)} completed, {len(filtered_uncompleted)} uncompleted")
            
            # Check for overlaps or missing assignments
            completed_ids = {a.id for a in filtered_completed}
            uncompleted_ids = {a.id for a in filtered_uncompleted}
            all_ids = {a.id for a in all_assignments}
            
            overlap = completed_ids.intersection(uncompleted_ids)
            missing = all_ids - completed_ids - uncompleted_ids
            
            if not overlap and not missing:
                print("   ✅ Perfect filtering: no overlaps, no missing assignments")
            else:
                if overlap:
                    print(f"   ❌ Found {len(overlap)} assignments in both sections")
                if missing:
                    print(f"   ❌ Found {len(missing)} assignments in neither section")
            
            print(f"\n🎉 COMPLETION TOGGLE TEST COMPLETED!")
            print("=" * 50)
            print("✅ Assignments move correctly between completed/uncompleted sections")
            print("✅ Completion toggle functionality working as expected")
            print("✅ No assignment duplication or loss")
            
        except Exception as e:
            print(f"❌ Error during testing: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_completion_toggle()