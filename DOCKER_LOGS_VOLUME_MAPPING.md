# Docker Volume Mapping & Log Retrieval Guide

## Volume Mapping for Canvas Sync Logs

The Docker Compose setup includes volume mapping to persist and access Canvas sync logs from your host machine.

### Current Setup

In `docker-compose.yml`, the following volumes are mapped:

**Web Service:**
```yaml
volumes:
  - ./logs:/app/logs          # Application logs (including Canvas sync)
  - ./static:/app/static      # Static files
```

**Celery Worker:**
```yaml
volumes:
  - ./logs:/app/logs          # Shares the same logs directory
```

**Celery Beat:**
```yaml
volumes:
  - ./logs:/app/logs          # Shares the same logs directory
```

### Directory Structure

When you run the containers, the following log structure is created:

```
./logs/
├── canvas_sync/
│   ├── operations.log          # Main Canvas sync operations
│   ├── api_calls.log           # Canvas API requests/responses
│   ├── database.log            # Database operations
│   ├── errors.log              # Error tracking
│   └── progress.log            # Real-time progress
├── analytics/
│   ├── events.log
│   ├── predictions.log
│   └── notifications.log
├── ml/
│   └── operations.log
├── exports/
│   └── operations.log
├── celery/
│   └── tasks.log
├── application.log             # Main application log
├── errors.log                  # Application errors
├── performance.log             # Performance metrics
├── security.log                # Security events
└── .gitkeep
```

## Accessing Logs

### From Your Host Machine

Since the logs are volume-mapped to `./logs`, you can access them directly from your project directory:

```bash
# View the entire canvas_sync directory
ls -lah logs/canvas_sync/

# View specific Canvas sync log
cat logs/canvas_sync/operations.log

# Monitor in real-time
tail -f logs/canvas_sync/operations.log
tail -f logs/canvas_sync/api_calls.log
```

### From Inside Docker Container

If you need to access logs from inside a running container:

```bash
# Access web container
docker exec -it gradetracker-web bash
tail -f /app/logs/canvas_sync/operations.log

# Access Celery worker
docker exec -it gradetracker-celery bash
tail -f /app/logs/canvas_sync/operations.log
```

### Copy Logs to Host

To copy all logs from container to your host machine:

```bash
# Copy entire logs directory
docker cp gradetracker-web:/app/logs ./logs_backup

# Copy specific file
docker cp gradetracker-web:/app/logs/canvas_sync/operations.log ./operations_backup.log
```

## Real-Time Log Monitoring

### Monitor Canvas Sync Operations

```bash
# Watch main operations log
tail -f logs/canvas_sync/operations.log

# Follow with timestamps and line numbers
tail -fn100 logs/canvas_sync/operations.log

# Search for specific user
grep "user_id: 123" logs/canvas_sync/operations.log

# Watch for errors in real-time
tail -f logs/canvas_sync/errors.log
```

### Monitor API Calls

```bash
# Watch all API calls
tail -f logs/canvas_sync/api_calls.log

# Find slow API calls
grep "duration_ms" logs/canvas_sync/api_calls.log | sort -t: -k2 -rn | head -20

# Monitor specific endpoint
grep "/courses" logs/canvas_sync/api_calls.log
```

### Monitor Progress

```bash
# Watch progress updates
tail -f logs/canvas_sync/progress.log

# Get progress percentage only
tail -f logs/canvas_sync/progress.log | grep "progress_percent"
```

### Monitor Database Operations

```bash
# Watch database operations
tail -f logs/canvas_sync/database.log

# Count operations by type
grep "operation" logs/canvas_sync/database.log | sort | uniq -c

# Find all Course operations
grep "Course" logs/canvas_sync/database.log
```

## Log Analysis

### Find All Errors for a Specific Sync

```bash
# Get task ID from operations log
TASK_ID="canvas_sync_123_1703254534"

# Find all logs for this task
grep "$TASK_ID" logs/canvas_sync/*.log

# Just errors
grep "$TASK_ID" logs/canvas_sync/errors.log
```

### Find All Activity for a Specific User

```bash
USER_ID="123"

# All canvas sync activity for user
grep "user_id: $USER_ID" logs/canvas_sync/operations.log

# All API calls made by user
grep "user_id: $USER_ID" logs/canvas_sync/api_calls.log

# All errors for user
grep "user_id: $USER_ID" logs/canvas_sync/errors.log
```

### Track a Complete Sync Session

