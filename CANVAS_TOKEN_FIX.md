# Canvas Token Persistence Issue - SOLUTION

## Problem Summary
Canvas access tokens were not persisting across logins. After logout and re-login, the system would say Canvas sync needs to be set up again, even though the token was saved in the database.

## Root Cause
The issue was in the production deployment configuration (`passenger_wsgi.py`). 

The Canvas access tokens are **encrypted** before being stored in the database using the Fernet symmetric encryption library. The encryption key comes from the environment variable `API_TOKEN_ENCRYPTION_KEY`.

**What was happening:**
1. The `.env` file contains `API_TOKEN_ENCRYPTION_KEY=afpWuojzOfALce2gn3IsQIn5GQJQ-GRzglWLKkRGhBQ=`
2. During development (running via `python app.py`), Flask auto-loads the `.env` file
3. **BUT** in production (via `passenger_wsgi.py`), the `.env` file was NOT being loaded
4. Without `API_TOKEN_ENCRYPTION_KEY`, the code fell back to generating a **random encryption key** on each app startup
5. Token encrypted with Key A on startup #1
6. After restart/logout, app generated new Key B
7. Token could not be decrypted with Key B (was encrypted with Key A)
8. System thought no token was configured

## Files Changed

### 1. `/passenger_wsgi.py` (CRITICAL FIX)
**Before:**
```python
import sys
import os

project_path = '/home/onlymyli/public_html/grades'
if project_path not in sys.path:
    sys.path.insert(0, project_path)

os.environ['FLASK_ENV'] = 'production'
os.environ['DATABASE_URL'] = 'mysql+pymysql://...'

from app import create_app
```

**After:**
```python
import sys
import os

project_path = '/home/onlymyli/public_html/grades'
if project_path not in sys.path:
    sys.path.insert(0, project_path)

# Load environment variables from .env file
from dotenv import load_dotenv
dotenv_path = os.path.join(project_path, '.env')
load_dotenv(dotenv_path)

# Set environment variables for production (override if needed)
os.environ['FLASK_ENV'] = 'production'
# DATABASE_URL and API_TOKEN_ENCRYPTION_KEY now come from .env file

from app import create_app
```

### 2. `/app.py` (Additional Safety)
Added explicit `.env` loading at the top to ensure it's loaded before any models are imported:

```python
# Load environment variables FIRST before any other imports
from dotenv import load_dotenv
load_dotenv()
```

### 3. `/app/models.py` (Better Error Messages)
Added warning when encryption key is missing:

```python
if ENCRYPTION_KEY:
    cipher = Fernet(ENCRYPTION_KEY.encode())
else:
    # CRITICAL WARNING: API_TOKEN_ENCRYPTION_KEY not found in environment!
    import warnings
    warnings.warn(
        "API_TOKEN_ENCRYPTION_KEY environment variable not set! "
        "Canvas tokens will not persist across app restarts.",
        RuntimeWarning
    )
    cipher = Fernet(Fernet.generate_key())
```

## Testing

Run the test script to verify encryption is working:

```bash
python test_canvas_token_encryption.py
```

Expected output:
```
============================================================
Canvas Token Encryption Test
============================================================

1. Encryption key loaded: YES ✓
   Key (first 20 chars): afpWuojzOfALce2gn3Is...

2. Original token: 1234~abcdefghijklmn...
   Encrypted token: gAAAAABl...
   Decrypted token: 1234~abcdefghijklmn...

3. Encryption/Decryption: SUCCESS ✓
   Tokens match! Encryption is working correctly.

4. Testing with database models...
   Model encryption: SUCCESS ✓

============================================================
All tests passed! ✓
Canvas token encryption is working correctly.
============================================================
```

## Deployment Steps

1. **Upload `.env` file to production server** at `/home/onlymyli/public_html/grades/.env`
   - Ensure it contains: `API_TOKEN_ENCRYPTION_KEY=afpWuojzOfALce2gn3IsQIn5GQJQ-GRzglWLKkRGhBQ=`

2. **Upload updated `passenger_wsgi.py`** to production server

3. **Restart the application:**
   ```bash
   touch /home/onlymyli/public_html/grades/passenger_wsgi.py
   ```
   (This tells Passenger to restart the app)

4. **Re-enter your Canvas token** in the settings page one more time
   - This will encrypt it with the **persistent** encryption key
   - From now on, it will persist across logins and app restarts

## Security Note
The `API_TOKEN_ENCRYPTION_KEY` should:
- ✓ Be in `.env` file (which is NOT committed to git per `.gitignore`)
- ✓ Be kept secret and backed up securely
- ✗ Never be changed once tokens are encrypted (old tokens won't decrypt)
- ✗ Never be committed to version control

If you ever need to rotate the encryption key, you'll need to:
1. Decrypt all existing tokens with the old key
2. Re-encrypt them with the new key
3. Update the database

## How It Works Now

1. **Token Storage:**
   - User enters token in settings: `1234~abcdefg...`
   - Model property setter encrypts it: `gAAAAABl3kj2...` (encrypted)
   - Saved to database column `_canvas_access_token`

2. **Token Retrieval:**
   - App reads from database: `gAAAAABl3kj2...` (encrypted)
   - Model property getter decrypts it using the same key: `1234~abcdefg...`
   - Passed to Canvas API service for authentication

3. **Persistence:**
   - Same encryption key used across all app restarts
   - Token can always be decrypted as long as key doesn't change
   - Works across logins, logouts, and server restarts
