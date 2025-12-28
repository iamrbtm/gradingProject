# Render.com Deployment & Build Optimization Guide

## Architecture Overview

Your Flask Grade Tracker on Render.com will use:

```
┌─────────────────────────────────────────────────────────────┐
│                     Render.com Platform                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            Flask Web Service (gradetracker)         │   │
│  │  - Handles API requests                             │   │
│  │  - Serves static files                              │   │
│  │  - 3 gunicorn workers + gevent                       │   │
│  │  - Auto-scaling: 1-3 instances                       │   │
│  └─────────────────────────────────────────────────────┘   │
│           ↓                           ↓                       │
│  ┌────────────────────────┐  ┌──────────────────────────┐  │
│  │  PostgreSQL Database   │  │  Redis Cache Service     │  │
│  │  (15-alpine, 10GB)     │  │  (7-alpine, 512MB)       │  │
│  │  - Managed backups     │  │  - Automatic persistence │  │
│  │  - Point-in-time       │  │  - LRU eviction policy   │  │
│  │    recovery            │  │                          │  │
│  └────────────────────────┘  └──────────────────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Build Optimization

### 1. Dockerfile Optimization (Dockerfile.render)

✅ **What's optimized:**

- **Slim base image**: `python:3.11-slim-bookworm` reduces image from ~1GB to ~150MB
- **Single-stage build**: No build artifacts left in final image
- **Minimal dependencies**: Only system packages needed for runtime
- **Layer caching**: Requirements copied separately for better caching on dependency changes
- **Non-root user**: Runs as `appuser` for security
- **Health checks**: Built-in endpoint monitoring

### 2. Requirements Optimization

Instead of using full `requirements.txt` with dev dependencies, use:

```bash
# In render.yaml or on Render dashboard:
pip install -r requirements.txt
```

Or for even smaller images, create a lightweight requirements:

```bash
# Core production dependencies only
pip install Flask Flask-SQLAlchemy gunicorn gevent redis
```

### 3. Build Process

Render will:

1. Pull your code from GitHub
2. Build Docker image using `Dockerfile.render`
3. Run `pip install -r requirements.txt`
4. Copy application code
5. Create non-root user and set permissions
6. Run health check to verify startup
7. Deploy instance and update DNS

**Estimated build time**: 3-5 minutes

### 4. Caching Strategy

#### Docker Layer Caching

```dockerfile
# Good: Copy requirements first (cached until changed)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Then copy code (layers rebuild on code changes)
COPY . .
```

#### Application Caching

- **Redis**: Stores session data and cache (managed by Render)
- **Browser caching**: Static assets served with Cache-Control headers
- **HTTP caching**: Use ETags for API responses

### 5. Reducing Build Time

#### Strategy 1: Smaller Dependencies

Remove unused packages from `requirements.txt`:

```python
# Remove if not used:
- xgboost, lightgbm (large ML libraries)
- scikit-learn (if basic analytics only)
- reportlab, fpdf2 (if not exporting PDFs)
```

#### Strategy 2: Use Pre-built Wheels

```dockerfile
# The base image includes many pre-built wheels
# Builds faster than compiling from source
pip install --only-binary :all: numpy pandas
```

#### Strategy 3: Multi-stage Build (if needed)

```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
```

## Production Configuration

### 1. Instance Plan

**Current (render.yaml)**: `standard` plan
- Best for production workloads
- 0.5 CPU, 1GB RAM per instance
- Auto-scaling: 1-3 instances
- Load balanced

**Alternatives**:
- `starter`: $7/month, shared resources (for dev/testing)
- `pro`: $25/month+, dedicated resources

### 2. Auto-Scaling Rules

```yaml
scaling:
  minInstances: 1      # Always run at least 1
  maxInstances: 3      # Never exceed 3 instances
  targetMemoryPercent: 70    # Scale up if >70% memory used
  targetCPUPercent: 80       # Scale up if >80% CPU used
```

Adjust based on traffic patterns.

### 3. Zero-Downtime Deploys

Render automatically:
- Maintains previous version while building new one
- Runs health checks before removing old instance
- Routes traffic only to healthy instances
- Rolls back if health check fails

### 4. Resource Limits

| Resource | Standard Plan | Notes |
|----------|---------------|-------|
| Memory | 1GB per instance | Monitor with Render dashboard |
| CPU | 0.5 CPU | Shared with others |
| Disk | 100GB ephemeral | Lost on redeploy |
| Persistent disk | Configurable | For logs (1GB configured) |

## Performance Tuning

### 1. Gunicorn Configuration

```bash
gunicorn \
  --workers 3 \
  --worker-class gevent \
  --worker-connections 1000 \
  --timeout 120 \
  --access-logfile - \
  app:app
