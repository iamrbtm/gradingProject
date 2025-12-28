#!/usr/bin/env python3
"""
Add is_extra_credit column to assignment table using Flask app context
"""
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db
from sqlalchemy import text

def add_extra_credit_column():
    app = create_app()
    
    with app.app_context():
        try:
            # Check if column exists
            result = db.engine.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'assignment' 
                AND COLUMN_NAME = 'is_extra_credit'
            """))
            
            if result.fetchone():
                print("✓ is_extra_credit column already exists")
            else:
                print("Adding is_extra_credit column to assignment table...")
                
                # Add the column
                db.engine.execute(text("""
                    ALTER TABLE assignment 
                    ADD COLUMN is_extra_credit BOOLEAN NOT NULL DEFAULT FALSE
                """))
                
                print("✓ is_extra_credit column added successfully!")
            
            print("Migration completed successfully!")
            return True
            
        except Exception as e:
            print(f"Error during migration: {e}")
            return False

if __name__ == '__main__':
    add_extra_credit_column()