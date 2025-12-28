# Canvas Sync Monitoring System - Quick Reference Index

## 📚 Documentation Files

### Essential Reading (Start Here)
- **CANVAS_MONITORING_COMPLETE.md** - Complete system overview and summary
- **CANVAS_SYNC_LOGGING_QUICK_START.md** - 5-minute quick start guide

### Implementation & Integration
- **CANVAS_MONITORING_INTEGRATION.md** - How to integrate with your Flask app
- **CANVAS_METRICS_API.md** - REST API reference with examples

### Detailed Documentation
- **CANVAS_SYNC_LOGGING_ENHANCEMENTS.md** - Full feature documentation
- **FIX_METADATA_COLUMN.md** - Bug fix and workaround documentation
- **CANVAS_SYNC_LOGGING.md** - Original logging system documentation
- **DOCKER_LOGS_VOLUME_MAPPING.md** - Docker volume setup
- **LOG_RETRIEVAL_QUICK_REFERENCE.md** - Log access quick reference

## 🛠️ Core Files

### Scripts
- **analyze_canvas_logs.py** - Log analysis and parsing tool

### Services
- **app/services/canvas_sync_metrics.py** - Metrics tracking service
- **app/tasks/log_cleanup.py** - Log cleanup and archival task

### Models & API
- **app/models.py** - CanvasSyncMetrics database model
- **app/blueprints/canvas_metrics_api.py** - REST API endpoints

### Database
- **migrations/add_canvas_sync_metrics.py** - Database migration

## 🚀 5-Minute Setup

```bash
# 1. Create database table
python -c "from app import db, create_app; app = create_app(); app.app_context().push(); db.create_all()"

# 2. Register API in app/__init__.py (add this line):
from app.blueprints.canvas_metrics_api import register_canvas_metrics_api
register_canvas_metrics_api(app)

# 3. Test the system
curl http://localhost:5000/api/canvas/metrics/health

# 4. View real-time logs
tail -f logs/canvas_sync/operations.log

# 5. Analyze logs
python analyze_canvas_logs.py
```

## 📊 Available Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/canvas/metrics/health` | Health check |
| GET | `/api/canvas/metrics/summary` | Global summary |
| GET | `/api/canvas/metrics/recent` | Recent syncs |
| GET | `/api/canvas/metrics/failed` | Failed syncs |
| GET | `/api/canvas/metrics/performance` | Performance stats |
| GET | `/api/canvas/metrics/sync/<id>` | Specific sync |
| GET | `/api/canvas/metrics/sync/task/<id>` | By task ID |
| GET | `/api/canvas/metrics/user/<id>/summary` | User summary |
| GET | `/api/canvas/metrics/user/<id>/syncs` | User's syncs |
| GET | `/api/canvas/metrics/logs/cleanup-status` | Log status |
| POST | `/api/canvas/metrics/logs/cleanup` | Trigger cleanup |

## 📝 Log Files Location

```
logs/canvas_sync/
├── operations.log       # Main sync operations
├── api_calls.log        # Canvas API requests
├── database.log         # Database operations
├── errors.log           # Error tracking
├── progress.log         # Real-time progress
└── archives/            # Compressed log archives
```

## 🔧 Key Functions

### Track Metrics in Your Code

```python
from app.services.canvas_sync_metrics import CanvasSyncMetricsTracker

tracker = CanvasSyncMetricsTracker(task_id, user_id)
tracker.record_course(created=True)
tracker.complete_success()
```

### Query Metrics

```python
from app.services.canvas_sync_metrics import get_sync_metrics_summary

summary = get_sync_metrics_summary(user_id=42, days=7)
print(f"Success Rate: {summary['success_rate']:.1f}%")
```

### Analyze Logs

```bash
python analyze_canvas_logs.py          # Text report
python analyze_canvas_logs.py --json   # JSON export
```

### Clean Logs

```python
from app.tasks.log_cleanup import cleanup_canvas_sync_logs
result = cleanup_canvas_sync_logs.delay()
print(result.get())
```

## 🎯 Common Tasks

### View Real-Time Sync Operations
```bash
tail -f logs/canvas_sync/operations.log
```

### Find Errors
```bash
tail -100 logs/canvas_sync/errors.log
grep "user_id: 42" logs/canvas_sync/errors.log
```

