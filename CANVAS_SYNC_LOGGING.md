# Canvas Sync Comprehensive Logging System

## Overview

A dedicated, highly-detailed logging system has been implemented specifically for Canvas sync operations. Every single step of the Canvas synchronization process is now logged with as much context and detail as possible.

## What Was Changed

### 1. **Logging Configuration** (`app/logging_config.py`)
Added a complete Canvas sync logging subsystem with:
- **5 dedicated log files** for different aspects of Canvas sync
- **File rotation** with 50MB limit per file, maintaining backups
- **Structured logging** with JSON format support
- **Specialized utility functions** for logging different types of Canvas events

### 2. **Canvas Sync Task File** (`app/tasks/canvas_sync.py`)
Enhanced with comprehensive logging throughout:
- Task startup and initialization
- User validation and credential checks  
- Progress tracking at every checkpoint
- Checkpoint save/restore operations
- Course processing with detailed statistics
- Error handling with full context
- Task completion and cleanup

### 3. **Canvas Sync Service** (`app/services/canvas_sync_service.py`)
Added detailed logging for:
- Connection testing with result details
- Term parsing and creation
- Course synchronization (create vs update)
- Assignment processing with score/submission details
- Category/group creation
- Database batch operations
- Incremental sync tracking
- Performance metrics

### 4. **Canvas API Service** (`app/services/canvas_api_service.py`)
Added API-level logging for:
- HTTP request details (method, endpoint, parameters)
- Response status codes and timing
- Pagination operations and page counts
- API error handling with full context
- Concurrent request tracking
- Fallback mechanism logging

## Log Files Structure

### 1. **logs/canvas_sync/operations.log** (50MB max)
**Purpose**: Main Canvas sync operations and task flow  
**Contains**: 
- Sync task start/completion
- User authentication
- Connection testing
- Term and course processing
- Checkpoint operations
- Overall progress and summary statistics

**Example Entry**:
```
[2024-12-22 10:15:34] INFO [sync_canvas_data_task:215]: Starting Canvas sync canvas_sync_123_1703254534 for user 1 (type: all)
[2024-12-22 10:15:35] INFO [sync_canvas_data_task:298]: Canvas connection test successful
[2024-12-22 10:15:36] INFO [_sync_all_streaming:535]: Fetched 12 courses from Canvas
[2024-12-22 10:15:42] INFO [_sync_all_streaming:560]: ✓ Course created: Introduction to Python
```

### 2. **logs/canvas_sync/api_calls.log** (30MB max)
**Purpose**: Detailed Canvas API HTTP communication  
**Contains**:
- Every API request (method, endpoint, parameters)
- Response status codes
- Request duration in milliseconds
- Item counts returned
- Pagination information
- API errors with details

**Example Entry**:
```
[2024-12-22 10:15:35] DEBUG [_make_request:89]: Making Canvas API request: GET /users/self
[2024-12-22 10:15:35] DEBUG [_make_request:93]: Canvas API response: GET /users/self - Status: 200 - Duration: 145.3ms
[2024-12-22 10:15:36] DEBUG [_get_paginated_data:115]: Fetching paginated data from /courses with params: {...}
[2024-12-22 10:15:36] INFO [_get_paginated_data:140]: Pagination complete: Total 12 items from endpoint /courses (1 pages)
```

### 3. **logs/canvas_sync/database.log** (30MB max)
**Purpose**: Database operations during Canvas sync  
**Contains**:
- Create/update/delete operations
- Entity type (Course, Assignment, Category)
- Count of affected records
- Course context
- Batch operation details

**Example Entry**:
```
[2024-12-22 10:15:37] DEBUG [log_canvas_db_operation]: Database sync: Course (count: 1)
[2024-12-22 10:15:40] DEBUG [log_canvas_db_operation]: Database create: Assignment (count: 1)
[2024-12-22 10:15:45] INFO [_sync_course_assignments:879]: Successfully flushed 8 assignments in batch
```

### 4. **logs/canvas_sync/errors.log** (20MB max)
**Purpose**: Error tracking during Canvas sync (ERROR level only)  
**Contains**:
- Error messages
- User ID and context
- Operation that failed
- Full exception details
- Retry attempts

**Example Entry**:
```
[2024-12-22 10:16:12] ERROR [sync_canvas_data_task:351]: Canvas sync canvas_sync_123_1703254534 failed after 38.2s: Connection timeout
[2024-12-22 10:16:12] ERROR [log_canvas_error]: Canvas sync error in sync_task: Connection timeout
[2024-12-22 10:16:12] ERROR [sync_canvas_data_celery]: Retry attempt 1/3
```

### 5. **logs/canvas_sync/progress.log** (25MB max)
**Purpose**: Real-time progress tracking  
**Contains**:
- Progress percentage updates
- Current item being processed
- Total items to process
- Elapsed time
- Task ID for tracking

**Example Entry**:
```
[2024-12-22 10:15:37] INFO [log_canvas_progress]: Sync progress: 8% - Introduction to Python
[2024-12-22 10:15:42] INFO [log_canvas_progress]: Sync progress: 25% - Advanced Python
[2024-12-22 10:16:05] INFO [log_canvas_progress]: Sync progress: 100% - All Courses Synced
```

## Logging Details by Operation

