#!/usr/bin/env python3
"""
Migration script to add is_submitted field to Assignment table.
This field tracks Canvas's submission status for assignments.

Business Logic:
- is_submitted: True if student has submitted the assignment (regardless of grading)
- completed: True if assignment is graded OR submitted
- This ensures submitted assignments show as "completed" even if not graded yet
"""

import pymysql
import os
from datetime import datetime
from urllib.parse import unquote
import dotenv

dotenv.load_dotenv()

def get_db_config():
    """Get database configuration from environment variable."""
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    # Parse DATABASE_URL: mysql://user:password@host:port/database
    # Example: mysql://onlymyli:Braces4me%23%23@jeremyguill.com:3306/onlymyli_grades
    
    # Remove mysql:// or mysql+pymysql:// prefix
    if database_url.startswith('mysql+pymysql://'):
        database_url = database_url[16:]  # Remove 'mysql+pymysql://'
    elif database_url.startswith('mysql://'):
        database_url = database_url[8:]  # Remove 'mysql://'
    
    # Split into user_pass and host_port_db using the LAST @ (in case password contains @)
    parts = database_url.rsplit('@', 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid DATABASE_URL format: {database_url}")
    
    user_pass = parts[0]
    host_port_db = parts[1]
    
    # Split user and password using the FIRST : (username shouldn't contain :)
    user_pass_parts = user_pass.split(':', 1)
    if len(user_pass_parts) != 2:
        raise ValueError(f"Invalid user:password format in DATABASE_URL")
    
    user = unquote(user_pass_parts[0])
    password = unquote(user_pass_parts[1])
    
    # Split host_port_db
    host_db_parts = host_port_db.split('/')
    if len(host_db_parts) != 2:
        raise ValueError(f"Invalid host/database format in DATABASE_URL")
    
    host_port = host_db_parts[0]
    database = host_db_parts[1]
    
    if ':' in host_port:
        host, port_str = host_port.split(':')
        port = int(port_str)
    else:
        host = host_port
        port = 3306
    
    return {
        'host': host,
        'port': port,
        'user': user,
        'password': password,
        'database': database,
        'charset': 'utf8mb4'
    }

def add_is_submitted_field():
    """Add is_submitted field to assignment table."""
    try:
        db_config = get_db_config()
        print(f"Connecting to database: {db_config['host']}:{db_config['port']}/{db_config['database']}")
        connection = pymysql.connect(**db_config)
        
        with connection.cursor() as cursor:
            # Add is_submitted field to assignment table
            query = "ALTER TABLE assignment ADD COLUMN is_submitted BOOLEAN NOT NULL DEFAULT FALSE"
            
            try:
                cursor.execute(query)
                print(f"✅ Executed: {query}")
            except pymysql.Error as e:
                # Column might already exist
                if "Duplicate column name" in str(e):
                    print(f"⚠️  Column already exists: is_submitted")
                else:
                    print(f"❌ Error executing {query}: {e}")
                    raise
            
            # Add index for is_submitted field for faster queries
            index_query = "CREATE INDEX idx_assignment_is_submitted ON assignment(is_submitted)"
            
            try:
                cursor.execute(index_query)
                print(f"✅ Created index: idx_assignment_is_submitted")
            except pymysql.Error as e:
                if "Duplicate key name" in str(e):
                    print(f"⚠️  Index already exists: idx_assignment_is_submitted")
                else:
                    print(f"❌ Error creating index: {e}")
        
        connection.commit()
        connection.close()
        print("\n✅ is_submitted field migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False

def verify_migration():
    """Verify that the is_submitted field was added successfully."""
    try:
        db_config = get_db_config()
        connection = pymysql.connect(**db_config)
        
        with connection.cursor() as cursor:
            # Check assignment table columns
            cursor.execute("DESCRIBE assignment")
            assignment_columns = [row[0] for row in cursor.fetchall()]
            
            print("\n📋 Verification Results:")
            print("\nAssignment table is_submitted field:")
            
            if 'is_submitted' in assignment_columns:
                print("  ✅ is_submitted field exists")
                
                # Get field details
                cursor.execute("SHOW COLUMNS FROM assignment WHERE Field = 'is_submitted'")
                field_info = cursor.fetchone()
                if field_info:
                    print(f"     Type: {field_info[1]}")
                    print(f"     Null: {field_info[2]}")
                    print(f"     Default: {field_info[4]}")
            else:
                print("  ❌ is_submitted field NOT found")
                return False
            
            # Check if index exists
            cursor.execute("SHOW INDEX FROM assignment WHERE Key_name = 'idx_assignment_is_submitted'")
            index_exists = cursor.fetchone() is not None
            
            if index_exists:
                print("  ✅ idx_assignment_is_submitted index exists")
            else:
                print("  ⚠️  idx_assignment_is_submitted index NOT found")
        
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        return False

def main():
    """Main migration function."""
    print("🚀 Starting is_submitted field migration...")
    print(f"📅 Migration started at: {datetime.now()}")
    print("\n📖 Business Logic:")
    print("   - is_submitted: Tracks if assignment is submitted (any workflow_state except 'unsubmitted')")
    print("   - completed: Will be True if assignment is submitted OR graded")
    print("   - This ensures submitted work shows as completed even before grading\n")
    
    # Step 1: Add is_submitted field
    print("1️⃣ Adding is_submitted field to assignment table...")
    if not add_is_submitted_field():
        print("❌ Failed to add is_submitted field")
        return False
    
    # Step 2: Verify migration
    print("\n2️⃣ Verifying migration...")
    if not verify_migration():
        print("❌ Failed to verify migration")
        return False
    
    print(f"\n🎉 Migration completed successfully at {datetime.now()}!")
    print("\n📝 Next steps:")
    print("   1. The is_submitted field will be populated on next Canvas sync")
    print("   2. Submitted assignments will automatically have completed=True")
    print("   3. Canvas workflow_state values handled:")
    print("      • 'unsubmitted' → is_submitted=False, completed=False")
    print("      • 'submitted' → is_submitted=True, completed=True")
    print("      • 'graded' → is_submitted=True, completed=True")
    print("      • 'pending_review' → is_submitted=True, completed=True")
    
    return True

if __name__ == "__main__":
    import sys
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
