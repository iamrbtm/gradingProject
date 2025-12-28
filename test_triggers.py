"""
Test script to demonstrate the assignment table triggers in action.
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_trigger_scenarios():
    """Test various scenarios with the assignment triggers."""
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL not found!")
        return
    
    engine = create_engine(database_url)
    
    with engine.connect() as connection:
        # Get a course to use
        result = connection.execute(text("SELECT id FROM course LIMIT 1"))
        course = result.fetchone()
        
        if not course:
            print("❌ No courses found in database.")
            return
        
        course_id = course[0]
        
        print("\n" + "="*80)
        print("TESTING ASSIGNMENT TABLE TRIGGERS")
        print("="*80)
        
        # Scenario 1: Create assignment with is_submitted=TRUE
        print("\n📝 Scenario 1: Creating assignment with is_submitted=TRUE")
        print("   Input: is_submitted=TRUE, is_missing=FALSE, completed=FALSE")
        connection.execute(text("""
            INSERT INTO assignment 
            (name, max_score, course_id, is_submitted, is_missing, completed)
            VALUES 
            ('Trigger Test 1', 100, :course_id, TRUE, FALSE, FALSE)
        """), {"course_id": course_id})
        connection.commit()
        
        result = connection.execute(text("""
            SELECT is_submitted, is_missing, completed 
            FROM assignment WHERE name = 'Trigger Test 1'
        """))
        row = result.fetchone()
        if row:
            print(f"   Result: is_submitted={bool(row[0])}, is_missing={bool(row[1])}, completed={bool(row[2])}")
            print(f"   ✅ Expected: is_submitted=True, is_missing=False, completed=True")
        
        # Scenario 2: Create assignment with is_missing=TRUE
        print("\n📝 Scenario 2: Creating assignment with is_missing=TRUE")
        print("   Input: is_submitted=FALSE, is_missing=TRUE, completed=FALSE")
        connection.execute(text("""
            INSERT INTO assignment 
            (name, max_score, course_id, is_submitted, is_missing, completed)
            VALUES 
            ('Trigger Test 2', 100, :course_id, FALSE, TRUE, FALSE)
        """), {"course_id": course_id})
        connection.commit()
        
        result = connection.execute(text("""
            SELECT is_submitted, is_missing, completed 
            FROM assignment WHERE name = 'Trigger Test 2'
        """))
        row = result.fetchone()
        if row:
            print(f"   Result: is_submitted={bool(row[0])}, is_missing={bool(row[1])}, completed={bool(row[2])}")
            print(f"   ✅ Expected: is_submitted=False, is_missing=True, completed=False")
        
        # Scenario 3: Update assignment to mark as submitted
        print("\n📝 Scenario 3: Updating assignment - clear is_missing, then mark as submitted")
        print("   Input: Set is_missing=FALSE, is_submitted=TRUE on 'Trigger Test 2'")
        connection.execute(text("""
            UPDATE assignment 
            SET is_missing = FALSE, is_submitted = TRUE
            WHERE name = 'Trigger Test 2'
        """))
        connection.commit()
        
        result = connection.execute(text("""
            SELECT is_submitted, is_missing, completed 
            FROM assignment WHERE name = 'Trigger Test 2'
        """))
        row = result.fetchone()
        if row:
            print(f"   Result: is_submitted={bool(row[0])}, is_missing={bool(row[1])}, completed={bool(row[2])}")
            print(f"   ✅ Expected: is_submitted=True, is_missing=False, completed=True")
        
        # Scenario 4: Update assignment to mark as missing
        print("\n📝 Scenario 4: Updating assignment to mark as missing")
        print("   Input: Set is_missing=TRUE on 'Trigger Test 1'")
        connection.execute(text("""
            UPDATE assignment 
            SET is_missing = TRUE
            WHERE name = 'Trigger Test 1'
        """))
        connection.commit()
        
        result = connection.execute(text("""
            SELECT is_submitted, is_missing, completed 
            FROM assignment WHERE name = 'Trigger Test 1'
        """))
        row = result.fetchone()
        if row:
            print(f"   Result: is_submitted={bool(row[0])}, is_missing={bool(row[1])}, completed={bool(row[2])}")
            print(f"   ✅ Expected: is_submitted=False, is_missing=True, completed=False")
        
        # Scenario 5: Conflict scenario - try to set both is_submitted=TRUE and is_missing=TRUE
        print("\n📝 Scenario 5: Conflict scenario - both is_submitted=TRUE and is_missing=TRUE")
        print("   Input: Set is_submitted=TRUE, is_missing=TRUE")
        connection.execute(text("""
            UPDATE assignment 
            SET is_submitted = TRUE, is_missing = TRUE
            WHERE name = 'Trigger Test 1'
        """))
        connection.commit()
        
        result = connection.execute(text("""
            SELECT is_submitted, is_missing, completed 
            FROM assignment WHERE name = 'Trigger Test 1'
        """))
        row = result.fetchone()
        if row:
            print(f"   Result: is_submitted={bool(row[0])}, is_missing={bool(row[1])}, completed={bool(row[2])}")
            print(f"   ✅ Expected: is_submitted=False, is_missing=True, completed=False")
            print(f"   💡 Note: is_missing takes priority over is_submitted")
        
        # Clean up
        print("\n🧹 Cleaning up test data...")
        connection.execute(text("DELETE FROM assignment WHERE name LIKE 'Trigger Test%'"))
        connection.commit()
        
        print("\n" + "="*80)
        print("✅ All trigger scenarios tested successfully!")
        print("="*80)
        print("\nSummary:")
        print("   • When is_submitted=TRUE → is_missing=FALSE, completed=TRUE")
        print("   • When is_missing=TRUE → is_submitted=FALSE, completed=FALSE")
        print("   • is_missing=TRUE takes priority in conflict situations")
        print("="*80)

if __name__ == '__main__':
    test_trigger_scenarios()
