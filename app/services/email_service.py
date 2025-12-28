"""
Email Service for Analytics Reports
Provides email functionality for sending analytics reports and notifications.
"""

import os
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from flask import current_app, render_template_string
from flask_mail import Mail, Message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


logger = logging.getLogger("exports")


class EmailService:
    """Service for sending analytics emails."""

    def __init__(self, mail_instance: Optional[Mail] = None):
        self.mail = mail_instance
        self._templates = self._load_email_templates()

    def _get_mail_instance(self) -> Mail:
        """Get Flask-Mail instance."""
        if self.mail:
            return self.mail

        # Try to get from current app
        try:
            return current_app.extensions["mail"]
        except (RuntimeError, KeyError):
            raise RuntimeError(
                "Flask-Mail not initialized. Ensure Flask-Mail is configured in your app."
            )

    def _load_email_templates(self) -> Dict[str, str]:
        """Load email templates."""
        return {
            "analytics_report": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Analytics Report - {{ report_title }}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #4a90e2; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f9f9f9; }
        .metrics { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 20px 0; }
        .metric-card { background: white; padding: 15px; border-radius: 5px; border-left: 4px solid #4a90e2; }
        .metric-value { font-size: 24px; font-weight: bold; color: #4a90e2; }
        .metric-label { font-size: 14px; color: #666; }
        .footer { text-align: center; padding: 20px; font-size: 12px; color: #666; }
        .attachment-info { background: #e8f4fd; padding: 15px; border-radius: 5px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ report_title }}</h1>
            <p>Generated on {{ generated_at }}</p>
        </div>
        
        <div class="content">
            <h2>Hello {{ user_name }},</h2>
            
            <p>{{ report_description }}</p>
            
            {% if metrics %}
            <div class="metrics">
                {% for metric in metrics %}
                <div class="metric-card">
                    <div class="metric-value">{{ metric.value }}</div>
                    <div class="metric-label">{{ metric.label }}</div>
                </div>
                {% endfor %}
            </div>
            {% endif %}
            
            {% if has_attachments %}
            <div class="attachment-info">
                <h3>📎 Report Attachments</h3>
                <p>This email includes detailed analytics reports in the following formats:</p>
                <ul>
                    {% for attachment in attachments %}
                    <li><strong>{{ attachment.name }}</strong> - {{ attachment.description }}</li>
                    {% endfor %}
                </ul>
            </div>
            {% endif %}
            
            {% if insights %}
            <h3>Key Insights</h3>
            <ul>
                {% for insight in insights %}
                <li>{{ insight }}</li>
                {% endfor %}
            </ul>
            {% endif %}
            
            <p>Thank you for using our analytics platform!</p>
        </div>
        
        <div class="footer">
            <p>This is an automated email from the Grade Tracking Analytics System.</p>
            <p>If you have questions, please contact your system administrator.</p>
        </div>
    </div>
</body>
</html>
            """,
            "notification_digest": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Analytics Notifications</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #28a745; color: white; padding: 15px; text-align: center; }
        .notification { background: white; border-left: 4px solid #28a745; padding: 15px; margin: 10px 0; }
        .notification.warning { border-left-color: #ffc107; }
        .notification.error { border-left-color: #dc3545; }
        .notification-title { font-weight: bold; margin-bottom: 5px; }
        .notification-time { font-size: 12px; color: #666; }
        .footer { text-align: center; padding: 15px; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Analytics Notifications</h1>
            <p>{{ notification_count }} new notifications</p>
        </div>
        
        {% for notification in notifications %}
        <div class="notification {{ notification.type }}">
            <div class="notification-title">{{ notification.title }}</div>
            <div>{{ notification.message }}</div>
            <div class="notification-time">{{ notification.created_at }}</div>
        </div>
        {% endfor %}
        
        <div class="footer">
            <p>Grade Tracking Analytics System</p>
        </div>
    </div>
</body>
</html>
            """,
            "system_alert": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>System Alert - {{ alert_title }}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #dc3545; color: white; padding: 15px; text-align: center; }
        .alert-content { background: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px; margin: 15px 0; }
        .footer { text-align: center; padding: 15px; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 {{ alert_title }}</h1>
        </div>
        
        <div class="alert-content">
            <p><strong>Alert:</strong> {{ alert_message }}</p>
            <p><strong>Time:</strong> {{ alert_time }}</p>
            {% if alert_details %}
            <p><strong>Details:</strong> {{ alert_details }}</p>
            {% endif %}
        </div>
        
        <p>Please review the system status and take appropriate action if necessary.</p>
        
        <div class="footer">
            <p>Automated System Alert - Grade Tracking Analytics</p>
        </div>
    </div>
</body>
</html>
            """,
        }

    def send_analytics_report(
        self,
        recipient_email: str,
        user_name: str,
        report_title: str,
        report_data: Dict[str, Any],
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """Send analytics report email with optional attachments."""
        try:
            mail = self._get_mail_instance()

            # Prepare email data
            email_data = {
                "user_name": user_name,
                "report_title": report_title,
                "generated_at": datetime.now().strftime("%B %d, %Y at %I:%M %p"),
                "report_description": report_data.get(
                    "description", "Your analytics report is ready."
                ),
                "metrics": report_data.get("metrics", []),
                "insights": report_data.get("insights", []),
                "has_attachments": bool(attachments),
                "attachments": attachments or [],
            }

            # Render HTML content
            html_content = render_template_string(
                self._templates["analytics_report"], **email_data
            )

            # Create message
            msg = Message(
                subject=f"Analytics Report: {report_title}",
                sender=current_app.config.get("MAIL_USERNAME"),
                recipients=[recipient_email],
            )
            msg.html = html_content

            # Add text alternative
            msg.body = f"""
Analytics Report: {report_title}

Hello {user_name},

{email_data["report_description"]}

Generated on: {email_data["generated_at"]}

{"Attachments included in this email." if attachments else ""}

Thank you for using our analytics platform!
            """.strip()

            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    if os.path.exists(attachment["path"]):
                        with current_app.open_resource(attachment["path"], "rb") as f:
                            msg.attach(
                                attachment["filename"],
                                attachment.get(
                                    "content_type", "application/octet-stream"
                                ),
                                f.read(),
                            )

            # Send email
            mail.send(msg)

            logger.info(f"Analytics report email sent to {recipient_email}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to send analytics report email to {recipient_email}: {str(e)}"
            )
            return False

    def send_notification_digest(
        self, recipient_email: str, notifications: List[Dict[str, Any]]
    ) -> bool:
        """Send notification digest email."""
        try:
            mail = self._get_mail_instance()

            # Prepare email data
            email_data = {
                "notification_count": len(notifications),
                "notifications": notifications,
            }

            # Render HTML content
            html_content = render_template_string(
                self._templates["notification_digest"], **email_data
            )

            # Create message
            msg = Message(
                subject=f"Analytics Notifications ({len(notifications)} new)",
                sender=current_app.config.get("MAIL_USERNAME"),
                recipients=[recipient_email],
            )
            msg.html = html_content

            # Add text alternative
            msg.body = f"""
Analytics Notifications

You have {len(notifications)} new notifications:

""" + "\\n".join([f"• {n['title']}: {n['message']}" for n in notifications])

            # Send email
            mail.send(msg)

            logger.info(f"Notification digest email sent to {recipient_email}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to send notification digest to {recipient_email}: {str(e)}"
            )
            return False

    def send_system_alert(
        self,
        recipient_emails: List[str],
        alert_title: str,
        alert_message: str,
        alert_details: Optional[str] = None,
    ) -> bool:
        """Send system alert email to administrators."""
        try:
            mail = self._get_mail_instance()

            # Prepare email data
            email_data = {
                "alert_title": alert_title,
                "alert_message": alert_message,
                "alert_time": datetime.now().strftime("%B %d, %Y at %I:%M %p"),
                "alert_details": alert_details,
            }

            # Render HTML content
            html_content = render_template_string(
                self._templates["system_alert"], **email_data
            )

            # Create message
            msg = Message(
                subject=f"🚨 System Alert: {alert_title}",
                sender=current_app.config.get("MAIL_USERNAME"),
                recipients=recipient_emails,
            )
            msg.html = html_content

            # Add text alternative
            msg.body = f"""
SYSTEM ALERT: {alert_title}

{alert_message}

Time: {email_data["alert_time"]}
{f"Details: {alert_details}" if alert_details else ""}

Please review the system status and take appropriate action.
            """.strip()

            # Send email
            mail.send(msg)

            logger.info(
                f"System alert email sent to {len(recipient_emails)} recipients"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send system alert email: {str(e)}")
            return False

    def send_export_notification(
        self,
        recipient_email: str,
        user_name: str,
        export_type: str,
        file_path: str,
        download_url: Optional[str] = None,
    ) -> bool:
        """Send export completion notification."""
        try:
            mail = self._get_mail_instance()

            # Determine if we should attach the file or provide a download link
            attach_file = os.path.getsize(file_path) < 10 * 1024 * 1024  # 10MB limit

            subject = f"Export Complete: {export_type}"

            if attach_file:
                html_content = f"""
<h2>Export Complete</h2>
<p>Hello {user_name},</p>
<p>Your {export_type} export has been completed and is attached to this email.</p>
<p>Generated on: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
<p>Thank you!</p>
                """
            else:
                html_content = f"""
<h2>Export Complete</h2>
<p>Hello {user_name},</p>
<p>Your {export_type} export has been completed.</p>
<p>The file is too large to attach. {"Please use this download link: " + download_url if download_url else "Please contact support for file access."}</p>
<p>Generated on: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
<p>Thank you!</p>
                """

            # Create message
            msg = Message(
                subject=subject,
                sender=current_app.config.get("MAIL_USERNAME"),
                recipients=[recipient_email],
            )
            msg.html = html_content
            msg.body = f"Your {export_type} export is ready. {'File attached.' if attach_file else 'Download link: ' + (download_url or 'Contact support.')}"

            # Attach file if small enough
            if attach_file and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    filename = os.path.basename(file_path)
                    content_type = self._get_content_type(filename)
                    msg.attach(filename, content_type, f.read())

            # Send email
            mail.send(msg)

            logger.info(f"Export notification email sent to {recipient_email}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to send export notification to {recipient_email}: {str(e)}"
            )
            return False

    def _get_content_type(self, filename: str) -> str:
        """Get content type based on file extension."""
        ext = filename.lower().split(".")[-1]
        content_types = {
            "pdf": "application/pdf",
            "csv": "text/csv",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "json": "application/json",
            "zip": "application/zip",
        }
        return content_types.get(ext, "application/octet-stream")


# Utility functions for easy access
def send_analytics_report_email(
    recipient_email: str,
    user_name: str,
    report_title: str,
    report_data: Dict[str, Any],
    attachments: Optional[List[Dict[str, Any]]] = None,
) -> bool:
    """Send analytics report email - utility function."""
    email_service = EmailService()
    return email_service.send_analytics_report(
        recipient_email, user_name, report_title, report_data, attachments
    )


def send_notification_digest_email(
    recipient_email: str, notifications: List[Dict[str, Any]]
) -> bool:
    """Send notification digest email - utility function."""
    email_service = EmailService()
    return email_service.send_notification_digest(recipient_email, notifications)


def send_system_alert_email(
    recipient_emails: List[str],
    alert_title: str,
    alert_message: str,
    alert_details: Optional[str] = None,
) -> bool:
    """Send system alert email - utility function."""
    email_service = EmailService()
    return email_service.send_system_alert(
        recipient_emails, alert_title, alert_message, alert_details
    )


def send_export_notification_email(
    recipient_email: str,
    user_name: str,
    export_type: str,
    file_path: str,
    download_url: Optional[str] = None,
) -> bool:
    """Send export notification email - utility function."""
    email_service = EmailService()
    return email_service.send_export_notification(
        recipient_email, user_name, export_type, file_path, download_url
    )
