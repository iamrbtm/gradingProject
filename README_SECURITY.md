# Security Setup Guide

## 🚨 CRITICAL SECURITY REQUIREMENTS

Your application has been updated with essential security fixes. Follow these steps immediately:

### 1. Environment Variables Setup

Create a `.env` file in your project root:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```bash
# Generate a secure Flask secret key
FLASK_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Generate API token encryption key
API_TOKEN_ENCRYPTION_KEY=$(python3 generate_encryption_key.py | grep "API_TOKEN_ENCRYPTION_KEY=" | cut -d'=' -f2)

# Set your database URL (NO hardcoded credentials!)
DATABASE_URL=mysql+pymysql://your_username:your_password@your_host:3306/your_database
```

### 2. Database Migration

Run the migration to encrypt existing Canvas tokens:

```bash
python3 migrate_canvas_tokens.py
```

### 3. Verify Security

Check that:
- ✅ No hardcoded credentials in `config.py`
- ✅ No credentials in `AGENTS.md`
- ✅ Canvas tokens are encrypted in database
- ✅ CSRF protection is enabled
- ✅ Environment variables are set

## Security Features Implemented

### ✅ API Token Encryption
- Canvas access tokens are now encrypted at rest
- Uses Fernet encryption (AES 128)
- Requires `API_TOKEN_ENCRYPTION_KEY` environment variable

### ✅ CSRF Protection
- All forms protected with CSRF tokens
- AJAX requests include CSRF headers
- Configurable via `WTF_CSRF_ENABLED`

### ✅ Secure Configuration
- No hardcoded secrets in code
- Environment variable validation
- Separate configs for dev/staging/production

## Security Best Practices

### Password Security
- Use strong, unique passwords
- Enable 2FA where possible
- Regular password rotation

### API Keys
- Rotate API keys regularly
- Use least-privilege access
- Monitor API usage

### Database Security
- Use parameterized queries (SQLAlchemy handles this)
- Regular backups
- Access logging enabled

### Network Security
- Use HTTPS in production
- Configure secure headers
- Rate limiting enabled

## Emergency Security Checklist

If you suspect a breach:

1. **IMMEDIATELY** rotate all API keys and passwords
2. Change the `API_TOKEN_ENCRYPTION_KEY`
3. Run `python3 migrate_canvas_tokens.py` to re-encrypt tokens
4. Check access logs for suspicious activity
5. Notify affected users

## Monitoring

Enable logging to monitor for security events:

```python
import logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger('security')
```

Watch for:
- Failed login attempts
- Unusual API usage
- Database access patterns
- Token decryption failures

## Compliance

For educational institutions:
- FERPA compliance for student data
- Regular security audits
- Data retention policies
- User consent for data collection