"""
Migration script to add database triggers for Assignment table.

Triggers:
- assignment_submitted_trigger: When is_submitted=TRUE, set is_missing=FALSE and completed=TRUE
- assignment_missing_trigger: When is_missing=TRUE, set is_submitted=FALSE and completed=FALSE
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

def get_database_url():
    """Get database URL from environment variables."""
    return os.environ.get('DATABASE_URL')

def create_triggers():
    """Create database triggers for Assignment table."""
    database_url = get_database_url()
    
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables!")
        return False
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as connection:
            # Drop existing triggers if they exist
            print("\n🗑️  Dropping existing triggers (if any)...")
            
            drop_triggers = [
                "DROP TRIGGER IF EXISTS assignment_submitted_before_update",
                "DROP TRIGGER IF EXISTS assignment_submitted_before_insert",
                "DROP TRIGGER IF EXISTS assignment_missing_before_update",
                "DROP TRIGGER IF EXISTS assignment_missing_before_insert",
                "DROP TRIGGER IF EXISTS assignment_status_before_update",
                "DROP TRIGGER IF EXISTS assignment_status_before_insert"
            ]
            
            for drop_sql in drop_triggers:
                try:
                    connection.execute(text(drop_sql))
                    connection.commit()
                except Exception as e:
                    print(f"⚠️  Warning dropping trigger: {e}")
            
            print("✅ Old triggers dropped (if any existed)")
            
            # Create a single trigger that handles both rules with proper priority
            # Priority: is_missing=TRUE takes precedence (sets is_submitted=FALSE, completed=FALSE)
            # Then: is_submitted=TRUE sets is_missing=FALSE, completed=TRUE
            print("\n📝 Creating trigger: assignment_status_before_update...")
            
            trigger_update = """
            CREATE TRIGGER assignment_status_before_update
            BEFORE UPDATE ON assignment
            FOR EACH ROW
            BEGIN
                -- Priority 1: If is_missing is being set to TRUE, override other fields
                IF NEW.is_missing = TRUE THEN
                    SET NEW.is_submitted = FALSE;
                    SET NEW.completed = FALSE;
                -- Priority 2: If is_submitted is TRUE and is_missing is FALSE
                ELSEIF NEW.is_submitted = TRUE THEN
                    SET NEW.is_missing = FALSE;
                    SET NEW.completed = TRUE;
                END IF;
            END;
            """
            
            connection.execute(text(trigger_update))
            connection.commit()
            print("✅ Created trigger: assignment_status_before_update")
            
            # Create trigger for INSERT operations as well
            print("📝 Creating trigger: assignment_status_before_insert...")
            
            trigger_insert = """
            CREATE TRIGGER assignment_status_before_insert
            BEFORE INSERT ON assignment
            FOR EACH ROW
            BEGIN
                -- Priority 1: If is_missing is TRUE, override other fields
                IF NEW.is_missing = TRUE THEN
                    SET NEW.is_submitted = FALSE;
                    SET NEW.completed = FALSE;
                -- Priority 2: If is_submitted is TRUE and is_missing is FALSE
                ELSEIF NEW.is_submitted = TRUE THEN
                    SET NEW.is_missing = FALSE;
                    SET NEW.completed = TRUE;
                END IF;
            END;
            """
            
            connection.execute(text(trigger_insert))
            connection.commit()
            print("✅ Created trigger: assignment_status_before_insert")
        
        print("\n✅ All triggers created successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating triggers: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_triggers():
    """Verify that triggers were created successfully."""
    database_url = get_database_url()
    
    if not database_url:
        print("❌ DATABASE_URL not found!")
        return False
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as connection:
            # Get all triggers on assignment table
            result = connection.execute(text("""
                SELECT TRIGGER_NAME, EVENT_MANIPULATION, ACTION_TIMING
                FROM information_schema.TRIGGERS
                WHERE EVENT_OBJECT_TABLE = 'assignment'
                ORDER BY TRIGGER_NAME
            """))
            
            triggers = result.fetchall()
            
            print("\n📋 Triggers on assignment table:")
            if triggers:
                for trigger in triggers:
                    print(f"  ✅ {trigger[0]} ({trigger[2]} {trigger[1]})")
            else:
                print("  ⚠️  No triggers found")
            
            return len(triggers) == 2
        
    except Exception as e:
        print(f"❌ Error verifying triggers: {e}")
        return False

def test_triggers():
    """Test the triggers by creating test data."""
    database_url = get_database_url()
    
    if not database_url:
        print("❌ DATABASE_URL not found!")
        return False
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as connection:
            print("\n🧪 Testing triggers...")
            
            # Get a course to use for test assignments
            result = connection.execute(text("SELECT id FROM course LIMIT 1"))
            course = result.fetchone()
            
            if not course:
                print("⚠️  No courses found in database. Skipping trigger tests.")
                return True
            
            course_id = course[0]
            
            # Test 1: Insert assignment with is_submitted=TRUE (and is_missing=FALSE)
            print("\n📝 Test 1: Inserting assignment with is_submitted=TRUE, is_missing=FALSE...")
            connection.execute(text("""
                INSERT INTO assignment 
                (name, max_score, course_id, is_submitted, is_missing, completed)
                VALUES 
                ('Test Submitted Assignment', 100, :course_id, TRUE, FALSE, FALSE)
            """), {"course_id": course_id})
            connection.commit()
            
            result = connection.execute(text("""
                SELECT is_submitted, is_missing, completed 
                FROM assignment 
                WHERE name = 'Test Submitted Assignment'
            """))
            row = result.fetchone()
            
            if row:
                print(f"   is_submitted: {row[0]} (expected: 1/True)")
                print(f"   is_missing: {row[1]} (expected: 0/False)")
                print(f"   completed: {row[2]} (expected: 1/True)")
                
                if row[0] == 1 and row[1] == 0 and row[2] == 1:
                    print("   ✅ Trigger worked correctly!")
                else:
                    print("   ❌ Trigger did not work as expected!")
            
            # Test 2: Update assignment with is_missing=TRUE
            print("\n📝 Test 2: Updating assignment with is_missing=TRUE...")
            connection.execute(text("""
                UPDATE assignment 
                SET is_missing = TRUE, is_submitted = TRUE, completed = TRUE
                WHERE name = 'Test Submitted Assignment'
            """))
            connection.commit()
            
            result = connection.execute(text("""
                SELECT is_submitted, is_missing, completed 
                FROM assignment 
                WHERE name = 'Test Submitted Assignment'
            """))
            row = result.fetchone()
            
            if row:
                print(f"   is_submitted: {row[0]} (expected: 0/False)")
                print(f"   is_missing: {row[1]} (expected: 1/True)")
                print(f"   completed: {row[2]} (expected: 0/False)")
                
                if row[0] == 0 and row[1] == 1 and row[2] == 0:
                    print("   ✅ Trigger worked correctly!")
                else:
                    print("   ❌ Trigger did not work as expected!")
            
            # Clean up test data
            connection.execute(text("""
                DELETE FROM assignment WHERE name = 'Test Submitted Assignment'
            """))
            connection.commit()
            print("\n🧹 Cleaned up test data")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing triggers: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("🚀 Starting Assignment table trigger migration...")
    print("\nThis will create the following triggers:")
    print("   1. assignment_status_before_update: Enforces is_submitted and is_missing business rules on UPDATE")
    print("   2. assignment_status_before_insert: Enforces is_submitted and is_missing business rules on INSERT")
    print("\nBusiness Rules (with priority):")
    print("   • Priority 1: If is_missing=TRUE → is_submitted=FALSE, completed=FALSE")
    print("   • Priority 2: If is_submitted=TRUE (and is_missing=FALSE) → is_missing=FALSE, completed=TRUE")
    print()
    
    # Step 1: Create triggers
    print("1️⃣ Creating database triggers...")
    if not create_triggers():
        print("❌ Failed to create triggers")
        sys.exit(1)
    
    # Step 2: Verify triggers
    print("\n2️⃣ Verifying triggers...")
    if not verify_triggers():
        print("⚠️  Verification showed issues")
    
    # Step 3: Test triggers
    print("\n3️⃣ Testing triggers...")
    if not test_triggers():
        print("⚠️  Trigger tests showed issues")
    
    print("\n" + "="*80)
    print("✅ Trigger migration completed!")
    print("\nNOTE:")
    print("   • These triggers automatically maintain data consistency")
    print("   • Priority 1: is_missing=TRUE → is_submitted=FALSE, completed=FALSE")
    print("   • Priority 2: is_submitted=TRUE → is_missing=FALSE, completed=TRUE")
    print("   • Triggers apply to both INSERT and UPDATE operations")
    print("="*80)