```

**Tuning hints**:
- `--workers`: Set to (2 × CPU cores) + 1
  - For 0.5 CPU: Use 2-3 workers
  - For 1+ CPU: Use 3-4 workers
- `--worker-class gevent`: Handles concurrent connections efficiently
- `--timeout`: Increase for long-running requests

### 2. Database Connection Pooling

```python
# In config.py
SQLALCHEMY_POOL_SIZE = 10        # Max pool size
SQLALCHEMY_MAX_OVERFLOW = 20     # Additional connections
SQLALCHEMY_POOL_RECYCLE = 3600   # Recycle after 1 hour
SQLALCHEMY_POOL_PRE_PING = True  # Test connection before use
```

### 3. Redis Configuration

The Redis instance is configured with:

```
--maxmemory 512mb
--maxmemory-policy allkeys-lru
--appendonly yes
```

This means:
- Maximum 512MB memory
- Least Recently Used items evicted when full
- Data persisted to disk

### 4. Static File Serving

For production, serve static files through:

1. **Render's static file handling**: Automatic for `/static` directory
2. **CDN integration**: Consider adding Cloudflare for faster delivery
3. **Cache headers**: Set in Flask app:

```python
@app.after_request
def set_cache_headers(response):
    response.headers['Cache-Control'] = 'public, max-age=3600'
    return response
```

## Monitoring & Logging

### 1. Built-in Monitoring

Render provides:
- CPU/memory usage graphs
- Network I/O graphs
- Deployment history
- Error logs from stderr/stdout

### 2. Application Logs

Logs are written to:
- `/app/logs` - Persisted disk for long-term storage
- stdout/stderr - Available in Render dashboard

### 3. Health Checks

Render monitors the `/health` endpoint:

```python
# In your Flask app:
@app.route('/health')
def health():
    return {'status': 'ok'}, 200
```

If health check fails 3 times, Render restarts the instance.

### 4. Recommended Additions

Add monitoring tools:

```bash
pip install sentry-sdk flask-debugtoolbar
```

Then in your app:

```python
import sentry_sdk
sentry_sdk.init("your-sentry-dsn", traces_sample_rate=1.0)
```

## Security Checklist

- [ ] All secrets set in Render dashboard (not in `.env` or code)
- [ ] `FLASK_SECRET_KEY` is random (not "dev-secret-key")
- [ ] `SESSION_COOKIE_SECURE` is `true` (HTTPS only)
- [ ] Database password is strong and unique
- [ ] API tokens are encrypted (API_TOKEN_ENCRYPTION_KEY set)
- [ ] CORS headers configured for production domain
- [ ] CSRF protection enabled
- [ ] Rate limiting enabled
- [ ] Secrets not logged (Render hides secrets from logs)

## Troubleshooting Common Issues

### Issue: "Cannot connect to database"

**Solutions**:
1. Verify database service is running (check Render dashboard)
2. Check DATABASE_URL format (postgresql:// for Render Postgres)
3. Verify credentials in environment variables
4. Test connection string locally first

### Issue: "Out of memory"

**Solutions**:
1. Increase instance plan to "pro" (more RAM)
2. Reduce Redis maxmemory if not needed
3. Profile application for memory leaks
4. Consider pagination for large data queries

### Issue: "Build takes too long"

**Solutions**:
1. Remove unused dependencies from requirements.txt
2. Use `requirements-render.txt` with only essentials
3. Cache Docker layers (ensure requirements.txt is copied early)
4. Consider using smaller base image

### Issue: "Health check failing"

**Solutions**:
1. Add logging to `/health` endpoint
2. Check database connection in health check
3. Increase `start_period` in render.yaml (currently 40s)
4. Review service logs for startup errors

## Deployment Steps

1. **Prepare repository**:
   ```bash
   git add render.yaml Dockerfile.render .dockerignore
   git commit -m "Add Render.com configuration"
   git push
   ```

2. **Connect to Render**:
   - Go to https://dashboard.render.com
   - Click "New" → "Web Service"
   - Connect GitHub repository
   - Select branch to deploy
   - Render detects `render.yaml` automatically

3. **Set environment variables**:
   - Go to service → "Environment" tab
   - Add all variables from `RENDER_ENV_SETUP.md`
   - Use "Secret" for sensitive values

4. **Deploy**:
   - Render auto-deploys on git push
   - Or click "Manual Deploy" in dashboard
   - Monitor build logs during deployment

5. **Verify**:
   - Check health endpoint: `https://your-service.onrender.com/health`
   - Test key features
   - Monitor logs for errors

## Cost Estimation

| Service | Plan | Price |
|---------|------|-------|
| Web Service | Standard | $7-12/month |
| PostgreSQL | Starter | $7/month |
| Redis | Starter | $6/month |
| **Total** | | **~$20-25/month** |

Can reduce to ~$13/month using "starter" plans for development.

## Next Steps

1. Create `render.yaml` ✅ (done)
2. Create `Dockerfile.render` ✅ (done)
3. Update `.dockerignore` ✅ (done)
4. Test locally with Docker first
5. Push to GitHub
6. Connect repo to Render.com
7. Set environment variables in dashboard
8. Deploy and test all features

## References

- Render.com Docs: https://render.com/docs
- Render Infrastructure as Code: https://render.com/docs/infrastructure-as-code
- Flask Deployment: https://flask.palletsprojects.com/deployment/
- Gunicorn Settings: https://docs.gunicorn.org/en/stable/settings.html
- PostgreSQL on Render: https://render.com/docs/databases
