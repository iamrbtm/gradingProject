# Canvas Sync Metrics API Documentation

## Overview

The Canvas Sync Metrics API provides REST endpoints for querying Canvas sync performance metrics and managing log files.

## Base URL

```
/api/canvas/metrics
```

## Endpoints

### 1. Get Specific Sync Metrics

**GET** `/sync/<sync_id>`

Retrieve detailed metrics for a specific sync operation by database ID.

**Parameters:**
- `sync_id` (path, required): Database ID of the sync record

**Response:**
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

### 2. Get Sync by Task ID

**GET** `/sync/task/<task_id>`

Retrieve metrics for a specific sync by Celery task ID.

**Parameters:**
- `task_id` (path, required): Celery task ID

**Response:** Same as endpoint #1

**Example:**
```bash
curl http://localhost:5000/api/canvas/metrics/sync/task/abc123def456
```

### 3. Get User Summary

**GET** `/user/<user_id>/summary`

Get aggregated sync statistics for a specific user.

**Parameters:**
- `user_id` (path, required): User ID
- `days` (query, optional): Number of days to look back (default: 7)

**Response:**
```json
{
  "user_id": 42,
  "period_days": 7,
  "total_syncs": 15,
  "successful_syncs": 14,
  "failed_syncs": 1,
  "success_rate": 93.3,
  "total_duration_seconds": 3150.5,
  "average_duration_seconds": 210.0,
  "total_courses_processed": 350,
  "total_assignments_processed": 5200,
  "total_api_calls": 18500,
  "total_api_failures": 5,
  "recent_error": "Connection timeout"
}
```

### 4. Get User Syncs List

**GET** `/user/<user_id>/syncs`

Get all syncs for a specific user with pagination and filtering.

**Parameters:**
- `user_id` (path, required): User ID
- `limit` (query, optional): Maximum results (default: 50, max: 500)
- `status` (query, optional): Filter by status (completed, failed, in_progress, partial)

**Response:**
```json
{
  "user_id": 42,
  "count": 15,
  "syncs": [
    {
      "id": 15,
      "sync_task_id": "task123",
      "sync_status": "completed",
      "sync_start_time": "2025-12-22T10:15:00",
      "total_duration_seconds": 210.5,
      "courses_processed": 25
    }
    // ... more syncs
  ]
}
```

### 5. Get Global Summary

**GET** `/summary`

Get Canvas sync statistics across all users.

**Parameters:**
- `days` (query, optional): Number of days to look back (default: 7)

**Response:**
```json
{
  "period_days": 7,
  "total_syncs": 250,
  "successful_syncs": 240,
  "failed_syncs": 10,
  "success_rate": 96.0,
  "total_duration_seconds": 52500.0,
  "average_duration_seconds": 210.0,
  "total_courses_processed": 8500,
  "total_assignments_processed": 125000,
  "total_api_calls": 450000,
  "total_api_failures": 150,
  "average_api_call_duration_ms": 125.5,
  "unique_users": 42
}
```

### 6. Get Recent Syncs

**GET** `/recent`

Get the most recently completed sync operations.

**Parameters:**
- `limit` (query, optional): Maximum results (default: 20, max: 100)

**Response:**
```json
{
  "count": 20,
  "syncs": [
    {
      "id": 250,
      "sync_task_id": "task250",
      "user_id": 42,
      "sync_status": "completed",
      "sync_start_time": "2025-12-22T10:15:00",
      "total_duration_seconds": 210.5
    }
    // ... more syncs
  ]
}
```

### 7. Get Failed Syncs

**GET** `/failed`

Get failed sync operations for debugging.

**Parameters:**
- `limit` (query, optional): Maximum results (default: 20, max: 100)
- `days` (query, optional): Only include failures from last N days (default: 7)

**Response:**
```json
{
  "count": 2,
  "period_days": 7,
  "syncs": [
    {
      "id": 248,
      "sync_task_id": "task248",
      "user_id": 35,
      "sync_status": "failed",
      "sync_start_time": "2025-12-22T08:00:00",
      "error_message": "Canvas API timeout after 3 retries"
    }
    // ... more failed syncs
  ]
}
```

### 8. Get Performance Statistics

**GET** `/performance`

Get aggregated performance statistics for completed syncs.

**Parameters:**
- `days` (query, optional): Number of days to look back (default: 30)

**Response:**
```json
{
  "period_days": 30,
  "sync_count": 450,
  "duration": {
    "min_seconds": 45.2,
    "max_seconds": 1200.5,
    "avg_seconds": 210.0,
    "total_seconds": 94500.0
  },
  "api_calls": {
    "total": 945000,
    "avg_per_sync": 2100.0
  },
  "database": {
    "total_operations": 945000,
    "avg_per_sync": 2100.0
  },
  "items_processed": {
    "total_courses": 11250,
    "total_assignments": 168750,
    "total_submissions": 843750
  }
}
```

