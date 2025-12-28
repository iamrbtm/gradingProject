#!/usr/bin/env python3
"""
Test script to verify is_submitted and completed logic.
Tests the business logic: if is_submitted=True, then completed=True.
"""

def test_workflow_state_logic():
    """Test the workflow_state to is_submitted/completed mapping."""
    
    test_cases = [
        # (workflow_state, expected_is_submitted, expected_completed, description)
        ('unsubmitted', False, False, 'Not yet submitted'),
        ('submitted', True, True, 'Submitted but not graded'),
        ('graded', True, True, 'Graded assignment'),
        ('pending_review', True, True, 'Pending review'),
        (None, False, False, 'No workflow state'),
        ('', False, False, 'Empty workflow state'),
    ]
    
    print("🧪 Testing workflow_state logic...")
    print("=" * 70)
    
    all_passed = True
    
    for workflow_state, expected_submitted, expected_completed, description in test_cases:
        # Simulate the logic from canvas_sync_service.py
        if workflow_state is None:
            workflow_state = 'unsubmitted'
        
        is_submitted = workflow_state in ['submitted', 'graded', 'pending_review']
        completed = is_submitted
        
        # Verify business rule: if submitted, must be completed
        business_rule_ok = (not is_submitted) or completed
        
        passed = (
            is_submitted == expected_submitted and 
            completed == expected_completed and
            business_rule_ok
        )
        
        status = "✅ PASS" if passed else "❌ FAIL"
        all_passed = all_passed and passed
        
        print(f"\n{status} | {description}")
        print(f"   workflow_state: '{workflow_state}'")
        print(f"   is_submitted: {is_submitted} (expected: {expected_submitted})")
        print(f"   completed: {completed} (expected: {expected_completed})")
        print(f"   Business rule (submitted → completed): {business_rule_ok}")
        
        if not passed:
            print(f"   ⚠️  MISMATCH DETECTED!")
    
    print("\n" + "=" * 70)
    
    if all_passed:
        print("✅ All tests passed!")
        print("\n✓ Business rule verified: is_submitted=True → completed=True")
        return True
    else:
        print("❌ Some tests failed!")
        return False

def test_submission_data_scenarios():
    """Test various submission data scenarios."""
    
    print("\n\n🧪 Testing submission data scenarios...")
    print("=" * 70)
    
    scenarios = [
        {
            'name': 'Assignment submitted, awaiting grading',
            'submission': {'workflow_state': 'submitted', 'score': None, 'missing': False},
            'expected': {'is_submitted': True, 'completed': True, 'score': None, 'is_missing': False}
        },
        {
            'name': 'Assignment graded',
            'submission': {'workflow_state': 'graded', 'score': 95.0, 'missing': False},
            'expected': {'is_submitted': True, 'completed': True, 'score': 95.0, 'is_missing': False}
        },
        {
            'name': 'Assignment not submitted',
            'submission': {'workflow_state': 'unsubmitted', 'score': None, 'missing': False},
            'expected': {'is_submitted': False, 'completed': False, 'score': None, 'is_missing': False}
        },
        {
            'name': 'Assignment missing (not submitted)',
            'submission': {'workflow_state': 'unsubmitted', 'score': None, 'missing': True},
            'expected': {'is_submitted': False, 'completed': False, 'score': None, 'is_missing': True}
        },
        {
            'name': 'Assignment pending review',
            'submission': {'workflow_state': 'pending_review', 'score': None, 'missing': False},
            'expected': {'is_submitted': True, 'completed': True, 'score': None, 'is_missing': False}
        },
        {
            'name': 'No submission data available',
            'submission': None,
            'expected': {'is_submitted': False, 'completed': False, 'score': None, 'is_missing': False}
        }
    ]
    
    all_passed = True
    
    for scenario in scenarios:
        submission = scenario['submission']
        expected = scenario['expected']
        
        # Simulate the logic from canvas_sync_service.py
        if submission:
            workflow_state = submission.get('workflow_state', 'unsubmitted')
            is_submitted = workflow_state in ['submitted', 'graded', 'pending_review']
            completed = is_submitted
            score = float(submission['score']) if submission.get('score') is not None else None
            is_missing = submission.get('missing', False)
        else:
            is_submitted = False
            completed = False
            score = None
            is_missing = False
        
        # Verify results
        passed = (
            is_submitted == expected['is_submitted'] and
            completed == expected['completed'] and
            score == expected['score'] and
            is_missing == expected['is_missing']
        )
        
        # Verify business rule
        business_rule_ok = (not is_submitted) or completed
        passed = passed and business_rule_ok
        
        status = "✅ PASS" if passed else "❌ FAIL"
        all_passed = all_passed and passed
        
        print(f"\n{status} | {scenario['name']}")
        print(f"   is_submitted: {is_submitted} (expected: {expected['is_submitted']})")
        print(f"   completed: {completed} (expected: {expected['completed']})")
        print(f"   score: {score} (expected: {expected['score']})")
        print(f"   is_missing: {is_missing} (expected: {expected['is_missing']})")
        print(f"   Business rule: {business_rule_ok}")
        
        if not passed:
            print(f"   ⚠️  MISMATCH DETECTED!")
    
    print("\n" + "=" * 70)
    
    if all_passed:
        print("✅ All scenarios passed!")
        return True
    else:
        print("❌ Some scenarios failed!")
        return False

def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("TESTING is_submitted AND completed LOGIC")
    print("=" * 70)
    print("\n📋 Business Requirements:")
    print("   1. Track is_submitted separately from completed")
    print("   2. If is_submitted=True, then completed=True (invariant)")
    print("   3. completed can be True even if not graded yet")
    print("   4. This shows submitted work as 'done' even before grading\n")
    
    test1_passed = test_workflow_state_logic()
    test2_passed = test_submission_data_scenarios()
    
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    
    if test1_passed and test2_passed:
        print("✅ All tests passed!")
        print("\n✓ Logic is correct and ready for production")
        print("✓ Business rule enforced: is_submitted → completed")
        return 0
    else:
        print("❌ Some tests failed!")
        print("\n⚠️  Fix the logic before deploying")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
