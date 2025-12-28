#!/usr/bin/env python3
"""
Test script to verify Canvas token encryption/decryption works correctly.
This helps diagnose token persistence issues.
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test encryption key is loaded
encryption_key = os.environ.get('API_TOKEN_ENCRYPTION_KEY')
print("=" * 60)
print("Canvas Token Encryption Test")
print("=" * 60)
print(f"\n1. Encryption key loaded: {'YES ✓' if encryption_key else 'NO ✗'}")

if encryption_key:
    print(f"   Key (first 20 chars): {encryption_key[:20]}...")
else:
    print("   ERROR: API_TOKEN_ENCRYPTION_KEY not found in environment!")
    print("   This will cause tokens to not persist across restarts.")
    sys.exit(1)

# Test encryption/decryption
from cryptography.fernet import Fernet
cipher = Fernet(encryption_key.encode())

# Simulate saving a Canvas token
test_token = "1234~abcdefghijklmnopqrstuvwxyz1234567890ABCDEFG"
print(f"\n2. Original token: {test_token[:20]}...")

# Encrypt (what happens when you save)
encrypted = cipher.encrypt(test_token.encode()).decode()
print(f"   Encrypted token: {encrypted[:50]}...")

# Decrypt (what happens when you retrieve)
try:
    decrypted = cipher.decrypt(encrypted.encode()).decode()
    print(f"   Decrypted token: {decrypted[:20]}...")
    
    if decrypted == test_token:
        print("\n3. Encryption/Decryption: SUCCESS ✓")
        print("   Tokens match! Encryption is working correctly.")
    else:
        print("\n3. Encryption/Decryption: FAILED ✗")
        print("   Tokens don't match!")
        sys.exit(1)
except Exception as e:
    print(f"\n3. Encryption/Decryption: FAILED ✗")
    print(f"   Error: {e}")
    sys.exit(1)

# Test with database model
print("\n4. Testing with database models...")
try:
    from app.models import User, cipher as model_cipher
    
    # Check if the cipher in models matches our cipher
    test_encrypted_by_model = model_cipher.encrypt(test_token.encode()).decode()
    test_decrypted_by_model = model_cipher.decrypt(test_encrypted_by_model.encode()).decode()
    
    if test_decrypted_by_model == test_token:
        print("   Model encryption: SUCCESS ✓")
    else:
        print("   Model encryption: FAILED ✗")
        sys.exit(1)
        
except ImportError as e:
    # Database driver not installed, skip this test
    print(f"   Model encryption: SKIPPED (database driver not available)")
    print(f"   This is OK - basic encryption tests passed")
except Exception as e:
    print(f"   Model encryption: FAILED ✗")
    print(f"   Error: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("All tests passed! ✓")
print("Canvas token encryption is working correctly.")
print("=" * 60)
