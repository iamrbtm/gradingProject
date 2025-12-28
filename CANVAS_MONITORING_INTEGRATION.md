# Canvas Sync Monitoring Integration Guide

## Quick Setup (5 minutes)

### Step 1: Register the API Blueprint

Add this to your `app/__init__.py` file:

```python
# After creating the Flask app and registering other blueprints
from app.blueprints.canvas_metrics_api import register_canvas_metrics_api

app = create_app()

# Register all blueprints
app.register_blueprint(main_bp)
app.register_blueprint(courses_bp)
# ... other blueprints ...

# Register the Canvas metrics API
register_canvas_metrics_api(app)
```

Or in your main app creation function:

```python
def create_app():
    app = Flask(__name__)
    # ... app configuration ...
    
    # Register blueprints
    from app.blueprints.canvas_metrics_api import register_canvas_metrics_api
    register_canvas_metrics_api(app)
    
    return app
```

### Step 2: Create Database Table

Run one of these commands:

```bash
# Option 1: Using Flask shell
flask shell
>>> from app import db
>>> db.create_all()

# Option 2: Using Python
python -c "from app import db, create_app; app = create_app(); app.app_context().push(); db.create_all()"

# Option 3: Using Flask-Migrate
flask db upgrade
```

### Step 3: Test the API

```bash
# Health check
curl http://localhost:5000/api/canvas/metrics/health

# Global summary
curl http://localhost:5000/api/canvas/metrics/summary

# Recent syncs
curl http://localhost:5000/api/canvas/metrics/recent
```

## Integration Examples

### Add to Canvas Sync Task

Integrate metrics tracking into your existing sync task:

```python
from app.services.canvas_sync_metrics import CanvasSyncMetricsTracker
from app.models import db

@shared_task(bind=True)
def sync_canvas_data_task(self, user_id, sync_type='all', **kwargs):
    # Initialize metrics tracker
    tracker = CanvasSyncMetricsTracker(
        task_id=self.request.id,
        user_id=user_id,
        sync_type=sync_type
    )
    
    try:
        # Your sync logic here
        courses = sync_courses(user_id)
        for course in courses:
            created = course['id'] not in existing_ids
            tracker.record_course(created=created)
            
            # Sync assignments
            assignments = sync_assignments(course['id'])
            for assignment in assignments:
                created = assignment['id'] not in existing_ids
                tracker.record_assignment(created=created)
        
        # Mark as complete
        result = tracker.complete_success()
        db.session.add(result)
        db.session.commit()
        
        return {'status': 'success', 'task_id': self.request.id}
        
    except Exception as e:
        result = tracker.complete_failure(str(e))
        db.session.add(result)
        db.session.commit()
        
        return {'status': 'error', 'message': str(e)}
```

### Create a Monitoring Dashboard

Here's a simple Flask route for a dashboard:

```python
from flask import render_template
import requests
import json

@app.route('/dashboard/canvas-sync')
def canvas_sync_dashboard():
    """Canvas sync monitoring dashboard."""
    try:
        # Fetch metrics from API
        summary = requests.get(
            'http://localhost:5000/api/canvas/metrics/summary?days=7'
        ).json()
        
        recent = requests.get(
            'http://localhost:5000/api/canvas/metrics/recent?limit=20'
        ).json()
        
        failed = requests.get(
            'http://localhost:5000/api/canvas/metrics/failed?days=7'
        ).json()
        
        performance = requests.get(
            'http://localhost:5000/api/canvas/metrics/performance?days=30'
        ).json()
        
        return render_template('canvas_sync_dashboard.html',
                             summary=summary,
                             recent=recent,
                             failed=failed,
                             performance=performance)
    except Exception as e:
        return f"Error loading dashboard: {str(e)}", 500
```

And the template (`templates/canvas_sync_dashboard.html`):

