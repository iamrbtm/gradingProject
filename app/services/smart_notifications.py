"""
Smart Notification System
=========================

This module provides adaptive, intelligent notifications based on user behavior
patterns, academic performance, and contextual factors.

Key Features:
- User behavior learning and pattern recognition
- Contextual notification generation
- Adaptive delivery timing optimization
- Personalized content customization
- Effectiveness tracking and optimization
- Multi-channel delivery support

Author: Analytics Team
Date: 2024-12-19
"""

import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta, time
from dataclasses import dataclass
from enum import Enum
import json
import statistics
from collections import defaultdict, Counter

from ..models import (
    db,
    User,
    Course,
    Term,
    Assignment,
    NotificationPreference,
    SmartNotification,
    NotificationInteraction,
    UserBehaviorPattern,
    PerformanceMetric,
    RiskAssessment,
)
from sqlalchemy import desc, func

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Enumeration of notification types."""

    ASSIGNMENT_DUE = "assignment_due"
    GRADE_UPDATE = "grade_update"
    PERFORMANCE_ALERT = "performance_alert"
    MOTIVATION_MESSAGE = "motivation_message"
    STUDY_REMINDER = "study_reminder"
    ACHIEVEMENT = "achievement"
    RISK_WARNING = "risk_warning"
    DEADLINE_APPROACHING = "deadline_approaching"
    WEEKLY_SUMMARY = "weekly_summary"
    CUSTOM_REMINDER = "custom_reminder"


class DeliveryChannel(Enum):
    """Enumeration of delivery channels."""

    EMAIL = "email"
    WEB_PUSH = "web_push"
    IN_APP = "in_app"
    SMS = "sms"
    DASHBOARD = "dashboard"


class Priority(Enum):
    """Enumeration of notification priorities."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "urgent"


@dataclass
class NotificationContext:
    """Context information for notification generation."""

    user_id: int
    current_time: datetime
    user_behavior_patterns: Dict[str, Any]
    recent_activity: List[Dict[str, Any]]
    academic_status: Dict[str, Any]
    preferences: Dict[str, Any]


@dataclass
class NotificationContent:
    """Generated notification content."""

    title: str
    message: str
    action_text: Optional[str]
    action_url: Optional[str]
    metadata: Dict[str, Any]
    personalization_factors: List[str]


@dataclass
class DeliverySchedule:
    """Notification delivery schedule."""

    optimal_time: datetime
    backup_times: List[datetime]
    channel_preference: List[DeliveryChannel]
    urgency_level: Priority
    expected_engagement_rate: float