### 9. Get Log Cleanup Status

**GET** `/logs/cleanup-status`

Get information about log file sizes and archives.

**Response:**
```json
{
  "timestamp": "2025-12-22T10:30:00",
  "log_files": [
    {
      "name": "operations.log",
      "size_mb": 45.2,
      "modified": "2025-12-22T10:30:00"
    },
    {
      "name": "api_calls.log",
      "size_mb": 32.1,
      "modified": "2025-12-22T10:30:00"
    }
  ],
  "archives": [
    {
      "name": "operations_20251215_090000.tar.gz",
      "size_mb": 8.5,
      "created": "2025-12-15T09:00:00"
    }
  ],
  "total_log_size_mb": 125.5,
  "total_archive_size_mb": 45.3
}
```

### 10. Trigger Manual Log Cleanup

**POST** `/logs/cleanup`

Manually trigger the log cleanup task.

**Parameters:**
- `max_lines` (query, optional): Max lines per log file (default: 10000)
- `archive_days` (query, optional): Archive files older than N days (default: 7)
- `delete_days` (query, optional): Delete archives older than N days (default: 30)

**Response:**
```json
{
  "status": "started",
  "task_id": "cleanup-task-123",
  "message": "Log cleanup task triggered"
}
```

**Example:**
```bash
curl -X POST "http://localhost:5000/api/canvas/metrics/logs/cleanup?max_lines=5000&archive_days=14"
```

### 11. Health Check

**GET** `/health`

Check if the metrics system is healthy.

**Response:**
```json
{
  "timestamp": "2025-12-22T10:30:00",
  "status": "healthy",
  "database": "healthy",
  "logs_directory": "present"
}
```

## Error Responses

All endpoints return standard error responses:

```json
{
  "error": "Error message description"
}
```

Common status codes:
- `200` - Success
- `404` - Resource not found
- `500` - Server error

## Usage Examples

### Get performance summary for last 14 days
```bash
curl "http://localhost:5000/api/canvas/metrics/summary?days=14"
```

### Get all failed syncs from last 30 days
```bash
curl "http://localhost:5000/api/canvas/metrics/failed?days=30&limit=50"
```

### Get user performance metrics
```bash
curl "http://localhost:5000/api/canvas/metrics/user/42/summary?days=7"
```

### Get recent syncs (last 30)
```bash
curl "http://localhost:5000/api/canvas/metrics/recent?limit=30"
```

### Trigger log cleanup
```bash
curl -X POST "http://localhost:5000/api/canvas/metrics/logs/cleanup"
```

## Integration Examples

### Python
```python
import requests

# Get user summary
response = requests.get(
    'http://localhost:5000/api/canvas/metrics/user/42/summary',
    params={'days': 7}
)
summary = response.json()
print(f"Success Rate: {summary['success_rate']:.1f}%")
```

### JavaScript/Node.js
```javascript
// Get global summary
const response = await fetch('/api/canvas/metrics/summary?days=7');
const summary = await response.json();
console.log(`Total Syncs: ${summary.total_syncs}`);
```

### cURL Monitoring Script
```bash
#!/bin/bash
while true; do
  status=$(curl -s http://localhost:5000/api/canvas/metrics/health)
  failed=$(curl -s http://localhost:5000/api/canvas/metrics/failed?days=1)
  
  if [ $(echo $failed | jq '.count') -gt 0 ]; then
    echo "Alert: Failed syncs detected!"
  fi
  
  sleep 3600  # Check every hour
done
```

## Rate Limiting

There is currently no rate limiting on these endpoints. For production use, consider implementing:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(app, key_func=get_remote_address)
canvas_metrics_bp.before_request(limiter.limit("100 per hour"))
```

## Authentication

Currently, these endpoints are not authenticated. For production, add authentication:

```python
from flask_login import login_required

@canvas_metrics_bp.route('/summary')
@login_required
def get_global_summary():
    # ... endpoint code
```

## Dashboard Integration

These endpoints are designed to power dashboards. Example dashboard data structure:

```python
dashboard_data = {
    'summary': requests.get('/api/canvas/metrics/summary').json(),
    'recent': requests.get('/api/canvas/metrics/recent?limit=10').json(),
    'failed': requests.get('/api/canvas/metrics/failed?days=7').json(),
    'performance': requests.get('/api/canvas/metrics/performance?days=30').json(),
    'logs': requests.get('/api/canvas/metrics/logs/cleanup-status').json(),
}
```

