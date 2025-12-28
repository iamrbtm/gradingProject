#!/usr/bin/env python3
"""
Migration script to convert SQLite database to MySQL.
This script exports data from the existing SQLite database and imports it into MySQL.
"""

import os
import sqlite3
import pymysql
from datetime import datetime
import sys

# Database configurations
SQLITE_DB_PATH = 'instance/grade_tracker.db'
MYSQL_CONFIG = {
    'host': 'jeremyguill.com',
    'port': 3306,
    'user': 'onlymyli',
    'password': 'Braces4me##',
    'database': 'onlymyli_grades',
    'charset': 'utf8mb4'
}

def export_sqlite_data():
    """Export all data from SQLite database."""
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"SQLite database not found at {SQLITE_DB_PATH}")
        return None
    
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    cursor = conn.cursor()
    
    data = {}
    
    # Define table order for foreign key constraints
    tables = ['user', 'term', 'course', 'grade_category', 'assignment', 'todo_item', 'campus_closure']
    
    for table in tables:
        try:
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            data[table] = [dict(row) for row in rows]
            print(f"Exported {len(rows)} records from {table}")
        except sqlite3.Error as e:
            print(f"Error exporting {table}: {e}")
    
    conn.close()
    return data

def create_mysql_schema():
    """Create MySQL database schema."""
    try:
        # Connect directly to the existing database
        connection = pymysql.connect(**MYSQL_CONFIG)
        
        with connection.cursor() as cursor:
            # Drop existing tables in reverse order to handle foreign keys
            drop_tables = [
                "DROP TABLE IF EXISTS campus_closure",
                "DROP TABLE IF EXISTS todo_item", 
                "DROP TABLE IF EXISTS assignment",
                "DROP TABLE IF EXISTS grade_category",
                "DROP TABLE IF EXISTS course",
                "DROP TABLE IF EXISTS term",
                "DROP TABLE IF EXISTS user"
            ]
            
            for drop_sql in drop_tables:
                cursor.execute(drop_sql)
            
            # Create tables with MySQL-specific syntax
            create_tables = [
                """
                CREATE TABLE user (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(80) NOT NULL UNIQUE,
                    password_hash VARCHAR(128) NOT NULL
                ) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """,
                """
                CREATE TABLE term (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nickname VARCHAR(100) NOT NULL,
                    season VARCHAR(20) NOT NULL,
                    year INT NOT NULL,
                    school_name VARCHAR(200) NOT NULL,
                    start_date DATETIME NULL,
                    end_date DATETIME NULL,
                    user_id INT NOT NULL,
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
                ) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """,
                """
                CREATE TABLE course (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    credits FLOAT NOT NULL DEFAULT 0.0,
                    term_id INT NOT NULL,
                    is_weighted BOOLEAN NOT NULL DEFAULT TRUE,
                    is_category BOOLEAN NOT NULL DEFAULT FALSE,
                    FOREIGN KEY (term_id) REFERENCES term(id) ON DELETE CASCADE
                ) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """,
                """
                CREATE TABLE grade_category (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    weight FLOAT NOT NULL,
                    course_id INT NOT NULL,
                    FOREIGN KEY (course_id) REFERENCES course(id) ON DELETE CASCADE
                ) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """,
                """
                CREATE TABLE assignment (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    score FLOAT NULL,
                    max_score FLOAT NOT NULL,
                    course_id INT NOT NULL,
                    category_id INT NULL,
                    due_date DATETIME NULL,
                    last_synced_calendar DATETIME NULL,
                    last_synced_reminders DATETIME NULL,
                    calendar_event_id VARCHAR(255) NULL,
                    reminders_item_id VARCHAR(255) NULL,
                    last_modified DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (course_id) REFERENCES course(id) ON DELETE CASCADE,
                    FOREIGN KEY (category_id) REFERENCES grade_category(id) ON DELETE SET NULL
                ) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """,
                """
                CREATE TABLE todo_item (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    description VARCHAR(255) NOT NULL,
                    due_date DATETIME NULL,
                    is_completed BOOLEAN DEFAULT FALSE,
                    course_id INT NULL,
                    FOREIGN KEY (course_id) REFERENCES course(id) ON DELETE SET NULL
                ) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """,
                """
                CREATE TABLE campus_closure (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    date DATETIME NOT NULL,
                    reason VARCHAR(255) NOT NULL,
                    term_id INT NOT NULL,
                    FOREIGN KEY (term_id) REFERENCES term(id) ON DELETE CASCADE
                ) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            ]
            
            for create_sql in create_tables:
                cursor.execute(create_sql)
                
        connection.commit()
        connection.close()
        print("MySQL schema created successfully")
        return True
        
    except Exception as e:
        print(f"Error creating MySQL schema: {e}")
        return False

def import_data_to_mysql(data):
    """Import data into MySQL database."""
    if not data:
        print("No data to import")
        return False
    
    try:
        connection = pymysql.connect(**MYSQL_CONFIG)
        
        # Import data in order to respect foreign key constraints
        tables_order = ['user', 'term', 'course', 'grade_category', 'assignment', 'todo_item', 'campus_closure']
        
        for table in tables_order:
            if table not in data or not data[table]:
                continue
                
            with connection.cursor() as cursor:
                records = data[table]
                if not records:
                    continue
                
                # Get column names from first record
                columns = list(records[0].keys())
                placeholders = ', '.join(['%s'] * len(columns))
                columns_str = ', '.join(columns)
                
                insert_sql = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
                
                # Prepare data for insertion
                insert_data = []
                for record in records:
                    row_data = []
                    for col in columns:
                        value = record[col]
                        # Convert datetime strings to proper format
                        if col in ['start_date', 'end_date', 'due_date', 'last_synced_calendar', 
                                  'last_synced_reminders', 'last_modified', 'date'] and value:
                            try:
                                # Handle different datetime formats
                                if isinstance(value, str):
                                    # Try parsing common SQLite datetime formats
                                    try:
                                        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                        value = dt
                                    except:
                                        try:
                                            dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                                            value = dt
                                        except:
                                            value = None
                            except:
                                value = None
                        row_data.append(value)
                    insert_data.append(row_data)
                
                cursor.executemany(insert_sql, insert_data)
                print(f"Imported {len(insert_data)} records into {table}")
        
        connection.commit()
        connection.close()
        print("Data import completed successfully")
        return True
        
    except Exception as e:
        print(f"Error importing data to MySQL: {e}")
        return False

def main():
    """Main migration function."""
    print("Starting SQLite to MySQL migration...")
    
    # Step 1: Export data from SQLite
    print("\n1. Exporting data from SQLite...")
    data = export_sqlite_data()
    if not data:
        print("Failed to export SQLite data")
        return False
    
    # Step 2: Create MySQL schema
    print("\n2. Creating MySQL schema...")
    if not create_mysql_schema():
        print("Failed to create MySQL schema")
        return False
    
    # Step 3: Import data to MySQL
    print("\n3. Importing data to MySQL...")
    if not import_data_to_mysql(data):
        print("Failed to import data to MySQL")
        return False
    
    print("\n✅ Migration completed successfully!")
    print("Your application is now configured to use MySQL.")
    print("Remember to install the required dependencies: pip install PyMySQL mysqlclient")
    
    return True

if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1)