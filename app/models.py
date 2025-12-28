from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
from enum import Enum
import json
import os


# Initialize SQLAlchemy instance
db = SQLAlchemy()

# Encryption key for API tokens (MUST be in environment variables)
ENCRYPTION_KEY = os.environ.get("API_TOKEN_ENCRYPTION_KEY")
if ENCRYPTION_KEY:
    cipher = Fernet(ENCRYPTION_KEY)
else:
    # CRITICAL WARNING: API_TOKEN_ENCRYPTION_KEY not found in environment!
    # This will cause token persistence issues across app restarts.
    import warnings

    warnings.warn(
        "API_TOKEN_ENCRYPTION_KEY environment variable not set! "
        "Canvas tokens will not persist across app restarts. "
        "Please set this in your .env file or environment.",
        RuntimeWarning,
    )
    # Fallback for development - generate a key (not secure for production!)
    cipher = Fernet(Fernet.generate_key())


class TodoItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    due_date = db.Column(db.DateTime, nullable=True)
    is_completed = db.Column(db.Boolean, default=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=True)
    course = db.relationship("Course", backref="todo_items", lazy=True)

    def __repr__(self):
        return f"<TodoItem {self.description}>"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    terms = db.relationship(
        "Term", backref="user", lazy=True, cascade="all, delete-orphan"
    )

    # Canvas API integration fields (encrypted)
    canvas_base_url = db.Column(db.String(255), nullable=True)
    _canvas_access_token = db.Column(db.String(500), nullable=True)  # Encrypted
    canvas_last_sync = db.Column(db.DateTime, nullable=True)

    # Last sync results
    canvas_last_sync_courses = db.Column(db.Integer, default=0)
    canvas_last_sync_assignments = db.Column(db.Integer, default=0)
    canvas_last_sync_categories = db.Column(db.Integer, default=0)
    canvas_sync_status = db.Column(
        db.String(50), default="idle"
    )  # idle, running, completed, failed

    # Analytics and notifications settings (JSON fields for flexibility)
    notification_settings = db.Column(db.JSON, nullable=True)
    analytics_preferences = db.Column(db.JSON, nullable=True)
    last_activity_analysis = db.Column(db.DateTime, nullable=True)

    # User behavior tracking
    timezone = db.Column(db.String(50), nullable=True, default="UTC")
    preferred_study_times = db.Column(
        db.JSON, nullable=True
    )  # Array of preferred hour ranges

    @property
    def canvas_access_token(self):
        """Get decrypted Canvas access token."""
        if self._canvas_access_token:
            try:
                return cipher.decrypt(self._canvas_access_token.encode()).decode()
            except Exception:
                return None
        return None

    @canvas_access_token.setter
    def canvas_access_token(self, value):
        """Set encrypted Canvas access token."""
        if value:
            self._canvas_access_token = cipher.encrypt(value.encode()).decode()
        else:
            self._canvas_access_token = None

    def set_password(self, password):
        from werkzeug.security import generate_password_hash

        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash

        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


