"""
Migration: Add Canvas Sync Metrics table

This migration creates a new table to track Canvas sync operation metrics
and performance statistics.

To run this migration with the Flask-SQLAlchemy model, simply run:
    python -c "from app import db, create_app; app = create_app(); app.app_context().push(); db.create_all()"

Or with Flask CLI:
    flask db upgrade

This file serves as documentation for the migration structure.
"""

# The migration is defined in the model app/models.py as CanvasSyncMetrics
# When you run db.create_all(), this table will be created automatically

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS canvas_sync_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sync_task_id VARCHAR(255) NOT NULL UNIQUE INDEX `idx_canvas_sync_task_id`,
    user_id INT,
    sync_start_time DATETIME NOT NULL,
    sync_end_time DATETIME,
    total_duration_seconds FLOAT,
    sync_status VARCHAR(50) NOT NULL DEFAULT 'in_progress',
    error_message LONGTEXT,
    sync_type VARCHAR(50) NOT NULL DEFAULT 'all',
    target_course_id INT,
    courses_processed INT NOT NULL DEFAULT 0,
    courses_created INT NOT NULL DEFAULT 0,
    courses_updated INT NOT NULL DEFAULT 0,
    assignments_processed INT NOT NULL DEFAULT 0,
    assignments_created INT NOT NULL DEFAULT 0,
    assignments_updated INT NOT NULL DEFAULT 0,
    submissions_processed INT NOT NULL DEFAULT 0,
    submissions_created INT NOT NULL DEFAULT 0,
    submissions_updated INT NOT NULL DEFAULT 0,
    grades_processed INT NOT NULL DEFAULT 0,
    grades_updated INT NOT NULL DEFAULT 0,
    api_calls_made INT NOT NULL DEFAULT 0,
    api_calls_failed INT NOT NULL DEFAULT 0,
    total_api_duration_ms FLOAT NOT NULL DEFAULT 0.0,
    api_rate_limit_hits INT NOT NULL DEFAULT 0,
    db_operations INT NOT NULL DEFAULT 0,
    db_duration_ms FLOAT NOT NULL DEFAULT 0.0,
    total_data_size_bytes BIGINT NOT NULL DEFAULT 0,
    incremental_sync BOOLEAN NOT NULL DEFAULT TRUE,
    use_pagination BOOLEAN NOT NULL DEFAULT TRUE,
    chunk_size INT NOT NULL DEFAULT 10,
    sync_metadata JSON,
    FOREIGN KEY (user_id) REFERENCES user(id),
    INDEX `idx_canvas_sync_user_id` (user_id),
    INDEX `idx_canvas_sync_start_time` (sync_start_time),
    INDEX `idx_canvas_sync_user_time` (user_id, sync_start_time),
    INDEX `idx_canvas_sync_status_time` (sync_status, sync_start_time),
    INDEX `idx_canvas_sync_type` (sync_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""
