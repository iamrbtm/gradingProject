#!/usr/bin/env python3
"""
Migration script to encrypt existing Canvas API tokens in the database.
Run this once after deploying the encryption changes.
"""

import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app import create_app
from app.models import db, User
from cryptography.fernet import Fernet

def migrate_canvas_tokens():
    """Migrate existing plain text Canvas tokens to encrypted format."""

    # Check if encryption key is set
    encryption_key = os.environ.get('API_TOKEN_ENCRYPTION_KEY')
    if not encryption_key:
        print("ERROR: API_TOKEN_ENCRYPTION_KEY environment variable not set!")
        print("Generate a key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
        return False

    cipher = Fernet(encryption_key.encode())

    app = create_app()

    with app.app_context():
        try:
            # Get all users with Canvas tokens
            users_with_tokens = User.query.filter(User._canvas_access_token.isnot(None)).all()

            if not users_with_tokens:
                print("No Canvas tokens to migrate.")
                return True

            print(f"Found {len(users_with_tokens)} users with Canvas tokens to migrate.")

            for user in users_with_tokens:
                try:
                    # Check if token is already encrypted (starts with encrypted prefix)
                    if user._canvas_access_token.startswith('gAAAAA'):  # Fernet encrypted tokens start with this
                        print(f"User {user.username}: Token already encrypted, skipping.")
                        continue

                    # Encrypt the plain text token
                    encrypted_token = cipher.encrypt(user._canvas_access_token.encode()).decode()

                    # Update the database
                    user._canvas_access_token = encrypted_token
                    print(f"User {user.username}: Token encrypted successfully.")

                except Exception as e:
                    print(f"ERROR encrypting token for user {user.username}: {e}")
                    continue

            # Commit all changes
            db.session.commit()
            print("Migration completed successfully!")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"Migration failed: {e}")
            return False

if __name__ == '__main__':
    success = migrate_canvas_tokens()
    sys.exit(0 if success else 1)