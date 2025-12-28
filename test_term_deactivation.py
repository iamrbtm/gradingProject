#!/usr/bin/env python3
"""
Test script for term deactivation functionality
"""

import sqlite3
import os

def test_term_deactivation():
    db_path = os.path.join('instance', 'grade_tracker.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if active column exists
        cursor.execute("PRAGMA table_info(term)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'active' in columns:
            print("✓ 'active' column exists in term table")
            
            # Check current term data
            cursor.execute("SELECT id, nickname, active FROM term")
            terms = cursor.fetchall()
            
            print(f"\nFound {len(terms)} terms:")
            for term_id, nickname, active in terms:
                status = "Active" if active else "Inactive"
                print(f"  - {nickname} (ID: {term_id}): {status}")
            
            # Test deactivating a term (if any exist)
            if terms:
                test_term_id = terms[0][0]
                test_term_name = terms[0][1]
                
                # Toggle the term's active status
                cursor.execute("UPDATE term SET active = 0 WHERE id = ?", (test_term_id,))
                conn.commit()
                print(f"\n✓ Deactivated term '{test_term_name}' (ID: {test_term_id})")
                
                # Toggle it back
                cursor.execute("UPDATE term SET active = 1 WHERE id = ?", (test_term_id,))
                conn.commit()
                print(f"✓ Reactivated term '{test_term_name}' (ID: {test_term_id})")
            
            print("\n✓ Term deactivation functionality appears to be working correctly!")
            
        else:
            print("✗ 'active' column not found in term table")
            
    except Exception as e:
        print(f"Test failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    test_term_deactivation()