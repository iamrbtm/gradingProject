# Quick Reference: Canvas Sync Log Retrieval

## TL;DR - Get Logs Now

The logs are already mapped to your host machine at: **`./logs/canvas_sync/`**

```bash
# View Canvas sync logs in real-time
tail -f ./logs/canvas_sync/operations.log
tail -f ./logs/canvas_sync/api_calls.log
tail -f ./logs/canvas_sync/errors.log
tail -f ./logs/canvas_sync/progress.log
```

## Log Files You Can Access

| File | Purpose | Access |
|------|---------|--------|
| `operations.log` | Main sync operations | `./logs/canvas_sync/operations.log` |
| `api_calls.log` | Canvas API requests | `./logs/canvas_sync/api_calls.log` |
| `database.log` | Database operations | `./logs/canvas_sync/database.log` |
| `errors.log` | Error tracking | `./logs/canvas_sync/errors.log` |
| `progress.log` | Progress updates | `./logs/canvas_sync/progress.log` |

## Common Commands

### Monitor in Real-Time
```bash
# Watch operations
tail -f logs/canvas_sync/operations.log

# Follow progress
tail -f logs/canvas_sync/progress.log

# Watch errors as they happen
tail -f logs/canvas_sync/errors.log

# Watch API calls
tail -f logs/canvas_sync/api_calls.log
```

### Search Logs
```bash
# Find all errors
cat logs/canvas_sync/errors.log

# Find activity for user 123
grep "user_id: 123" logs/canvas_sync/operations.log

# Find slow API calls
grep "duration_ms" logs/canvas_sync/api_calls.log | sort -t: -k2 -rn | head -10

# Count course operations
grep "Course" logs/canvas_sync/database.log | wc -l
```

### Copy Logs
```bash
# Copy all Canvas sync logs to a backup
cp -r logs/canvas_sync backup_logs/

# Archive and compress
tar -czf canvas_sync_logs_$(date +%Y%m%d_%H%M%S).tar.gz logs/canvas_sync/

# Copy specific log file
cp logs/canvas_sync/errors.log ./errors_backup.log
```

## Docker Container Access

If logs aren't in `./logs/` for some reason:

```bash
# Access from running container
docker exec gradetracker-web ls -la /app/logs/canvas_sync/

# View logs from container
docker exec gradetracker-web tail -f /app/logs/canvas_sync/operations.log

# Copy from container to host
docker cp gradetracker-web:/app/logs/canvas_sync ./logs_from_container
```

## File Locations Summary

```
Your Project Root:
├── logs/
│   └── canvas_sync/
│       ├── operations.log         ← Main Canvas sync log
│       ├── api_calls.log          ← API request/response log
│       ├── database.log           ← Database operations log
│       ├── errors.log             ← Error tracking log
│       └── progress.log           ← Progress updates log
└── docker-compose.yml             ← Already has: ./logs:/app/logs
```

## What Each Log Contains

**operations.log**
- Sync start/end
- User validation
- Course processing
- Completion summary

**api_calls.log**
- API endpoints called
- Response times
- Success/failure status

**database.log**
- Courses created/updated
- Assignments created/updated
- Categories created

**errors.log**
- All errors that occurred
- User and context
- Full error details

**progress.log**
- Real-time progress %
- Current item
- Elapsed time

## Verify Volume Mapping

```bash
# Check docker-compose has volume mapped
cat docker-compose.yml | grep "logs:/app/logs"

# Verify on running container
docker inspect gradetracker-web | grep -A 5 '"logs"'

# List what's actually mounted
docker exec gradetracker-web ls -la /app/logs/canvas_sync/
```

## Troubleshooting

**Logs not showing up?**
```bash
# Make sure containers are running
docker-compose ps

# Check container is healthy
docker-compose logs web

# Verify directory exists in container
docker exec gradetracker-web mkdir -p /app/logs/canvas_sync

# Check permissions
docker exec gradetracker-web ls -la /app/logs/
```

**Can't find logs directory?**
```bash
# Your logs should be here
pwd
ls -la logs/

# If not, check docker volume
docker volume ls | grep logs

# Inspect the volume
docker volume inspect gradetracker-mysql-data
```

**Logs taking too much space?**
```bash
# Check size
du -sh logs/canvas_sync/

# Archive old logs
tar -czf archive_$(date +%Y%m%d).tar.gz logs/canvas_sync/

# Manually cleanup old rotated logs
find logs/canvas_sync -name "*.log.[0-9]*" -mtime +7 -delete
```

That's it! Your Canvas sync logs are ready to access from `./logs/canvas_sync/`
