# Canvas Sync Performance Testing Guide

This guide explains how to test the Canvas sync optimizations with real data.

## Prerequisites

1. **Database indexes installed** - Run `python add_canvas_indexes.py` (already done ✓)
2. **Canvas credentials configured** - User must have Canvas Base URL and Access Token set
3. **Working Flask environment** - Virtual environment with all dependencies installed

## Performance Testing

### Method 1: Using the Performance Test Script (Recommended)

The `test_canvas_performance.py` script provides comprehensive performance testing with timing measurements.

**Usage:**
```bash
source venv/bin/activate
python test_canvas_performance.py <username>
```

**Example:**
```bash
python test_canvas_performance.py jeremy
```

**What it tests:**
1. **Full Sync** - Syncs all Canvas courses and measures time
2. **Incremental Sync** - Syncs only updated courses and compares speed
3. **Single Course Sync** - Tests syncing individual courses

**Expected Output:**
```
==================================================================
CANVAS SYNC PERFORMANCE TEST
==================================================================

Testing for user: jeremy
Canvas URL: https://canvas.example.edu
✓ Canvas connection successful

------------------------------------------------------------------
TEST 1: Full Sync (All Courses)
------------------------------------------------------------------
Current database state:
  - Terms: 2
  - Courses: 8
  - Assignments: 124

Starting full sync...
✓ Full sync completed in 8.45s

Sync Results:
  - Courses processed: 8
  - Assignments processed: 124
  - Categories created: 24

------------------------------------------------------------------
TEST 2: Incremental Sync (Only Updated Courses)
------------------------------------------------------------------
✓ Incremental sync completed in 1.23s
  → 85.4% faster than full sync

==================================================================
PERFORMANCE SUMMARY
==================================================================

Optimization Benefits:
✓ Connection pooling active (10 connections, retry strategy)
✓ Concurrent pagination (5 workers)
✓ Concurrent data fetching (3 workers)
✓ Bulk submissions fetching
✓ Batch database operations (~6 flushes per sync)
✓ Database indexes on Canvas ID columns
```

### Method 2: Manual Testing via Flask App

You can also test through the web interface:

1. **Start the Flask app:**
   ```bash
   source venv/bin/activate
   python app.py
   ```

2. **Navigate to Canvas settings** and configure your Canvas credentials

3. **Run sync** and observe the console output for timing information

4. **Check logs** in `app.log` for detailed performance metrics

## Known Issues

### Numpy/Pandas Compatibility Error

If you encounter this error:
```
ValueError: numpy.dtype size changed, may indicate binary incompatibility
```

**Solution:**
```bash
source venv/bin/activate
pip install --upgrade numpy pandas
```

Or reinstall with compatible versions:
```bash
pip uninstall numpy pandas
pip install numpy==1.24.3 pandas==2.0.3
```

### Environment Variable Warnings

**API_TOKEN_ENCRYPTION_KEY not set:**
- Add to your `.env` file: `API_TOKEN_ENCRYPTION_KEY=<your-key>`
- Generate a key: `python generate_encryption_key.py`

**Flask-Limiter warning:**
- This is informational only for development
- Production should use Redis/Memcached backend

## Verification Checklist

After testing, verify all optimizations are working:

- [ ] Connection pooling - Check logs for "pool_connections=10"
- [ ] Concurrent pagination - Multiple pages fetched in parallel
- [ ] Incremental sync - Subsequent syncs are 90%+ faster
- [ ] Bulk submissions - One API call per course instead of N calls
- [ ] Batch database operations - Only ~6 flushes per sync (check logs)
- [ ] Database indexes - Query performance improved (check EXPLAIN)
- [ ] Progress indicators - Clear visual feedback during sync

## Measuring Performance Improvements

### Expected Results

| Metric | Before Optimization | After Optimization | Improvement |
|--------|-------------------|-------------------|-------------|
| First sync (50 assignments) | ~30s | ~12s | 60% faster |
| Incremental sync | ~30s | ~2s | 93% faster |
| Database flushes | ~50+ | ~6 | 88% reduction |
| API requests (assignments) | N+1 calls | 1 call | N times faster |

### Actual measurements will vary based on:
- Number of courses and assignments
- Network latency to Canvas API
- Database server performance
- Canvas API rate limits

## Troubleshooting

### Slow sync despite optimizations

1. **Check Canvas API rate limits** - Canvas may be throttling requests
2. **Verify database indexes** - Run `SHOW INDEXES FROM assignment;`
3. **Check network latency** - Test connection to Canvas server
4. **Review logs** - Look for errors or retries in `app.log`

### Database connection errors

1. **Verify DATABASE_URL** in `.env` file
2. **Test connection** - `python -c "from app.models import db; print(db)"`
3. **Check credentials** - Ensure password is URL-encoded

### Import errors

1. **Activate virtual environment** - `source venv/bin/activate`
2. **Install dependencies** - `pip install -r requirements.txt`
3. **Check Python version** - Requires Python 3.8+

## Next Steps

After successful testing:

1. **Monitor real-world usage** - Track sync times over days/weeks
2. **Add metrics/monitoring** - Consider adding prometheus/grafana
3. **Tune worker counts** - Adjust ThreadPoolExecutor workers if needed
4. **Consider caching** - Add Redis caching for frequently accessed data
5. **Implement webhooks** - Use Canvas webhooks for real-time updates

## Additional Resources

- Canvas API Documentation: https://canvas.instructure.com/doc/api/
- Flask-SQLAlchemy Performance: https://flask-sqlalchemy.palletsprojects.com/
- Python Threading: https://docs.python.org/3/library/concurrent.futures.html

---

**Last Updated:** November 23, 2025  
**Related Docs:** CANVAS_SYNC_OPTIMIZATIONS.md
