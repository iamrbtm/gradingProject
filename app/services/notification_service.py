from flask import current_app
from flask_mail import Message
from app.models import db, Assignment, User, Course, Term
from datetime import datetime, timedelta
from sqlalchemy import and_

class NotificationService:
    """Service for handling notifications and reminders."""

    @staticmethod
    def send_email(to, subject, body):
        """Send email using Flask-Mail."""
        try:
            msg = Message(subject, recipients=[to], body=body)
            current_app.mail.send(msg)
            current_app.logger.info(f"Email sent to {to}: {subject}")
            return True
        except Exception as e:
            current_app.logger.error(f"Failed to send email to {to}: {e}")
            return False

    @staticmethod
    def get_upcoming_assignments(user_id, days_ahead=7):
        """Get assignments due in the next X days."""
        future_date = datetime.now() + timedelta(days=days_ahead)
        assignments = Assignment.query.join(Course).join(Term).filter(
            and_(
                Term.user_id == user_id,
                Assignment.due_date >= datetime.now(),
                Assignment.due_date <= future_date,
                Assignment.score.is_(None)  # Not completed
            )
        ).order_by(Assignment.due_date).all()
        return assignments

    @staticmethod
    def get_overdue_assignments(user_id):
        """Get overdue assignments."""
        assignments = Assignment.query.join(Course).join(Term).filter(
            and_(
                Term.user_id == user_id,
                Assignment.due_date < datetime.now(),
                Assignment.score.is_(None)  # Not completed
            )
        ).order_by(Assignment.due_date).all()
        return assignments

    @staticmethod
    def send_reminders(user_id):
        """Send email reminders for upcoming assignments."""
        user = User.query.get(user_id)
        if not user:
            return False

        upcoming = NotificationService.get_upcoming_assignments(user_id)
        overdue = NotificationService.get_overdue_assignments(user_id)

        if not upcoming and not overdue:
            return True  # No reminders needed

        body = "Grade Tracker Reminders\n\n"

        if overdue:
            body += "OVERDUE ASSIGNMENTS:\n"
            for assignment in overdue:
                body += f"- {assignment.name} (Course: {assignment.course.name}) - Due: {assignment.due_date.strftime('%Y-%m-%d')}\n"
            body += "\n"

        if upcoming:
            body += "UPCOMING ASSIGNMENTS:\n"
            for assignment in upcoming:
                days = (assignment.due_date - datetime.now()).days
                body += f"- {assignment.name} (Course: {assignment.course.name}) - Due in {days} days\n"

        subject = "Grade Tracker: Assignment Reminders"
        return NotificationService.send_email(user.username, subject, body)  # Assuming username is email

    @staticmethod
    def get_dashboard_notifications(user_id):
        """Get notifications for dashboard."""
        overdue = NotificationService.get_overdue_assignments(user_id)
        upcoming = NotificationService.get_upcoming_assignments(user_id, 3)  # Next 3 days

        notifications = []
        if overdue:
            notifications.append({
                'type': 'overdue',
                'count': len(overdue),
                'message': f"You have {len(overdue)} overdue assignment(s)"
            })

        if upcoming:
            notifications.append({
                'type': 'upcoming',
                'count': len(upcoming),
                'message': f"You have {len(upcoming)} assignment(s) due soon"
            })

        return notifications