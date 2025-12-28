#!/usr/bin/env python3
"""
Quick test script to validate sync functionality without running full Flask server.
"""
import os
import sys
sys.path.append('.')

def test_sync_imports():
    """Test that all sync-related imports work correctly."""
    print("Testing sync imports...")
    
    try:
        from app.models import db, Assignment, Course, Term, User
        print("✓ Models imported successfully")
    except ImportError as e:
        print(f"✗ Models import failed: {e}")
        return False
    
    # RemindersSyncManager removed - only Google Tasks sync remains
    try:
        from app.google_tasks_sync import GoogleTasksSyncManager
        print("✓ GoogleTasksSyncManager imported successfully")
    except ImportError as e:
        print(f"✗ GoogleTasksSyncManager import failed: {e}")
        return False
    
    try:
        from app.blueprints.main import main_bp
        print("✓ Main blueprint imported successfully")
    except ImportError as e:
        print(f"✗ Main blueprint import failed: {e}")
        return False
    
    return True

def test_sync_routes():
    """Test that sync routes are properly defined."""
    print("\nTesting sync routes...")
    
    try:
        # Import and create app to test routes
        from app import create_app
        app = create_app('development')
        
        with app.app_context():
            # Get all routes from the app
            routes = []
            for rule in app.url_map.iter_rules():
                routes.append(rule.rule)
            
            expected_routes = [
                '/sync',
                '/sync/individual/<int:assignment_id>',
                '/sync/bulk',
                '/sync/all', 
                '/sync/progress',
                '/sync/execute'
            ]
            
            for route in expected_routes:
                # Check if route pattern exists
                route_found = any(route in r for r in routes)
                if route_found:
                    print(f"✓ Route {route} found")
                else:
                    print(f"✗ Route {route} not found")
                    return False
            
            return True
        
    except Exception as e:
        print(f"✗ Route testing failed: {e}")
        return False

def test_template_exists():
    """Test that sync template exists."""
    print("\nTesting template...")
    
    template_path = "app/templates/sync.html"
    if os.path.exists(template_path):
        print("✓ Sync template exists")
        
        # Check for key elements
        with open(template_path, 'r') as f:
            content = f.read()
            
        required_elements = [
            'Sync All Assignments',
            'bulk-sync-btn',
            'selectAllCheckbox',
            'assignment-checkbox',
            'progress-section'
        ]
        
        for element in required_elements:
            if element in content:
                print(f"✓ Template contains {element}")
            else:
                print(f"✗ Template missing {element}")
                return False
        
        return True
    else:
        print("✗ Sync template not found")
        return False

def test_app_creation():
    """Test that the Flask app can be created."""
    print("\nTesting app creation...")
    
    try:
        from app import create_app
        app = create_app('development')
        print("✓ Flask app created successfully")
        
        with app.app_context():
            print("✓ App context works")
        
        return True
    except Exception as e:
        print(f"✗ App creation failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=== Sync System Validation ===\n")
    
    tests = [
        test_sync_imports,
        test_sync_routes, 
        test_template_exists,
        test_app_creation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"=== Results: {passed}/{total} tests passed ===")
    
    if passed == total:
        print("🎉 All tests passed! Sync system is ready.")
        return True
    else:
        print("❌ Some tests failed. Check the output above.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)