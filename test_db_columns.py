#!/usr/bin/env python3
"""
Test script to add database columns
"""

import os
from dotenv import load_dotenv
load_dotenv()

# Mock the flask_limiter module
import sys
from unittest.mock import MagicMock
sys.modules['flask_limiter'] = MagicMock()

from app import create_app

def test_db():
    """Test database operations"""
    app = create_app()

    with app.app_context():
        from app.models import db

        # Create all tables (should add new columns)
        db.create_all()
        print("Database tables created/updated")

        # Check if columns exist
        inspector = db.inspect(db.engine)
        columns = inspector.get_columns('user')
        column_names = [col['name'] for col in columns]
        print(f"User table columns: {column_names}")

        # Check for our new columns
        new_columns = ['canvas_last_sync_courses', 'canvas_last_sync_assignments', 'canvas_last_sync_categories', 'canvas_sync_status']
        for col in new_columns:
            if col in column_names:
                print(f"✓ Column {col} exists")
            else:
                print(f"✗ Column {col} missing")

if __name__ == '__main__':
    test_db()