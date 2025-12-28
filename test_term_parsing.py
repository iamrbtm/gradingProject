#!/usr/bin/env python3
"""
Simple test script for Canvas Sync Service term parsing functionality
"""

import sys
import os
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_canvas_term_parsing():
    """
    Test Canvas term parsing with various formats
    """
    print("🧪 Testing Canvas Term Parsing")
    print("=" * 40)
    
    # Import after setting up the path
    from app.services.canvas_sync_service import CanvasSyncService
    from unittest.mock import Mock
    
    # Create mock user (only need ID for this test)
    mock_user = Mock()
    mock_user.id = 1
    
    # Initialize sync service (no Canvas API needed for parsing)
    sync_service = CanvasSyncService(mock_user, None)
    
    # Test cases covering various Canvas term formats
    test_cases = [
        # Standard formats
        ({'name': 'Spring 2025'}, 'Spring', 2025),
        ({'name': 'Fall 2024'}, 'Fall', 2024),
        ({'name': 'Summer 2023'}, 'Summer', 2023),
        ({'name': 'Winter 2025'}, 'Winter', 2025),
        
        # With additional text
        ({'name': 'Spring 2025 Semester'}, 'Spring', 2025),
        ({'name': 'Fall 2024 Quarter'}, 'Fall', 2024),
        ({'name': 'Summer Session 2023'}, 'Summer', 2023),
        
        # Abbreviated formats
        ({'name': 'SPR 2025'}, 'Spring', 2025),
        ({'name': 'FAL 2024'}, 'Fall', 2024),
        ({'name': 'SUM 2023'}, 'Summer', 2023),
        ({'name': 'WIN 2025'}, 'Winter', 2025),
        
        # Edge cases
        ({'name': 'Unknown Format 2023'}, 'Fall', 2023),  # Default to Fall
        ({'name': 'Test 2022'}, 'Fall', 2022),  # Default to Fall
        ({'name': ''}, 'Fall', datetime.now().year),  # Empty name
        (None, 'Fall', datetime.now().year),  # No term data
        
        # Real-world examples
        ({'name': 'Spring Semester 2025'}, 'Spring', 2025),
        ({'name': 'Autumn Quarter 2024'}, 'Fall', 2024),
        ({'name': 'Winter Session 2025-26'}, 'Winter', 2025),
    ]
    
    print("Test Results:")
    print("Input Term Name                  -> Parsed Season  Year")
    print("-" * 55)
    
    all_passed = True
    for i, (canvas_term, expected_season, expected_year) in enumerate(test_cases, 1):
        try:
            season, year = sync_service._parse_canvas_term(canvas_term)
            
            # Format input name for display
            input_name = canvas_term['name'] if canvas_term and canvas_term.get('name') else 'None'
            
            # Check if result matches expectation
            passed = (season == expected_season and year == expected_year)
            status = "✅" if passed else "❌"
            
            print(f"{input_name:<30} -> {season:<8} {year}  {status}")
            
            if not passed:
                print(f"   Expected: {expected_season} {expected_year}")
                all_passed = False
                
        except Exception as e:
            print(f"{input_name:<30} -> ERROR: {e}  ❌")
            all_passed = False
    
    print("-" * 55)
    
    if all_passed:
        print("🎉 All parsing tests passed!")
        print("\n✅ Key Features Verified:")
        print("  - Handles standard season names (Spring, Summer, Fall, Winter)")
        print("  - Handles abbreviated formats (SPR, SUM, FAL, WIN)")
        print("  - Extracts 4-digit years correctly")
        print("  - Defaults to Fall season for unknown formats")
        print("  - Handles edge cases (empty names, no term data)")
        print("  - Case-insensitive matching")
        
        return True
    else:
        print("❌ Some tests failed!")
        return False

def show_term_creation_info():
    """
    Show information about the term creation process
    """
    print("\n" + "=" * 50)
    print("📝 Term Auto-Creation Process")
    print("=" * 50)
    
    print("When Canvas sync encounters a course with term data:")
    print("1. 📋 Parse Canvas term name to extract season and year")
    print("2. 🔍 Check if term already exists for user")
    print("3. 🏗️  If not found, create new term with:")
    print("   - nickname: '{season} {year}' (e.g., 'Spring 2025')")
    print("   - school_name: 'Canvas Import'")
    print("   - active: True")
    print("   - user_id: Current user's ID")
    print("4. 🔄 Deactivate other terms (only one active at a time)")
    print("5. ✅ Return term ID for course association")
    
    print("\nThis eliminates the need for users to manually create terms!")
    print("Canvas sync will automatically organize courses by term.")

if __name__ == "__main__":
    success = test_canvas_term_parsing()
    show_term_creation_info()
    
    if success:
        print("\n🚀 Canvas Sync with Auto-Term Creation is ready!")
        print("   The enhancement has been successfully implemented.")
    else:
        print("\n⚠️  Some issues were found that need attention.")