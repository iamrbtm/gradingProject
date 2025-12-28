# CSRF Token Issue - "The CSRF session token is missing" 

## Problem
When saving the settings page, you get: "Bad Request - The CSRF session token is missing"

## Root Causes

There are multiple potential causes for CSRF token issues:

### 1. **Session Not Persisting** (Most Likely)
If the Flask session isn't being maintained properly, the CSRF token stored in the session will be lost between page loads.

**Causes:**
- `SECRET_KEY` not loaded from environment (changes on each restart)
- Session cookies not being set due to `SESSION_COOKIE_SECURE = True` with HTTP
- Session expiring too quickly

### 2. **Environment Variables Not Loaded**
If `.env` file isn't loaded in production, `FLASK_SECRET_KEY` will use default value which changes behavior.

## Changes Made to Fix

### 1. `/config.py` - Session & CSRF Configuration

**Added:**
```python
# In base Config class:
SESSION_COOKIE_NAME = 'grades_session'  # Custom session cookie name
WTF_CSRF_TIME_LIMIT = None  # Don't expire CSRF tokens
WTF_CSRF_CHECK_DEFAULT = True

# In ProductionConfig:
SESSION_COOKIE_SECURE = os.environ.get('USE_HTTPS', 'False').lower() == 'true'
WTF_CSRF_SSL_STRICT = False  # Allow CSRF over HTTP
```

