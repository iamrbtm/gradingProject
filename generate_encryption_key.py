#!/usr/bin/env python3
"""
Generate a secure encryption key for API token encryption.
Run this to generate a new key for the API_TOKEN_ENCRYPTION_KEY environment variable.
"""

from cryptography.fernet import Fernet

def generate_key():
    """Generate a new Fernet encryption key."""
    key = Fernet.generate_key()
    print("Generated encryption key:")
    print(key.decode())
    print()
    print("Add this to your .env file:")
    print(f"API_TOKEN_ENCRYPTION_KEY={key.decode()}")
    print()
    print("⚠️  WARNING: Keep this key secure! Anyone with this key can decrypt your API tokens.")
    print("Store it in environment variables, not in your code or version control.")

if __name__ == '__main__':
    generate_key()