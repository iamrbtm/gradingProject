# Canvas Sync Logging & Monitoring - Quick Start Guide

## 📦 What's New

You now have a complete enterprise-grade monitoring system for Canvas sync operations with:

1. **5 Specialized Log Files** (in `./logs/canvas_sync/`)
   - `operations.log` - Main sync operations
   - `api_calls.log` - Canvas API requests
   - `database.log` - Database operations
   - `errors.log` - Error tracking
   - `progress.log` - Real-time progress

2. **Log Analysis Script** (`analyze_canvas_logs.py`)
   - Parse and summarize logs automatically
   - Generate performance reports
   - Export data as JSON

3. **Automatic Log Cleanup** (`app/tasks/log_cleanup.py`)
   - Archive old logs daily
   - Clean up oversized log files
   - Delete old archives
   - Runs automatically at 2:00 AM

4. **Performance Metrics Database** (`CanvasSyncMetrics`)
   - Track sync duration, API calls, errors
   - Query sync history by user/date
   - Generate dashboards and reports

## 🚀 Quick Start (5 minutes)

### 1. View Current Logs

```bash
# Real-time log monitoring
tail -f ./logs/canvas_sync/operations.log
tail -f ./logs/canvas_sync/errors.log

# Search logs
grep "error_message" logs/canvas_sync/errors.log
grep "user_id: 123" logs/canvas_sync/operations.log
```

### 2. Analyze Logs

```bash
# Generate text report
python analyze_canvas_logs.py

# Generate JSON report
python analyze_canvas_logs.py --json
```

### 3. Check Metrics Database

```bash
# Flask shell
flask shell

# Query recent syncs
from app.models import CanvasSyncMetrics
syncs = CanvasSyncMetrics.query.order_by(
    CanvasSyncMetrics.sync_start_time.desc()
).limit(10).all()

for sync in syncs:
    print(f"{sync.sync_task_id}: {sync.sync_status} ({sync.total_duration_seconds}s)")
```

## 📊 Key Files Created

| File | Purpose | Location |
|------|---------|----------|
| `analyze_canvas_logs.py` | Log analysis tool | Root directory |
| `app/tasks/log_cleanup.py` | Cleanup scheduler | App tasks |
| `app/services/canvas_sync_metrics.py` | Metrics tracking | App services |
| `migrations/add_canvas_sync_metrics.py` | Database migration | Migrations |
| `CANVAS_SYNC_LOGGING_ENHANCEMENTS.md` | Full documentation | Root directory |

## 🔧 Setup Instructions

### 1. Create Log Directory (if needed)

```bash
mkdir -p ./logs/canvas_sync
chmod 755 ./logs/canvas_sync
```

### 2. Create Database Table

```bash
python -c "from app import db, create_app; \
           app = create_app(); \
           app.app_context().push(); \
           db.create_all()"
```

Or:
```bash
flask db upgrade
```

### 3. Enable Cleanup Schedule (Optional)

In your app initialization or config:

```python
from app.tasks.log_cleanup import register_cleanup_schedule

# In your Flask app creation
register_cleanup_schedule(celery_app)
```

## 📈 Common Usage Patterns

### Track a Sync Operation

```python
from app.services.canvas_sync_metrics import CanvasSyncMetricsTracker

tracker = CanvasSyncMetricsTracker(
    task_id='celery-123-abc',
    user_id=42,
    sync_type='all'
)

# Record operations during sync
tracker.record_course(created=True)
tracker.record_assignment(updated=True)
tracker.record_api_call(duration_ms=125.5)

# Mark complete
tracker.complete_success()  # or .complete_failure(error_message)
```

### Get Sync Summary

```python
from app.services.canvas_sync_metrics import get_sync_metrics_summary

# Last 7 days for user 42
summary = get_sync_metrics_summary(user_id=42, days=7)

print(f"Success Rate: {summary['success_rate']:.1f}%")
print(f"Total Courses: {summary['total_courses_processed']}")
print(f"Total Syncs: {summary['total_syncs']}")
```

### Get Global Summary

```python
from app.services.canvas_sync_metrics import get_all_sync_metrics_summary

summary = get_all_sync_metrics_summary(days=7)

print(f"Total Syncs: {summary['total_syncs']}")
print(f"Unique Users: {summary['unique_users']}")
print(f"Success Rate: {summary['success_rate']:.1f}%")
```

## 🐛 Debugging

### Log Location Problems

