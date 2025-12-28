"""
Add Canvas-specific database indexes for performance optimization.
This is a standalone script that directly connects to the database.
"""

import os
import pymysql
from dotenv import load_dotenv
from urllib.parse import unquote

# Load environment variables
load_dotenv()

def add_canvas_indexes():
    """Add Canvas-specific indexes to improve sync performance."""
    
    # Parse database URL
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not found in environment")
        return
    
    # Parse MySQL connection string
    # Format: mysql+pymysql://user:pass@host:port/dbname
    parts = database_url.replace('mysql+pymysql://', '').split('@')
    user_pass = parts[0].split(':')
    host_db = parts[1].split('/')
    host_port = host_db[0].split(':')
    
    username = unquote(user_pass[0])
    password = unquote(user_pass[1])
    host = host_port[0]
    port = int(host_port[1]) if len(host_port) > 1 else 3306
    database = host_db[1]
    
    print(f"Connecting to database: {host}:{port}/{database}")
    
    try:
        # Connect to database
        connection = pymysql.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            database=database
        )
        
        cursor = connection.cursor()
        
        # Canvas-specific indexes
        canvas_indexes = [
            # Assignment table - Canvas lookups
            ("idx_assignment_canvas_id", 
             "CREATE INDEX idx_assignment_canvas_id ON assignment(canvas_assignment_id)"),
            
            ("idx_assignment_canvas_course_id", 
             "CREATE INDEX idx_assignment_canvas_course_id ON assignment(canvas_course_id)"),
            
            ("idx_assignment_canvas_lookup", 
             "CREATE INDEX idx_assignment_canvas_lookup ON assignment(canvas_assignment_id, course_id)"),
            
            # Course table - Canvas lookups
            ("idx_course_canvas_id", 
             "CREATE INDEX idx_course_canvas_id ON course(canvas_course_id)"),
            
            ("idx_course_canvas_lookup", 
             "CREATE INDEX idx_course_canvas_lookup ON course(canvas_course_id, term_id)"),
            
            # GradeCategory table - Name lookups for Canvas sync
            ("idx_grade_category_name_lookup", 
             "CREATE INDEX idx_grade_category_name_lookup ON grade_category(course_id, name)"),
        ]
        
        # General performance indexes (if not already present)
        general_indexes = [
            ("idx_assignment_course_id", 
             "CREATE INDEX idx_assignment_course_id ON assignment(course_id)"),
            
            ("idx_assignment_category_id", 
             "CREATE INDEX idx_assignment_category_id ON assignment(category_id)"),
            
            ("idx_course_term_id", 
             "CREATE INDEX idx_course_term_id ON course(term_id)"),
            
            ("idx_grade_category_course_id", 
             "CREATE INDEX idx_grade_category_course_id ON grade_category(course_id)"),
        ]
        
        all_indexes = canvas_indexes + general_indexes
        success_count = 0
        skip_count = 0
        
        print(f"\nAdding {len(all_indexes)} indexes...")
        print("=" * 60)
        
        for index_name, index_sql in all_indexes:
            try:
                cursor.execute(index_sql)
                print(f"✓ Added index: {index_name}")
                success_count += 1
            except pymysql.err.OperationalError as e:
                if "Duplicate key name" in str(e):
                    print(f"○ Index already exists: {index_name}")
                    skip_count += 1
                else:
                    print(f"✗ Error adding {index_name}: {e}")
            except Exception as e:
                print(f"✗ Error adding {index_name}: {e}")
        
        connection.commit()
        print("=" * 60)
        print(f"\n✓ Index operation complete!")
        print(f"  - Added: {success_count}")
        print(f"  - Already existed: {skip_count}")
        print(f"  - Total: {len(all_indexes)}")
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")

if __name__ == "__main__":
    add_canvas_indexes()