class SmartNotificationService:
    """
    Intelligent notification service with adaptive learning capabilities.

    This service learns from user behavior patterns to optimize notification
    timing, content, and delivery methods for maximum effectiveness.
    """

    def __init__(self):
        """Initialize the smart notification service."""
        self.notification_cache = {}
        self.behavior_analysis_window = timedelta(days=30)
        self.min_behavior_data_points = 5

    def generate_contextual_notifications(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Generate contextual notifications based on user's current situation.

        Args:
            user_id: The user ID to generate notifications for

        Returns:
            List of generated notifications with delivery recommendations
        """
        try:
            logger.info(f"Generating contextual notifications for user {user_id}")

            # Get notification context
            context = self._build_notification_context(user_id)

            # Generate different types of notifications
            notifications = []

            # Assignment-related notifications
            notifications.extend(self._generate_assignment_notifications(context))

            # Performance-related notifications
            notifications.extend(self._generate_performance_notifications(context))

            # Motivational notifications
            notifications.extend(self._generate_motivational_notifications(context))

            # Study reminder notifications
            notifications.extend(self._generate_study_reminders(context))

            # Achievement notifications
            notifications.extend(self._generate_achievement_notifications(context))

            # Filter and prioritize notifications
            notifications = self._filter_and_prioritize_notifications(
                notifications, context
            )

            # Optimize delivery schedule for each notification
            for notification in notifications:
                delivery_schedule = self._optimize_delivery_schedule(
                    notification, context
                )
                # Convert DeliverySchedule dataclass to dict for JSON serialization
                notification["delivery_schedule"] = {
                    "optimal_time": delivery_schedule.optimal_time.isoformat()
                    if delivery_schedule.optimal_time
                    else None,
                    "backup_times": [
                        t.isoformat() for t in delivery_schedule.backup_times
                    ],
                    "channel_preference": [
                        ch.value for ch in delivery_schedule.channel_preference
                    ],
                    "urgency_level": delivery_schedule.urgency_level.value,
                    "expected_engagement_rate": delivery_schedule.expected_engagement_rate,
                }

            # Store notifications in database
            self._store_notifications(notifications)

            logger.info(f"Generated {len(notifications)} contextual notifications")
            return notifications

        except Exception as e:
            logger.error(
                f"Error generating contextual notifications for user {user_id}: {str(e)}"
            )
            return []

    def learn_user_behavior_patterns(self, user_id: int) -> Dict[str, Any]:
        """
        Analyze and learn user behavior patterns for notification optimization.

        Args:
            user_id: The user ID to analyze

        Returns:
            Dictionary with learned behavior patterns
        """
        try:
            logger.info(f"Learning behavior patterns for user {user_id}")

            # Analyze notification interaction patterns
            interaction_patterns = self._analyze_notification_interactions(user_id)

            # Analyze activity timing patterns
            timing_patterns = self._analyze_activity_timing(user_id)

            # Analyze engagement preferences
            engagement_patterns = self._analyze_engagement_preferences(user_id)

            # Analyze content preferences
            content_patterns = self._analyze_content_preferences(user_id)

            # Combine patterns
            behavior_patterns = {
                "interaction_patterns": interaction_patterns,
                "timing_patterns": timing_patterns,
                "engagement_patterns": engagement_patterns,
                "content_patterns": content_patterns,
                "last_updated": datetime.utcnow().isoformat(),
                "confidence_score": self._calculate_pattern_confidence(user_id),
            }

            # Store learned patterns
            self._store_behavior_patterns(user_id, behavior_patterns)

            logger.info(f"Learned behavior patterns for user {user_id}")
            return behavior_patterns

        except Exception as e:
            logger.error(
                f"Error learning behavior patterns for user {user_id}: {str(e)}"
            )
            return {}

    def optimize_notification_timing(
        self, user_id: int, notification_type: NotificationType
    ) -> datetime:
        """
        Optimize notification timing based on user behavior patterns.

        Args:
            user_id: The user ID
            notification_type: Type of notification

        Returns:
            Optimal datetime for notification delivery
        """
        try:
            logger.info(f"Optimizing notification timing for user {user_id}")

            # Get user behavior patterns
            patterns = self._get_user_behavior_patterns(user_id)

            if not patterns:
                # Default to sensible times if no patterns available
                return self._get_default_notification_time(notification_type)

            # Get optimal time based on patterns
            timing_patterns = patterns.get("timing_patterns", {})

            # Find best time slot for this notification type
            type_preferences = timing_patterns.get(notification_type.value, {})

            if type_preferences:
                optimal_hour = type_preferences.get("preferred_hour", 10)
                optimal_minute = type_preferences.get("preferred_minute", 0)
            else:
                # Use general activity patterns
                general_patterns = timing_patterns.get("general_activity", {})
                optimal_hour = general_patterns.get("most_active_hour", 10)
                optimal_minute = 0

            # Calculate next optimal time
            now = datetime.utcnow()

            # Try today first
            optimal_today = now.replace(
                hour=optimal_hour, minute=optimal_minute, second=0, microsecond=0
            )

            if optimal_today > now:
                return optimal_today
            else:
                # Tomorrow at the optimal time
                return optimal_today + timedelta(days=1)

        except Exception as e:
            logger.error(
                f"Error optimizing notification timing for user {user_id}: {str(e)}"
            )
            return datetime.utcnow() + timedelta(hours=1)

    def personalize_notification_content(
        self,
        user_id: int,
        notification_type: NotificationType,
        base_content: Dict[str, str],
    ) -> NotificationContent:
        """
        Personalize notification content based on user preferences and behavior.

        Args:
            user_id: The user ID
            notification_type: Type of notification
            base_content: Base content to personalize

        Returns:
            Personalized NotificationContent
        """
        try:
            logger.info(f"Personalizing notification content for user {user_id}")

            user = User.query.get(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            # Get user behavior patterns
            patterns = self._get_user_behavior_patterns(user_id)
            content_preferences = (
                patterns.get("content_patterns", {}) if patterns else {}
            )

            # Get user preferences
            preferences = self._get_user_notification_preferences(user_id)

            # Personalize title
            title = self._personalize_title(
                base_content.get("title", ""),
                user,
                content_preferences,
                notification_type,
            )

            # Personalize message
            message = self._personalize_message(
                base_content.get("message", ""),
                user,
                content_preferences,
                notification_type,
            )

            # Determine action text and URL
            action_text, action_url = self._determine_action(
                notification_type, base_content.get("action_url", ""), user_id
            )

            # Build metadata
            metadata = {
                "notification_type": notification_type.value,
                "personalization_applied": True,
                "user_preferences_used": list(content_preferences.keys()),
                "generated_at": datetime.utcnow().isoformat(),
            }

            # Track personalization factors
            personalization_factors = self._track_personalization_factors(
                content_preferences, preferences, notification_type
            )

            return NotificationContent(
                title=title,
                message=message,
                action_text=action_text,
                action_url=action_url,
                metadata=metadata,
                personalization_factors=personalization_factors,
            )

        except Exception as e:
            logger.error(
                f"Error personalizing notification content for user {user_id}: {str(e)}"
            )
            # Return base content if personalization fails
            return NotificationContent(
                title=base_content.get("title", ""),
                message=base_content.get("message", ""),
                action_text=base_content.get("action_text"),
                action_url=base_content.get("action_url"),
                metadata={"error": str(e)},
                personalization_factors=[],
            )

    def track_notification_effectiveness(
        self,
        notification_id: int,
        interaction_type: str,
        interaction_time: Optional[datetime] = None,
    ) -> None:
        """
        Track notification interaction for effectiveness analysis.

        Args:
            notification_id: The notification ID
            interaction_type: Type of interaction (viewed, clicked, dismissed, etc.)
            interaction_time: When the interaction occurred (defaults to now)
        """
        try:
            if interaction_time is None:
                interaction_time = datetime.utcnow()

            logger.info(
                f"Tracking notification {notification_id} interaction: {interaction_type}"
            )

            # Get the notification
            notification = SmartNotification.query.get(notification_id)
            if not notification:
                logger.warning(f"Notification {notification_id} not found")
                return

            # Record interaction
            interaction = NotificationInteraction(
                notification_id=notification_id,
                user_id=notification.user_id,
                interaction_type=interaction_type,
                interaction_time=interaction_time,
                context_metadata={
                    "delivery_channel": notification.notification_metadata.get(
                        "delivery_channel", "unknown"
                    )
                    if notification.notification_metadata
                    else "unknown",
                    "notification_type": notification.notification_type,
                    "time_to_interaction": (
                        interaction_time - notification.created_at
                    ).total_seconds(),
                },
            )

            db.session.add(interaction)

            # Update notification effectiveness metrics
            if interaction_type in ["viewed", "read"]:
                notification.read_time = interaction_time
            elif interaction_type in ["clicked", "action_taken"]:
                notification.action_taken = True

            # Calculate effectiveness score
            notification.effectiveness_score = self._calculate_effectiveness_score(
                notification, interaction
            )

            db.session.commit()

            logger.info(f"Tracked interaction for notification {notification_id}")

        except Exception as e:
            logger.error(f"Error tracking notification effectiveness: {str(e)}")
            db.session.rollback()

    def get_notification_analytics(
        self, user_id: int, days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Get notification analytics and effectiveness metrics.

        Args:
            user_id: The user ID
            days_back: Number of days to analyze

        Returns:
            Dictionary with notification analytics
        """
        try:
            logger.info(f"Getting notification analytics for user {user_id}")

            cutoff_date = datetime.utcnow() - timedelta(days=days_back)

            # Get notifications in timeframe
            notifications = SmartNotification.query.filter(
                SmartNotification.user_id == user_id,
                SmartNotification.created_at >= cutoff_date,
            ).all()

            if not notifications:
                return {"message": "No notifications in timeframe"}

            # Calculate basic metrics
            total_sent = len(notifications)
            total_viewed = sum(1 for n in notifications if n.read_time is not None)
            total_acted = sum(1 for n in notifications if n.action_taken)

            # Calculate rates
            view_rate = total_viewed / total_sent if total_sent > 0 else 0
            action_rate = total_acted / total_viewed if total_viewed > 0 else 0
            overall_effectiveness = total_acted / total_sent if total_sent > 0 else 0

            # Analyze by notification type
            type_analytics = self._analyze_by_notification_type(notifications)

            # Analyze by delivery channel
            channel_analytics = self._analyze_by_delivery_channel(notifications)

            # Analyze timing effectiveness
            timing_analytics = self._analyze_timing_effectiveness(notifications)

            # Get personalization impact
            personalization_impact = self._analyze_personalization_impact(notifications)

            analytics = {
                "summary": {
                    "total_notifications": total_sent,
                    "total_viewed": total_viewed,
                    "total_acted": total_acted,
                    "view_rate": view_rate,
                    "action_rate": action_rate,
                    "overall_effectiveness": overall_effectiveness,
                },
                "by_type": type_analytics,
                "by_channel": channel_analytics,
                "timing_analysis": timing_analytics,
                "personalization_impact": personalization_impact,
                "recommendations": self._generate_optimization_recommendations(
                    view_rate, action_rate, type_analytics, channel_analytics
                ),
            }

            logger.info(f"Generated notification analytics for user {user_id}")
            return analytics

        except Exception as e:
            logger.error(
                f"Error getting notification analytics for user {user_id}: {str(e)}"
            )
            return {}

    def _build_notification_context(self, user_id: int) -> NotificationContext:
        """Build comprehensive context for notification generation."""
        try:
            user = User.query.get(user_id)
            current_time = datetime.utcnow()

            # Get behavior patterns
            behavior_patterns = self._get_user_behavior_patterns(user_id)

            # Get recent activity
            recent_activity = self._get_recent_user_activity(user_id)

            # Get academic status
            academic_status = self._get_academic_status(user_id)

            # Get notification preferences
            preferences = self._get_user_notification_preferences(user_id)

            return NotificationContext(
                user_id=user_id,
                current_time=current_time,
                user_behavior_patterns=behavior_patterns,
                recent_activity=recent_activity,
                academic_status=academic_status,
                preferences=preferences,
            )

        except Exception as e:
            logger.error(
                f"Error building notification context for user {user_id}: {str(e)}"
            )
            return NotificationContext(
                user_id=user_id,
                current_time=datetime.utcnow(),
                user_behavior_patterns={},
                recent_activity=[],
                academic_status={},
                preferences={},
            )

    def _generate_assignment_notifications(
        self, context: NotificationContext
    ) -> List[Dict[str, Any]]:
        """Generate assignment-related notifications."""
        notifications = []

        try:
            # Get upcoming assignments
            upcoming_assignments = self._get_upcoming_assignments(context.user_id)

            for assignment in upcoming_assignments:
                days_until_due = (assignment.due_date - context.current_time).days

                if days_until_due <= 0:
                    # Overdue assignment
                    notifications.append(
                        {
                            "user_id": context.user_id,
                            "type": NotificationType.ASSIGNMENT_DUE.value,
                            "priority": Priority.CRITICAL.value,
                            "title": f"Overdue: {assignment.name}",
                            "message": f"Assignment '{assignment.name}' was due {abs(days_until_due)} days ago",
                            "action_url": f"/assignment/{assignment.id}",
                            "metadata": {
                                "assignment_id": assignment.id,
                                "course_id": assignment.course_id,
                                "days_overdue": abs(days_until_due),
                            },
                        }
                    )
                elif days_until_due <= 1:
                    # Due soon
                    notifications.append(
                        {
                            "user_id": context.user_id,
                            "type": NotificationType.DEADLINE_APPROACHING.value,
                            "priority": Priority.HIGH.value,
                            "title": f"Due Tomorrow: {assignment.name}",
                            "message": f"Assignment '{assignment.name}' is due tomorrow",
                            "action_url": f"/assignment/{assignment.id}",
                            "metadata": {
                                "assignment_id": assignment.id,
                                "course_id": assignment.course_id,
                                "days_until_due": days_until_due,
                            },
                        }
                    )
                elif days_until_due <= 3:
                    # Due in a few days
                    notifications.append(
                        {
                            "user_id": context.user_id,
                            "type": NotificationType.ASSIGNMENT_DUE.value,
                            "priority": Priority.MEDIUM.value,
                            "title": f"Coming Up: {assignment.name}",
                            "message": f"Assignment '{assignment.name}' is due in {days_until_due} days",
                            "action_url": f"/assignment/{assignment.id}",
                            "metadata": {
                                "assignment_id": assignment.id,
                                "course_id": assignment.course_id,
                                "days_until_due": days_until_due,
                            },
                        }
                    )

        except Exception as e:
            logger.error(f"Error generating assignment notifications: {str(e)}")

        return notifications

    def _generate_performance_notifications(
        self, context: NotificationContext
    ) -> List[Dict[str, Any]]:
        """Generate performance-related notifications."""
        notifications = []

        # Define cutoff date for recent assessments (last 30 days)
        cutoff_date = datetime.utcnow() - timedelta(days=30)

        try:
            # Check for recent risk assessments
            recent_risks = (
                RiskAssessment.query.filter(
                    RiskAssessment.user_id == context.user_id,
                    RiskAssessment.assessment_date >= cutoff_date,
                    RiskAssessment.risk_level.in_(["high", "critical"]),
                )
                .order_by(RiskAssessment.assessment_date.desc())
                .limit(5)
                .all()
            )

            for risk in recent_risks:
                if risk.risk_level in ["high", "critical"]:
                    notifications.append(
                        {
                            "user_id": context.user_id,
                            "type": NotificationType.RISK_WARNING.value,
                            "priority": Priority.HIGH.value
                            if risk.risk_level == "high"
                            else Priority.CRITICAL.value,
                            "title": f"Academic Risk Alert: {risk.risk_level.title()}",
                            "message": f"Course performance needs attention. Risk level: {risk.risk_level}",
                            "action_url": f"/course/{risk.course_id}/analytics",
                            "metadata": {
                                "course_id": risk.course_id,
                                "risk_level": risk.risk_level,
                                "risk_score": float(risk.risk_score),
                            },
                        }
                    )

        except Exception as e:
            logger.error(f"Error generating performance notifications: {str(e)}")

        return notifications

    def _generate_motivational_notifications(
        self, context: NotificationContext
    ) -> List[Dict[str, Any]]:
        """Generate motivational and encouraging notifications."""
        notifications = []

        try:
            # Check if user needs motivation based on recent performance
            academic_status = context.academic_status

            if academic_status.get("recent_trend") == "declining":
                motivational_messages = [
                    "Every expert was once a beginner. Keep pushing forward!",
                    "Your hard work will pay off. Stay focused on your goals!",
                    "Challenges are opportunities to grow. You've got this!",
                    "Progress, not perfection. Every step counts!",
                ]

                import random

                message = random.choice(motivational_messages)

                notifications.append(
                    {
                        "user_id": context.user_id,
                        "type": NotificationType.MOTIVATION_MESSAGE.value,
                        "priority": Priority.MEDIUM.value,
                        "title": "Stay Strong! 💪",
                        "message": message,
                        "action_url": "/dashboard",
                        "metadata": {
                            "motivation_type": "encouragement",
                            "trigger": "declining_performance",
                        },
                    }
                )

        except Exception as e:
            logger.error(f"Error generating motivational notifications: {str(e)}")

        return notifications

    def _generate_study_reminders(
        self, context: NotificationContext
    ) -> List[Dict[str, Any]]:
        """Generate study reminder notifications."""
        notifications = []

        try:
            # Check user's study patterns
            behavior_patterns = context.user_behavior_patterns
            timing_patterns = behavior_patterns.get("timing_patterns", {})

            # If user has established study patterns, remind them
            if "preferred_study_time" in timing_patterns:
                preferred_hour = timing_patterns["preferred_study_time"].get("hour", 19)

                # Check if it's near their preferred study time
                current_hour = context.current_time.hour

                if abs(current_hour - preferred_hour) <= 1:
                    notifications.append(
                        {
                            "user_id": context.user_id,
                            "type": NotificationType.STUDY_REMINDER.value,
                            "priority": Priority.LOW.value,
                            "title": "Study Time! 📚",
                            "message": "It's your usual study time. Ready to make progress?",
                            "action_url": "/dashboard",
                            "metadata": {
                                "reminder_type": "pattern_based",
                                "preferred_time": preferred_hour,
                            },
                        }
                    )

        except Exception as e:
            logger.error(f"Error generating study reminders: {str(e)}")

        return notifications

    def _generate_achievement_notifications(
        self, context: NotificationContext
    ) -> List[Dict[str, Any]]:
        """Generate achievement and milestone notifications."""
        notifications = []

        try:
            # Check for recent achievements
            academic_status = context.academic_status

            # Check for GPA improvements
            current_gpa = academic_status.get("current_gpa", 0)
            if current_gpa >= 3.5:
                notifications.append(
                    {
                        "user_id": context.user_id,
                        "type": NotificationType.ACHIEVEMENT.value,
                        "priority": Priority.MEDIUM.value,
                        "title": "Outstanding Performance! 🌟",
                        "message": f"Your GPA of {current_gpa:.2f} is excellent! Keep up the great work!",
                        "action_url": "/analytics",
                        "metadata": {
                            "achievement_type": "high_gpa",
                            "gpa_value": current_gpa,
                        },
                    }
                )

        except Exception as e:
            logger.error(f"Error generating achievement notifications: {str(e)}")

        return notifications

    def _filter_and_prioritize_notifications(
        self, notifications: List[Dict[str, Any]], context: NotificationContext
    ) -> List[Dict[str, Any]]:
        """Filter and prioritize notifications based on user preferences and context."""
        try:
            # Remove duplicates
            unique_notifications = []
            seen_keys = set()

            for notification in notifications:
                key = (
                    notification["type"],
                    notification.get("metadata", {}).get("assignment_id", ""),
                )
                if key not in seen_keys:
                    unique_notifications.append(notification)
                    seen_keys.add(key)

            # Sort by priority
            priority_order = {
                "urgent": 4,  # CRITICAL
                "high": 3,  # HIGH
                "medium": 2,  # MEDIUM
                "low": 1,  # LOW
            }

            unique_notifications.sort(
                key=lambda x: priority_order.get(x["priority"], 0), reverse=True
            )

            # Limit number of notifications to avoid overwhelming user
            max_notifications = context.preferences.get("max_daily_notifications", 10)
            return unique_notifications[:max_notifications]

        except Exception as e:
            logger.error(f"Error filtering and prioritizing notifications: {str(e)}")
            return notifications

    def _optimize_delivery_schedule(
        self, notification: Dict[str, Any], context: NotificationContext
    ) -> DeliverySchedule:
        """Optimize delivery schedule for a notification."""
        try:
            notification_type = NotificationType(notification["type"])
            optimal_time = self.optimize_notification_timing(
                context.user_id, notification_type
            )

            # Generate backup times
            backup_times = [
                optimal_time + timedelta(hours=2),
                optimal_time + timedelta(hours=4),
                optimal_time + timedelta(days=1),
            ]

            # Determine channel preference
            preferences = context.preferences
            preferred_channels = preferences.get(
                "preferred_channels", [DeliveryChannel.EMAIL.value]
            )
            channel_preference = [DeliveryChannel(ch) for ch in preferred_channels]

            # Determine urgency
            priority = Priority(notification["priority"])

            # Estimate engagement rate based on historical data
            expected_engagement = self._estimate_engagement_rate(
                context.user_id, notification_type
            )

            return DeliverySchedule(
                optimal_time=optimal_time,
                backup_times=backup_times,
                channel_preference=channel_preference,
                urgency_level=priority,
                expected_engagement_rate=expected_engagement,
            )

        except Exception as e:
            logger.error(f"Error optimizing delivery schedule: {str(e)}")
            return DeliverySchedule(
                optimal_time=datetime.utcnow() + timedelta(hours=1),
                backup_times=[],
                channel_preference=[DeliveryChannel.EMAIL],
                urgency_level=Priority.MEDIUM,
                expected_engagement_rate=0.5,
            )

    def _store_notifications(self, notifications: List[Dict[str, Any]]) -> None:
        """Store generated notifications in database."""
        try:
            logger.info(f"DEBUG: Storing {len(notifications)} notifications")
            for notification_data in notifications:
                # Debug: Print notification data keys
                logger.info(f"Notification data keys: {list(notification_data.keys())}")
                if "delivery_channel" in notification_data:
                    logger.error(
                        f"Found delivery_channel in notification_data: {notification_data['delivery_channel']}"
                    )

                # Debug: Check priority value before conversion
                original_priority = notification_data["priority"]
                converted_priority = self._convert_priority_to_db_value(
                    original_priority
                )
                logger.info(
                    f"Priority conversion: {original_priority} -> {converted_priority}"
                )

                # Extract user_id from notification data
                user_id = notification_data.get("user_id")

                # If user_id not found, try metadata
                if not user_id and "metadata" in notification_data:
                    user_id = notification_data["metadata"].get("user_id")

                # Skip notification if user_id is still None (required field)
                if not user_id:
                    logger.warning(
                        f"Skipping notification with missing user_id: {notification_data.get('title')}"
                    )
                    continue

                notification = SmartNotification(
                    user_id=user_id,
                    notification_type=notification_data["type"],
                    title=notification_data["title"],
                    message=notification_data["message"],
                    priority=converted_priority,
                    action_url=notification_data.get("action_url"),
                    notification_metadata=notification_data.get("metadata", {}),
                    created_at=datetime.utcnow(),
                )

                db.session.add(notification)

            db.session.commit()
            logger.info(f"Stored {len(notifications)} notifications")

        except Exception as e:
            logger.error(f"Error storing notifications: {str(e)}")
            db.session.rollback()

    def _convert_priority_to_db_value(self, priority_value):
        """Convert priority enum value to database string."""
        # Handle both enum objects and string values
        if isinstance(priority_value, Priority):
            priority_name = priority_value.name
        elif isinstance(priority_value, str):
            priority_name = priority_value.upper()
        else:
            # Handle numeric values
            priority_map = {1: "LOW", 2: "MEDIUM", 3: "HIGH", 4: "CRITICAL"}
            priority_name = priority_map.get(priority_value, "MEDIUM")

        # Convert to database enum values
        db_priority_map = {
            "LOW": "low",
            "MEDIUM": "medium",
            "HIGH": "high",
            "CRITICAL": "urgent",
        }
        return db_priority_map.get(priority_name, "medium")

    def _priority_to_db_string(self, priority_enum):
        """Convert Priority enum to database string value."""
        priority_map = {
            Priority.LOW: "low",
            Priority.MEDIUM: "medium",
            Priority.HIGH: "high",
            Priority.CRITICAL: "urgent",
        }
        result = priority_map.get(priority_enum, "medium")
        logger.info(f"Converting priority {priority_enum} -> {result}")
        return result

    def _get_user_behavior_patterns(self, user_id: int) -> Dict[str, Any]:
        """Get user behavior patterns from database."""
        try:
            pattern = (
                UserBehaviorPattern.query.filter_by(
                    user_id=user_id, pattern_type="notification_optimization"
                )
                .order_by(desc(UserBehaviorPattern.last_updated))
                .first()
            )

            if pattern:
                return pattern.pattern_data

            return {}

        except Exception as e:
            logger.error(
                f"Error getting user behavior patterns for user {user_id}: {str(e)}"
            )
            return {}

    def _get_user_notification_preferences(self, user_id: int) -> Dict[str, Any]:
        """Get user notification preferences."""
        try:
            preferences = NotificationPreference.query.filter_by(user_id=user_id).all()

            prefs_dict = {}
            for pref in preferences:
                prefs_dict[pref.notification_type] = {
                    "enabled": pref.enabled,
                    "delivery_method": pref.delivery_method,
                    "frequency": pref.frequency_limit,
                }

            return prefs_dict

        except Exception as e:
            logger.error(
                f"Error getting notification preferences for user {user_id}: {str(e)}"
            )
            return {}

    def _get_recent_user_activity(self, user_id: int) -> List[Dict[str, Any]]:
        """Get recent user activity for context."""
        try:
            # This would typically query various activity logs
            # For now, return empty list
            return []

        except Exception as e:
            logger.error(
                f"Error getting recent user activity for user {user_id}: {str(e)}"
            )
            return []

    def _get_academic_status(self, user_id: int) -> Dict[str, Any]:
        """Get current academic status for context."""
        try:
            # Get recent performance metrics
            recent_metrics = (
                PerformanceMetric.query.filter(PerformanceMetric.user_id == user_id)
                .order_by(PerformanceMetric.calculation_date.desc())
                .limit(10)
                .all()
            )

            if recent_metrics:
                gpa_metrics = [
                    m for m in recent_metrics if m.metric_type == "overall_gpa"
                ]
                current_gpa = float(gpa_metrics[0].metric_value) if gpa_metrics else 0.0

                # Determine trend
                if len(gpa_metrics) >= 2:
                    recent_gpa = float(gpa_metrics[0].metric_value)
                    previous_gpa = float(gpa_metrics[1].metric_value)

                    if recent_gpa > previous_gpa * 1.02:
                        trend = "improving"
                    elif recent_gpa < previous_gpa * 0.98:
                        trend = "declining"
                    else:
                        trend = "stable"
                else:
                    trend = "stable"

                return {
                    "current_gpa": current_gpa,
                    "recent_trend": trend,
                    "metrics_available": len(recent_metrics),
                }

            return {
                "current_gpa": 0.0,
                "recent_trend": "stable",
                "metrics_available": 0,
            }

        except Exception as e:
            logger.error(f"Error getting academic status for user {user_id}: {str(e)}")
            return {}

    def _get_upcoming_assignments(self, user_id: int) -> List[Assignment]:
        """Get upcoming assignments for the user."""
        try:
            upcoming_date = datetime.utcnow() + timedelta(days=7)

            assignments = (
                db.session.query(Assignment)
                .join(Course)
                .join(Term)
                .filter(
                    Term.user_id == user_id,
                    Assignment.due_date <= upcoming_date,
                    Assignment.score.is_(None),  # Not yet completed
                )
                .order_by(Assignment.due_date)
                .all()
            )

            return assignments

        except Exception as e:
            logger.error(
                f"Error getting upcoming assignments for user {user_id}: {str(e)}"
            )
            return []

    def _analyze_notification_interactions(self, user_id: int) -> Dict[str, Any]:
        """Analyze notification interaction patterns."""
        # Implementation would analyze historical interactions
        return {}

    def _analyze_activity_timing(self, user_id: int) -> Dict[str, Any]:
        """Analyze user activity timing patterns."""
        # Implementation would analyze when user is most active
        return {"most_active_hour": 10, "preferred_study_time": {"hour": 19}}

    def _analyze_engagement_preferences(self, user_id: int) -> Dict[str, Any]:
        """Analyze user engagement preferences."""
        # Implementation would analyze engagement patterns
        return {}

    def _analyze_content_preferences(self, user_id: int) -> Dict[str, Any]:
        """Analyze user content preferences."""
        # Implementation would analyze content preferences
        return {}

    def _calculate_pattern_confidence(self, user_id: int) -> float:
        """Calculate confidence in learned patterns."""
        # Implementation would calculate confidence based on data quality
        return 0.7

    def _store_behavior_patterns(self, user_id: int, patterns: Dict[str, Any]) -> None:
        """Store learned behavior patterns."""
        try:
            pattern = UserBehaviorPattern(
                user_id=user_id,
                pattern_type="notification_optimization",
                pattern_data=patterns,
                confidence_score=patterns.get("confidence_score", 0.5),
                last_training_date=datetime.utcnow().date(),
            )

            db.session.add(pattern)
            db.session.commit()

        except Exception as e:
            logger.error(f"Error storing behavior patterns: {str(e)}")
            db.session.rollback()

    def _get_default_notification_time(
        self, notification_type: NotificationType
    ) -> datetime:
        """Get default notification time for given type."""
        now = datetime.utcnow()

        # Default times based on notification type
        default_hours = {
            NotificationType.ASSIGNMENT_DUE: 9,
            NotificationType.GRADE_UPDATE: 14,
            NotificationType.PERFORMANCE_ALERT: 10,
            NotificationType.MOTIVATION_MESSAGE: 8,
            NotificationType.STUDY_REMINDER: 19,
            NotificationType.ACHIEVEMENT: 16,
            NotificationType.RISK_WARNING: 10,
            NotificationType.DEADLINE_APPROACHING: 9,
            NotificationType.WEEKLY_SUMMARY: 18,
        }

        default_hour = default_hours.get(notification_type, 10)

        # Calculate next occurrence
        next_time = now.replace(hour=default_hour, minute=0, second=0, microsecond=0)
        if next_time <= now:
            next_time += timedelta(days=1)

        return next_time

    def _personalize_title(
        self,
        base_title: str,
        user: User,
        content_preferences: Dict[str, Any],
        notification_type: NotificationType,
    ) -> str:
        """Personalize notification title."""
        # Add user's first name if available
        if user.first_name:
            if not any(
                name in base_title.lower()
                for name in [user.first_name.lower(), "you", "your"]
            ):
                base_title = f"{user.first_name}, {base_title}"

        return base_title

    def _personalize_message(
        self,
        base_message: str,
        user: User,
        content_preferences: Dict[str, Any],
        notification_type: NotificationType,
    ) -> str:
        """Personalize notification message."""
        # This could be enhanced with more sophisticated personalization
        return base_message

    def _determine_action(
        self, notification_type: NotificationType, base_url: str, user_id: int
    ) -> Tuple[Optional[str], Optional[str]]:
        """Determine action text and URL for notification."""
        action_mapping = {
            NotificationType.ASSIGNMENT_DUE: ("View Assignment", base_url),
            NotificationType.GRADE_UPDATE: ("Check Grade", base_url),
            NotificationType.PERFORMANCE_ALERT: ("View Analytics", base_url),
            NotificationType.MOTIVATION_MESSAGE: ("View Dashboard", "/dashboard"),
            NotificationType.STUDY_REMINDER: ("Start Studying", "/dashboard"),
            NotificationType.ACHIEVEMENT: ("View Progress", "/analytics"),
            NotificationType.RISK_WARNING: ("Get Help", base_url),
        }

        return action_mapping.get(notification_type, (None, base_url))

    def _track_personalization_factors(
        self,
        content_preferences: Dict[str, Any],
        preferences: Dict[str, Any],
        notification_type: NotificationType,
    ) -> List[str]:
        """Track factors used in personalization."""
        factors = []

        if content_preferences:
            factors.append("content_preferences")
        if preferences:
            factors.append("delivery_preferences")

        factors.append(f"notification_type_{notification_type.value}")

        return factors

    def _calculate_effectiveness_score(
        self, notification: SmartNotification, interaction: NotificationInteraction
    ) -> float:
        """Calculate effectiveness score for a notification."""
        score = 0.0

        # Base score for being viewed
        if notification.read_time:
            score += 0.3

        # Higher score for action taken
        if notification.action_taken:
            score += 0.7

        # Factor in time to interaction (faster = better)
        if interaction.interaction_time and notification.created_at:
            time_to_interaction = (
                interaction.interaction_time - notification.created_at
            ).total_seconds()
            if time_to_interaction < 3600:  # Within 1 hour
                score += 0.2
            elif time_to_interaction < 86400:  # Within 24 hours
                score += 0.1

        return min(1.0, score)

    def _analyze_by_notification_type(
        self, notifications: List[SmartNotification]
    ) -> Dict[str, Any]:
        """Analyze notifications by type."""
        type_stats = defaultdict(lambda: {"sent": 0, "viewed": 0, "acted": 0})

        for notification in notifications:
            stats = type_stats[notification.notification_type]
            stats["sent"] += 1
            if notification.read_time:
                stats["viewed"] += 1
            if notification.action_taken:
                stats["acted"] += 1

        # Calculate rates
        for type_name, stats in type_stats.items():
            stats["view_rate"] = (
                stats["viewed"] / stats["sent"] if stats["sent"] > 0 else 0
            )
            stats["action_rate"] = (
                stats["acted"] / stats["viewed"] if stats["viewed"] > 0 else 0
            )

        return dict(type_stats)

    def _analyze_by_delivery_channel(
        self, notifications: List[SmartNotification]
    ) -> Dict[str, Any]:
        """Analyze notifications by delivery channel."""
        channel_stats = defaultdict(lambda: {"sent": 0, "viewed": 0, "acted": 0})

        for notification in notifications:
            delivery_channel = (
                notification.notification_metadata.get("delivery_channel", "unknown")
                if notification.notification_metadata
                else "unknown"
            )
            stats = channel_stats[delivery_channel]
            stats["sent"] += 1
            if notification.read_time:
                stats["viewed"] += 1
            if notification.action_taken:
                stats["acted"] += 1

        # Calculate rates
        for channel, stats in channel_stats.items():
            stats["view_rate"] = (
                stats["viewed"] / stats["sent"] if stats["sent"] > 0 else 0
            )
            stats["action_rate"] = (
                stats["acted"] / stats["viewed"] if stats["viewed"] > 0 else 0
            )

        return dict(channel_stats)

    def _analyze_timing_effectiveness(
        self, notifications: List[SmartNotification]
    ) -> Dict[str, Any]:
        """Analyze timing effectiveness."""
        # Analyze effectiveness by hour of day
        hourly_stats = defaultdict(lambda: {"sent": 0, "effectiveness_sum": 0.0})

        for notification in notifications:
            hour = notification.created_at.hour
            stats = hourly_stats[hour]
            stats["sent"] += 1
            if notification.effectiveness_score:
                stats["effectiveness_sum"] += notification.effectiveness_score

        # Calculate average effectiveness by hour
        hourly_effectiveness = {}
        for hour, stats in hourly_stats.items():
            avg_effectiveness = (
                stats["effectiveness_sum"] / stats["sent"] if stats["sent"] > 0 else 0
            )
            hourly_effectiveness[hour] = {
                "average_effectiveness": avg_effectiveness,
                "notifications_sent": stats["sent"],
            }

        return {"hourly_effectiveness": hourly_effectiveness}

    def _analyze_personalization_impact(
        self, notifications: List[SmartNotification]
    ) -> Dict[str, Any]:
        """Analyze impact of personalization."""
        # This would compare personalized vs non-personalized notifications
        return {"personalization_lift": 0.15}  # Placeholder

    def _generate_optimization_recommendations(
        self,
        view_rate: float,
        action_rate: float,
        type_analytics: Dict[str, Any],
        channel_analytics: Dict[str, Any],
    ) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []

        if view_rate < 0.3:
            recommendations.append(
                "Consider adjusting notification timing to increase view rates"
            )

        if action_rate < 0.1:
            recommendations.append(
                "Focus on making notifications more actionable and relevant"
            )

        # Find best performing notification types
        best_type = max(
            type_analytics.items(),
            key=lambda x: x[1].get("action_rate", 0),
            default=(None, {}),
        )[0]
        if best_type:
            recommendations.append(
                f"Consider increasing frequency of {best_type} notifications"
            )

        return recommendations

    def _estimate_engagement_rate(
        self, user_id: int, notification_type: NotificationType
    ) -> float:
        """Estimate engagement rate based on historical data."""
        # This would analyze historical engagement rates
        return 0.4  # Placeholder