```html
<!DOCTYPE html>
<html>
<head>
    <title>Canvas Sync Monitoring</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .metric { 
            display: inline-block; 
            border: 1px solid #ddd; 
            padding: 15px; 
            margin: 10px; 
            border-radius: 5px;
        }
        .metric h3 { margin: 0; color: #333; }
        .metric .value { font-size: 24px; font-weight: bold; color: #0066cc; }
        .failed { background-color: #ffe6e6; }
        .successful { background-color: #e6f3ff; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>Canvas Sync Monitoring Dashboard</h1>
    
    <div class="metrics">
        <div class="metric successful">
            <h3>Total Syncs (7 days)</h3>
            <div class="value">{{ summary.total_syncs }}</div>
        </div>
        
        <div class="metric">
            <h3>Success Rate</h3>
            <div class="value">{{ "%.1f"|format(summary.success_rate) }}%</div>
        </div>
        
        <div class="metric">
            <h3>Avg Duration</h3>
            <div class="value">{{ "%.0f"|format(summary.average_duration_seconds) }}s</div>
        </div>
        
        <div class="metric failed">
            <h3>Failed Syncs</h3>
            <div class="value">{{ failed.count }}</div>
        </div>
    </div>
    
    <h2>Recent Sync Operations</h2>
    <table>
        <tr>
            <th>Task ID</th>
            <th>User</th>
            <th>Status</th>
            <th>Duration</th>
            <th>Courses</th>
            <th>Time</th>
        </tr>
        {% for sync in recent.syncs %}
        <tr>
            <td>{{ sync.sync_task_id[:8] }}...</td>
            <td>{{ sync.user_id }}</td>
            <td>{{ sync.sync_status }}</td>
            <td>{{ "%.1f"|format(sync.total_duration_seconds) }}s</td>
            <td>{{ sync.courses.processed }}</td>
            <td>{{ sync.sync_start_time }}</td>
        </tr>
        {% endfor %}
    </table>
    
    {% if failed.count > 0 %}
    <h2>Failed Syncs</h2>
    <table>
        <tr>
            <th>Task ID</th>
            <th>User</th>
            <th>Error</th>
            <th>Time</th>
        </tr>
        {% for sync in failed.syncs %}
        <tr>
            <td>{{ sync.sync_task_id[:8] }}...</td>
            <td>{{ sync.user_id }}</td>
            <td>{{ sync.error_message }}</td>
            <td>{{ sync.sync_start_time }}</td>
        </tr>
        {% endfor %}
    </table>
    {% endif %}
</body>
</html>
```

### Add Slack Notifications

Send alerts to Slack when syncs fail:

```python
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

slack_client = WebClient(token=os.environ.get('SLACK_BOT_TOKEN'))

def notify_sync_failure(sync_metrics):
    """Send Slack notification on sync failure."""
    try:
        slack_client.chat_postMessage(
            channel='#canvas-sync-alerts',
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Canvas Sync Failed*\n"
                               f"User: {sync_metrics.user_id}\n"
                               f"Error: {sync_metrics.error_message}\n"
                               f"Time: {sync_metrics.sync_start_time}"
                    }
                }
            ]
        )
    except SlackApiError as e:
        logger.error(f"Failed to send Slack notification: {e}")
```

Then call in your sync task:

```python
if sync_metrics.sync_status == 'failed':
    notify_sync_failure(sync_metrics)
```

### Add Email Reports

Generate periodic email reports:

```python
from flask_mail import Mail, Message
from datetime import datetime, timedelta

mail = Mail()

def send_sync_report(days=7):
    """Send weekly sync report via email."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    summary = get_all_sync_metrics_summary(days=days)
    failed = CanvasSyncMetrics.query.filter(
        CanvasSyncMetrics.sync_status == 'failed',
        CanvasSyncMetrics.sync_start_time >= cutoff_date
    ).all()
    
    html = f"""
    <h1>Canvas Sync Report - Last {days} Days</h1>
    <p>Total Syncs: {summary['total_syncs']}</p>
    <p>Success Rate: {summary['success_rate']:.1f}%</p>
    <p>Failed Syncs: {len(failed)}</p>
    
    <h2>Failed Syncs</h2>
    <ul>
    {''.join([f"<li>User {f.user_id}: {f.error_message}</li>" for f in failed])}
    </ul>
    """
    
    msg = Message(
        subject=f'Canvas Sync Report - {datetime.now().strftime("%Y-%m-%d")}',
        recipients=['admin@example.com'],
        html=html
    )
    
    mail.send(msg)
```

Schedule with Celery Beat:

