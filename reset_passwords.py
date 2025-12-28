#!/usr/bin/env python3
"""
Password Reset Script - Updates all user passwords after fixing the hash length issue.
This script allows you to reset passwords for existing users.
"""

import os

def reset_user_passwords():
    """Reset passwords for existing users."""
    
    os.environ['DATABASE_URL'] = 'mysql+pymysql://onlymyli:Braces4me%23%23@jeremyguill.com:3306/onlymyli_grades'
    
    from app import create_app
    app = create_app('production')
    
    with app.app_context():
        from app.models import User, db
        
        print("=== PASSWORD RESET TOOL ===")
        print("Due to the database field length issue, existing user passwords need to be reset.")
        print()
        
        users = User.query.all()
        print(f"Found {len(users)} users:")
        for i, user in enumerate(users, 1):
            print(f"{i}. {user.username} (ID: {user.id})")
        
        print()
        print("Suggested password resets:")
        
        # Define default passwords for known users
        password_updates = {
            'rbtm2006': 'Braces4me',
            'testuser': 'Braces4me', 
            'jguill': 'Braces4me',
            'jeremy@dudefishprinting.com': 'Braces4me'
        }
        
        for user in users:
            if user.username in password_updates:
                new_password = password_updates[user.username]
                user.set_password(new_password)
                print(f"✅ Reset password for {user.username}")
            else:
                # Set default password for unknown users
                user.set_password('Braces4me')
                print(f"✅ Set default password for {user.username}")
        
        # Save all changes
        db.session.commit()
        print()
        print("🎉 All passwords have been reset!")
        print()
        print("Login credentials:")
        for user in users:
            if user.username in password_updates:
                print(f"  Username: {user.username} | Password: {password_updates[user.username]}")
            else:
                print(f"  Username: {user.username} | Password: Braces4me")
        
        print()
        print("Testing authentication for first user...")
        first_user = users[0]
        test_password = password_updates.get(first_user.username, 'Braces4me')
        is_valid = first_user.check_password(test_password)
        print(f"Authentication test for {first_user.username}: {'✅ SUCCESS' if is_valid else '❌ FAILED'}")

if __name__ == "__main__":
    reset_user_passwords()