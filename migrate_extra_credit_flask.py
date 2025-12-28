#!/usr/bin/env python3
"""
Flask-based migration script to add is_extra_credit column to assignment table
"""
import os
from app import create_app
from app.models import db

def migrate_extra_credit():
    """Add is_extra_credit column to assignment table using Flask's database context."""
    
    # Set the environment to production to use the MySQL database
    os.environ['FLASK_ENV'] = 'production'
    
    app = create_app('production')
    
    with app.app_context():
        try:
            # Check if column already exists by trying to query it
            with db.engine.connect() as connection:
                result = connection.execute(db.text("SHOW COLUMNS FROM assignment LIKE 'is_extra_credit'"))
                column_exists = result.fetchone() is not None
                
                if column_exists:
                    print("✓ is_extra_credit column already exists")
                else:
                    print("Adding is_extra_credit column to assignment table...")
                    
                    # Add the column using raw SQL
                    connection.execute(db.text("""
                        ALTER TABLE assignment 
                        ADD COLUMN is_extra_credit BOOLEAN NOT NULL DEFAULT FALSE
                    """))
                    connection.commit()
                
                print("✓ is_extra_credit column added successfully!")
            
            print("Migration completed successfully!")
            return True
            
        except Exception as e:
            print(f"Error during migration: {e}")
            return False

if __name__ == '__main__':
    success = migrate_extra_credit()
    exit(0 if success else 1)