### User Validation
```
Validates Canvas credentials and user account
Logs:
- User ID lookup
- Credential existence check
- Validation success/failure
```

### API Pagination
```
Tracks multi-page API responses
Logs:
- First page fetch
- Total pages detected
- Concurrent vs sequential fetching
- Final item count
```

### Course Syncing
```
Processes each Canvas course
Logs:
- Course name and ID
- Create vs update decision
- Assignment count
- Category assignments
- Completion status
```

### Assignment Syncing
```
Processes assignments within courses
Logs:
- Assignment name and ID
- Points possible (max score)
- Due date parsing
- Submission status
- Score tracking
```

### Database Operations
```
Tracks all database changes
Logs:
- Operation type (create/update/delete)
- Entity type
- Count of records
- Batch vs individual operations
- Flush operations
```

## Usage

### Setup
The logging system is automatically initialized when the Flask app starts with:
```python
from app.logging_config import setup_comprehensive_logging
setup_comprehensive_logging(app)
```

### Accessing Logs
View real-time logs:
```bash
# Monitor operations
tail -f logs/canvas_sync/operations.log

# Watch API calls
tail -f logs/canvas_sync/api_calls.log

# Track errors
tail -f logs/canvas_sync/errors.log

# Monitor progress
tail -f logs/canvas_sync/progress.log
```

### Log Analysis
All logs include:
- **Timestamp**: UTC timestamp of each event
- **Level**: DEBUG, INFO, WARNING, ERROR
- **Function/Line**: Where the log originated
- **Message**: Detailed description
- **Context**: User ID, course ID, task ID, etc.

## Log Rotation

Each log file automatically rotates when it reaches:
- **operations.log**: 50MB (keep 10 backups)
- **api_calls.log**: 30MB (keep 8 backups)
- **database.log**: 30MB (keep 8 backups)
- **errors.log**: 20MB (keep 10 backups)
- **progress.log**: 25MB (keep 7 backups)

Old rotated files are named: `filename.log.1`, `filename.log.2`, etc.

## Features

✓ **Comprehensive Coverage**: Every step of Canvas sync logged  
✓ **Hierarchical Logging**: Multiple loggers for different aspects  
✓ **Automatic Rotation**: Prevents logs from consuming too much disk  
✓ **Structured Format**: Easy to parse and analyze  
✓ **Error Tracking**: Dedicated error log with full context  
✓ **Performance Metrics**: API call timing and duration  
✓ **Progress Tracking**: Real-time sync progress updates  
✓ **Contextual Info**: User ID, course ID, task ID in all logs  
✓ **Fallback Support**: Works even if Redis is unavailable  
✓ **JSON Support**: Can output structured JSON logs if enabled  

## Example Complete Sync Log Flow

```
1. Sync Task Started
   ↓ [operations.log]: Canvas sync started
   ↓ [operations.log]: User credentials validated
   
2. Connection Test
   ↓ [operations.log]: Testing Canvas connection
   ↓ [api_calls.log]: GET /users/self → 200 (145ms)
   ↓ [operations.log]: Connection successful

3. Fetch Courses
   ↓ [operations.log]: Fetching courses from Canvas
   ↓ [api_calls.log]: GET /courses → 200 (312ms, 12 items, 1 page)
   
4. Process Each Course
   For each course:
   ↓ [operations.log]: Syncing course "Intro to Python"
   ↓ [operations.log]: Course created
   ↓ [database.log]: Database create: Course (count: 1)
   
5. Process Assignments
   For each assignment:
   ↓ [api_calls.log]: GET /assignments → 200 (245ms, 8 items)
   ↓ [database.log]: Database create: Assignment (count: 1)
   
6. Progress Updates
   ↓ [progress.log]: 8% - Introduction to Python
   ↓ [progress.log]: 42% - Advanced Python
   ↓ [progress.log]: 100% - Sync complete

7. Completion
   ↓ [operations.log]: Sync completed (42.3 seconds)
   ↓ [operations.log]: Summary: 12 courses, 142 assignments, 8 categories
```

## Debugging with Logs

### Find all errors for a user:
```bash
grep "user_id: 123" logs/canvas_sync/errors.log
```

### Track a specific sync task:
```bash
grep "canvas_sync_123_1703254534" logs/canvas_sync/operations.log
```

### Find slow API calls:
```bash
grep "duration_ms" logs/canvas_sync/api_calls.log | grep -v "^[1-9]" | head -20
```

### Watch assignment syncing:
```bash
grep "Assignment" logs/canvas_sync/database.log
```

### Get progress timeline:
```bash
grep "progress" logs/canvas_sync/progress.log | tail -20
```

## Performance Monitoring

The logs record:
- **API call duration**: Identify slow endpoints
- **Database batch sizes**: Monitor efficiency
- **Total sync time**: Track improvements
- **Error rates**: Spot problematic courses
- **Pagination overhead**: Measure API efficiency

## Summary

You now have complete, detailed visibility into every step of Canvas synchronization. The logging system captures:

- **12+ distinct event types**
- **5 specialized log files**
- **Hundreds of data points per sync**
- **Full error context and stacktraces**
- **Real-time progress information**
- **API performance metrics**
- **Database operation tracking**

This enables complete debugging, performance analysis, and troubleshooting of any Canvas sync issue.
