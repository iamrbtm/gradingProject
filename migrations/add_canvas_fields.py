#!/usr/bin/env python3
"""
Migration script to add Canvas integration fields to the database.
This script adds the Canvas API fields to the existing MySQL database.
"""

import pymysql
from datetime import datetime

# Database configuration
MYSQL_CONFIG = {
    'host': 'jeremyguill.com',
    'port': 3306,
    'user': 'onlymyli',
    'password': 'Braces4me##',
    'database': 'onlymyli_grades',
    'charset': 'utf8mb4'
}

def add_canvas_fields():
    """Add Canvas integration fields to existing tables."""
    try:
        connection = pymysql.connect(**MYSQL_CONFIG)
        
        with connection.cursor() as cursor:
            # Add Canvas fields to user table
            user_canvas_fields = [
                "ALTER TABLE user ADD COLUMN canvas_base_url VARCHAR(255) NULL",
                "ALTER TABLE user ADD COLUMN canvas_access_token VARCHAR(255) NULL", 
                "ALTER TABLE user ADD COLUMN canvas_last_sync DATETIME NULL"
            ]
            
            # Add Canvas fields to course table
            course_canvas_fields = [
                "ALTER TABLE course ADD COLUMN canvas_course_id VARCHAR(255) NULL",
                "ALTER TABLE course ADD COLUMN last_synced_canvas DATETIME NULL"
            ]
            
            # Add Canvas fields to assignment table
            assignment_canvas_fields = [
                "ALTER TABLE assignment ADD COLUMN canvas_assignment_id VARCHAR(255) NULL",
                "ALTER TABLE assignment ADD COLUMN canvas_course_id VARCHAR(255) NULL",
                "ALTER TABLE assignment ADD COLUMN last_synced_canvas DATETIME NULL",
                "ALTER TABLE assignment ADD COLUMN completed BOOLEAN NOT NULL DEFAULT FALSE",
                "ALTER TABLE assignment ADD COLUMN is_extra_credit BOOLEAN NOT NULL DEFAULT FALSE",
                "ALTER TABLE assignment ADD COLUMN last_synced_tasks DATETIME NULL",
                "ALTER TABLE assignment ADD COLUMN google_task_id VARCHAR(255) NULL"
            ]
            
            all_queries = user_canvas_fields + course_canvas_fields + assignment_canvas_fields
            
            for query in all_queries:
                try:
                    cursor.execute(query)
                    print(f"✅ Executed: {query}")
                except pymysql.Error as e:
                    # Column might already exist
                    if "Duplicate column name" in str(e):
                        print(f"⚠️  Column already exists: {query}")
                    else:
                        print(f"❌ Error executing {query}: {e}")
            
            # Add indexes for Canvas fields
            canvas_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_user_canvas_last_sync ON user(canvas_last_sync)",
                "CREATE INDEX IF NOT EXISTS idx_course_canvas_id ON course(canvas_course_id)",
                "CREATE INDEX IF NOT EXISTS idx_course_last_synced_canvas ON course(last_synced_canvas)",
                "CREATE INDEX IF NOT EXISTS idx_assignment_canvas_id ON assignment(canvas_assignment_id)",
                "CREATE INDEX IF NOT EXISTS idx_assignment_canvas_course ON assignment(canvas_course_id)",
                "CREATE INDEX IF NOT EXISTS idx_assignment_last_synced_canvas ON assignment(last_synced_canvas)",
                "CREATE INDEX IF NOT EXISTS idx_assignment_completed ON assignment(completed)"
            ]
            
            for index_query in canvas_indexes:
                try:
                    # MySQL doesn't support IF NOT EXISTS for indexes, so we'll handle the error
                    cursor.execute(index_query.replace("IF NOT EXISTS ", ""))
                    print(f"✅ Created index: {index_query}")
                except pymysql.Error as e:
                    if "Duplicate key name" in str(e):
                        print(f"⚠️  Index already exists: {index_query}")
                    else:
                        print(f"❌ Error creating index {index_query}: {e}")
        
        connection.commit()
        connection.close()
        print("\n✅ Canvas fields migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False

def verify_migration():
    """Verify that the Canvas fields were added successfully."""
    try:
        connection = pymysql.connect(**MYSQL_CONFIG)
        
        with connection.cursor() as cursor:
            # Check user table columns
            cursor.execute("DESCRIBE user")
            user_columns = [row[0] for row in cursor.fetchall()]
            
            # Check course table columns  
            cursor.execute("DESCRIBE course")
            course_columns = [row[0] for row in cursor.fetchall()]
            
            # Check assignment table columns
            cursor.execute("DESCRIBE assignment")
            assignment_columns = [row[0] for row in cursor.fetchall()]
            
            print("\n📋 Verification Results:")
            
            # Expected Canvas fields
            expected_user_fields = ['canvas_base_url', 'canvas_access_token', 'canvas_last_sync']
            expected_course_fields = ['canvas_course_id', 'last_synced_canvas']
            expected_assignment_fields = ['canvas_assignment_id', 'canvas_course_id', 'last_synced_canvas', 'completed', 'is_extra_credit']
            
            print("\nUser table Canvas fields:")
            for field in expected_user_fields:
                status = "✅" if field in user_columns else "❌"
                print(f"  {status} {field}")
            
            print("\nCourse table Canvas fields:")
            for field in expected_course_fields:
                status = "✅" if field in course_columns else "❌"
                print(f"  {status} {field}")
            
            print("\nAssignment table Canvas fields:")
            for field in expected_assignment_fields:
                status = "✅" if field in assignment_columns else "❌"
                print(f"  {status} {field}")
        
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        return False

def main():
    """Main migration function."""
    print("🚀 Starting Canvas fields migration...")
    print(f"📅 Migration started at: {datetime.now()}")
    
    # Step 1: Add Canvas fields
    print("\n1️⃣ Adding Canvas integration fields...")
    if not add_canvas_fields():
        print("❌ Failed to add Canvas fields")
        return False
    
    # Step 2: Verify migration
    print("\n2️⃣ Verifying migration...")
    if not verify_migration():
        print("❌ Failed to verify migration")
        return False
    
    print(f"\n🎉 Canvas migration completed successfully at {datetime.now()}!")
    print("\n📝 Next steps:")
    print("   1. Update your Canvas credentials in the settings page")
    print("   2. Test the Canvas sync functionality")
    print("   3. Create your first Canvas sync")
    
    return True

if __name__ == "__main__":
    import sys
    if main():
        sys.exit(0)
    else:
        sys.exit(1)