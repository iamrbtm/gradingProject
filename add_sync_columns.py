#!/usr/bin/env python3
"""
Script to add sync status columns to the user table
"""

import os
from dotenv import load_dotenv
load_dotenv()

from app import create_app

def add_sync_columns():
    """Add sync status columns to user table"""
    app = create_app()

    with app.app_context():
        from app.models import db

        # Check if columns already exist
        inspector = db.inspect(db.engine)
        columns = inspector.get_columns('user')
        column_names = [col['name'] for col in columns]

        if 'canvas_last_sync_courses' not in column_names:
            print("Adding canvas_last_sync_courses column...")
            db.engine.execute(db.text("ALTER TABLE user ADD COLUMN canvas_last_sync_courses INTEGER DEFAULT 0"))

        if 'canvas_last_sync_assignments' not in column_names:
            print("Adding canvas_last_sync_assignments column...")
            db.engine.execute(db.text("ALTER TABLE user ADD COLUMN canvas_last_sync_assignments INTEGER DEFAULT 0"))

        if 'canvas_last_sync_categories' not in column_names:
            print("Adding canvas_last_sync_categories column...")
            db.engine.execute(db.text("ALTER TABLE user ADD COLUMN canvas_last_sync_categories INTEGER DEFAULT 0"))

        if 'canvas_sync_status' not in column_names:
            print("Adding canvas_sync_status column...")
            db.engine.execute(db.text("ALTER TABLE user ADD COLUMN canvas_sync_status VARCHAR(50) DEFAULT 'idle'"))

        print("Sync status columns added successfully!")

if __name__ == '__main__':
    add_sync_columns()