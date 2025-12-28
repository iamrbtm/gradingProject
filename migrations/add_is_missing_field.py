#!/usr/bin/env python3
"""
Migration script to add is_missing field to Assignment table.
This field tracks Canvas's missing status for assignments.
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

def add_is_missing_field():
    """Add is_missing field to assignment table."""
    try:
        connection = pymysql.connect(**MYSQL_CONFIG)
        
        with connection.cursor() as cursor:
            # Add is_missing field to assignment table
            query = "ALTER TABLE assignment ADD COLUMN is_missing BOOLEAN NOT NULL DEFAULT FALSE"
            
            try:
                cursor.execute(query)
                print(f"✅ Executed: {query}")
            except pymysql.Error as e:
                # Column might already exist
                if "Duplicate column name" in str(e):
                    print(f"⚠️  Column already exists: is_missing")
                else:
                    print(f"❌ Error executing {query}: {e}")
                    raise
            
            # Add index for is_missing field for faster queries
            index_query = "CREATE INDEX idx_assignment_is_missing ON assignment(is_missing)"
            
            try:
                cursor.execute(index_query)
                print(f"✅ Created index: {index_query}")
            except pymysql.Error as e:
                if "Duplicate key name" in str(e):
                    print(f"⚠️  Index already exists: idx_assignment_is_missing")
                else:
                    print(f"❌ Error creating index {index_query}: {e}")
        
        connection.commit()
        connection.close()
        print("\n✅ is_missing field migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False

def verify_migration():
    """Verify that the is_missing field was added successfully."""
    try:
        connection = pymysql.connect(**MYSQL_CONFIG)
        
        with connection.cursor() as cursor:
            # Check assignment table columns
            cursor.execute("DESCRIBE assignment")
            assignment_columns = [row[0] for row in cursor.fetchall()]
            
            print("\n📋 Verification Results:")
            print("\nAssignment table is_missing field:")
            
            if 'is_missing' in assignment_columns:
                print("  ✅ is_missing field exists")
                
                # Get field details
                cursor.execute("SHOW COLUMNS FROM assignment WHERE Field = 'is_missing'")
                field_info = cursor.fetchone()
                print(f"     Type: {field_info[1]}")
                print(f"     Null: {field_info[2]}")
                print(f"     Default: {field_info[4]}")
            else:
                print("  ❌ is_missing field NOT found")
                return False
        
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        return False

def main():
    """Main migration function."""
    print("🚀 Starting is_missing field migration...")
    print(f"📅 Migration started at: {datetime.now()}")
    
    # Step 1: Add is_missing field
    print("\n1️⃣ Adding is_missing field to assignment table...")
    if not add_is_missing_field():
        print("❌ Failed to add is_missing field")
        return False
    
    # Step 2: Verify migration
    print("\n2️⃣ Verifying migration...")
    if not verify_migration():
        print("❌ Failed to verify migration")
        return False
    
    print(f"\n🎉 Migration completed successfully at {datetime.now()}!")
    print("\n📝 Next steps:")
    print("   1. The is_missing field will be populated on next Canvas sync")
    print("   2. Missing assignments will now use Canvas's missing flag")
    
    return True

if __name__ == "__main__":
    import sys
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
