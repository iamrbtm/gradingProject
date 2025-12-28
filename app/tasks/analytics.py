"""
Analytics Update Tasks
====================

This module contains Celery tasks for automated analytics updates including:
- Performance metric calculations
- Trend analysis updates
- Risk assessment refreshes
- Notification generation

Author: Analytics Team
Date: 2024-12-19
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

try:
    from celery import shared_task

    CELERY_AVAILABLE = True
except ImportError:

    def shared_task(func):
        return func

    CELERY_AVAILABLE = False

from ..models import (
    db,
    User,
    Term,
    Course,
    Assignment,
    PerformanceMetric,
    PerformanceTrend,
    RiskAssessment,
    GradePrediction,
)
from ..services.performance_analytics import PerformanceAnalyticsService
from ..services.predictive_analytics import PredictiveAnalyticsEngine
from ..services.smart_notifications import SmartNotificationService

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="app.tasks.analytics.update_all_analytics")
def update_all_analytics(self):
    """Update all analytics for all users."""
    try:
        logger.info("Starting comprehensive analytics update")

        # Get all users with academic data
        users = (
            User.query.join(Term).join(Course).join(Assignment).group_by(User.id).all()
        )

        results = {
            "users_processed": 0,
            "metrics_updated": 0,
            "trends_updated": 0,
            "predictions_updated": 0,
            "notifications_generated": 0,
            "errors": [],
        }

        performance_service = PerformanceAnalyticsService()
        predictive_service = PredictiveAnalyticsEngine()
        notification_service = SmartNotificationService()

        for user in users:
            try:
                logger.info(f"Updating analytics for user {user.id}")

                # Update performance metrics
                try:
                    metrics = performance_service.calculate_performance_metrics(user.id)
                    results["metrics_updated"] += len(metrics)
                except Exception as e:
                    logger.error(f"Error updating metrics for user {user.id}: {str(e)}")
                    results["errors"].append(f"User {user.id} metrics: {str(e)}")

                # Update trends
                try:
                    trends = performance_service.analyze_performance_trends(user.id)
                    results["trends_updated"] += len(trends)
                except Exception as e:
                    logger.error(f"Error updating trends for user {user.id}: {str(e)}")
                    results["errors"].append(f"User {user.id} trends: {str(e)}")

                # Update predictions for user's courses
                try:
                    predictions_count = 0
                    for term in user.terms:
                        for course in term.courses:
                            try:
                                prediction = predictive_service.predict_final_grade(
                                    course.id, user.id
                                )
                                if prediction:
                                    predictions_count += 1
                            except Exception as e:
                                logger.warning(
                                    f"Could not predict for course {course.id}: {str(e)}"
                                )

                    results["predictions_updated"] += predictions_count
                except Exception as e:
                    logger.error(
                        f"Error updating predictions for user {user.id}: {str(e)}"
                    )
                    results["errors"].append(f"User {user.id} predictions: {str(e)}")

                # Generate notifications
                try:
                    notifications = (
                        notification_service.generate_contextual_notifications(user.id)
                    )
                    results["notifications_generated"] += len(notifications)
                except Exception as e:
                    logger.error(
                        f"Error generating notifications for user {user.id}: {str(e)}"
                    )
                    results["errors"].append(f"User {user.id} notifications: {str(e)}")

                results["users_processed"] += 1

            except Exception as e:
                logger.error(f"Error processing user {user.id}: {str(e)}")
                results["errors"].append(f"User {user.id} general: {str(e)}")

        # Commit all updates
        db.session.commit()

        logger.info(
            f"Analytics update completed. Processed {results['users_processed']} users"
        )

        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            **results,
        }

    except Exception as e:
        logger.error(f"Error in comprehensive analytics update: {str(e)}")
        db.session.rollback()
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@shared_task(bind=True, name="app.tasks.analytics.update_performance_metrics")
def update_performance_metrics(self):
    """Update performance metrics for all users."""
    try:
        logger.info("Updating performance metrics")

        performance_service = PerformanceAnalyticsService()
        users = User.query.join(Term).group_by(User.id).all()

        metrics_updated = 0
        errors = []

        for user in users:
            try:
                metrics = performance_service.calculate_performance_metrics(user.id)
                metrics_updated += len(metrics)
            except Exception as e:
                logger.error(f"Error updating metrics for user {user.id}: {str(e)}")
                errors.append(f"User {user.id}: {str(e)}")

        db.session.commit()

        logger.info(
            f"Performance metrics update completed. Updated {metrics_updated} metrics"
        )

        return {
            "status": "success",
            "metrics_updated": metrics_updated,
            "users_processed": len(users),
            "errors": errors,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error updating performance metrics: {str(e)}")
        db.session.rollback()
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@shared_task(bind=True, name="app.tasks.analytics.update_user_analytics")
def update_user_analytics(self, user_id: int):
    """Update analytics for a specific user."""
    try:
        logger.info(f"Updating analytics for user {user_id}")

        user = User.query.get(user_id)
        if not user:
            return {
                "status": "error",
                "error": f"User {user_id} not found",
                "timestamp": datetime.utcnow().isoformat(),
            }

        performance_service = PerformanceAnalyticsService()
        predictive_service = PredictiveAnalyticsEngine()
        notification_service = SmartNotificationService()

        results = {
            "metrics_updated": 0,
            "trends_updated": 0,
            "predictions_updated": 0,
            "notifications_generated": 0,
        }

        # Update performance metrics
        metrics = performance_service.calculate_performance_metrics(user_id)
        results["metrics_updated"] = len(metrics)

        # Update trends
        trends = performance_service.analyze_performance_trends(user_id)
        results["trends_updated"] = len(trends)

        # Update predictions
        predictions_count = 0
        for term in user.terms:
            for course in term.courses:
                try:
                    prediction = predictive_service.predict_final_grade(
                        course.id, user_id
                    )
                    if prediction:
                        predictions_count += 1
                except Exception as e:
                    logger.warning(
                        f"Could not predict for course {course.id}: {str(e)}"
                    )

        results["predictions_updated"] = predictions_count

        # Generate notifications
        notifications = notification_service.generate_contextual_notifications(user_id)
        results["notifications_generated"] = len(notifications)

        db.session.commit()

        logger.info(f"User {user_id} analytics updated successfully")

        return {
            "status": "success",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            **results,
        }

    except Exception as e:
        logger.error(f"Error updating analytics for user {user_id}: {str(e)}")
        db.session.rollback()
        return {
            "status": "error",
            "user_id": user_id,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@shared_task(bind=True, name="app.tasks.analytics.refresh_risk_assessments")
def refresh_risk_assessments(self):
    """Refresh risk assessments for all active courses."""
    try:
        logger.info("Refreshing risk assessments")

        predictive_service = PredictiveAnalyticsEngine()

        # Get all active courses (current term)
        current_year = datetime.now().year
        current_month = datetime.now().month

        if current_month in [1, 2, 3]:
            season = "Winter"
        elif current_month in [4, 5, 6]:
            season = "Spring"
        elif current_month in [7, 8]:
            season = "Summer"
        else:
            season = "Fall"

        active_courses = (
            Course.query.join(Term)
            .filter(
                Term.year == current_year, Term.season == season, Term.active == True
            )
            .all()
        )

        assessments_updated = 0
        errors = []

        for course in active_courses:
            try:
                # Get the user for this course
                user_id = course.term.user_id

                # Generate risk assessment
                assessment = predictive_service.assess_course_risk(course.id, user_id)
                if assessment:
                    assessments_updated += 1

            except Exception as e:
                logger.error(f"Error assessing risk for course {course.id}: {str(e)}")
                errors.append(f"Course {course.id}: {str(e)}")

        db.session.commit()

        logger.info(
            f"Risk assessments refresh completed. Updated {assessments_updated} assessments"
        )

        return {
            "status": "success",
            "assessments_updated": assessments_updated,
            "courses_processed": len(active_courses),
            "errors": errors,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error refreshing risk assessments: {str(e)}")
        db.session.rollback()
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@shared_task(bind=True, name="app.tasks.analytics.cleanup_old_analytics_data")
def cleanup_old_analytics_data(self):
    """Clean up old analytics data to maintain performance."""
    try:
        logger.info("Cleaning up old analytics data")

        # Remove old performance metrics (older than 1 year)
        old_metrics_cutoff = datetime.utcnow() - timedelta(days=365)
        old_metrics = PerformanceMetric.query.filter(
            PerformanceMetric.created_at < old_metrics_cutoff
        ).all()

        metrics_removed = len(old_metrics)
        for metric in old_metrics:
            db.session.delete(metric)

        # Remove old trend data (older than 6 months)
        old_trends_cutoff = datetime.utcnow() - timedelta(days=180)
        old_trends = PerformanceTrend.query.filter(
            PerformanceTrend.created_at < old_trends_cutoff
        ).all()

        trends_removed = len(old_trends)
        for trend in old_trends:
            db.session.delete(trend)

        # Remove old predictions (older than 3 months or for completed courses)
        old_predictions_cutoff = datetime.utcnow() - timedelta(days=90)
        old_predictions = GradePrediction.query.filter(
            GradePrediction.created_at < old_predictions_cutoff
        ).all()

        predictions_removed = len(old_predictions)
        for prediction in old_predictions:
            db.session.delete(prediction)

        # Remove resolved risk assessments older than 6 months
        old_risks_cutoff = datetime.utcnow() - timedelta(days=180)
        old_risks = RiskAssessment.query.filter(
            RiskAssessment.resolved_at < old_risks_cutoff,
            RiskAssessment.resolved_at.isnot(None),
        ).all()

        risks_removed = len(old_risks)
        for risk in old_risks:
            db.session.delete(risk)

        db.session.commit()

        total_removed = (
            metrics_removed + trends_removed + predictions_removed + risks_removed
        )

        logger.info(f"Analytics cleanup completed. Removed {total_removed} records")

        return {
            "status": "success",
            "metrics_removed": metrics_removed,
            "trends_removed": trends_removed,
            "predictions_removed": predictions_removed,
            "risks_removed": risks_removed,
            "total_removed": total_removed,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error cleaning up analytics data: {str(e)}")
        db.session.rollback()
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


# Utility functions for manual testing
def update_analytics_sync():
    """Update analytics synchronously for testing."""
    return update_all_analytics()


def update_user_sync(user_id: int):
    """Update user analytics synchronously for testing."""
    return update_user_analytics(user_id)


if __name__ == "__main__":
    # Test the analytics update system
    print("Testing analytics update system...")
    result = update_analytics_sync()
    print(f"Result: {result}")
