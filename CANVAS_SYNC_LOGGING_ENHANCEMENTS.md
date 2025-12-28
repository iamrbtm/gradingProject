# Canvas Sync Logging Enhancements

## Overview

This document describes the additional enhancements made to the Canvas sync logging and monitoring system beyond the core logging implementation.

## Completed Enhancements

### 1. Canvas Sync Log Analysis Tool 📊

**File**: `analyze_canvas_logs.py`

A comprehensive Python script for analyzing Canvas sync logs. This tool parses all 5 log files and generates detailed reports about sync performance.

#### Features
- **Operations Analysis**: Sync tasks, courses processed, assignments synced
- **API Analysis**: HTTP methods, status codes, request timing, pagination tracking
- **Database Analysis**: Operation counts by type, entities affected, batch operations
- **Error Analysis**: Error counts by user and course, recent error details
- **Progress Analysis**: Progress tracking by task, completion percentages
- **Export Capabilities**: Generate JSON reports for programmatic analysis

#### Usage

```bash
# Generate text report to console
python analyze_canvas_logs.py

# Specify custom log directory
python analyze_canvas_logs.py --log-dir /path/to/logs/canvas_sync

# Export as JSON for analysis
python analyze_canvas_logs.py --json

# Export to specific file
python analyze_canvas_logs.py --json --output custom_report.json
```

#### Output Example

```
================================================================================
CANVAS SYNC LOG ANALYSIS REPORT
Generated: 2025-12-22 10:15:30
================================================================================

📊 OPERATIONS SUMMARY
────────────────────────────────────────────────────────────────────────────
Total Operations Log Lines: 2,450
Sync Tasks Started: 15
Canvas Connections Tested: 15
Courses Processed: 87
Total Assignments Synced: 1,240
Total Elapsed Time: 3,450.25 seconds
Time Range: 2025-12-15 08:00:00 - 2025-12-22 10:00:00

🌐 API CALLS ANALYSIS
────────────────────────────────────────────────────────────────────────────
Total API Calls: 8,920
By HTTP Method:
  GET: 8,200
  POST: 450
  PUT: 270
Total Request Duration: 45,000.50 ms
Average Request Time: 5.05 ms
Paginated Requests: 420
Status Codes:
  200: 8,750
  429: 50
  500: 5
```

### 2. Log Cleanup and Archival Task 🗂️

**File**: `app/tasks/log_cleanup.py`

Automated Celery task for managing log files and archives.

#### Features
- **Auto-Archive**: Compress old log files to tar.gz archives
- **Log Cleanup**: Trim log files to keep only recent entries
- **Archive Deletion**: Delete very old archives to free disk space
- **Status Reporting**: Get information about log files and archives

#### Functions

```python
# Clean up logs (can be scheduled)
from app.tasks.log_cleanup import cleanup_canvas_sync_logs
result = cleanup_canvas_sync_logs.delay(
    max_log_lines=10000,
    archive_age_days=7,
    delete_age_days=30
)

# Get cleanup status
from app.tasks.log_cleanup import get_cleanup_status
status = get_cleanup_status()
print(status['total_log_size_mb'])  # Total size of log files
print(status['total_archive_size_mb'])  # Total size of archives
```

#### Default Schedule
- Runs daily at 2:00 AM
- Keeps 10,000 lines per log file
- Archives files after 7 days
- Deletes archives after 30 days

To register the schedule, add this to your Celery configuration:

```python
from app.tasks.log_cleanup import register_cleanup_schedule
register_cleanup_schedule(celery_app)
```

#### Manual Cleanup

```bash
# Via Flask shell
flask shell
>>> from app.tasks.log_cleanup import cleanup_canvas_sync_logs
>>> result = cleanup_canvas_sync_logs.delay()

# Check result
>>> result.get()
{
    'archived_files': 5,
    'cleaned_up_files': 5,
    'total_lines_removed': 45000,
    'deleted_archives': 2
}
```