```python
app.conf.beat_schedule['send-sync-report'] = {
    'task': 'app.tasks.send_sync_report',
    'schedule': crontab(hour=9, minute=0, day_of_week=1),  # Every Monday at 9 AM
}
```

### Create Grafana Dashboards

Export metrics to Prometheus for Grafana:

```python
from prometheus_client import Counter, Histogram, Gauge

sync_count = Counter(
    'canvas_sync_total',
    'Total Canvas syncs',
    ['status', 'sync_type']
)

sync_duration = Histogram(
    'canvas_sync_duration_seconds',
    'Canvas sync duration',
    buckets=[10, 30, 60, 120, 300, 600]
)

sync_courses = Gauge(
    'canvas_sync_courses_processed',
    'Courses processed in sync'
)

def record_prometheus_metrics(sync_metrics):
    """Record metrics to Prometheus."""
    sync_count.labels(
        status=sync_metrics.sync_status,
        sync_type=sync_metrics.sync_type
    ).inc()
    
    if sync_metrics.total_duration_seconds:
        sync_duration.observe(sync_metrics.total_duration_seconds)
    
    sync_courses.set(sync_metrics.courses_processed or 0)
```

## Testing

### Unit Tests

```python
import pytest
from app.services.canvas_sync_metrics import CanvasSyncMetricsTracker
from app.models import db, CanvasSyncMetrics

def test_metrics_tracker():
    """Test metrics tracking."""
    tracker = CanvasSyncMetricsTracker(
        task_id='test-123',
        user_id=42
    )
    
    tracker.record_course(created=True)
    tracker.record_assignment(updated=True)
    
    assert tracker.metrics.courses_processed == 1
    assert tracker.metrics.assignments_processed == 1
    assert tracker.metrics.courses_created == 1

def test_api_endpoint(client):
    """Test API endpoint."""
    response = client.get('/api/canvas/metrics/health')
    assert response.status_code == 200
    assert response.json['status'] == 'healthy'
```

### Integration Tests

```python
def test_full_sync_with_metrics(client, db_session):
    """Test sync task with metrics recording."""
    # Create test data
    user = create_test_user(42)
    
    # Run sync
    result = sync_canvas_data_task(user.id)
    
    # Verify metrics were recorded
    metric = CanvasSyncMetrics.query.filter_by(
        sync_task_id=result['task_id']
    ).first()
    
    assert metric is not None
    assert metric.sync_status == 'completed'
    assert metric.courses_processed > 0
```

## Troubleshooting

### Metrics Not Recording

```python
# Check if table exists
python -c "from app.models import db, CanvasSyncMetrics; from app import create_app; app = create_app(); app.app_context().push(); print(db.engine.dialect.has_table(db.engine, 'canvas_sync_metrics'))"

# Recreate table if missing
python -c "from app import db, create_app; app = create_app(); app.app_context().push(); db.create_all()"
```

### API Not Responding

```bash
# Check if API is registered
curl http://localhost:5000/api/canvas/metrics/health

# Check Flask logs
flask run --debug
```

### Database Errors

```python
# Clear old data
from app.models import db, CanvasSyncMetrics
from datetime import datetime, timedelta

cutoff = datetime.utcnow() - timedelta(days=90)
CanvasSyncMetrics.query.filter(
    CanvasSyncMetrics.sync_start_time < cutoff
).delete()
db.session.commit()
```

## Production Checklist

- [ ] Register API blueprint in app initialization
- [ ] Create database table (db.create_all())
- [ ] Add authentication to API endpoints
- [ ] Set up rate limiting
- [ ] Configure log rotation
- [ ] Schedule automatic cleanup task
- [ ] Add Slack/email notifications
- [ ] Create monitoring dashboard
- [ ] Set up performance monitoring (Prometheus/Grafana)
- [ ] Document metrics for your team

## Support

For issues or questions about the Canvas sync monitoring system:
1. Check the API documentation: `CANVAS_METRICS_API.md`
2. Review the quick start guide: `CANVAS_SYNC_LOGGING_QUICK_START.md`
3. Check full documentation: `CANVAS_SYNC_LOGGING_ENHANCEMENTS.md`
4. Run health check: `curl http://localhost:5000/api/canvas/metrics/health`

