# Render.com Environment Variables Configuration

This document outlines all environment variables needed for deploying the Flask Grade Tracker on Render.com.

## Quick Start

1. Create a `render.yaml` file in your repository root (already provided)
2. Push to GitHub
3. Connect your repository to Render.com
4. Set the following environment variables in the Render dashboard

## Environment Variables

### Core Flask Configuration

| Variable | Value | Description |
|----------|-------|-------------|
| `FLASK_ENV` | `production` | Sets Flask to production mode |
| `FLASK_APP` | `app.py` | Main application file |
| `PORT` | `5000` | Port where the app runs (Render sets this) |
| `PYTHONUNBUFFERED` | `1` | Ensures Python output is logged immediately |
| `PYTHONDONTWRITEBYTECODE` | `1` | Prevents creation of .pyc files |

### Database Configuration

#### Option 1: Using Render PostgreSQL (Recommended)

```yaml
DATABASE_URL: postgresql://[user]:[password]@[host]:5432/[database]
```

Set up a PostgreSQL database on Render and get the connection string from the dashboard.

**Note:** If using PostgreSQL, you may need to modify database schema if currently using MySQL-specific features.

#### Option 2: Using Render MySQL

```yaml
DATABASE_URL: mysql+pymysql://[user]:[password]@[host]:3306/[database]
```

### Cache & Sessions (Render Redis)

| Variable | Value | Description |
|----------|-------|-------------|
| `CACHE_TYPE` | `redis` | Use Redis for caching |
| `REDIS_URL` | From Render Redis service | Connection string to Redis instance |
| `CACHE_REDIS_URL` | Same as `REDIS_URL` | Redis URL for Flask-Caching |
| `RATELIMIT_STORAGE_URL` | Same as `REDIS_URL` | Redis URL for rate limiting |

The `render.yaml` file automatically connects to Render's managed Redis service.

### Security (Set in Render Dashboard - DO NOT commit to git)

| Variable | Description |
|----------|-------------|
| `FLASK_SECRET_KEY` | Secret key for Flask sessions. Generate with: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `API_TOKEN_ENCRYPTION_KEY` | Key for encrypting Canvas API tokens. Should be base64-encoded 32-byte key |
| `MAIL_USERNAME` | Email address for sending notifications (optional) |
| `MAIL_PASSWORD` | Email password or app-specific password (optional) |

### Email Configuration (Optional)

| Variable | Value | Default |
|----------|-------|---------|
| `MAIL_SERVER` | `smtp.gmail.com` | SMTP server address |
| `MAIL_PORT` | `587` | SMTP port |
| `MAIL_USE_TLS` | `true` | Use TLS for SMTP |
| `MAIL_USERNAME` | Your email | Gmail address if using Gmail |
| `MAIL_PASSWORD` | App-specific password | Gmail app password |

### HTTPS & Security

| Variable | Value | Description |
|----------|-------|-------------|
| `USE_HTTPS` | `true` | Enable HTTPS (Render provides free SSL) |
| `SESSION_COOKIE_SECURE` | `true` | Only send cookies over HTTPS |
| `SESSION_COOKIE_HTTPONLY` | `true` | Prevent JavaScript from accessing cookies |

### Logging

| Variable | Value | Default |
|----------|-------|---------|
| `LOG_LEVEL` | `INFO`, `DEBUG`, or `ERROR` | `INFO` |

### Feature Flags

| Variable | Value | Description |
|----------|-------|-------------|
| `ENABLE_NOTIFICATIONS` | `true` or `false` | Enable/disable notifications |
| `ENABLE_ANALYTICS` | `true` or `false` | Enable/disable analytics |
| `ENABLE_MOBILE_OPTIMIZATION` | `true` or `false` | Enable/disable mobile optimizations |

## Setting Environment Variables in Render Dashboard

1. Log in to Render.com
2. Go to your service
3. Click "Environment" tab
4. Add each variable:
   - For sensitive data (keys, passwords): Add as "Secret"
   - For regular config: Add as "Environment Variable"

### Secrets vs Environment Variables

**Secrets** (hidden, not in logs):
- `FLASK_SECRET_KEY`
- `API_TOKEN_ENCRYPTION_KEY`
- `MAIL_PASSWORD`
- `DATABASE_URL` (contains password)
- `REDIS_URL` (contains password)

**Environment Variables** (visible in logs):
- `FLASK_ENV`
- `LOG_LEVEL`
- Feature flags
- Other non-sensitive config

## PostgreSQL vs MySQL Considerations

### If using PostgreSQL (Default in render.yaml):

```python
# No changes needed - SQLAlchemy supports both
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

### If using MySQL:

```python
# Keep PyMySQL in requirements.txt
DATABASE_URL=mysql+pymysql://user:password@host:3306/dbname
```

If your schema has MySQL-specific features, test thoroughly before deploying.

## Redis Connection String Format

Render provides connection strings like:
```
redis://:[password]@[host]:[port]
```

Set both `REDIS_URL` and `CACHE_REDIS_URL` to this value.

## Verification Checklist

After setting environment variables:

- [ ] Flask starts without configuration errors
- [ ] Database connection works
- [ ] Redis connection works (cache operations succeed)
- [ ] HTTPS is working (check certificate)
- [ ] Health check endpoint (`/health`) returns 200
- [ ] Logs are properly written to `/app/logs`
- [ ] Email sending works (if enabled)

## Troubleshooting

### "Connection refused" errors
- Check that database/redis services are deployed first
- Verify connection strings in environment variables
- Check that services are in the same Render region

### "Permission denied" writing to logs
- The app runs as non-root user `appuser`
- Ensure `/app/logs` directory has write permissions
- Check that the disk mount is properly configured

### High memory usage
- Redis may need memory limit increase
- Consider upgrading Render plan for more resources
- Check for memory leaks in application

### Slow builds
- Update requirements.txt to remove unnecessary packages
- Use `requirements-render.txt` with only production dependencies
- Consider using smaller base Docker image

## Auto-Deploy

Once this repository is connected to Render:
- Every push to your main branch triggers a new deploy
- Previous deployments are preserved for quick rollback
- Render handles SSL certificate renewal automatically

## Support

For Render.com specific issues: https://render.com/docs
For Flask configuration: https://flask.palletsprojects.com/
