#!/usr/bin/env python3
"""
MySQL migration script to add is_extra_credit column to assignment table
"""
import pymysql
import os
from urllib.parse import urlparse

def add_extra_credit_column():
    # Parse the database URL
    database_url = os.environ.get('DATABASE_URL', 'mysql+pymysql://onlymyli:Braces4me%23%23@jeremyguill.com:3306/onlymyli_grades')
    
    # Remove the mysql+pymysql:// prefix for pymysql
    if database_url.startswith('mysql+pymysql://'):
        database_url = database_url.replace('mysql+pymysql://', 'mysql://')
    
    parsed = urlparse(database_url)
    
    try:
        # Connect to MySQL database
        connection = pymysql.connect(
            host=parsed.hostname,
            port=parsed.port or 3306,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip('/'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        print("Connected to MySQL database successfully!")
        
        with connection.cursor() as cursor:
            # Check if column already exists
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'assignment' 
                AND COLUMN_NAME = 'is_extra_credit'
            """, (parsed.path.lstrip('/'),))
            
            if cursor.fetchone():
                print("✓ is_extra_credit column already exists")
            else:
                print("Adding is_extra_credit column to assignment table...")
                
                # Add the column
                cursor.execute("""
                    ALTER TABLE assignment 
                    ADD COLUMN is_extra_credit BOOLEAN NOT NULL DEFAULT FALSE
                """)
                
                print("✓ is_extra_credit column added successfully!")
            
            # Commit the changes
            connection.commit()
            print("Migration completed successfully!")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        return False
    
    finally:
        if 'connection' in locals():
            connection.close()
    
    return True

if __name__ == '__main__':
    add_extra_credit_column()