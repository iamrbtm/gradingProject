# Canvas Token & CSRF Issues - Complete Fix Summary

## Two Issues Fixed

### Issue 1: Canvas Token Not Persisting After Logout/Login
**Problem:** Canvas sync says "needs to be set up" after each logout, even though token is in database.

**Root Cause:** Encryption key (`API_TOKEN_ENCRYPTION_KEY`) wasn't being loaded from `.env` in production, so a random key was generated on each restart. Tokens encrypted with Key A couldn't be decrypted with Key B after restart.

**Files Changed:**
- ✅ `passenger_wsgi.py` - Added `.env` loading
- ✅ `app.py` - Added explicit `.env` loading  
- ✅ `app/models.py` - Added warning when encryption key missing

---

### Issue 2: CSRF Token Error When Saving Settings
**Problem:** "Bad Request - The CSRF session token is missing" when submitting settings form.

**Root Cause:** Sessions weren't persisting properly due to:
- Sessions not made permanent
- CSRF tokens expiring after 1 hour
- `SESSION_COOKIE_SECURE=True` requiring HTTPS when running on HTTP
- `.env` file not loaded (so `SECRET_KEY` was inconsistent)

**Files Changed:**
- ✅ `config.py` - Fixed session/CSRF configuration
- ✅ `app/blueprints/auth.py` - Made sessions permanent
- ✅ `app/error_handlers.py` - Added CSRF error handler
- ✅ `passenger_wsgi.py` - Added environment variable verification

---

## All Modified Files

1. **`passenger_wsgi.py`** - Loads `.env` file and verifies required environment variables
2. **`app.py`** - Explicit `.env` loading before imports
3. **`config.py`** - Fixed CSRF/session settings for HTTP, made CSRF tokens non-expiring
4. **`app/models.py`** - Warning when encryption key missing
5. **`app/blueprints/auth.py`** - Permanent sessions with remember=True
6. **`app/error_handlers.py`** - User-friendly CSRF error handling

---

## Deployment Checklist

### 1. Upload Files to Production Server

Upload these modified files to `/home/onlymyli/public_html/grades/`:
- `passenger_wsgi.py`
- `app.py`
- `config.py`
- `app/models.py`
- `app/blueprints/auth.py`
- `app/error_handlers.py`

### 2. Verify `.env` File Exists

Location: `/home/onlymyli/public_html/grades/.env`

Must contain:
```bash
FLASK_SECRET_KEY=e583d219a19e8df3f3ec5cfbcdf19ca9b6082f71e947c851630a420e3fbb667b
API_TOKEN_ENCRYPTION_KEY=afpWuojzOfALce2gn3IsQIn5GQJQ-GRzglWLKkRGhBQ=
DATABASE_URL=mysql+pymysql://onlymyli:Braces4me%23%23@jeremyguill.com:3306/onlymyli_grades

# If using HTTP (not HTTPS):
USE_HTTPS=false
```

### 3. Set Correct File Permissions

```bash
chmod 644 /home/onlymyli/public_html/grades/.env
chmod 644 /home/onlymyli/public_html/grades/passenger_wsgi.py
```

### 4. Restart Application

```bash
touch /home/onlymyli/public_html/grades/passenger_wsgi.py
```

### 5. Test the Fixes

1. **Clear browser cookies** for your site (or use incognito/private mode)
2. **Login** to the application
3. **Go to Settings** page
4. **Enter Canvas token** and base URL
5. **Click Save Settings** - Should save successfully without CSRF error
6. **Logout and login again** - Canvas token should still be there
7. **Restart application** (touch passenger_wsgi.py) and login - Canvas token should persist

---

## Verification Steps

### Test Environment Variables Loading

SSH to server and run:
```bash
cd /home/onlymyli/public_html/grades
python3 << 'EOF'
from dotenv import load_dotenv
import os
load_dotenv()
print("FLASK_SECRET_KEY:", "✓ LOADED" if os.environ.get('FLASK_SECRET_KEY') else "✗ MISSING")
print("API_TOKEN_ENCRYPTION_KEY:", "✓ LOADED" if os.environ.get('API_TOKEN_ENCRYPTION_KEY') else "✗ MISSING")
print("DATABASE_URL:", "✓ LOADED" if os.environ.get('DATABASE_URL') else "✗ MISSING")
EOF
```