```bash
# Check where logs are being written
ls -la ./logs/canvas_sync/
du -sh ./logs/canvas_sync/

# Check Docker volume mapping
docker exec <container-name> ls -la /app/logs/canvas_sync/

# Copy logs from container
docker cp <container-name>:/app/logs ./logs_backup/
```

### Database Issues

```bash
# Check if table exists
mysql> SHOW TABLES LIKE 'canvas_sync_metrics';

# Check table structure
mysql> DESCRIBE canvas_sync_metrics;

# Count records
mysql> SELECT COUNT(*) FROM canvas_sync_metrics;
```

### Analysis Script Issues

```bash
# Check if logs exist before analyzing
python analyze_canvas_logs.py --log-dir ./logs/canvas_sync

# Debug with verbose output
python -u analyze_canvas_logs.py
```

## 📋 Log File Examples

### operations.log
```
[2025-12-22 10:15:30] INFO - Canvas Sync: task_id: abc123def456, event: sync_started, user_id: 42, sync_type: all
[2025-12-22 10:15:35] INFO - Canvas Sync: task_id: abc123def456, event: courses_fetched, count: 25
[2025-12-22 10:16:45] INFO - Canvas Sync: task_id: abc123def456, event: sync_completed, courses_processed: 25, assignments_synced: 340, elapsed_time_seconds: 75
```

### errors.log
```
[2025-12-22 10:20:15] ERROR - Canvas Sync Error: user_id: 42, error_message: Connection timeout, operation: fetch_courses, course_id: 123
```

### api_calls.log
```
[2025-12-22 10:15:32] INFO - Canvas API: method: GET, endpoint: /api/v1/courses, status_code: 200, duration_ms: 145.2, page: 1
```

## 🎯 Performance Tips

### Optimize Log Analysis
```bash
# For large log files, use grep to pre-filter
grep "2025-12-22" logs/canvas_sync/operations.log | python analyze_canvas_logs.py

# Or analyze specific date range
tail -n 10000 logs/canvas_sync/operations.log | analyze_canvas_logs.py
```

### Archive Old Logs Manually
```bash
# Create archive of current logs
tar -czf canvas_logs_backup.tar.gz ./logs/canvas_sync/

# Clear old logs (keep most recent)
find ./logs/canvas_sync/ -name "*.log*" -mtime +30 -delete
```

### Monitor Disk Usage
```bash
# Check current size
du -sh ./logs/canvas_sync/

# Set up daily check
0 0 * * * du -sh /path/to/logs/canvas_sync/ >> /var/log/log-size.txt
```

## 🔗 Integration with Canvas Sync

The logging system is **already integrated** into:
- ✅ `app/tasks/canvas_sync.py` - Sync task logging
- ✅ `app/services/canvas_sync_service.py` - Service logging
- ✅ `app/services/canvas_api_service.py` - API logging

No additional integration needed - logs start automatically when sync runs!

## 📚 Full Documentation

For complete details, see: **CANVAS_SYNC_LOGGING_ENHANCEMENTS.md**

Topics covered:
- Detailed setup instructions
- API integration examples
- Dashboard creation
- Troubleshooting guide
- Performance considerations

## 🆘 Need Help?

1. **Logs not being created?**
   - Check `./logs/canvas_sync/` directory exists
   - Verify file permissions (should be readable/writable)
   - Check Flask app initialization includes logging setup

2. **Analysis script not working?**
   - Ensure logs exist: `ls -la ./logs/canvas_sync/`
   - Run with explicit log directory: `python analyze_canvas_logs.py --log-dir ./logs/canvas_sync`

3. **Metrics table doesn't exist?**
   - Run: `python -c "from app import db, create_app; app = create_app(); app.app_context().push(); db.create_all()"`
   - Or: `flask db upgrade`

4. **Cleanup not running?**
   - Check Celery Beat is running: `celery -A celery_app inspect scheduled`
   - Manually trigger: `flask shell` → `from app.tasks.log_cleanup import cleanup_canvas_sync_logs; cleanup_canvas_sync_logs.delay()`

## ✨ What You Can Now Do

- 📊 **Analyze sync performance** over time
- 🔍 **Debug sync issues** with detailed logs
- ⚠️ **Track errors** by user and course
- 📈 **Monitor API performance** and rate limits
- 💾 **Query sync history** from database
- 🧹 **Automatically manage** log files
- 📱 **Build dashboards** from metrics data

All while logs stay organized and disk space is managed automatically!