```bash
# Find when sync started
head -20 logs/canvas_sync/operations.log

# Extract task ID
grep "Starting Canvas sync" logs/canvas_sync/operations.log | head -1

# Monitor that task through all logs
TASK_ID="canvas_sync_123_1703254534"
echo "=== Operations ==="
grep "$TASK_ID" logs/canvas_sync/operations.log
echo "=== API Calls ==="
grep "$TASK_ID" logs/canvas_sync/api_calls.log | wc -l
echo "=== Database Ops ==="
grep "$TASK_ID" logs/canvas_sync/database.log | wc -l
echo "=== Progress ==="
grep "$TASK_ID" logs/canvas_sync/progress.log
echo "=== Errors ==="
grep "$TASK_ID" logs/canvas_sync/errors.log
```

## Log Rotation & Cleanup

### Understanding Log Rotation

Logs are automatically rotated when they exceed:
- `operations.log`: 50MB (keeps 10 backups)
- `api_calls.log`: 30MB (keeps 8 backups)
- `database.log`: 30MB (keeps 8 backups)
- `errors.log`: 20MB (keeps 10 backups)
- `progress.log`: 25MB (keeps 7 backups)

Rotated files are named: `filename.log.1`, `filename.log.2`, etc.

### View Rotated Logs

```bash
# List all canvas_sync logs (including rotated ones)
ls -lah logs/canvas_sync/

# View older rotated log
cat logs/canvas_sync/operations.log.1

# Search across all rotated logs
grep "error_message" logs/canvas_sync/errors.log*
```

### Archive Old Logs

```bash
# Create archive of old logs
tar -czf canvas_sync_logs_backup_$(date +%Y%m%d).tar.gz logs/canvas_sync/

# Archive with timestamp
mkdir -p logs_archive
mv logs/canvas_sync/operations.log.* logs_archive/
tar -czf logs_archive_$(date +%Y%m%d_%H%M%S).tar.gz logs_archive/
```

## Docker Compose Useful Commands

```bash
# Start containers and follow logs
docker-compose up -d
docker-compose logs -f web

# View logs from all services
docker-compose logs --tail=100

# View only Canvas sync service logs
docker-compose logs -f web celery-worker celery-beat

# Stop but keep logs
docker-compose stop

# Remove containers but keep logs (volumes persist)
docker-compose down

# Remove everything including logs
docker-compose down -v  # WARNING: Deletes volumes!
```

## Accessing Logs Programmatically

### Python Script to Analyze Logs

```python
import json
from pathlib import Path
from datetime import datetime

log_dir = Path("./logs/canvas_sync")

# Read recent operations
with open(log_dir / "operations.log") as f:
    last_10_lines = f.readlines()[-10:]
    for line in last_10_lines:
        print(line.strip())

# Count errors by type
errors = {}
with open(log_dir / "errors.log") as f:
    for line in f:
        if "operation" in line:
            # Parse and count
            print(line.strip())

# Analyze API performance
import statistics
durations = []
with open(log_dir / "api_calls.log") as f:
    for line in f:
        if "duration_ms" in line:
            # Extract duration and add to list
            pass

print(f"Average API duration: {statistics.mean(durations):.1f}ms")
```

## Troubleshooting Log Access

### Logs Directory Not Accessible

```bash
# Check permissions
ls -lad logs/

# Fix permissions if needed
chmod 755 logs/
chmod 755 logs/canvas_sync/

# Ensure containers have write access
docker-compose down
docker-compose up -d --force-recreate
```

### Logs Not Being Created

```bash
# Check if containers are running
docker-compose ps

# Check container logs for errors
docker-compose logs web

# Verify volume mapping
docker inspect gradetracker-web | grep -A 10 Mounts

# Verify log directory in container
docker exec gradetracker-web ls -la /app/logs/canvas_sync/
```

### Disk Space Issues

```bash
# Check log directory size
du -sh logs/

# Check individual log sizes
du -sh logs/canvas_sync/*

# Clean up old rotated logs
find logs/canvas_sync -name "*.log.[0-9]*" -mtime +30 -delete
```

## Best Practices

1. **Regular Backups**: Archive logs regularly
   ```bash
   tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/
   ```

2. **Monitor Log Size**: Keep track of log directory size
   ```bash
   watch -n 300 'du -sh logs/'
   ```

3. **Set Up Log Rotation**: Use the built-in rotation
   - Logs rotate automatically when size limits are reached
   - Old logs are kept with numeric suffixes

4. **Search Efficiently**: Use `grep` with proper patterns
   ```bash
   grep -h "error_message" logs/canvas_sync/errors.log* | sort | uniq -c
   ```

5. **Automate Analysis**: Create scripts to parse and analyze logs
   - Track success rates
   - Identify problematic courses
   - Monitor performance trends

## Summary

- **Logs are mapped to `./logs`** in your project directory
- **Canvas sync logs** are in `./logs/canvas_sync/`
- **5 specialized log files** capture different aspects
- **Access from host** using `tail -f logs/canvas_sync/operations.log`
- **Automatic rotation** prevents disk space issues
- **Search and analyze** using standard Linux tools

You can now easily retrieve, monitor, and analyze all Canvas sync operations!