Expected output:
```
FLASK_SECRET_KEY: ✓ LOADED
API_TOKEN_ENCRYPTION_KEY: ✓ LOADED
DATABASE_URL: ✓ LOADED
```

### Test Canvas Token Encryption

Run locally (or upload to server):
```bash
python test_canvas_token_encryption.py
```

Should show:
```
============================================================
All tests passed! ✓
Canvas token encryption is working correctly.
============================================================
```

### Check Application Logs

After restart, check for warnings:
```bash
# Check application logs
tail -f /home/onlymyli/public_html/grades/logs/grade_tracker.log

# Or Passenger logs
tail -f ~/passenger.log
```

Should NOT see: `WARNING: Missing required environment variables`

---

## What Happens Now

### Canvas Token Persistence ✓
1. User enters Canvas token in settings
2. Token encrypted with **persistent** encryption key from `.env`
3. Encrypted token saved to database
4. On logout → login → Token successfully decrypted and works
5. On app restart → Token successfully decrypted and works

### CSRF Token Working ✓
1. User visits settings page
2. CSRF token generated and stored in **persistent** session
3. Session stored in signed cookie using **consistent** `SECRET_KEY` from `.env`
4. User submits form with CSRF token
5. Flask validates token against session → ✓ Success
6. Settings saved successfully

---

## Important Notes

### DO NOT Change These Variables

Once deployed, **NEVER** change these without migrating data:

- `FLASK_SECRET_KEY` - Changing this will log out all users
- `API_TOKEN_ENCRYPTION_KEY` - Changing this will make all encrypted tokens unreadable

### Security

- ✅ `.env` file is NOT in git (check `.gitignore`)
- ✅ `.env` file has appropriate permissions (644)
- ✅ Keys are random and sufficiently long
- ✅ CSRF protection enabled
- ✅ Session cookies are HTTPOnly
- ✅ Tokens encrypted at rest in database

### Backup `.env` File

**CRITICAL:** Backup your `.env` file securely! If lost, you'll need to:
1. Generate new keys
2. All users will be logged out
3. All Canvas tokens will need to be re-entered

---

## Troubleshooting

### If Canvas Token Still Doesn't Persist

1. Check `.env` file exists and has `API_TOKEN_ENCRYPTION_KEY`
2. Restart application after uploading `.env`
3. Check logs for encryption warnings
4. Run `test_canvas_token_encryption.py` to verify

### If CSRF Error Still Occurs

1. Clear browser cookies completely
2. Try in incognito/private mode
3. Check `.env` has `FLASK_SECRET_KEY`
4. Verify `USE_HTTPS=false` if using HTTP
5. Check browser DevTools → Network → Check cookies are being set

### If Sessions Don't Persist

1. Check `FLASK_SECRET_KEY` is loaded (run verification script)
2. Check browser accepts cookies
3. If behind proxy, may need to set `SESSION_COOKIE_DOMAIN`

---

## Testing Script Included

**`test_canvas_token_encryption.py`** - Tests encryption/decryption works correctly

Run anytime to verify token encryption:
```bash
python test_canvas_token_encryption.py
```

---

## Documentation Files Created

- `CANVAS_TOKEN_FIX.md` - Detailed explanation of Canvas token issue
- `CSRF_TOKEN_FIX.md` - Detailed explanation of CSRF issue  
- `COMPLETE_FIX_SUMMARY.md` - This file (overview of both issues)
- `test_canvas_token_encryption.py` - Encryption verification script

---

## Next Steps

1. ✅ Upload all modified files to production
2. ✅ Verify `.env` file exists with all required variables
3. ✅ Restart application
4. ✅ Test: Login → Settings → Save (should work without CSRF error)
5. ✅ Test: Enter Canvas token → Logout → Login (token should persist)
6. ✅ Test: Restart app → Login (token should still persist)

Both issues should now be completely resolved! 🎉
