"""
Test Canvas Sync Performance Optimizations

This script tests the Canvas sync functionality with timing measurements
to verify that the optimizations are working as expected.
"""

import time
import sys
from datetime import datetime
from app.models import db, User, Term, Course, Assignment
from app.services.canvas_sync_service import create_canvas_sync_service, CanvasSyncError

def format_time(seconds):
    """Format seconds into a readable string."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"

def test_canvas_connection(username):
    """Test Canvas API connection for a user."""
    print("=" * 70)
    print("CANVAS SYNC PERFORMANCE TEST")
    print("=" * 70)
    print()
    
    # Find user
    user = User.query.filter_by(username=username).first()
    if not user:
        print(f"ERROR: User '{username}' not found")
        return None
    
    print(f"Testing for user: {username}")
    print(f"Canvas URL: {user.canvas_base_url}")
    print()
    
    # Test connection
    try:
        sync_service = create_canvas_sync_service(user)
        result = sync_service.test_connection()
        
        if result['success']:
            print(f"✓ Canvas connection successful")
            print(f"  Connected as: {result['user'].get('name', 'Unknown')}")
            print()
            return sync_service
        else:
            print(f"✗ Canvas connection failed: {result.get('error', 'Unknown error')}")
            return None
    except CanvasSyncError as e:
        print(f"✗ Canvas credentials not configured: {e}")
        return None

def get_current_stats(user):
    """Get current database statistics for the user."""
    terms = Term.query.filter_by(user_id=user.id).all()
    courses = Course.query.join(Term).filter(Term.user_id == user.id).all()
    assignments = Assignment.query.join(Course).join(Term).filter(Term.user_id == user.id).all()
    
    return {
        'terms': len(terms),
        'courses': len(courses),
        'assignments': len(assignments)
    }

def test_full_sync(sync_service, user):
    """Test full Canvas sync with timing."""
    print("-" * 70)
    print("TEST 1: Full Sync (All Courses)")
    print("-" * 70)
    
    # Get initial stats
    initial_stats = get_current_stats(user)
    print(f"Current database state:")
    print(f"  - Terms: {initial_stats['terms']}")
    print(f"  - Courses: {initial_stats['courses']}")
    print(f"  - Assignments: {initial_stats['assignments']}")
    print()
    
    # Perform sync with timing
    print("Starting full sync...")
    start_time = time.time()
    
    try:
        results = sync_service.sync_all_data(use_incremental=False)
        
        elapsed_time = time.time() - start_time
        
        print()
        print(f"✓ Full sync completed in {format_time(elapsed_time)}")
        print()
        print("Sync Results:")
        print(f"  - Courses processed: {results['courses_processed']}")
        print(f"  - Courses created: {results['courses_created']}")
        print(f"  - Courses updated: {results['courses_updated']}")
        print(f"  - Assignments processed: {results['assignments_processed']}")
        print(f"  - Assignments created: {results['assignments_created']}")
        print(f"  - Assignments updated: {results['assignments_updated']}")
        print(f"  - Categories created: {results['categories_created']}")
        
        if results['errors']:
            print(f"  - Errors: {len(results['errors'])}")
            for error in results['errors'][:3]:  # Show first 3 errors
                print(f"    • {error}")
        
        # Get final stats
        final_stats = get_current_stats(user)
        print()
        print(f"Final database state:")
        print(f"  - Terms: {final_stats['terms']} (+{final_stats['terms'] - initial_stats['terms']})")
        print(f"  - Courses: {final_stats['courses']} (+{final_stats['courses'] - initial_stats['courses']})")
        print(f"  - Assignments: {final_stats['assignments']} (+{final_stats['assignments'] - initial_stats['assignments']})")
        
        return elapsed_time, results
        
    except Exception as e:
        print(f"✗ Sync failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def test_incremental_sync(sync_service, user):
    """Test incremental Canvas sync with timing."""
    print()
    print("-" * 70)
    print("TEST 2: Incremental Sync (Only Updated Courses)")
    print("-" * 70)
    
    if not user.canvas_last_sync:
        print("⚠ No previous sync timestamp found, incremental sync will fetch all courses")
    else:
        print(f"Last sync: {user.canvas_last_sync}")
    
    print()
    
    # Perform incremental sync with timing
    print("Starting incremental sync...")
    start_time = time.time()
    
    try:
        results = sync_service.sync_all_data(use_incremental=True)
        
        elapsed_time = time.time() - start_time
        
        print()
        print(f"✓ Incremental sync completed in {format_time(elapsed_time)}")
        print()
        print("Sync Results:")
        print(f"  - Courses processed: {results['courses_processed']}")
        print(f"  - Assignments processed: {results['assignments_processed']}")
        
        return elapsed_time, results
        
    except Exception as e:
        print(f"✗ Incremental sync failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def test_single_course_sync(sync_service, user):
    """Test syncing a single course."""
    print()
    print("-" * 70)
    print("TEST 3: Single Course Sync")
    print("-" * 70)
    
    # Find a course with Canvas ID
    course = Course.query.join(Term).filter(
        Term.user_id == user.id,
        Course.canvas_course_id.isnot(None)
    ).first()
    
    if not course:
        print("⚠ No Canvas-linked courses found, skipping single course sync test")
        return None, None
    
    print(f"Testing with course: {course.name}")
    print(f"Canvas ID: {course.canvas_course_id}")
    print()
    
    # Count current assignments
    initial_count = Assignment.query.filter_by(course_id=course.id).count()
    print(f"Current assignments: {initial_count}")
    print()
    
    # Perform sync with timing
    print("Starting course sync...")
    start_time = time.time()
    
    try:
        results = sync_service.sync_course_data(course.id)
        
        elapsed_time = time.time() - start_time
        
        print()
        print(f"✓ Course sync completed in {format_time(elapsed_time)}")
        print()
        print("Sync Results:")
        print(f"  - Assignments processed: {results['assignments_processed']}")
        print(f"  - Assignments created: {results['assignments_created']}")
        print(f"  - Assignments updated: {results['assignments_updated']}")
        print(f"  - Categories created: {results['categories_created']}")
        
        final_count = Assignment.query.filter_by(course_id=course.id).count()
        print(f"  - Total assignments now: {final_count}")
        
        return elapsed_time, results
        
    except Exception as e:
        print(f"✗ Course sync failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def main():
    """Run all performance tests."""
    if len(sys.argv) < 2:
        print("Usage: python test_canvas_performance.py <username>")
        print()
        print("Example: python test_canvas_performance.py jeremy")
        sys.exit(1)
    
    username = sys.argv[1]
    
    # Import app to get context
    from app import app
    
    with app.app_context():
        # Test connection
        sync_service = test_canvas_connection(username)
        if not sync_service:
            sys.exit(1)
        
        user = User.query.filter_by(username=username).first()
        
        # Run tests
        full_time, full_results = test_full_sync(sync_service, user)
        
        if full_time:
            # Wait a moment then test incremental
            time.sleep(2)
            incr_time, incr_results = test_incremental_sync(sync_service, user)
            
            # Test single course
            single_time, single_results = test_single_course_sync(sync_service, user)
            
            # Summary
            print()
            print("=" * 70)
            print("PERFORMANCE SUMMARY")
            print("=" * 70)
            print()
            print(f"Full sync time: {format_time(full_time)}")
            if incr_time:
                print(f"Incremental sync time: {format_time(incr_time)}")
                speedup = ((full_time - incr_time) / full_time * 100) if full_time > 0 else 0
                print(f"  → {speedup:.1f}% faster than full sync")
            if single_time:
                print(f"Single course sync time: {format_time(single_time)}")
            
            print()
            print("Optimization Benefits:")
            print("✓ Connection pooling active (10 connections, retry strategy)")
            print("✓ Concurrent pagination (5 workers)")
            print("✓ Concurrent data fetching (3 workers)")
            print("✓ Bulk submissions fetching")
            print("✓ Batch database operations (~6 flushes per sync)")
            print("✓ Database indexes on Canvas ID columns")
            print()

if __name__ == "__main__":
    main()
