"""
Database migration script to add performance indexes.
Run this script to add indexes for better query performance.
"""

from app.models import db
from app import app

def add_performance_indexes():
    """Add database indexes for better performance."""
    
    with app.app_context():
        try:
            # Add indexes for commonly queried fields
            indexes = [
                # Assignment table indexes
                "CREATE INDEX IF NOT EXISTS idx_assignment_due_date ON assignment(due_date);",
                "CREATE INDEX IF NOT EXISTS idx_assignment_course_id ON assignment(course_id);",
                "CREATE INDEX IF NOT EXISTS idx_assignment_score ON assignment(score);",
                "CREATE INDEX IF NOT EXISTS idx_assignment_category_id ON assignment(category_id);",
                
                # Canvas-specific indexes for Assignment table
                "CREATE INDEX IF NOT EXISTS idx_assignment_canvas_id ON assignment(canvas_assignment_id);",
                "CREATE INDEX IF NOT EXISTS idx_assignment_canvas_course_id ON assignment(canvas_course_id);",
                "CREATE INDEX IF NOT EXISTS idx_assignment_canvas_lookup ON assignment(canvas_assignment_id, course_id);",
                
                # Term table indexes
                "CREATE INDEX IF NOT EXISTS idx_term_user_id ON term(user_id);",
                "CREATE INDEX IF NOT EXISTS idx_term_active ON term(active);",
                "CREATE INDEX IF NOT EXISTS idx_term_user_active ON term(user_id, active);",
                "CREATE INDEX IF NOT EXISTS idx_term_year_season ON term(year, season);",
                
                # Course table indexes
                "CREATE INDEX IF NOT EXISTS idx_course_term_id ON course(term_id);",
                "CREATE INDEX IF NOT EXISTS idx_course_name ON course(name);",
                
                # Canvas-specific indexes for Course table
                "CREATE INDEX IF NOT EXISTS idx_course_canvas_id ON course(canvas_course_id);",
                "CREATE INDEX IF NOT EXISTS idx_course_canvas_lookup ON course(canvas_course_id, term_id);",
                
                # TodoItem table indexes
                "CREATE INDEX IF NOT EXISTS idx_todo_due_date ON todo_item(due_date);",
                "CREATE INDEX IF NOT EXISTS idx_todo_completed ON todo_item(is_completed);",
                "CREATE INDEX IF NOT EXISTS idx_todo_course_id ON todo_item(course_id);",
                
                # GradeCategory table indexes
                "CREATE INDEX IF NOT EXISTS idx_grade_category_course_id ON grade_category(course_id);",
                "CREATE INDEX IF NOT EXISTS idx_grade_category_name_lookup ON grade_category(course_id, name);",
                
                # User table indexes (username already has unique constraint)
                # Additional composite indexes for common queries
                "CREATE INDEX IF NOT EXISTS idx_assignment_course_score ON assignment(course_id, score);",
                "CREATE INDEX IF NOT EXISTS idx_assignment_due_score ON assignment(due_date, score);",
            ]
            
            print(f"Adding {len(indexes)} performance indexes...")
            
            success_count = 0
            for index_sql in indexes:
                try:
                    db.session.execute(db.text(index_sql))
                    index_name = index_sql.split(' ')[5]
                    print(f"✓ Added index: {index_name}")
                    success_count += 1
                except Exception as e:
                    print(f"✗ Failed to add index: {e}")
            
            db.session.commit()
            print(f"\n✓ Successfully added {success_count}/{len(indexes)} indexes!")
            
        except Exception as e:
            print(f"Error adding indexes: {e}")
            db.session.rollback()

if __name__ == "__main__":
    add_performance_indexes()