#!/usr/bin/env python3
"""
Database migration script to ensure the audit_log table exists with all required columns.

This script ensures the audit_log table and its columns exist, which might be missing 
in the production database.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def get_database_url():
    """Get the database URL from the Flask app config."""
    try:
        from app import create_app
        app = create_app()
        with app.app_context():
            return app.config['SQLALCHEMY_DATABASE_URI']
    except Exception as e:
        print(f"Could not get database URL from app config: {e}")
        return None

def ensure_audit_log_table():
    """Ensure the audit_log table exists with all required columns."""
    database_url = get_database_url()
    if not database_url:
        print("Error: Could not determine database URL")
        return False
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        # Check if audit_log table exists
        with engine.connect() as conn:
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM audit_log LIMIT 1"))
                print("audit_log table exists")
            except OperationalError as e:
                if "doesn't exist" in str(e) or "no such table" in str(e):
                    print("audit_log table does not exist. Creating it now...")
                    create_audit_log_table(conn, database_url)
                else:
                    print(f"Unexpected error checking audit_log table: {e}")
                    return False
        
        # Check and add missing columns
        ensure_audit_log_columns(engine, database_url)
        
        return True
        
    except Exception as e:
        print(f"Error ensuring audit_log table: {e}")
        return False

def create_audit_log_table(conn, database_url):
    """Create the audit_log table."""
    if 'mysql' in database_url.lower() or 'pymysql' in database_url.lower():
        # MySQL syntax
        sql = """
        CREATE TABLE audit_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            assignment_id INT NOT NULL,
            assignment_name VARCHAR(200) NOT NULL,
            course_id INT NOT NULL,
            action VARCHAR(100) NOT NULL,
            old_value VARCHAR(500),
            new_value VARCHAR(500),
            field_changed VARCHAR(50) NOT NULL,
            timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (assignment_id) REFERENCES assignment(id),
            FOREIGN KEY (course_id) REFERENCES course(id)
        )
        """
    else:
        # SQLite syntax
        sql = """
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL,
            assignment_name VARCHAR(200) NOT NULL,
            course_id INTEGER NOT NULL,
            action VARCHAR(100) NOT NULL,
            old_value VARCHAR(500),
            new_value VARCHAR(500),
            field_changed VARCHAR(50) NOT NULL,
            timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (assignment_id) REFERENCES assignment(id),
            FOREIGN KEY (course_id) REFERENCES course(id)
        )
        """
    
    print(f"Creating audit_log table...")
    conn.execute(text(sql))
    conn.commit()
    print("Successfully created audit_log table.")

def ensure_audit_log_columns(engine, database_url):
    """Ensure all required columns exist in the audit_log table."""
    required_columns = [
        ('id', 'INT'),
        ('assignment_id', 'INT'),
        ('assignment_name', 'VARCHAR(200)'),
        ('course_id', 'INT'),
        ('action', 'VARCHAR(100)'),
        ('old_value', 'VARCHAR(500)'),
        ('new_value', 'VARCHAR(500)'),
        ('field_changed', 'VARCHAR(50)'),
        ('timestamp', 'DATETIME')
    ]
    
    with engine.connect() as conn:
        for col_name, col_type in required_columns:
            try:
                # Try to select the column
                conn.execute(text(f"SELECT {col_name} FROM audit_log LIMIT 1"))
                print(f"Column '{col_name}' exists")
            except OperationalError as e:
                if "Unknown column" in str(e) or "no such column" in str(e):
                    print(f"Adding missing column '{col_name}'...")
                    if 'mysql' in database_url.lower() or 'pymysql' in database_url.lower():
                        if col_name == 'timestamp':
                            sql = f"ALTER TABLE audit_log ADD COLUMN {col_name} {col_type} NOT NULL DEFAULT CURRENT_TIMESTAMP"
                        else:
                            sql = f"ALTER TABLE audit_log ADD COLUMN {col_name} {col_type}"
                    else:
                        if col_name == 'timestamp':
                            sql = f"ALTER TABLE audit_log ADD COLUMN {col_name} {col_type} NOT NULL DEFAULT CURRENT_TIMESTAMP"
                        else:
                            sql = f"ALTER TABLE audit_log ADD COLUMN {col_name} {col_type}"
                    
                    conn.execute(text(sql))
                    conn.commit()
                    print(f"Successfully added column '{col_name}'")

if __name__ == "__main__":
    print("Starting audit_log table migration...")
    success = ensure_audit_log_table()
    if success:
        print("Audit log table migration completed successfully!")
        sys.exit(0)
    else:
        print("Audit log table migration failed!")
        sys.exit(1)