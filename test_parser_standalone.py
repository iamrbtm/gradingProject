#!/usr/bin/env python3
"""
Standalone Canvas Parser Test - doesn't require Flask app initialization
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the parser directly
from app.utils.canvas_parser import parse_canvas_grades, validate_canvas_data

def test_canvas_parser():
    # Read test data
    with open('test_canvas_data.txt', 'r') as f:
        canvas_data = f.read()
    
    print("Canvas Parser Test")
    print("=" * 50)
    print(f"Input data length: {len(canvas_data)} characters")
    print()
    
    try:
        # Parse the data
        df = parse_canvas_grades(canvas_data, year_hint=2024)
        
        print(f"✅ Successfully parsed {len(df)} assignments")
        print()
        
        # Show parsed assignments
        print("Parsed Assignments:")
        print("-" * 30)
        for i in range(len(df)):
            row = df.iloc[i]
            name = row['name']
            score = row['score']
            max_score = row['max_score']
            category = row['category']
            due_date = row['due_date']
            
            score_str = f"{score}/{max_score}" if score is not None and max_score is not None else f"-/{max_score}" if max_score is not None else "No score"
            due_str = str(due_date) if due_date is not None else "No due date"
            
            print(f"{i+1:2d}. {str(name)[:50]:<50} | {score_str:<10} | {str(category):<15} | {due_str}")
        
        print()
        
        # Validate data
        validation = validate_canvas_data(df)
        print("Validation Results:")
        print("-" * 30)
        print(f"Total assignments: {validation['total_assignments']}")
        print(f"Valid assignments: {validation['valid_assignments']}")
        print(f"Missing due dates: {len(validation['missing_due_dates'])}")
        print(f"Missing max scores: {len(validation['missing_max_scores'])}")
        print(f"Is complete: {validation['is_complete']}")
        
        # Calculate success rates
        due_date_success = (len(df) - len(validation['missing_due_dates'])) / len(df) * 100 if len(df) > 0 else 0
        max_score_success = (len(df) - len(validation['missing_max_scores'])) / len(df) * 100 if len(df) > 0 else 0
        
        print()
        print("Success Rates:")
        print("-" * 30)
        print(f"Due date parsing: {due_date_success:.1f}%")
        print(f"Max score parsing: {max_score_success:.1f}%")
        
        if validation['issues']:
            print()
            print("Issues found:")
            for issue in validation['issues'][:5]:  # Show first 5 issues
                print(f"  - {issue}")
            if len(validation['issues']) > 5:
                print(f"  ... and {len(validation['issues']) - 5} more")
        
    except Exception as e:
        print(f"❌ Parser failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_canvas_parser()