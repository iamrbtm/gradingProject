"""
Notification Tasks for Analytics System
Handles automated notification delivery, digest emails, and alerts.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

try:
    from celery import shared_task

    CELERY_AVAILABLE = True
except ImportError:

    def shared_task(func):
        return func

    CELERY_AVAILABLE = False

# Setup logger
logger = logging.getLogger("notifications")


@shared_task(bind=True, name="app.tasks.notifications.send_analytics_report_email")
def send_analytics_report_email_task(
    self,
    user_id: int,
    report_data: Dict[str, Any],
    attachments: Optional[List[Dict[str, Any]]] = None,
):
    """Send analytics report via email."""
    try:
        from app.services.email_service import send_analytics_report_email
        from app.models import User

        # Get user information
        user = User.query.get(user_id)
        if not user or not user.email:
            logger.warning(f"User {user_id} not found or has no email address")
            return {"status": "error", "message": "User not found or no email"}

        # Send the report
        success = send_analytics_report_email(
            recipient_email=user.email,
            user_name=user.name or "User",
            report_title=report_data.get("title", "Analytics Report"),
            report_data=report_data,
            attachments=attachments,
        )

        if success:
            logger.info(f"Analytics report email sent successfully to {user.email}")
            return {"status": "success", "recipient": user.email}
        else:
            logger.error(f"Failed to send analytics report email to {user.email}")
            return {"status": "error", "message": "Email delivery failed"}

    except Exception as e:
        logger.error(f"Error in send_analytics_report_email_task: {str(e)}")
        return {"status": "error", "message": str(e)}


@shared_task(bind=True, name="app.tasks.notifications.process_pending_notifications")
def process_pending_notifications(self):
    """Process and send pending notifications."""
    try:
        from app.models import SmartNotification, User, db
        from app.services.email_service import send_notification_digest_email

        # Get pending notifications grouped by user
        pending_notifications = (
            db.session.query(SmartNotification)
            .filter(SmartNotification.delivery_status == "pending")
            .filter(SmartNotification.scheduled_delivery_time <= datetime.utcnow())
            .all()
        )

        if not pending_notifications:
            logger.info("No pending notifications to process")
            return {"status": "success", "processed": 0}

        # Group notifications by user
        user_notifications = {}
        for notification in pending_notifications:
            user_id = notification.user_id
            if user_id not in user_notifications:
                user_notifications[user_id] = []
            user_notifications[user_id].append(notification)

        processed_count = 0
        failed_count = 0

        for user_id, notifications in user_notifications.items():
            try:
                user = User.query.get(user_id)
                if not user or not user.email:
                    logger.warning(
                        f"User {user_id} not found or has no email - skipping notifications"
                    )
                    continue

                # Check user's notification preferences
                from app.models import NotificationPreference

                prefs = NotificationPreference.query.filter_by(user_id=user_id).first()

                if prefs and not prefs.email_enabled:
                    logger.info(
                        f"Email notifications disabled for user {user_id} - skipping"
                    )
                    # Mark as delivered but not sent
                    for notification in notifications:
                        notification.delivery_status = "skipped"
                        notification.delivered_at = datetime.utcnow()
                    continue

                # Prepare notification data for email
                notification_data = []
                for notification in notifications:
                    notification_data.append(
                        {
                            "title": notification.title,
                            "message": notification.content,
                            "type": notification.notification_type,
                            "created_at": notification.created_at.strftime(
                                "%Y-%m-%d %H:%M"
                            ),
                        }
                    )

                # Send digest email
                success = send_notification_digest_email(user.email, notification_data)

                if success:
                    # Mark notifications as delivered
                    for notification in notifications:
                        notification.delivery_status = "delivered"
                        notification.delivered_at = datetime.utcnow()
                    processed_count += len(notifications)
                    logger.info(
                        f"Sent {len(notifications)} notifications to {user.email}"
                    )
                else:
                    # Mark as failed
                    for notification in notifications:
                        notification.delivery_status = "failed"
                        notification.delivery_attempts = (
                            notification.delivery_attempts or 0
                        ) + 1
                    failed_count += len(notifications)
                    logger.error(f"Failed to send notifications to {user.email}")

            except Exception as e:
                logger.error(
                    f"Error processing notifications for user {user_id}: {str(e)}"
                )
                failed_count += len(notifications)

        # Commit all changes
        db.session.commit()

        result = {
            "status": "success",
            "processed": processed_count,
            "failed": failed_count,
            "total_users": len(user_notifications),
        }

        logger.info(f"Notification processing complete: {result}")
        return result

    except Exception as e:
        logger.error(f"Error in process_pending_notifications: {str(e)}")
        return {"status": "error", "message": str(e)}


@shared_task(bind=True, name="app.tasks.notifications.send_system_alert")
def send_system_alert_task(
    self,
    alert_title: str,
    alert_message: str,
    alert_details: Optional[str] = None,
    recipient_emails: Optional[List[str]] = None,
):
    """Send system alert to administrators."""
    try:
        from app.services.email_service import send_system_alert_email
        from app.models import User, db

        # If no specific recipients, send to all admins
        if not recipient_emails:
            admin_users = User.query.filter_by(is_admin=True).all()
            recipient_emails = [user.email for user in admin_users if user.email]

        if not recipient_emails:
            logger.warning("No recipient emails found for system alert")
            return {"status": "error", "message": "No recipients found"}

        # Send alert email
        success = send_system_alert_email(
            recipient_emails=recipient_emails,
            alert_title=alert_title,
            alert_message=alert_message,
            alert_details=alert_details,
        )

        if success:
            logger.info(f"System alert sent to {len(recipient_emails)} recipients")
            return {"status": "success", "recipients": len(recipient_emails)}
        else:
            logger.error("Failed to send system alert email")
            return {"status": "error", "message": "Email delivery failed"}

    except Exception as e:
        logger.error(f"Error in send_system_alert_task: {str(e)}")
        return {"status": "error", "message": str(e)}


@shared_task(bind=True, name="app.tasks.notifications.send_weekly_digest")
def send_weekly_digest_task(self, user_id: Optional[int] = None):
    """Send weekly analytics digest to users."""
    try:
        from app.models import User, db
        from app.services.performance_analytics import PerformanceAnalyticsService
        from app.services.email_service import send_analytics_report_email

        # If no user specified, send to all active users
        if user_id:
            users = [User.query.get(user_id)]
        else:
            users = User.query.filter_by(active=True).all()

        users = [user for user in users if user and user.email]

        if not users:
            logger.warning("No users found for weekly digest")
            return {"status": "error", "message": "No users found"}

        sent_count = 0
        failed_count = 0

        performance_service = PerformanceAnalyticsService()

        for user in users:
            try:
                # Check if user has opted in for weekly digests
                from app.models import NotificationPreference

                prefs = NotificationPreference.query.filter_by(user_id=user.id).first()

                if prefs and not prefs.weekly_digest:
                    logger.info(f"Weekly digest disabled for user {user.id} - skipping")
                    continue

                # Get weekly performance data
                week_ago = datetime.utcnow() - timedelta(days=7)
                performance_data = performance_service.get_performance_metrics(
                    user.id, start_date=week_ago
                )

                # Prepare report data
                report_data = {
                    "title": "Weekly Analytics Digest",
                    "description": f"Your academic performance summary for the week of {week_ago.strftime('%B %d, %Y')}",
                    "metrics": [
                        {
                            "label": "Current GPA",
                            "value": f"{performance_data.get('current_gpa', 'N/A')}",
                        },
                        {
                            "label": "Assignments Completed",
                            "value": f"{performance_data.get('completed_assignments', 0)}",
                        },
                        {
                            "label": "Study Sessions",
                            "value": f"{performance_data.get('study_sessions', 0)}",
                        },
                        {
                            "label": "Performance Trend",
                            "value": performance_data.get("trend_direction", "Stable"),
                        },
                    ],
                    "insights": performance_data.get("insights", []),
                }

                # Send email
                success = send_analytics_report_email(
                    recipient_email=user.email,
                    user_name=user.name or "User",
                    report_title="Weekly Analytics Digest",
                    report_data=report_data,
                )

                if success:
                    sent_count += 1
                    logger.info(f"Weekly digest sent to {user.email}")
                else:
                    failed_count += 1
                    logger.error(f"Failed to send weekly digest to {user.email}")

            except Exception as e:
                logger.error(f"Error sending weekly digest to user {user.id}: {str(e)}")
                failed_count += 1

        result = {
            "status": "success",
            "sent": sent_count,
            "failed": failed_count,
            "total_users": len(users),
        }

        logger.info(f"Weekly digest processing complete: {result}")
        return result

    except Exception as e:
        logger.error(f"Error in send_weekly_digest_task: {str(e)}")
        return {"status": "error", "message": str(e)}


@shared_task(bind=True, name="app.tasks.notifications.cleanup_old_notifications")
def cleanup_old_notifications_task(self, days_to_keep: int = 30):
    """Clean up old delivered notifications."""
    try:
        from app.models import SmartNotification, db

        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        # Delete old delivered notifications
        deleted_count = (
            db.session.query(SmartNotification)
            .filter(SmartNotification.delivery_status == "delivered")
            .filter(SmartNotification.delivered_at < cutoff_date)
            .delete()
        )

        db.session.commit()

        logger.info(f"Cleaned up {deleted_count} old notifications")
        return {"status": "success", "deleted": deleted_count}

    except Exception as e:
        logger.error(f"Error in cleanup_old_notifications_task: {str(e)}")
        return {"status": "error", "message": str(e)}


# Utility functions for manual task triggering
def trigger_analytics_report_email(
    user_id: int,
    report_data: Dict[str, Any],
    attachments: Optional[List[Dict[str, Any]]] = None,
):
    """Trigger analytics report email task."""
    if CELERY_AVAILABLE:
        return send_analytics_report_email_task.delay(user_id, report_data, attachments)
    else:
        return send_analytics_report_email_task(user_id, report_data, attachments)


def trigger_system_alert(
    alert_title: str,
    alert_message: str,
    alert_details: Optional[str] = None,
    recipient_emails: Optional[List[str]] = None,
):
    """Trigger system alert task."""
    if CELERY_AVAILABLE:
        return send_system_alert_task.delay(
            alert_title, alert_message, alert_details, recipient_emails
        )
    else:
        return send_system_alert_task(
            alert_title, alert_message, alert_details, recipient_emails
        )


def trigger_weekly_digest(user_id: Optional[int] = None):
    """Trigger weekly digest task."""
    if CELERY_AVAILABLE:
        return send_weekly_digest_task.delay(user_id)
    else:
        return send_weekly_digest_task(user_id)
