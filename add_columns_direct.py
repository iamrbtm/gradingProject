#!/usr/bin/env python3
"""
Direct script to add database columns
"""

import pymysql
import os
from dotenv import load_dotenv
load_dotenv()

def add_columns():
    """Add sync status columns directly to database"""

    # Get database connection details from DATABASE_URL
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("DATABASE_URL not found")
        return

    # Parse the MySQL URL
    # mysql+pymysql://user:pass@host:port/db
    url_parts = database_url.replace('mysql+pymysql://', '').split('@')
    user_pass = url_parts[0].split(':')
    host_port_db = url_parts[1].split('/')

    user = user_pass[0]
    password = user_pass[1]
    host_port = host_port_db[0].split(':')
    host = host_port[0]
    port = int(host_port[1])
    db_name = host_port_db[1]

    try:
        # Connect to database
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=db_name
        )

        with conn.cursor() as cursor:
            # Check existing columns
            cursor.execute("DESCRIBE user")
            columns = cursor.fetchall()
            column_names = [col[0] for col in columns]
            print(f"Existing columns: {column_names}")

            # Add missing columns
            if 'canvas_last_sync_courses' not in column_names:
                cursor.execute("ALTER TABLE user ADD COLUMN canvas_last_sync_courses INTEGER DEFAULT 0")
                print("Added canvas_last_sync_courses")

            if 'canvas_last_sync_assignments' not in column_names:
                cursor.execute("ALTER TABLE user ADD COLUMN canvas_last_sync_assignments INTEGER DEFAULT 0")
                print("Added canvas_last_sync_assignments")

            if 'canvas_last_sync_categories' not in column_names:
                cursor.execute("ALTER TABLE user ADD COLUMN canvas_last_sync_categories INTEGER DEFAULT 0")
                print("Added canvas_last_sync_categories")

            if 'canvas_sync_status' not in column_names:
                cursor.execute("ALTER TABLE user ADD COLUMN canvas_sync_status VARCHAR(50) DEFAULT 'idle'")
                print("Added canvas_sync_status")

            # Check final columns
            cursor.execute("DESCRIBE user")
            columns = cursor.fetchall()
            column_names = [col[0] for col in columns]
            print(f"Final columns: {column_names}")

        conn.commit()
        print("Database columns added successfully!")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    add_columns()