### 3. Canvas Sync Metrics Database Table 📈

**Model**: `app/models.py::CanvasSyncMetrics`
**Service**: `app/services/canvas_sync_metrics.py`
**Migration**: `migrations/add_canvas_sync_metrics.py`

A comprehensive database table for tracking Canvas sync performance metrics.

#### Features
- **Performance Tracking**: Track duration, API calls, database operations
- **Statistics Collection**: Count courses, assignments, submissions processed
- **Error Tracking**: Store error messages and failure reasons
- **User Attribution**: Link syncs to user IDs
- **Time Analysis**: Start/end times for performance trending

#### Database Schema

```python
class CanvasSyncMetrics(db.Model):
    # Identifiers
    sync_task_id: str (unique)
    user_id: int (foreign key)
    
    # Timing
    sync_start_time: datetime
    sync_end_time: datetime
    total_duration_seconds: float
    
    # Status
    sync_status: str  # 'in_progress', 'completed', 'failed', 'partial'
    error_message: str
    
    # Statistics
    courses_processed: int
    assignments_processed: int
    submissions_processed: int
    grades_processed: int
    
    # API Metrics
    api_calls_made: int
    api_calls_failed: int
    total_api_duration_ms: float
    api_rate_limit_hits: int
    
    # Database Metrics
    db_operations: int
    db_duration_ms: float
```

#### Setup

```bash
# Create the table
python -c "from app import db, create_app; app = create_app(); app.app_context().push(); db.create_all()"

# Or with Flask CLI
flask db upgrade
```

#### Usage Examples

```python
from app.services.canvas_sync_metrics import (
    CanvasSyncMetricsTracker,
    get_sync_metrics_summary,
    get_all_sync_metrics_summary
)
from app.models import db

# Track a sync operation
tracker = CanvasSyncMetricsTracker(
    task_id='celery-task-123',
    user_id=42,
    sync_type='all'
)

# Record operations
tracker.record_course(created=True)
tracker.record_assignment(updated=True)
tracker.record_api_call(duration_ms=125.5)

# Complete the sync
try:
    tracker.complete_success()
except Exception as e:
    tracker.complete_failure(str(e))

# Get summary for a user (last 7 days)
summary = get_sync_metrics_summary(user_id=42, days=7)
print(f"Success Rate: {summary['success_rate']:.1f}%")
print(f"Total Courses: {summary['total_courses_processed']}")

# Get overall summary
overall = get_all_sync_metrics_summary(days=7)
print(f"Total Syncs: {overall['total_syncs']}")
print(f"Unique Users: {overall['unique_users']}")
```

#### API Response Format

```json
{
  "id": 1,
  "sync_task_id": "abc123def456",
  "user_id": 42,
  "sync_start_time": "2025-12-22T10:15:00",
  "sync_end_time": "2025-12-22T10:18:30",
  "total_duration_seconds": 210.5,
  "sync_status": "completed",
  "error_message": null,
  "sync_type": "all",
  "courses": {
    "processed": 25,
    "created": 2,
    "updated": 23
  },
  "assignments": {
    "processed": 340,
    "created": 15,
    "updated": 325
  },
  "api_metrics": {
    "calls_made": 1240,
    "calls_failed": 2,
    "total_duration_ms": 8450.5,
    "rate_limit_hits": 0
  }
}
```

## Integration Points

### With Canvas Sync Task

To integrate metrics tracking into your sync task:

```python
from app.services.canvas_sync_metrics import CanvasSyncMetricsTracker

@shared_task(bind=True)
def sync_canvas_data_task(self, user_id, sync_type='all', **kwargs):
    tracker = CanvasSyncMetricsTracker(
        task_id=self.request.id,
        user_id=user_id,
        sync_type=sync_type
    )
    
    try:
        # Your sync logic here
        courses = sync_courses(user_id)
        tracker.record_course(created=len(new_courses) > 0)
        
        # ... more sync operations
        
        return tracker.complete_success().to_dict()
    except Exception as e:
        return tracker.complete_failure(str(e)).to_dict()
```