### Check Performance
```bash
curl "http://localhost:5000/api/canvas/metrics/performance?days=30"
```

### Get User Summary
```bash
curl "http://localhost:5000/api/canvas/metrics/user/42/summary?days=7"
```

### Manual Log Cleanup
```bash
curl -X POST "http://localhost:5000/api/canvas/metrics/logs/cleanup"
```

### Generate Report
```bash
python analyze_canvas_logs.py > report.txt
python analyze_canvas_logs.py --json --output report.json
```

## 🐛 Troubleshooting

### Logs Not Creating?
```bash
mkdir -p logs/canvas_sync
chmod 755 logs/canvas_sync
```

### Database Table Missing?
```python
from app import db, create_app
app = create_app()
app.app_context().push()
db.create_all()
```

### API Not Responding?
```bash
curl http://localhost:5000/api/canvas/metrics/health
```

### Check Cleanup Status?
```bash
curl http://localhost:5000/api/canvas/metrics/logs/cleanup-status
```

## 📦 What's Tracked

- ✅ Sync timing (start, end, duration)
- ✅ Courses processed (created, updated, total)
- ✅ Assignments processed (created, updated, total)
- ✅ Submissions processed
- ✅ Grades updated
- ✅ API calls (count, failures, duration)
- ✅ Database operations (count, duration)
- ✅ Errors (type, message, user, course)
- ✅ User/course attribution
- ✅ Sync status (completed, failed, partial)

## 🔐 Production Checklist

- [ ] API blueprint registered
- [ ] Database table created
- [ ] Log directory exists
- [ ] Cleanup task scheduled
- [ ] Health endpoint working
- [ ] Metrics being recorded
- [ ] Logs being created
- [ ] Permissions set correctly
- [ ] Backups configured
- [ ] Monitoring set up

## 💡 Pro Tips

1. **Monitor Failures**: `curl /api/canvas/metrics/failed?days=1`
2. **Check Performance**: `curl /api/canvas/metrics/performance?days=7`
3. **User Analytics**: `curl /api/canvas/metrics/user/42/summary`
4. **Disk Usage**: `curl /api/canvas/metrics/logs/cleanup-status`
5. **Batch Analysis**: `python analyze_canvas_logs.py --json` then process JSON

## 📞 Support Resources

| Issue | Solution |
|-------|----------|
| Logs missing | See "Logs Not Creating?" above |
| Metrics not saving | See "Database Table Missing?" above |
| API 404 errors | Register blueprint in app/__init__.py |
| Cleanup not running | Check Celery Beat: `celery -A celery_app inspect scheduled` |
| High disk usage | Run cleanup: `curl -X POST /api/canvas/metrics/logs/cleanup` |

## 🎓 Learning Path

1. **Quick Setup** → CANVAS_SYNC_LOGGING_QUICK_START.md
2. **Integration** → CANVAS_MONITORING_INTEGRATION.md
3. **API Usage** → CANVAS_METRICS_API.md
4. **Full Details** → CANVAS_SYNC_LOGGING_ENHANCEMENTS.md
5. **Advanced** → Review the source code in app/

## 📈 Metrics Examples

### Global Summary
```json
{
  "total_syncs": 250,
  "successful_syncs": 240,
  "failed_syncs": 10,
  "success_rate": 96.0,
  "average_duration_seconds": 210.0,
  "unique_users": 42
}
```

### User Summary
```json
{
  "user_id": 42,
  "total_syncs": 15,
  "success_rate": 93.3,
  "total_courses_processed": 350,
  "total_assignments_processed": 5200
}
```

### Performance Stats
```json
{
  "sync_count": 450,
  "duration": {
    "avg_seconds": 210.0,
    "min_seconds": 45.2,
    "max_seconds": 1200.5
  },
  "api_calls": {
    "total": 945000,
    "avg_per_sync": 2100.0
  }
}
```

## 🚀 Next Steps

1. Read: CANVAS_MONITORING_COMPLETE.md
2. Setup: Follow 5-Minute Setup above
3. Test: curl http://localhost:5000/api/canvas/metrics/health
4. Integrate: Add to your sync task
5. Monitor: Set up dashboards/alerts

---

**Version**: 1.0
**Status**: Production Ready
**Last Updated**: December 22, 2025

