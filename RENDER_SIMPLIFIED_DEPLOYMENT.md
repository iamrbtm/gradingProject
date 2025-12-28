# Render.com Deployment - Updated Quick Start

## What Changed

Your `render.yaml` has been **simplified to use Render's native services**:

### Before
- Tried to define PostgreSQL and Redis as Docker services
- Required more complex IaC configuration
- PostgreSQL and Redis created via IaC (not ideal)

### Now (Better)
- `render.yaml` only defines the **Flask web service**
- PostgreSQL and Redis created manually in Render Dashboard
- Cleaner separation of concerns
- Uses Render's fully-managed database and cache services
- Easier to manage and update

## Quick Deployment Steps

### STEP 1: Create PostgreSQL Database (5 minutes)

```bash
1. Go to https://dashboard.render.com
2. Click "New" → "PostgreSQL"
3. Configure:
   - Name: gradetracker-db
   - Database: gradetracker
   - User: gradetracker_user
   - Region: US East (or your choice)
4. Click "Create Database"
5. 📌 COPY and save the "External Database URL"
   (you'll paste this as DATABASE_URL)
```

### STEP 2: Create Redis Cache (5 minutes)

```bash
1. Click "New" → "Redis"
2. Configure:
   - Name: gradetracker-redis
   - Region: US East (SAME as database)
   - Eviction Policy: allkeys-lru
3. Click "Create Redis"
4. 📌 COPY and save the "Redis URL"
   (you'll paste this as REDIS_URL)
```

### STEP 3: Push Code to GitHub

```bash
./github-setup.sh
./push-to-github.sh main "Add Render.com configuration"
```

### STEP 4: Create Web Service in Render

```bash
1. In Render Dashboard, click "New" → "Web Service"
2. Click "Connect GitHub"
3. Select your repository
4. Select branch: main
5. Click "Connect"
6. Configure:
   - Name: gradetracker
   - Runtime: Docker (auto-detected from render.yaml)
   - Build Command: (auto-detected)
   - Start Command: (auto-detected from render.yaml)
7. Click "Create Web Service"
```

### STEP 5: Set Environment Variables

```bash
In your service → "Environment" tab, add:

CRITICAL SECRETS (Set as "Secret" type - hidden from logs):
─────────────────────────────────────────────────────────
DATABASE_URL
  Paste the PostgreSQL External URL from Step 1
  Format: postgresql://user:password@host:5432/database

REDIS_URL
  Paste the Redis URL from Step 2
  Format: redis://:password@host:port

FLASK_SECRET_KEY
  Generate: python -c "import secrets; print(secrets.token_hex(32))"
  Generate a NEW random value, don't reuse old one

API_TOKEN_ENCRYPTION_KEY
  Use your existing encryption key
  (from your .env or config file)

OPTIONAL SECRETS:
─────────────────
MAIL_USERNAME
  Your email address (if using email notifications)

MAIL_PASSWORD
  Your email password or app-specific password

IMPORTANT:
──────────
- Set these as "Secret" type (not Environment Variable)
- They will be hidden from logs
- Cannot be viewed after creation
```

### STEP 6: Deploy!

```bash
Click "Deploy" in the Render Dashboard
OR
Push to GitHub: ./push-quick.sh "Your message"
(Auto-deploys if connected)
```

## File Structure

```
render.yaml
├── services:
│   └── web:
│       - name: gradetracker
│       - runtime: docker
│       - dockerfilePath: ./Dockerfile.render
│       - healthCheckPath: /health
│       - startCommand: gunicorn ...
│       - envVars: (basic config, no secrets)
│
├── STEP 1: Create PostgreSQL via Dashboard
├── STEP 2: Create Redis via Dashboard
└── STEP 5: Add DATABASE_URL and REDIS_URL as secrets
```

## Advantages of This Approach

✅ **Simpler Configuration**
- render.yaml only handles web service
- Cleaner and easier to maintain
- No Docker containers for DB/Cache

✅ **Better-Managed Services**
- Render handles all database maintenance
- Automatic backups
- Automatic security patches
- Point-in-time recovery available
- Automatic failover

✅ **Better Performance**
- Optimized Postgres & Redis instances
- Faster than containerized versions
- Better resource isolation
- Dedicated hardware (on paid plans)

✅ **Easier Scaling**
- Just change plan in Dashboard
- No rebuilding containers
- Instant plan changes

## Environment Variables Summary

### Must Set in Dashboard
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - Redis connection
- `FLASK_SECRET_KEY` - Flask sessions (generate new)
- `API_TOKEN_ENCRYPTION_KEY` - Canvas token encryption

### Already in render.yaml (no need to set)
- `FLASK_ENV=production`
- `FLASK_APP=app.py`
- `USE_HTTPS=true`
- `SESSION_COOKIE_SECURE=true`
- `LOG_LEVEL=INFO`

### Optional
- `MAIL_USERNAME` - Email notifications
- `MAIL_PASSWORD` - Email notifications

## Troubleshooting

### "Health check failing"
```
Solution:
1. Wait 1-2 minutes for services to start
2. Check DATABASE_URL and REDIS_URL are set
3. Check FLASK_SECRET_KEY is set
4. View logs: Service → Logs tab
```

### "Cannot connect to database"
```
Solution:
1. Verify DATABASE_URL is correct
2. Check PostgreSQL service is running
3. Wait for PostgreSQL to initialize (2-3 min)
4. Verify format: postgresql://user:pass@host:5432/db
```

### "Cannot connect to Redis"
```
Solution:
1. Verify REDIS_URL is correct
2. Check Redis service is running
3. Wait for Redis to initialize
4. Verify format: redis://:password@host:port
```

### "Services won't start"
```
Solution:
1. Check all required variables are set
2. Use only "Secret" type for sensitive data
3. Ensure no typos in variable names
4. Check logs for error messages
5. Click "Deploy" again
```

## Costs (Unchanged)

```
Web Service (Standard):     $12/month
PostgreSQL (Starter):       $7/month
Redis (Starter):            $6/month
─────────────────────────────────────
Total:                      ~$25/month
```

## Migration from Previous Setup

If you already have the old docker-based `render.yaml`:

1. ✅ You already have this new version (I updated it)
2. Push to GitHub: `./push-to-github.sh main "Update render.yaml"`
3. Delete old web service in Render Dashboard
4. Create new services (PostgreSQL, Redis, Web) using steps above
5. Set environment variables
6. Done!

## Next Steps

1. **Now**: Push to GitHub
   ```bash
   ./push-to-github.sh main "Update Render.com configuration"
   ```

2. **Then**: Go to https://dashboard.render.com and:
   - Create PostgreSQL (Step 1)
   - Create Redis (Step 2)
   - Create Web Service (Step 4)
   - Set environment variables (Step 5)
   - Deploy!

3. **Finally**: Test your app at https://gradetracker.onrender.com

## Questions?

See the detailed guides:
- `DEPLOYMENT_SUMMARY.md` - Full instructions
- `RENDER_ENV_SETUP.md` - Environment variables
- `RENDER_BUILD_GUIDE.md` - Build optimization
- `00_START_HERE.md` - Quick overview

Your app will be live in 20 minutes! 🚀