### With Logging System

The metrics system works alongside the file-based logging:
- File logs provide detailed operation logs
- Database metrics provide searchable, queryable performance data
- Analysis scripts parse file logs for historical reports

## Monitoring and Dashboards

### Creating a Monitoring Dashboard

```python
from flask import jsonify
from app.services.canvas_sync_metrics import (
    get_all_sync_metrics_summary,
    CanvasSyncMetrics
)

@app.route('/api/canvas/sync/metrics')
def sync_metrics():
    """Get Canvas sync metrics dashboard data."""
    summary = get_all_sync_metrics_summary(days=7)
    
    # Get recent syncs
    recent = CanvasSyncMetrics.query.order_by(
        CanvasSyncMetrics.sync_start_time.desc()
    ).limit(10).all()
    
    return jsonify({
        'summary': summary,
        'recent_syncs': [m.to_dict() for m in recent],
    })
```

## Performance Considerations

### Log File Sizes

Expected log file growth rates:
- **operations.log**: ~100-200 KB per sync run
- **api_calls.log**: ~50-100 KB per sync run
- **database.log**: ~30-50 KB per sync run
- **errors.log**: ~5-10 KB per sync run (only errors)
- **progress.log**: ~10-20 KB per sync run

With automatic cleanup at 10,000 lines per file, each log file stays under 10-50 MB.

### Database Metrics

With daily syncs:
- ~365 records per user per year
- Indexed queries for user/date ranges are fast
- Archive old metrics every 1-2 years

### Archival Storage

Compressed archives reduce size by 80-90%:
- One week of logs (5 files): ~50-100 MB
- Compressed: ~5-10 MB
- 52 weeks of archives: ~250-500 MB per year

## Next Steps (Optional)

### Web Dashboard
Create a Flask route/template to visualize metrics in real-time:
- Line graphs of sync duration over time
- Bar charts of items processed
- Error rate tracking
- Performance improvements

### Slack Integration
Send critical errors to Slack:
```python
if metrics.sync_status == 'failed':
    send_slack_alert(f"Canvas sync failed: {metrics.error_message}")
```

### Email Reports
Generate weekly/monthly summary emails with metrics trends.

### Metrics Aggregation
Store daily aggregations for faster dashboard queries:
```python
# daily_metrics: sum of all user syncs for that day
```

## Troubleshooting

### Log Analysis Not Working
```bash
# Check if logs directory exists
ls -la ./logs/canvas_sync/

# Create if missing
mkdir -p ./logs/canvas_sync/

# Run analysis with verbose output
python analyze_canvas_logs.py --log-dir ./logs/canvas_sync
```

### Cleanup Task Not Running
```python
# Check Celery Beat schedule
celery -A celery_app inspect scheduled

# Or manually trigger cleanup
from app.tasks.log_cleanup import cleanup_canvas_sync_logs
result = cleanup_canvas_sync_logs.delay()
print(result.get())
```

### Metrics Not Saving
```python
# Check if CanvasSyncMetrics table exists
from app.models import db, CanvasSyncMetrics
from app import create_app

app = create_app()
with app.app_context():
    db.create_all()  # Ensure table exists
```

## Summary

The Canvas sync logging enhancements provide:

1. ✅ **File-based detailed logging** - 5 specialized log files with auto-rotation
2. ✅ **Analysis tooling** - Python script to parse and analyze logs
3. ✅ **Automatic cleanup** - Celery task to archive and clean old logs
4. ✅ **Performance metrics** - Database table for queryable sync statistics
5. ✅ **Integration ready** - Easy to add to existing sync operations

These tools enable:
- Real-time debugging during sync operations
- Historical performance analysis and trending
- Error tracking and debugging
- Capacity planning based on actual data
- User and course-level metrics attribution

