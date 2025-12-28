# Critical Fix: SQLAlchemy Reserved Attribute Name

## Issue
The `CanvasSyncMetrics` model was using `metadata` as a column name, which is a **reserved name in SQLAlchemy's Declarative API**. This caused all Docker containers to fail on startup with:

```
sqlalchemy.exc.InvalidRequestError: Attribute name 'metadata' is reserved when using the Declarative API.
```

## Solution
Renamed the column from `metadata` to `sync_metadata` throughout the codebase.

## Files Updated

### 1. `app/models.py` (3 changes)
- Line 1065: `metadata` → `sync_metadata` (column definition)
- Line 1130: `self.metadata` → `self.sync_metadata` (in `to_dict()` method)
- Line 1168: `metadata=` → `sync_metadata=` (in `create_from_sync_result()` method)

### 2. `app/services/canvas_sync_metrics.py` (2 changes)
- Line 97-99: Updated `add_metadata()` method to use `self.metrics.sync_metadata`

### 3. `migrations/add_canvas_sync_metrics.py` (1 change)
- Updated SQL CREATE TABLE statement to use `sync_metadata` instead of `metadata`

## Verification
✅ `app/models.py` - Syntax valid
✅ `app/services/canvas_sync_metrics.py` - Syntax valid
✅ No remaining invalid references found

## Next Steps
The Docker containers should now start correctly. The fix is backward compatible since this is a new model that hasn't been deployed yet.

