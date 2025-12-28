#!/usr/bin/env python3
"""
Analytics System Migration
==========================

This migration adds all the necessary tables and columns for the analytics system:
1. Predictive Grade Analytics Engine
2. Academic Performance Analytics Suite
3. Smart Notification System

Run with: python migrations/add_analytics_system.py

Author: Analytics Team
Date: 2024-12-19
"""

import os
import sys
import logging
from datetime import datetime
from sqlalchemy import text

# Add the parent directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import db
from app import create_app

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_analytics_tables():
    """Create all new analytics tables."""

    logger.info("Creating analytics tables...")

    # SQL for creating all analytics tables
    analytics_tables_sql = [
        # Prediction Models Table
        """
        CREATE TABLE IF NOT EXISTS prediction_models (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            model_type ENUM('grade_prediction', 'risk_assessment', 'performance_forecast') NOT NULL,
            model_version VARCHAR(20) NOT NULL DEFAULT '1.0',
            model_data JSON NULL,
            accuracy_score DECIMAL(5,4) NULL,
            training_data_size INT NULL,
            feature_importance JSON NULL,
            last_trained TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
            INDEX idx_user_model_type (user_id, model_type),
            INDEX idx_model_performance (model_type, accuracy_score)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        # Grade Predictions Table
        """
        CREATE TABLE IF NOT EXISTS grade_predictions (
            id INT PRIMARY KEY AUTO_INCREMENT,
            course_id INT NOT NULL,
            user_id INT NOT NULL,
            predicted_grade DECIMAL(5,2) NOT NULL,
            confidence_score DECIMAL(5,4) NOT NULL,
            grade_range_min DECIMAL(5,2) NULL,
            grade_range_max DECIMAL(5,2) NULL,
            prediction_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            actual_grade DECIMAL(5,2) NULL,
            contributing_factors JSON NULL,
            model_version VARCHAR(20) NOT NULL DEFAULT '1.0',
            FOREIGN KEY (course_id) REFERENCES course(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
            INDEX idx_course_predictions (course_id, prediction_date),
            INDEX idx_user_predictions (user_id, prediction_date),
            INDEX idx_prediction_accuracy (actual_grade, predicted_grade)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        # Risk Assessments Table
        """
        CREATE TABLE IF NOT EXISTS risk_assessments (
            id INT PRIMARY KEY AUTO_INCREMENT,
            course_id INT NOT NULL,
            user_id INT NOT NULL,
            risk_level ENUM('low', 'medium', 'high', 'critical') NOT NULL,
            risk_score DECIMAL(5,4) NOT NULL,
            risk_factors JSON NULL,
            recommendations TEXT NULL,
            intervention_suggested BOOLEAN NOT NULL DEFAULT FALSE,
            assessment_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP NULL,
            resolution_method VARCHAR(100) NULL,
            FOREIGN KEY (course_id) REFERENCES course(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
            INDEX idx_active_risks (user_id, resolved_at, risk_level),
            INDEX idx_course_risks (course_id, assessment_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        # Performance Metrics Table
        """
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            term_id INT NULL,
            metric_type VARCHAR(50) NOT NULL,
            metric_value DECIMAL(10,4) NOT NULL,
            calculation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            metric_metadata JSON NULL,
            FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
            FOREIGN KEY (term_id) REFERENCES term(id) ON DELETE CASCADE,
            INDEX idx_user_metrics (user_id, metric_type, calculation_date),
            INDEX idx_term_metrics (term_id, metric_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        # Performance Trends Table
        """
        CREATE TABLE IF NOT EXISTS performance_trends (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            trend_type VARCHAR(50) NOT NULL,
            trend_direction ENUM('improving', 'declining', 'stable') NOT NULL,
            trend_strength DECIMAL(5,4) NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            data_points JSON NULL,
            statistical_significance DECIMAL(5,4) NULL,
            FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
            INDEX idx_user_trends (user_id, trend_type, end_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        # User Behavior Patterns Table
        """
        CREATE TABLE IF NOT EXISTS user_behavior_patterns (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            pattern_type VARCHAR(50) NOT NULL,
            pattern_data JSON NOT NULL,
            confidence_score DECIMAL(5,4) NOT NULL,
            sample_size INT NOT NULL DEFAULT 0,
            last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
            UNIQUE KEY unique_user_pattern (user_id, pattern_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        # Notification Preferences Table
        """
        CREATE TABLE IF NOT EXISTS notification_preferences (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            notification_type VARCHAR(50) NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            delivery_method ENUM('web', 'email', 'push') NOT NULL DEFAULT 'web',
            optimal_time TIME NULL,
            frequency_limit INT NOT NULL DEFAULT 5,
            quiet_hours_start TIME NULL,
            quiet_hours_end TIME NULL,
            preferences JSON NULL,
            FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
            UNIQUE KEY unique_user_notification (user_id, notification_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        # Smart Notifications Table
        """
        CREATE TABLE IF NOT EXISTS smart_notifications (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            notification_type VARCHAR(50) NOT NULL,
            title VARCHAR(255) NOT NULL,
            message TEXT NULL,
            priority ENUM('low', 'medium', 'high', 'urgent') NOT NULL DEFAULT 'medium',
            scheduled_time TIMESTAMP NULL,
            sent_time TIMESTAMP NULL,
            read_time TIMESTAMP NULL,
            action_taken BOOLEAN NOT NULL DEFAULT FALSE,
            action_url VARCHAR(500) NULL,
            effectiveness_score DECIMAL(3,2) NULL,
            notification_metadata JSON NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
            INDEX idx_user_notifications (user_id, sent_time, read_time),
            INDEX idx_scheduled_notifications (scheduled_time, sent_time),
            INDEX idx_notification_effectiveness (notification_type, effectiveness_score)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        # Notification Interactions Table
        """
        CREATE TABLE IF NOT EXISTS notification_interactions (
            id INT PRIMARY KEY AUTO_INCREMENT,
            notification_id INT NOT NULL,
            user_id INT NOT NULL,
            interaction_type ENUM('viewed', 'clicked', 'dismissed', 'snoozed') NOT NULL,
            interaction_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            device_info VARCHAR(255) NULL,
            additional_data JSON NULL,
            FOREIGN KEY (notification_id) REFERENCES smart_notifications(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
            INDEX idx_user_interactions (user_id, interaction_time),
            INDEX idx_notification_interactions (notification_id, interaction_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
    ]

    # Execute each table creation
    for i, sql in enumerate(analytics_tables_sql, 1):
        try:
            logger.info(f"Creating table {i}/{len(analytics_tables_sql)}...")
            db.session.execute(text(sql))
            db.session.commit()
            logger.info(f"Successfully created table {i}")
        except Exception as e:
            logger.error(f"Error creating table {i}: {str(e)}")
            db.session.rollback()
            raise


def add_analytics_columns():
    """Add analytics columns to existing tables."""

    logger.info("Adding analytics columns to existing tables...")

    # SQL for adding columns to existing tables
    column_additions = [
        # User table additions
        "ALTER TABLE user ADD COLUMN IF NOT EXISTS notification_settings JSON NULL",
        "ALTER TABLE user ADD COLUMN IF NOT EXISTS analytics_preferences JSON NULL",
        "ALTER TABLE user ADD COLUMN IF NOT EXISTS last_activity_analysis TIMESTAMP NULL",
        "ALTER TABLE user ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) NULL DEFAULT 'UTC'",
        "ALTER TABLE user ADD COLUMN IF NOT EXISTS preferred_study_times JSON NULL",
        # Course table additions
        "ALTER TABLE course ADD COLUMN IF NOT EXISTS difficulty_rating DECIMAL(3,2) NULL",
        "ALTER TABLE course ADD COLUMN IF NOT EXISTS workload_hours_per_week DECIMAL(4,2) NULL",
        "ALTER TABLE course ADD COLUMN IF NOT EXISTS performance_trend VARCHAR(20) NULL",
        "ALTER TABLE course ADD COLUMN IF NOT EXISTS last_analytics_update TIMESTAMP NULL",
        # Assignment table additions
        "ALTER TABLE assignment ADD COLUMN IF NOT EXISTS estimated_difficulty DECIMAL(3,2) NULL",
        "ALTER TABLE assignment ADD COLUMN IF NOT EXISTS time_investment_hours DECIMAL(4,2) NULL",
        "ALTER TABLE assignment ADD COLUMN IF NOT EXISTS submission_method VARCHAR(50) NULL",
        "ALTER TABLE assignment ADD COLUMN IF NOT EXISTS late_submission BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE assignment ADD COLUMN IF NOT EXISTS performance_impact DECIMAL(3,2) NULL",
        # Audit log table additions
        "ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS user_id INT NULL",
        "ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS session_id VARCHAR(100) NULL",
        "ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS ip_address VARCHAR(45) NULL",
        "ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS user_agent VARCHAR(500) NULL",
    ]

    # Execute each column addition
    for i, sql in enumerate(column_additions, 1):
        try:
            logger.info(f"Adding column {i}/{len(column_additions)}...")
            db.session.execute(text(sql))
            db.session.commit()
            logger.info(f"Successfully added column {i}")
        except Exception as e:
            logger.error(f"Error adding column {i}: {str(e)}")
            db.session.rollback()
            # Continue with other columns even if one fails


def add_foreign_key_constraints():
    """Add foreign key constraints for audit log user_id."""

    logger.info("Adding foreign key constraints...")

    foreign_key_sql = [
        # Add foreign key for audit_log.user_id (if it doesn't exist)
        """
        ALTER TABLE audit_log 
        ADD CONSTRAINT fk_audit_log_user 
        FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
        """
    ]

    for sql in foreign_key_sql:
        try:
            db.session.execute(text(sql))
            db.session.commit()
            logger.info("Successfully added foreign key constraint")
        except Exception as e:
            logger.warning(f"Foreign key constraint may already exist: {str(e)}")
            db.session.rollback()


def create_analytics_indexes():
    """Create additional indexes for analytics performance."""

    logger.info("Creating analytics indexes...")

    indexes = [
        # Assignment table indexes
        "CREATE INDEX IF NOT EXISTS idx_assignments_due_score ON assignment(due_date, score)",
        "CREATE INDEX IF NOT EXISTS idx_assignments_course_category ON assignment(course_id, category_id)",
        "CREATE INDEX IF NOT EXISTS idx_assignments_completion ON assignment(completed, is_submitted)",
        # Course table indexes
        "CREATE INDEX IF NOT EXISTS idx_courses_term_weighted ON course(term_id, is_weighted)",
        "CREATE INDEX IF NOT EXISTS idx_courses_performance ON course(performance_trend, difficulty_rating)",
        # Audit log indexes
        "CREATE INDEX IF NOT EXISTS idx_audit_user_timestamp ON audit_log(user_id, timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_audit_course_action ON audit_log(course_id, action)",
        "CREATE INDEX IF NOT EXISTS idx_audit_assignment_timestamp ON audit_log(assignment_id, timestamp)",
    ]

    for i, sql in enumerate(indexes, 1):
        try:
            logger.info(f"Creating index {i}/{len(indexes)}...")
            db.session.execute(text(sql))
            db.session.commit()
            logger.info(f"Successfully created index {i}")
        except Exception as e:
            logger.warning(f"Index {i} may already exist: {str(e)}")
            db.session.rollback()


def populate_default_notification_preferences():
    """Create default notification preferences for existing users."""

    logger.info("Creating default notification preferences for existing users...")

    try:
        # Get all existing users
        result = db.session.execute(text("SELECT id FROM user"))
        user_ids = [row[0] for row in result.fetchall()]

        # Default notification types and their settings
        default_notifications = [
            ("assignment_due", True, "web", "18:00:00", 3),
            ("grade_posted", True, "web", None, 5),
            ("risk_alert", True, "web", None, 2),
            ("performance_insight", True, "web", "19:00:00", 2),
            ("sync_update", False, "web", None, 1),
            ("goal_milestone", True, "web", None, 1),
            ("study_reminder", False, "web", "20:00:00", 2),
        ]

        # Insert default preferences for each user
        for user_id in user_ids:
            for (
                notif_type,
                enabled,
                delivery,
                optimal_time,
                freq_limit,
            ) in default_notifications:
                try:
                    db.session.execute(
                        text("""
                        INSERT IGNORE INTO notification_preferences 
                        (user_id, notification_type, enabled, delivery_method, optimal_time, frequency_limit)
                        VALUES (:user_id, :notif_type, :enabled, :delivery, :optimal_time, :freq_limit)
                        """),
                        {
                            "user_id": user_id,
                            "notif_type": notif_type,
                            "enabled": enabled,
                            "delivery": delivery,
                            "optimal_time": optimal_time,
                            "freq_limit": freq_limit,
                        },
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not create default preferences for user {user_id}: {str(e)}"
                    )

        db.session.commit()
        logger.info(
            f"Created default notification preferences for {len(user_ids)} users"
        )

    except Exception as e:
        logger.error(f"Error creating default notification preferences: {str(e)}")
        db.session.rollback()


def update_audit_log_user_ids():
    """Update existing audit log entries with user_id based on course ownership."""

    logger.info("Updating audit log entries with user_id...")

    try:
        # Update audit_log entries with user_id from course->term->user relationship
        update_sql = """
        UPDATE audit_log al
        JOIN course c ON al.course_id = c.id
        JOIN term t ON c.term_id = t.id
        SET al.user_id = t.user_id
        WHERE al.user_id IS NULL
        """

        db.session.execute(text(update_sql))
        db.session.commit()

        logger.info("Successfully updated audit log entries with user_id")

    except Exception as e:
        logger.error(f"Error updating audit log user_id: {str(e)}")
        db.session.rollback()


def verify_migration():
    """Verify that all tables and columns were created successfully."""

    logger.info("Verifying migration completion...")

    # Check that all new tables exist
    tables_to_check = [
        "prediction_models",
        "grade_predictions",
        "risk_assessments",
        "performance_metrics",
        "performance_trends",
        "user_behavior_patterns",
        "notification_preferences",
        "smart_notifications",
        "notification_interactions",
    ]

    for table in tables_to_check:
        try:
            result = db.session.execute(text(f"SHOW TABLES LIKE '{table}'"))
            if result.fetchone():
                logger.info(f"✓ Table '{table}' exists")
            else:
                logger.error(f"✗ Table '{table}' missing")
        except Exception as e:
            logger.error(f"✗ Error checking table '{table}': {str(e)}")

    # Check that new columns exist
    columns_to_check = [
        ("user", "notification_settings"),
        ("user", "analytics_preferences"),
        ("course", "difficulty_rating"),
        ("assignment", "estimated_difficulty"),
        ("audit_log", "user_id"),
    ]

    for table, column in columns_to_check:
        try:
            result = db.session.execute(
                text(f"SHOW COLUMNS FROM {table} LIKE '{column}'")
            )
            if result.fetchone():
                logger.info(f"✓ Column '{table}.{column}' exists")
            else:
                logger.error(f"✗ Column '{table}.{column}' missing")
        except Exception as e:
            logger.error(f"✗ Error checking column '{table}.{column}': {str(e)}")

    logger.info("Migration verification complete")


def main():
    """Run the complete analytics migration."""

    logger.info("=" * 60)
    logger.info("ANALYTICS SYSTEM MIGRATION")
    logger.info("=" * 60)
    logger.info(f"Started at: {datetime.now()}")

    try:
        # Create Flask app and get database context
        app = create_app()

        with app.app_context():
            logger.info("Database connection established")

            # Run migration steps
            create_analytics_tables()
            add_analytics_columns()
            add_foreign_key_constraints()
            create_analytics_indexes()
            populate_default_notification_preferences()
            update_audit_log_user_ids()
            verify_migration()

            logger.info("=" * 60)
            logger.info("MIGRATION COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)
            logger.info(f"Completed at: {datetime.now()}")

    except Exception as e:
        logger.error(f"MIGRATION FAILED: {str(e)}")
        logger.error("Please check the error details and re-run the migration")
        sys.exit(1)


if __name__ == "__main__":
    main()
