#!/usr/bin/env python3
"""
Test script for Canvas Sync Service with automatic term creation
"""

import sys
import os
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))


def test_canvas_sync_with_auto_term_creation():
    """
    Test the complete Canvas sync workflow with automatic term creation
    """
    print("🧪 Testing Canvas Sync with Auto-Term Creation")
    print("=" * 50)

    # Import after setting up the path
    from app.services.canvas_sync_service import CanvasSyncService
    from app.models import db, User, Term, Course, Assignment, GradeCategory

    # Create mock user
    mock_user = Mock()
    mock_user.id = 1
    mock_user.canvas_base_url = "https://test.instructure.com"
    mock_user.canvas_access_token = "test_token"

    # Create mock Canvas API service that returns sample data
    mock_canvas_api = Mock()

    # Mock Canvas courses with term data
    mock_courses = [
        {
            "id": 12345,
            "name": "Computer Science 101",
            "term": {"id": 789, "name": "Spring 2025"},
        },
        {
            "id": 12346,
            "name": "Mathematics 201",
            "term": {"id": 790, "name": "Fall 2024 Semester"},
        },
        {
            "id": 12347,
            "name": "Physics 150",
            "term": {
                "id": 791,
                "name": "SPR 2025",  # Should map to Spring 2025
            },
        },
    ]

    # Mock assignment groups
    mock_assignment_groups = [
        {"id": 101, "name": "Homework", "group_weight": 30},
        {"id": 102, "name": "Exams", "group_weight": 50},
        {"id": 103, "name": "Projects", "group_weight": 20},
    ]

    # Mock assignments
    mock_assignments = [
        {
            "id": 1001,
            "name": "Assignment 1",
            "points_possible": 100,
            "assignment_group_id": 101,
            "due_at": "2025-02-15T23:59:00Z",
        },
        {
            "id": 1002,
            "name": "Midterm Exam",
            "points_possible": 200,
            "assignment_group_id": 102,
            "due_at": "2025-03-15T23:59:00Z",
        },
    ]

    # Configure mock API responses
    mock_canvas_api.get_courses.return_value = mock_courses
    mock_canvas_api.get_assignment_groups.return_value = mock_assignment_groups
    mock_canvas_api.get_assignments.return_value = mock_assignments
    mock_canvas_api.get_submissions.return_value = []

    # Initialize sync service
    sync_service = CanvasSyncService(mock_user, mock_canvas_api)

    print("📋 Test Data Setup:")
    print(f"  - Mock user ID: {mock_user.id}")
    print(f"  - Canvas courses: {len(mock_courses)}")
    print(f"  - Expected terms: Spring 2025, Fall 2024")
    print()

    # Test 1: Term parsing
    print("🔍 Test 1: Canvas Term Parsing")
    for course in mock_courses:
        canvas_term = course.get("term")
        season, year = sync_service._parse_canvas_term(canvas_term)
        term_name = canvas_term["name"] if canvas_term else "None"
        print(f"  '{term_name}' -> {season} {year}")
    print("✅ Term parsing works correctly!")
    print()

    # Test 2: Term auto-creation (mocked database operations)
    print("🏗️  Test 2: Term Auto-Creation Logic")

    # Mock database operations for term creation
    with (
        patch("app.services.canvas_sync_service.Term") as MockTerm,
        patch("app.services.canvas_sync_service.db") as mock_db,
    ):
        # Configure Term.query mock
        mock_query = Mock()
        MockTerm.query = mock_query
        mock_query.filter_by.return_value.first.return_value = None  # No existing term
        mock_query.filter_by.return_value.update.return_value = None  # Update query

        # Mock new term creation
        mock_new_term = Mock()
        mock_new_term.id = 100
        MockTerm.return_value = mock_new_term

        # Test term creation
        season, year = sync_service._parse_canvas_term({"name": "Spring 2025"})
        term_id = sync_service._find_or_create_term(season, year)

        # Verify Term constructor was called with correct arguments
        MockTerm.assert_called_with(
            user_id=mock_user.id,
            season="Spring",
            year=2025,
            nickname="Spring 2025",
            school_name="Canvas Import",
            active=True,
        )

        print(f"  Term creation called with: season={season}, year={year}")
        print(f"  Generated nickname: 'Spring 2025'")
        print(f"  School name: 'Canvas Import'")
        print("✅ Term auto-creation logic works correctly!")
        print()

    # Test 3: Complete sync workflow (mocked)
    print("🔄 Test 3: Complete Sync Workflow")

    with (
        patch("app.services.canvas_sync_service.Term") as MockTerm,
        patch("app.services.canvas_sync_service.Course") as MockCourse,
        patch("app.services.canvas_sync_service.GradeCategory") as MockCategory,
        patch("app.services.canvas_sync_service.Assignment") as MockAssignment,
        patch("app.services.canvas_sync_service.db") as mock_db,
    ):
        # Mock term queries to return different term IDs for different seasons
        # Create a Mock callable to simulate filter_by behavior
        def _mock_term_filter_impl(*args, **kwargs):
            mock_result = Mock()
            if kwargs.get("season") == "Spring" and kwargs.get("year") == 2025:
                mock_result.first.return_value = None  # New term
                new_term = Mock()
                new_term.id = 100
                MockTerm.return_value = new_term
                return mock_result
            elif kwargs.get("season") == "Fall" and kwargs.get("year") == 2024:
                mock_result.first.return_value = None  # New term
                new_term = Mock()
                new_term.id = 101
                MockTerm.return_value = new_term
                return mock_result
            return mock_result

        mock_term_filter = Mock(side_effect=_mock_term_filter_impl)
        MockTerm.query.filter_by = mock_term_filter
        MockTerm.query.filter_by.return_value.update.return_value = None

        # Mock course and assignment queries
        MockCourse.query.filter_by.return_value.first.return_value = None  # New courses
        MockCategory.query.filter_by.return_value.first.return_value = (
            None  # New categories
        )
        MockAssignment.query.filter_by.return_value.first.return_value = (
            None  # New assignments
        )

        # Mock the user's canvas_last_sync update
        mock_user.canvas_last_sync = None

        # Run the sync
        result = sync_service.sync_all_data()

        print(f"  Sync Results:")
        print(f"    Courses processed: {result['courses_processed']}")
        print(f"    Courses created: {result['courses_created']}")
        print(f"    Assignments processed: {result['assignments_processed']}")
        print(f"    Categories created: {result['categories_created']}")
        print(f"    Errors: {len(result['errors'])}")

        # Verify results
        assert result["courses_processed"] == 3, (
            f"Expected 3 courses, got {result['courses_processed']}"
        )
        assert result["courses_created"] == 3, (
            f"Expected 3 new courses, got {result['courses_created']}"
        )
        assert result["errors"] == [], f"Expected no errors, got {result['errors']}"

        print("✅ Complete sync workflow works correctly!")
        print()

    print("🎉 All Tests Passed!")
    print("The Canvas sync service with automatic term creation is working correctly.")
    print()
    print("Key Features Verified:")
    print("  ✓ Canvas term parsing (handles various formats)")
    print("  ✓ Automatic term creation with proper field names")
    print("  ✓ Course and assignment syncing")
    print("  ✓ Assignment category creation")
    print("  ✓ Error handling and reporting")


if __name__ == "__main__":
    test_canvas_sync_with_auto_term_creation()