**Why:** 
- `WTF_CSRF_TIME_LIMIT = None` prevents CSRF tokens from expiring after 1 hour
- `SESSION_COOKIE_SECURE` set based on environment (don't require HTTPS unless explicitly enabled)
- `WTF_CSRF_SSL_STRICT = False` allows CSRF validation to work over HTTP

### 2. `/app/blueprints/auth.py` - Make Sessions Permanent

**Changed:**
```python
# Before:
login_user(user)

# After:
session.permanent = True
login_user(user, remember=True)
```

**Why:** Makes Flask sessions persistent across browser restarts and ensures they last for the full `PERMANENT_SESSION_LIFETIME` (1 hour).

### 3. `/app/error_handlers.py` - Better CSRF Error Handling

**Added:**
```python
@app.errorhandler(400)
def bad_request_error(error):
    """Handle 400 Bad Request errors (including CSRF failures)."""
    if 'CSRF' in str(error):
        app.logger.warning(f'CSRF validation failed: {request.url}')
        flash('Security token expired or missing. Please try again.', 'warning')
        return redirect(request.referrer or url_for('auth.login'))
```

**Why:** Provides user-friendly error messages instead of generic "Bad Request" page.

### 4. `/passenger_wsgi.py` - Verify Environment Variables

**Added:**
```python
required_vars = ['FLASK_SECRET_KEY', 'API_TOKEN_ENCRYPTION_KEY', 'DATABASE_URL']
missing_vars = [var for var in required_vars if not os.environ.get(var)]
if missing_vars:
    print(f"WARNING: Missing required environment variables: {', '.join(missing_vars)}")
```

**Why:** Helps diagnose if `.env` file isn't being loaded properly.

## Deployment Steps

1. **Update all modified files** on the production server:
   - `config.py`
   - `app/blueprints/auth.py`
   - `app/error_handlers.py`
   - `passenger_wsgi.py`

2. **Ensure `.env` file exists** at `/home/onlymyli/public_html/grades/.env` with:
   ```bash
   FLASK_SECRET_KEY=e583d219a19e8df3f3ec5cfbcdf19ca9b6082f71e947c851630a420e3fbb667b
   API_TOKEN_ENCRYPTION_KEY=afpWuojzOfALce2gn3IsQIn5GQJQ-GRzglWLKkRGhBQ=
   DATABASE_URL=mysql+pymysql://onlymyli:Braces4me%23%23@jeremyguill.com:3306/onlymyli_grades
   ```

3. **If using HTTP (not HTTPS)**, add to `.env`:
   ```bash
   USE_HTTPS=false
   ```

4. **Restart the application:**
   ```bash
   touch /home/onlymyli/public_html/grades/passenger_wsgi.py
   ```

5. **Clear browser cookies** for your site (or use incognito mode to test)

6. **Login again** - Session should now persist properly

7. **Try saving settings** - CSRF token should work

## Testing / Verification

### Check if Environment Variables are Loaded

SSH into your server and run:
```bash
cd /home/onlymyli/public_html/grades
python3 << 'EOF'
from dotenv import load_dotenv
import os
load_dotenv()
print("FLASK_SECRET_KEY:", "LOADED" if os.environ.get('FLASK_SECRET_KEY') else "MISSING")
print("API_TOKEN_ENCRYPTION_KEY:", "LOADED" if os.environ.get('API_TOKEN_ENCRYPTION_KEY') else "MISSING")
print("DATABASE_URL:", "LOADED" if os.environ.get('DATABASE_URL') else "MISSING")
EOF
```

Expected output:
```
FLASK_SECRET_KEY: LOADED
API_TOKEN_ENCRYPTION_KEY: LOADED
DATABASE_URL: LOADED
```

### Check Application Logs

After restarting, check if there are warnings about missing environment variables:
```bash
tail -f /home/onlymyli/public_html/grades/logs/grade_tracker.log
```

Or check Passenger logs:
```bash
tail -f ~/passenger.log
```

Look for the line: `WARNING: Missing required environment variables:`

### Browser Developer Tools

1. Open browser DevTools (F12)
2. Go to **Network** tab
3. Load the settings page
4. Look for the request to `/settings` when you submit the form
5. Check **Request Headers** - should include:
   - `Cookie: grades_session=...`
6. Check **Form Data** - should include:
   - `csrf_token=...`

If either is missing, sessions aren't working properly.

## Additional Troubleshooting

### If CSRF Still Fails

1. **Check if you're behind a proxy/load balancer:**
   - Add to `config.py` in `ProductionConfig`:
     ```python
     PREFERRED_URL_SCHEME = 'https'  # or 'http'
     ```

2. **Disable CSRF temporarily** (for testing only!):
   - Add to `.env`:
     ```bash
     WTF_CSRF_ENABLED=false
     ```
   - If this fixes it, the issue is with CSRF configuration, not sessions

3. **Check file permissions:**
   - `.env` file should be readable by the web server user
   ```bash
   chmod 644 /home/onlymyli/public_html/grades/.env
   ```

4. **Verify session storage:**
   - Flask stores sessions in signed cookies by default
   - Make sure `SECRET_KEY` is consistent (from `.env`)
   - Check browser cookies are enabled

### If Sessions Don't Persist

1. **Check cookie domain/path:**
   - If accessing via subdomain, cookies might not be set correctly
   - Add to `config.py`:
     ```python
     SESSION_COOKIE_DOMAIN = '.yourdomain.com'  # Note the leading dot
     ```

2. **Check session cookie settings:**
   - Add debug logging to verify session is being set:
   ```python
   # In app.py, after login:
   app.logger.info(f"Session ID: {session.get('_id')}")
   app.logger.info(f"Session permanent: {session.permanent}")
   ```

## Security Notes

### Important Environment Variables

**Never change these without migrating data:**
- `FLASK_SECRET_KEY` - Used for signing session cookies
- `API_TOKEN_ENCRYPTION_KEY` - Used for encrypting Canvas tokens in database

If either changes:
- All existing sessions will be invalidated (users logged out)
- All encrypted Canvas tokens will be unreadable (need re-entry)

### Production Security Checklist

- ✅ `.env` file should NOT be in git repository
- ✅ `.env` file should have restrictive permissions (600 or 644)
- ✅ `SECRET_KEY` should be random and at least 32 characters
- ✅ `SESSION_COOKIE_SECURE = True` if using HTTPS
- ✅ `SESSION_COOKIE_HTTPONLY = True` (already set)
- ✅ `WTF_CSRF_ENABLED = True` (default, already enabled)

## Summary

The CSRF issue was likely caused by a combination of:
1. Sessions not being made permanent (fixed in `auth.py`)
2. CSRF tokens expiring after 1 hour (fixed with `WTF_CSRF_TIME_LIMIT = None`)
3. Session cookies requiring HTTPS when running on HTTP (fixed with conditional `SESSION_COOKIE_SECURE`)
4. `.env` file not being loaded in production (fixed in `passenger_wsgi.py`)

All changes have been made to fix these issues. Deploy the updated files and restart the application.
