#!/usr/bin/env python3
"""
Test script to debug the course report 500 error with proper authentication
"""
import sys
sys.path.append('.')

from app import app
from app.models import User, db, Course
from werkzeug.security import generate_password_hash

def test_course_report_authenticated():
    """Test course report route with authentication"""
    with app.test_client() as client:
        with app.app_context():
            # Test with existing user and course
            user = User.query.filter_by(username='rbtm2006').first()
            course = Course.query.filter_by(id=1).first()
            
            if not user or not course:
                print("Missing test data - user or course not found")
                return
                
            print(f"Testing course report for user: {user.username}, course: {course.name}")
            
            # Simulate login by setting up session
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            # Test the course report route
            response = client.get(f'/course/{course.id}/report')
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 500:
                print("500 Error detected!")
                print("Response data:")
                print(response.get_data(as_text=True)[:2000])
                
                # Try to get more details from Flask debug info
                if hasattr(response, 'data'):
                    error_html = response.get_data(as_text=True)
                    if 'Traceback' in error_html:
                        # Extract traceback info
                        import re
                        traceback_match = re.search(r'<div class="traceback">.*?</div>', error_html, re.DOTALL)
                        if traceback_match:
                            print("Traceback found in response")
                
            elif response.status_code == 200:
                print("SUCCESS! Course report loaded successfully")
                print("Response length:", len(response.get_data(as_text=True)))
            else:
                print(f"Unexpected status code: {response.status_code}")
                print("Response headers:", dict(response.headers))

if __name__ == "__main__":
    test_course_report_authenticated()