class Term(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(100), nullable=False)
    season = db.Column(db.String(20), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    school_name = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    courses = db.relationship(
        "Course", backref="term", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Term {self.nickname} ({self.season} {self.year})>"


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    credits = db.Column(db.Float, nullable=False, default=0.0)
    term_id = db.Column(db.Integer, db.ForeignKey("term.id"), nullable=False)
    is_weighted = db.Column(db.Boolean, nullable=False, default=True)
    is_category = db.Column(db.Boolean, nullable=False, default=False)
    grade_categories = db.relationship(
        "GradeCategory", backref="course", lazy=True, cascade="all, delete-orphan"
    )
    assignments = db.relationship(
        "Assignment", backref="course", lazy=True, cascade="all, delete-orphan"
    )
    grade_predictions = db.relationship(
        "GradePrediction",
        backref="course",
        lazy=True,
        cascade="all, delete-orphan",
    )

    # Canvas API tracking fields
    canvas_course_id = db.Column(db.String(255), nullable=True)
    last_synced_canvas = db.Column(db.DateTime, nullable=True)

    # Analytics fields
    difficulty_rating = db.Column(db.Numeric(3, 2), nullable=True)  # 1.0-5.0 scale
    workload_hours_per_week = db.Column(db.Numeric(4, 2), nullable=True)
    performance_trend = db.Column(
        db.String(20), nullable=True
    )  # 'improving', 'declining', 'stable'
    last_analytics_update = db.Column(db.DateTime, nullable=True)

    # Indexes for analytics queries
    __table_args__ = (
        db.Index("idx_courses_term_weighted", "term_id", "is_weighted"),
        db.Index("idx_courses_performance", "performance_trend", "difficulty_rating"),
    )

    def __repr__(self):
        return f"<Course {self.name}>"


class GradeCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    weight = db.Column(db.Float, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    assignments = db.relationship("Assignment", backref="grade_category", lazy=True)

    def __repr__(self):
        return f"<GradeCategory {self.name} ({self.weight * 100}%)>"


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    score = db.Column(
        db.Float, nullable=True
    )  # Renamed from 'earned_score' for clarity
    max_score = db.Column(db.Float, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    category_id = db.Column(
        db.Integer, db.ForeignKey("grade_category.id"), nullable=True
    )
    due_date = db.Column(db.DateTime, nullable=True)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    is_submitted = db.Column(db.Boolean, nullable=False, default=False)
    is_extra_credit = db.Column(db.Boolean, nullable=False, default=False)
    is_missing = db.Column(db.Boolean, nullable=False, default=False)

    # Sync tracking fields
    last_synced_calendar = db.Column(db.DateTime, nullable=True)
    last_synced_tasks = db.Column(db.DateTime, nullable=True)
    calendar_event_id = db.Column(db.String(255), nullable=True)
    google_task_id = db.Column(db.String(255), nullable=True)
    last_modified = db.Column(
        db.DateTime,
        nullable=True,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )

    # Canvas API tracking fields
    canvas_assignment_id = db.Column(db.String(255), nullable=True)
    canvas_course_id = db.Column(db.String(255), nullable=True)
    last_synced_canvas = db.Column(db.DateTime, nullable=True)

    # Analytics fields for tracking patterns and predictions
    estimated_difficulty = db.Column(db.Numeric(3, 2), nullable=True)  # 1.0-5.0 scale
    time_investment_hours = db.Column(db.Numeric(4, 2), nullable=True)
    submission_method = db.Column(
        db.String(50), nullable=True
    )  # 'early', 'on_time', 'late'
    late_submission = db.Column(db.Boolean, nullable=False, default=False)
    performance_impact = db.Column(
        db.Numeric(3, 2), nullable=True
    )  # Impact on overall course grade

    # Indexes for analytics queries
    __table_args__ = (
        db.Index("idx_assignments_due_score", "due_date", "score"),
        db.Index("idx_assignments_course_category", "course_id", "category_id"),
        db.Index("idx_assignments_completion", "completed", "is_submitted"),
    )

    @property
    def earned_score(self):
        """Alias for score to maintain backward compatibility."""
        return self.score

    @earned_score.setter
    def earned_score(self, value):
        """Alias for score to maintain backward compatibility."""
        self.score = value

    def __repr__(self):
        return f"<Assignment {self.name}>"


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(
        db.Integer, db.ForeignKey("assignment.id"), nullable=False
    )
    assignment_name = db.Column(db.String(200), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False
    )  # Added for analytics
    action = db.Column(db.String(100), nullable=False)
    old_value = db.Column(db.String(500), nullable=True)
    new_value = db.Column(db.String(500), nullable=True)
    field_changed = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(
        db.DateTime, nullable=False, default=db.func.current_timestamp()
    )

    # Additional context for analytics
    session_id = db.Column(db.String(100), nullable=True)  # Track user sessions
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4/IPv6
    user_agent = db.Column(db.String(500), nullable=True)

    assignment = db.relationship("Assignment", backref="audit_logs", lazy=True)
    course = db.relationship("Course", backref="audit_logs", lazy=True)
    user = db.relationship("User", backref="audit_logs", lazy=True)

    # Indexes for analytics queries
    __table_args__ = (
        db.Index("idx_audit_user_timestamp", "user_id", "timestamp"),
        db.Index("idx_audit_course_action", "course_id", "action"),
        db.Index("idx_audit_assignment_timestamp", "assignment_id", "timestamp"),
    )

    def __repr__(self):
        return f"<AuditLog {self.action} on {self.assignment_name}>"


class CampusClosure(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    term_id = db.Column(db.Integer, db.ForeignKey("term.id"), nullable=False)

    def __repr__(self):
        return f"<CampusClosure {self.reason}>"


class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mail_server = db.Column(db.String(255), nullable=True)
    mail_port = db.Column(db.Integer, nullable=True)
    mail_username = db.Column(db.String(255), nullable=True)
    mail_password = db.Column(db.String(255), nullable=True)
    mail_use_tls = db.Column(db.Boolean, nullable=False, default=True)
    email_reminders = db.Column(db.Boolean, nullable=False, default=True)
    dashboard_notifications = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<Settings>"


class SyncProgress(db.Model):
    """Model to store sync progress across threads"""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    sync_type = db.Column(
        db.String(20), nullable=False
    )  # 'canvas', 'canvas_term', 'canvas_course'
    target_id = db.Column(
        db.Integer, nullable=True
    )  # term_id or course_id for specific syncs
    progress_percent = db.Column(db.Integer, default=0)
    completed_items = db.Column(db.Integer, default=0)
    total_items = db.Column(db.Integer, default=0)
    current_operation = db.Column(db.String(255), default="")
    current_item = db.Column(db.String(255), default="")
    elapsed_time = db.Column(db.Float, default=0.0)
    errors = db.Column(db.Text, default="")  # JSON string of errors
    is_complete = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime, server_default=db.func.now(), onupdate=db.func.now()
    )

    user = db.relationship("User", backref="sync_progress")

    def set_errors(self, errors_list):
        """Set errors as JSON string"""
        import json

        self.errors = json.dumps(errors_list)

    def get_errors(self):
        """Get errors as list"""
        import json

        if self.errors:
            try:
                return json.loads(self.errors)
            except:
                return []
        return []

    def to_dict(self):
        """Convert to dictionary for JSON response"""
        return {
            "progress_percent": self.progress_percent,
            "completed_items": self.completed_items,
            "total_items": self.total_items,
            "current_operation": self.current_operation,
            "current_item": self.current_item,
            "elapsed_time": self.elapsed_time,
            "errors": self.get_errors(),
            "is_complete": self.is_complete,
        }

    def __repr__(self):
        return (
            f"<SyncProgress {self.user_id}:{self.sync_type} {self.progress_percent}%>"
        )


# =============================================================================
# ANALYTICS AND PREDICTION MODELS
# =============================================================================


class NotificationType(Enum):
    """Enumeration of notification types for the smart notification system."""

    ASSIGNMENT_DUE = "assignment_due"
    GRADE_POSTED = "grade_posted"
    RISK_ALERT = "risk_alert"
    PERFORMANCE_INSIGHT = "performance_insight"
    SYNC_UPDATE = "sync_update"
    GOAL_MILESTONE = "goal_milestone"
    STUDY_REMINDER = "study_reminder"


class NotificationPriority(Enum):
    """Enumeration of notification priorities."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


class PredictionModel(db.Model):
    """
    Storage for machine learning models used in grade prediction.

    This model stores serialized ML models, their metadata, and performance metrics.
    Models are versioned and can be retrained as new data becomes available.
    """

    __tablename__ = "prediction_models"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    model_type = db.Column(
        db.Enum(
            "grade_prediction",
            "risk_assessment",
            "performance_forecast",
            name="model_types",
        ),
        nullable=False,
    )
    model_version = db.Column(db.String(20), nullable=False, default="1.0")
    model_data = db.Column(db.JSON, nullable=True)  # Serialized model parameters
    accuracy_score = db.Column(db.Numeric(5, 4), nullable=True)
    training_data_size = db.Column(db.Integer, nullable=True)
    feature_importance = db.Column(db.JSON, nullable=True)  # Feature importance scores
    last_trained = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    user = db.relationship("User", backref="prediction_models")

    # Indexes
    __table_args__ = (
        db.Index("idx_user_models", "user_id", "model_type"),
        db.Index("idx_model_trained", "user_id", "last_trained"),
    )

    def to_dict(self):
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "model_type": self.model_type.value
            if hasattr(self.model_type, "value")
            else str(self.model_type),
            "model_version": self.model_version,
            "accuracy_score": float(self.accuracy_score)
            if self.accuracy_score
            else None,
            "training_data_size": self.training_data_size,
            "last_trained": self.last_trained.isoformat(),
            "created_at": self.created_at.isoformat(),
        }

    def __repr__(self):
        return f"<PredictionModel {self.model_type} v{self.model_version}>"


class GradePrediction(db.Model):
    """
    Storage for grade predictions generated by the analytics engine.

    Tracks predictions over time to measure accuracy and improve models.
    """

    __tablename__ = "grade_predictions"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    predicted_grade = db.Column(db.Numeric(5, 2), nullable=False)
    confidence_score = db.Column(db.Numeric(5, 4), nullable=False)
    grade_range_min = db.Column(db.Numeric(5, 2), nullable=True)
    grade_range_max = db.Column(db.Numeric(5, 2), nullable=True)
    prediction_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    actual_grade = db.Column(
        db.Numeric(5, 2), nullable=True
    )  # Set when final grade available
    contributing_factors = db.Column(
        db.JSON, nullable=True
    )  # Factors that influenced prediction
    model_version = db.Column(db.String(20), nullable=False)

    # Relationships
    user = db.relationship("User", backref="grade_predictions")

    # Indexes
    __table_args__ = (
        db.Index("idx_course_predictions", "course_id", "prediction_date"),
        db.Index("idx_user_predictions", "user_id", "prediction_date"),
        db.Index("idx_prediction_accuracy", "actual_grade", "predicted_grade"),
    )

    @property
    def accuracy(self):
        """Calculate prediction accuracy if actual grade is available."""
        if self.actual_grade is not None:
            return (
                1.0
                - abs(float(self.actual_grade) - float(self.predicted_grade)) / 100.0
            )
        return None

    def to_dict(self):
        """Convert prediction to dictionary for API responses."""
        return {
            "id": self.id,
            "course_id": self.course_id,
            "predicted_grade": float(self.predicted_grade),
            "confidence": float(self.confidence_score),
            "grade_range": [float(self.grade_range_min), float(self.grade_range_max)]
            if self.grade_range_min
            else None,
            "prediction_date": self.prediction_date.isoformat(),
            "actual_grade": float(self.actual_grade) if self.actual_grade else None,
            "accuracy": self.accuracy,
            "factors": self.contributing_factors,
        }

    def __repr__(self):
        return f"<GradePrediction {self.predicted_grade}% for Course {self.course_id}>"


class RiskAssessment(db.Model):
    """
    Storage for academic risk assessments.

    Tracks risk levels over time and monitors intervention effectiveness.
    """

    __tablename__ = "risk_assessments"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    risk_level = db.Column(
        db.Enum("low", "medium", "high", "critical", name="risk_levels"), nullable=False
    )
    risk_score = db.Column(db.Numeric(5, 4), nullable=False)
    risk_factors = db.Column(db.JSON, nullable=True)  # Detailed risk analysis
    recommendations = db.Column(db.Text, nullable=True)
    intervention_suggested = db.Column(db.Boolean, nullable=False, default=False)
    assessment_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolution_method = db.Column(
        db.String(100), nullable=True
    )  # How risk was resolved

    # Relationships
    course = db.relationship("Course", backref="risk_assessments")
    user = db.relationship("User", backref="risk_assessments")

    # Indexes
    __table_args__ = (
        db.Index("idx_active_risks", "user_id", "resolved_at", "risk_level"),
        db.Index("idx_course_risks", "course_id", "assessment_date"),
    )

    @property
    def is_active(self):
        """Check if risk assessment is still active (unresolved)."""
        return self.resolved_at is None

    @property
    def days_active(self):
        """Calculate how many days the risk has been active."""
        end_date = self.resolved_at or datetime.utcnow()
        return (end_date - self.assessment_date).days

    def resolve(self, method=None):
        """Mark risk assessment as resolved."""
        self.resolved_at = datetime.utcnow()
        if method:
            self.resolution_method = method

    def to_dict(self):
        """Convert risk assessment to dictionary for API responses."""
        return {
            "id": self.id,
            "course_id": self.course_id,
            "risk_level": self.risk_level,
            "risk_score": float(self.risk_score),
            "factors": self.risk_factors,
            "recommendations": self.recommendations,
            "assessment_date": self.assessment_date.isoformat(),
            "is_active": self.is_active,
            "days_active": self.days_active,
        }

    def __repr__(self):
        return f"<RiskAssessment {self.risk_level} for Course {self.course_id}>"


class PerformanceMetric(db.Model):
    """
    Storage for calculated performance metrics.

    Stores various academic performance metrics calculated over time.
    """

    __tablename__ = "performance_metrics"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    term_id = db.Column(db.Integer, db.ForeignKey("term.id"), nullable=True)
    metric_type = db.Column(
        db.String(50), nullable=False
    )  # e.g., 'gpa', 'consistency', 'workload_balance'
    metric_value = db.Column(db.Numeric(10, 4), nullable=False)
    calculation_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    metric_metadata = db.Column(db.JSON, nullable=True)  # Additional metric details

    # Relationships
    user = db.relationship("User", backref="performance_metrics")
    term = db.relationship("Term", backref="performance_metrics")

    # Indexes
    __table_args__ = (
        db.Index("idx_user_metrics", "user_id", "metric_type", "calculation_date"),
        db.Index("idx_term_metrics", "term_id", "metric_type"),
    )

    def to_dict(self):
        """Convert metric to dictionary for API responses."""
        return {
            "id": self.id,
            "type": self.metric_type,
            "value": float(self.metric_value),
            "date": self.calculation_date.isoformat(),
            "metadata": self.metadata,
        }

    def __repr__(self):
        return f"<PerformanceMetric {self.metric_type}: {self.metric_value}>"


class PerformanceTrend(db.Model):
    """
    Storage for identified performance trends.

    Tracks long-term patterns in academic performance.
    """

    __tablename__ = "performance_trends"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    trend_type = db.Column(
        db.String(50), nullable=False
    )  # e.g., 'grade_trend', 'submission_pattern'
    trend_direction = db.Column(
        db.Enum("improving", "declining", "stable", name="trend_directions"),
        nullable=False,
    )
    trend_strength = db.Column(
        db.Numeric(5, 4), nullable=False
    )  # How strong the trend is (0-1)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    data_points = db.Column(db.JSON, nullable=True)  # Data supporting the trend
    statistical_significance = db.Column(db.Numeric(5, 4), nullable=True)

    # Relationships
    user = db.relationship("User", backref="performance_trends")

    # Indexes
    __table_args__ = (db.Index("idx_user_trends", "user_id", "trend_type", "end_date"),)

    @property
    def duration_days(self):
        """Calculate the duration of the trend in days."""
        return (self.end_date - self.start_date).days

    def to_dict(self):
        """Convert trend to dictionary for API responses."""
        return {
            "id": self.id,
            "type": self.trend_type,
            "direction": self.trend_direction,
            "strength": float(self.trend_strength),
            "duration_days": self.duration_days,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "significance": float(self.statistical_significance)
            if self.statistical_significance
            else None,
        }

    def __repr__(self):
        return f"<PerformanceTrend {self.trend_type}: {self.trend_direction}>"


class UserBehaviorPattern(db.Model):
    """
    Storage for learned user behavior patterns.

    Stores patterns learned from user interactions for personalization.
    """

    __tablename__ = "user_behavior_patterns"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    pattern_type = db.Column(
        db.String(50), nullable=False
    )  # e.g., 'study_times', 'submission_habits'
    pattern_data = db.Column(db.JSON, nullable=False)
    confidence_score = db.Column(db.Numeric(5, 4), nullable=False)
    sample_size = db.Column(
        db.Integer, nullable=False, default=0
    )  # Number of data points
    last_updated = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    user = db.relationship("User", backref="behavior_patterns")

    # Constraints
    __table_args__ = (
        db.UniqueConstraint("user_id", "pattern_type", name="unique_user_pattern"),
    )

    def update_pattern(self, new_data, new_confidence, sample_increase=1):
        """Update pattern with new data."""
        self.pattern_data = new_data
        self.confidence_score = new_confidence
        self.sample_size += sample_increase
        self.last_updated = datetime.utcnow()

    def to_dict(self):
        """Convert pattern to dictionary for API responses."""
        return {
            "type": self.pattern_type,
            "data": self.pattern_data,
            "confidence": float(self.confidence_score),
            "sample_size": self.sample_size,
            "last_updated": self.last_updated.isoformat(),
        }

    def __repr__(self):
        return (
            f"<UserBehaviorPattern {self.pattern_type} (conf: {self.confidence_score})>"
        )


class NotificationPreference(db.Model):
    """
    Storage for user notification preferences.

    Manages how and when users want to receive different types of notifications.
    """

    __tablename__ = "notification_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    delivery_method = db.Column(
        db.Enum("web", "email", "push", name="delivery_methods"),
        nullable=False,
        default="web",
    )
    optimal_time = db.Column(db.Time, nullable=True)  # Preferred time for notifications
    frequency_limit = db.Column(db.Integer, nullable=False, default=5)  # Max per day
    quiet_hours_start = db.Column(db.Time, nullable=True)
    quiet_hours_end = db.Column(db.Time, nullable=True)
    preferences = db.Column(db.JSON, nullable=True)  # Additional preferences

    # Relationships
    user = db.relationship("User", backref="notification_preferences")

    # Constraints
    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "notification_type", name="unique_user_notification"
        ),
    )

    def is_quiet_time(self, check_time=None):
        """Check if the given time is within quiet hours."""
        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False

        if check_time is None:
            check_time = datetime.now().time()

        # Handle overnight quiet hours (e.g., 10 PM to 7 AM)
        if self.quiet_hours_start > self.quiet_hours_end:
            return (
                check_time >= self.quiet_hours_start
                or check_time <= self.quiet_hours_end
            )
        else:
            return self.quiet_hours_start <= check_time <= self.quiet_hours_end

    def to_dict(self):
        """Convert preference to dictionary for API responses."""
        return {
            "type": self.notification_type,
            "enabled": self.enabled,
            "delivery_method": self.delivery_method,
            "optimal_time": self.optimal_time.isoformat()
            if self.optimal_time
            else None,
            "frequency_limit": self.frequency_limit,
            "quiet_hours": {
                "start": self.quiet_hours_start.isoformat()
                if self.quiet_hours_start
                else None,
                "end": self.quiet_hours_end.isoformat()
                if self.quiet_hours_end
                else None,
            },
            "preferences": self.preferences,
        }

    def __repr__(self):
        return f"<NotificationPreference {self.notification_type} ({self.delivery_method})>"


class SmartNotification(db.Model):
    """
    Storage for generated smart notifications.

    Tracks notification delivery, interaction, and effectiveness.
    """

    __tablename__ = "smart_notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=True)
    priority = db.Column(
        db.Enum("low", "medium", "high", "urgent", name="notification_priorities"),
        nullable=False,
        default="medium",
    )
    scheduled_time = db.Column(db.DateTime, nullable=True)
    sent_time = db.Column(db.DateTime, nullable=True)
    read_time = db.Column(db.DateTime, nullable=True)
    action_taken = db.Column(db.Boolean, nullable=False, default=False)
    action_url = db.Column(db.String(500), nullable=True)
    effectiveness_score = db.Column(
        db.Numeric(3, 2), nullable=True
    )  # 0-1 based on user interaction
    notification_metadata = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    user = db.relationship("User", backref="smart_notifications")

    # Indexes
    __table_args__ = (
        db.Index("idx_user_notifications", "user_id", "sent_time", "read_time"),
        db.Index("idx_scheduled_notifications", "scheduled_time", "sent_time"),
        db.Index(
            "idx_notification_effectiveness", "notification_type", "effectiveness_score"
        ),
    )

    @property
    def is_sent(self):
        """Check if notification has been sent."""
        return self.sent_time is not None

    @property
    def is_read(self):
        """Check if notification has been read."""
        return self.read_time is not None

    @property
    def response_time_minutes(self):
        """Calculate response time in minutes."""
        if self.sent_time and self.read_time:
            return (self.read_time - self.sent_time).total_seconds() / 60
        return None

    def mark_sent(self):
        """Mark notification as sent."""
        self.sent_time = datetime.utcnow()

    def mark_read(self):
        """Mark notification as read."""
        if not self.read_time:
            self.read_time = datetime.utcnow()

    def mark_action_taken(self):
        """Mark that user took action on notification."""
        self.action_taken = True
        if not self.read_time:
            self.mark_read()

    def calculate_effectiveness(self):
        """Calculate effectiveness score based on user interaction."""
        if not self.is_sent:
            return 0.0

        score = 0.0

        # Base score for being read
        if self.is_read:
            score += 0.3

            # Bonus for quick response
            response_time = self.response_time_minutes
            if response_time:
                if response_time <= 5:
                    score += 0.3
                elif response_time <= 30:
                    score += 0.2
                elif response_time <= 120:
                    score += 0.1

        # High score for action taken
        if self.action_taken:
            score += 0.4

        self.effectiveness_score = min(score, 1.0)
        return self.effectiveness_score

    def to_dict(self):
        """Convert notification to dictionary for API responses."""
        return {
            "id": self.id,
            "type": self.notification_type,
            "title": self.title,
            "message": self.message,
            "priority": self.priority,
            "scheduled_time": self.scheduled_time.isoformat()
            if self.scheduled_time
            else None,
            "sent_time": self.sent_time.isoformat() if self.sent_time else None,
            "read_time": self.read_time.isoformat() if self.read_time else None,
            "action_taken": self.action_taken,
            "action_url": self.action_url,
            "effectiveness": float(self.effectiveness_score)
            if self.effectiveness_score
            else None,
            "metadata": self.metadata,
        }

    def __repr__(self):
        return f"<SmartNotification {self.title} ({self.priority})>"


class NotificationInteraction(db.Model):
    """
    Storage for notification interaction events.

    Detailed tracking of how users interact with notifications.
    """

    __tablename__ = "notification_interactions"

    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(
        db.Integer, db.ForeignKey("smart_notifications.id"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    interaction_type = db.Column(
        db.Enum("viewed", "clicked", "dismissed", "snoozed", name="interaction_types"),
        nullable=False,
    )
    interaction_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    device_info = db.Column(db.String(255), nullable=True)
    additional_data = db.Column(db.JSON, nullable=True)

    # Relationships
    notification = db.relationship("SmartNotification", backref="interactions")
    user = db.relationship("User", backref="notification_interactions")

    # Indexes
    __table_args__ = (
        db.Index("idx_user_interactions", "user_id", "interaction_time"),
        db.Index(
            "idx_notification_interactions", "notification_id", "interaction_type"
        ),
    )

    def to_dict(self):
        """Convert interaction to dictionary for API responses."""
        return {
            "id": self.id,
            "notification_id": self.notification_id,
            "type": self.interaction_type,
            "time": self.interaction_time.isoformat(),
            "device": self.device_info,
            "data": self.additional_data,
        }

    def __repr__(self):
        return f"<NotificationInteraction {self.interaction_type} on {self.notification_id}>"


class CanvasSyncMetrics(db.Model):
    """
    Track Canvas sync performance metrics and statistics.

    This model stores metrics for each Canvas sync operation to enable
    performance monitoring, trend analysis, and troubleshooting.
    """

    __tablename__ = "canvas_sync_metrics"

    id = db.Column(db.Integer, primary_key=True)

    # Identifiers
    sync_task_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)

    # Timing
    sync_start_time = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    sync_end_time = db.Column(db.DateTime, nullable=True)
    total_duration_seconds = db.Column(db.Float, nullable=True)

    # Status
    sync_status = db.Column(
        db.String(50), default="in_progress", nullable=False, index=True
    )  # 'in_progress', 'completed', 'failed', 'partial'
    error_message = db.Column(db.Text, nullable=True)

    # Sync scope
    sync_type = db.Column(
        db.String(50), default="all", nullable=False
    )  # 'all', 'courses', 'assignments', 'grades'
    target_course_id = db.Column(db.Integer, nullable=True)

    # Statistics
    courses_processed = db.Column(db.Integer, default=0)
    courses_created = db.Column(db.Integer, default=0)
    courses_updated = db.Column(db.Integer, default=0)

    assignments_processed = db.Column(db.Integer, default=0)
    assignments_created = db.Column(db.Integer, default=0)
    assignments_updated = db.Column(db.Integer, default=0)

    submissions_processed = db.Column(db.Integer, default=0)
    submissions_created = db.Column(db.Integer, default=0)
    submissions_updated = db.Column(db.Integer, default=0)

    grades_processed = db.Column(db.Integer, default=0)
    grades_updated = db.Column(db.Integer, default=0)

    # API metrics
    api_calls_made = db.Column(db.Integer, default=0)
    api_calls_failed = db.Column(db.Integer, default=0)
    total_api_duration_ms = db.Column(db.Float, default=0.0)
    api_rate_limit_hits = db.Column(db.Integer, default=0)

    # Database metrics
    db_operations = db.Column(db.Integer, default=0)
    db_duration_ms = db.Column(db.Float, default=0.0)

    # Data size
    total_data_size_bytes = db.Column(db.BigInteger, default=0)

    # Additional context
    incremental_sync = db.Column(db.Boolean, default=True)
    use_pagination = db.Column(db.Boolean, default=True)
    chunk_size = db.Column(db.Integer, default=10)

    # Additional data as JSON (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    sync_metadata = db.Column(db.JSON, nullable=True)

    # Relationships
    user = db.relationship("User", backref="canvas_sync_metrics", lazy=True)

    # Indexes
    __table_args__ = (
        db.Index("idx_canvas_sync_user_time", "user_id", "sync_start_time"),
        db.Index("idx_canvas_sync_status_time", "sync_status", "sync_start_time"),
        db.Index("idx_canvas_sync_type", "sync_type"),
    )

    def __repr__(self):
        return f"<CanvasSyncMetrics {self.sync_task_id[:8]}... {self.sync_status}>"

    def to_dict(self) -> dict:
        """Convert metrics to dictionary for API responses."""
        return {
            "id": self.id,
            "sync_task_id": self.sync_task_id,
            "user_id": self.user_id,
            "sync_start_time": self.sync_start_time.isoformat()
            if self.sync_start_time
            else None,
            "sync_end_time": self.sync_end_time.isoformat()
            if self.sync_end_time
            else None,
            "total_duration_seconds": self.total_duration_seconds,
            "sync_status": self.sync_status,
            "error_message": self.error_message,
            "sync_type": self.sync_type,
            "target_course_id": self.target_course_id,
            "courses": {
                "processed": self.courses_processed,
                "created": self.courses_created,
                "updated": self.courses_updated,
            },
            "assignments": {
                "processed": self.assignments_processed,
                "created": self.assignments_created,
                "updated": self.assignments_updated,
            },
            "submissions": {
                "processed": self.submissions_processed,
                "created": self.submissions_created,
                "updated": self.submissions_updated,
            },
            "grades": {
                "processed": self.grades_processed,
                "updated": self.grades_updated,
            },
            "api_metrics": {
                "calls_made": self.api_calls_made,
                "calls_failed": self.api_calls_failed,
                "total_duration_ms": self.total_api_duration_ms,
                "rate_limit_hits": self.api_rate_limit_hits,
            },
            "database_metrics": {
                "operations": self.db_operations,
                "duration_ms": self.db_duration_ms,
            },
            "data_size_bytes": self.total_data_size_bytes,
            "incremental_sync": self.incremental_sync,
            "use_pagination": self.use_pagination,
            "chunk_size": self.chunk_size,
            "metadata": self.sync_metadata,
        }

    @staticmethod
    def create_from_sync_result(
        task_id: str, user_id: int, result: dict
    ) -> "CanvasSyncMetrics":
        """
        Create a metrics record from sync task result.

        Args:
            task_id: Celery task ID
            user_id: User ID who initiated the sync
            result: Dictionary with sync results

        Returns:
            CanvasSyncMetrics instance
        """
        metrics = CanvasSyncMetrics(
            sync_task_id=task_id,
            user_id=user_id,
            sync_status=result.get("status", "completed"),
            sync_type=result.get("sync_type", "all"),
            target_course_id=result.get("course_id"),
            courses_processed=result.get("courses", {}).get("processed", 0),
            courses_created=result.get("courses", {}).get("created", 0),
            courses_updated=result.get("courses", {}).get("updated", 0),
            assignments_processed=result.get("assignments", {}).get("processed", 0),
            assignments_created=result.get("assignments", {}).get("created", 0),
            assignments_updated=result.get("assignments", {}).get("updated", 0),
            api_calls_made=result.get("api_calls", {}).get("made", 0),
            api_calls_failed=result.get("api_calls", {}).get("failed", 0),
            total_api_duration_ms=result.get("api_calls", {}).get("duration_ms", 0),
            db_operations=result.get("db_operations", 0),
            db_duration_ms=result.get("db_duration_ms", 0),
            incremental_sync=result.get("incremental_sync", True),
            use_pagination=result.get("use_pagination", True),
            chunk_size=result.get("chunk_size", 10),
            sync_metadata=result.get("metadata"),
        )

        if "end_time" in result:
            metrics.sync_end_time = result["end_time"]
        if "duration" in result:
            metrics.total_duration_seconds = result["duration"]
        if "error" in result:
            metrics.error_message = result["error"]
            metrics.sync_status = "failed"

        return metrics
