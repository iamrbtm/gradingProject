"""
Analytics API Routes
===================

This module provides RESTful API endpoints for all analytics features including
predictive analytics, performance metrics, and smart notifications.

Routes:
- /analytics/predictions/<int:course_id> - Grade predictions
- /analytics/risk/<int:course_id> - Risk assessments
- /analytics/scenarios/<int:course_id> - Scenario analysis
- /analytics/performance - Performance metrics
- /analytics/trends - Performance trends
- /analytics/insights - Performance insights
- /analytics/notifications - Smart notifications
- /analytics/dashboard - Analytics dashboard data

Author: Analytics Team
Date: 2024-12-19
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

from app.models import db, Course, Term, User
from app.services.predictive_analytics import PredictiveAnalyticsEngine
from app.services.performance_analytics import PerformanceAnalyticsService
from app.services.smart_notifications import SmartNotificationService

logger = logging.getLogger(__name__)

# Create blueprint
analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")

# Initialize services
predictive_engine = PredictiveAnalyticsEngine()
performance_service = PerformanceAnalyticsService()
notification_service = SmartNotificationService()


@analytics_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for analytics services."""
    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "predictive_analytics": True,
                "performance_analytics": True,
                "smart_notifications": True,
            },
        }
    )


@analytics_bp.route("/predictions/<int:course_id>", methods=["GET"])
@login_required
def get_grade_prediction(course_id: int):
    """
    Get grade prediction for a specific course.

    Returns predictive analysis including confidence intervals and contributing factors.

    Query Parameters:
    - use_advanced_ml: Whether to use advanced ML models (default: true)
    """
    try:
        logger.info(
            f"Getting grade prediction for course {course_id}, user {current_user.id}"
        )

        # Parse query parameters
        use_advanced_ml = (
            request.args.get("use_advanced_ml", default="true").lower() == "true"
        )

        # Validate course ownership
        course = (
            Course.query.join(Term)
            .filter(Course.id == course_id, Term.user_id == current_user.id)
            .first()
        )

        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Generate prediction with optional advanced ML
        prediction = predictive_engine.predict_final_grade(
            course_id, current_user.id, use_advanced_ml
        )

        if prediction is None:
            return jsonify(
                {
                    "error": "Insufficient data for prediction",
                    "message": "Need more assignments completed to generate reliable prediction",
                }
            ), 400

        # Format response
        response = {
            "course_id": course_id,
            "course_name": course.name,
            "prediction": {
                "predicted_grade": prediction.predicted_grade,
                "confidence": prediction.confidence,
                "grade_range": {
                    "min": prediction.grade_range[0],
                    "max": prediction.grade_range[1],
                },
                "contributing_factors": prediction.contributing_factors,
                "model_version": prediction.model_version,
                "prediction_date": prediction.prediction_date.isoformat(),
            },
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "api_version": "2.0",
                "advanced_ml_used": "advanced" in prediction.model_version,
            },
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error getting grade prediction for course {course_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/risk/<int:course_id>", methods=["GET"])
@login_required
def get_risk_assessment(course_id: int):
    """
    Get risk assessment for a specific course.

    Returns risk level, score, factors, and intervention recommendations.
    """
    try:
        logger.info(
            f"Getting risk assessment for course {course_id}, user {current_user.id}"
        )

        # Validate course ownership
        course = (
            Course.query.join(Term)
            .filter(Course.id == course_id, Term.user_id == current_user.id)
            .first()
        )

        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Generate risk assessment
        risk_assessment = predictive_engine.assess_course_risk(
            course_id, current_user.id
        )

        if risk_assessment is None:
            return jsonify(
                {
                    "error": "Unable to assess risk",
                    "message": "Insufficient data for risk assessment",
                }
            ), 400

        # Format response
        response = {
            "course_id": course_id,
            "course_name": course.name,
            "risk_assessment": {
                "risk_level": risk_assessment.risk_level,
                "risk_score": risk_assessment.risk_score,
                "risk_factors": risk_assessment.risk_factors,
                "recommendations": risk_assessment.recommendations,
                "intervention_priority": risk_assessment.intervention_priority,
            },
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "api_version": "1.0",
            },
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error getting risk assessment for course {course_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/scenarios/<int:course_id>", methods=["GET"])
@login_required
def get_scenario_analysis(course_id: int):
    """
    Get scenario analysis for remaining assignments in a course.

    Returns what-if scenarios for different performance levels.
    """
    try:
        logger.info(
            f"Getting scenario analysis for course {course_id}, user {current_user.id}"
        )

        # Validate course ownership
        course = (
            Course.query.join(Term)
            .filter(Course.id == course_id, Term.user_id == current_user.id)
            .first()
        )

        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Generate scenario analysis
        scenarios = predictive_engine.generate_scenario_analysis(
            course_id, current_user.id
        )

        if not scenarios:
            return jsonify(
                {
                    "error": "Unable to generate scenarios",
                    "message": "No data available for scenario analysis",
                }
            ), 400

        # Format response
        response = {
            "course_id": course_id,
            "course_name": course.name,
            "scenarios": scenarios,
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "api_version": "1.0",
            },
        }

        return jsonify(response)

    except Exception as e:
        logger.error(
            f"Error getting scenario analysis for course {course_id}: {str(e)}"
        )
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/performance", methods=["GET"])
@login_required
def get_performance_metrics():
    """
    Get performance metrics for the current user.

    Query Parameters:
    - term_id: Optional specific term ID
    - metrics: Comma-separated list of specific metrics to calculate
    """
    try:
        logger.info(f"Getting performance metrics for user {current_user.id}")

        # Parse query parameters
        term_id = request.args.get("term_id", type=int)
        metrics_param = request.args.get("metrics", "")

        # Parse requested metrics
        if metrics_param:
            requested_metrics = [m.strip() for m in metrics_param.split(",")]
        else:
            requested_metrics = None

        # Get performance snapshot
        snapshot = performance_service.get_performance_snapshot(
            current_user.id, term_id
        )

        # Calculate specific metrics
        metrics = performance_service.calculate_performance_metrics(
            current_user.id, requested_metrics
        )

        # Format response
        response = {
            "user_id": current_user.id,
            "performance_snapshot": {
                "overall_gpa": snapshot.overall_gpa,
                "term_gpa": snapshot.term_gpa,
                "course_grades": snapshot.course_grades,
                "completion_rates": snapshot.completion_rates,
                "trend_direction": snapshot.trend_direction,
                "risk_courses": snapshot.risk_courses,
                "strength_areas": snapshot.strength_areas,
                "improvement_areas": snapshot.improvement_areas,
                "last_updated": snapshot.last_updated.isoformat(),
            },
            "metrics": metrics,
            "metadata": {
                "term_id": term_id,
                "generated_at": datetime.utcnow().isoformat(),
                "api_version": "1.0",
            },
        }

        return jsonify(response)

    except Exception as e:
        logger.error(
            f"Error getting performance metrics for user {current_user.id}: {str(e)}"
        )
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/trends", methods=["GET"])
@login_required
def get_performance_trends():
    """
    Get performance trend analysis for the current user.

    Query Parameters:
    - lookback_days: Number of days to look back (default: 90)
    """
    try:
        logger.info(f"Getting performance trends for user {current_user.id}")

        # Parse query parameters
        lookback_days = request.args.get("lookback_days", default=90, type=int)

        # Validate lookback_days
        if lookback_days < 1 or lookback_days > 365:
            return jsonify({"error": "lookback_days must be between 1 and 365"}), 400

        # Get trend analysis
        trends = performance_service.analyze_performance_trends(
            current_user.id, lookback_days
        )

        # Format trends for JSON serialization
        formatted_trends = {}
        for metric_name, trend_analysis in trends.items():
            formatted_trends[metric_name] = {
                "metric_name": trend_analysis.metric_name,
                "trend_direction": trend_analysis.trend_direction,
                "trend_strength": trend_analysis.trend_strength,
                "data_points": [
                    {"date": point[0].isoformat(), "value": point[1]}
                    for point in trend_analysis.data_points
                ],
                "statistical_significance": trend_analysis.statistical_significance,
                "forecast_next_period": trend_analysis.forecast_next_period,
                "confidence_interval": trend_analysis.confidence_interval,
            }

        # Format response
        response = {
            "user_id": current_user.id,
            "trends": formatted_trends,
            "analysis_period": {
                "lookback_days": lookback_days,
                "start_date": (
                    datetime.utcnow() - timedelta(days=lookback_days)
                ).isoformat(),
                "end_date": datetime.utcnow().isoformat(),
            },
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "api_version": "1.0",
            },
        }

        return jsonify(response)

    except Exception as e:
        logger.error(
            f"Error getting performance trends for user {current_user.id}: {str(e)}"
        )
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/insights", methods=["GET"])
@login_required
def get_performance_insights():
    """
    Get comprehensive performance insights and recommendations.

    Returns actionable insights, recommendations, and alerts.
    """
    try:
        logger.info(f"Getting performance insights for user {current_user.id}")

        # Get comprehensive insights
        insights = performance_service.get_performance_insights(current_user.id)

        if not insights:
            return jsonify(
                {
                    "error": "Unable to generate insights",
                    "message": "Insufficient data for insight generation",
                }
            ), 400

        # Format response
        response = {
            "user_id": current_user.id,
            "insights": insights,
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "api_version": "1.0",
            },
        }

        return jsonify(response)

    except Exception as e:
        logger.error(
            f"Error getting performance insights for user {current_user.id}: {str(e)}"
        )
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/comparative", methods=["GET"])
@login_required
def get_comparative_analysis():
    """
    Get comparative performance analysis.

    Query Parameters:
    - comparison_group: Type of comparison (term_cohort, course_peers, historical_self)
    """
    try:
        logger.info(f"Getting comparative analysis for user {current_user.id}")

        # Parse query parameters
        comparison_group = request.args.get("comparison_group", default="term_cohort")

        # Validate comparison group
        valid_groups = ["term_cohort", "course_peers", "historical_self"]
        if comparison_group not in valid_groups:
            return jsonify(
                {"error": f"Invalid comparison_group. Must be one of: {valid_groups}"}
            ), 400

        # Get comparative analysis
        analysis = performance_service.generate_comparative_analysis(
            current_user.id, comparison_group
        )

        # Format response
        response = {
            "user_id": current_user.id,
            "comparative_analysis": {
                "user_performance": analysis.user_performance,
                "cohort_average": analysis.cohort_average,
                "percentile_rank": analysis.percentile_rank,
                "performance_gap": analysis.performance_gap,
                "areas_of_excellence": analysis.areas_of_excellence,
                "areas_for_improvement": analysis.areas_for_improvement,
                "recommended_actions": analysis.recommended_actions,
            },
            "comparison_group": comparison_group,
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "api_version": "1.0",
            },
        }

        return jsonify(response)

    except Exception as e:
        logger.error(
            f"Error getting comparative analysis for user {current_user.id}: {str(e)}"
        )
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/notifications", methods=["GET"])
@login_required
def get_smart_notifications():
    """
    Get smart notifications for the current user.

    Returns contextually generated notifications with delivery optimization.
    """
    try:
        logger.info(f"Getting smart notifications for user {current_user.id}")

        # Generate contextual notifications
        notifications = notification_service.generate_contextual_notifications(
            current_user.id
        )

        # Format notifications for response
        formatted_notifications = []
        for notification in notifications:
            formatted_notification = {
                "type": notification["type"],
                "priority": notification["priority"],
                "title": notification["title"],
                "message": notification["message"],
                "action_url": notification.get("action_url"),
                "metadata": notification.get("metadata", {}),
                "delivery_schedule": None,  # Simplified for now - can be enhanced later
            }
            formatted_notifications.append(formatted_notification)

        # Format response
        response = {
            "user_id": current_user.id,
            "notifications": formatted_notifications,
            "notification_count": len(formatted_notifications),
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "api_version": "1.0",
            },
        }

        return jsonify(response)

    except Exception as e:
        logger.error(
            f"Error getting smart notifications for user {current_user.id}: {str(e)}"
        )
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/notifications/<int:notification_id>/track", methods=["POST"])
@login_required
def track_notification_interaction(notification_id: int):
    """
    Track notification interaction for effectiveness analysis.

    Request Body:
    {
        "interaction_type": "viewed|clicked|dismissed",
        "interaction_time": "ISO timestamp (optional)"
    }
    """
    try:
        logger.info(
            f"Tracking notification {notification_id} interaction for user {current_user.id}"
        )

        # Parse request data
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400

        interaction_type = data.get("interaction_type")
        if not interaction_type:
            return jsonify({"error": "interaction_type is required"}), 400

        # Validate interaction type
        valid_types = ["viewed", "clicked", "dismissed", "read", "action_taken"]
        if interaction_type not in valid_types:
            return jsonify(
                {"error": f"Invalid interaction_type. Must be one of: {valid_types}"}
            ), 400

        # Parse interaction time
        interaction_time = None
        if "interaction_time" in data:
            try:
                interaction_time = datetime.fromisoformat(
                    data["interaction_time"].replace("Z", "+00:00")
                )
            except ValueError:
                return jsonify({"error": "Invalid interaction_time format"}), 400

        # Track the interaction
        notification_service.track_notification_effectiveness(
            notification_id, interaction_type, interaction_time
        )

        # Format response
        response = {
            "notification_id": notification_id,
            "interaction_tracked": True,
            "interaction_type": interaction_type,
            "metadata": {
                "tracked_at": datetime.utcnow().isoformat(),
                "api_version": "1.0",
            },
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error tracking notification interaction: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/notifications/analytics", methods=["GET"])
@login_required
def get_notification_analytics():
    """
    Get notification analytics and effectiveness metrics.

    Query Parameters:
    - days_back: Number of days to analyze (default: 30)
    """
    try:
        logger.info(f"Getting notification analytics for user {current_user.id}")

        # Parse query parameters
        days_back = request.args.get("days_back", default=30, type=int)

        # Validate days_back
        if days_back < 1 or days_back > 365:
            return jsonify({"error": "days_back must be between 1 and 365"}), 400

        # Get notification analytics
        analytics = notification_service.get_notification_analytics(
            current_user.id, days_back
        )

        # Format response
        response = {
            "user_id": current_user.id,
            "analytics": analytics,
            "analysis_period": {
                "days_back": days_back,
                "start_date": (
                    datetime.utcnow() - timedelta(days=days_back)
                ).isoformat(),
                "end_date": datetime.utcnow().isoformat(),
            },
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "api_version": "1.0",
            },
        }

        return jsonify(response)

    except Exception as e:
        logger.error(
            f"Error getting notification analytics for user {current_user.id}: {str(e)}"
        )
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/dashboard", methods=["GET"])
@login_required
def get_analytics_dashboard_data():
    """
    Get comprehensive analytics data for the dashboard.

    Returns all key analytics in a single endpoint for dashboard display.
    """
    try:
        logger.info(f"Getting analytics dashboard data for user {current_user.id}")

        # Get performance snapshot
        performance_snapshot = performance_service.get_performance_snapshot(
            current_user.id
        )

        # Get recent insights
        insights = performance_service.get_performance_insights(current_user.id)

        # Get recent trends (last 30 days)
        trends = performance_service.analyze_performance_trends(current_user.id, 30)

        # Get recent notifications
        notifications = notification_service.generate_contextual_notifications(
            current_user.id
        )

        # Get courses for predictions
        user_courses = (
            Course.query.join(Term).filter(Term.user_id == current_user.id).all()
        )

        course_predictions = []
        for course in user_courses[-5:]:  # Last 5 courses
            try:
                prediction = predictive_engine.predict_final_grade(
                    course.id, current_user.id
                )
                risk_assessment = predictive_engine.assess_course_risk(
                    course.id, current_user.id
                )

                course_data = {
                    "course_id": course.id,
                    "course_name": course.name,
                    "prediction": {
                        "predicted_grade": prediction.predicted_grade
                        if prediction
                        else None,
                        "confidence": prediction.confidence if prediction else None,
                        "grade_range": prediction.grade_range if prediction else None,
                    }
                    if prediction
                    else None,
                    "risk_assessment": {
                        "risk_level": risk_assessment.risk_level
                        if risk_assessment
                        else None,
                        "risk_score": risk_assessment.risk_score
                        if risk_assessment
                        else None,
                    }
                    if risk_assessment
                    else None,
                }
                course_predictions.append(course_data)

            except Exception as course_error:
                logger.warning(
                    f"Error getting analytics for course {course.id}: {str(course_error)}"
                )
                continue

        # Format dashboard response
        response = {
            "user_id": current_user.id,
            "dashboard_data": {
                "performance_summary": {
                    "overall_gpa": performance_snapshot.overall_gpa,
                    "term_gpa": performance_snapshot.term_gpa,
                    "trend_direction": performance_snapshot.trend_direction,
                    "courses_at_risk": len(performance_snapshot.risk_courses),
                },
                "key_insights": insights.get("key_trends", [])[:3],  # Top 3 insights
                "alerts": insights.get("alerts", []),
                "recent_trends": {
                    name: {
                        "direction": trend.trend_direction,
                        "strength": trend.trend_strength,
                    }
                    for name, trend in list(trends.items())[:3]  # Top 3 trends
                },
                "course_predictions": course_predictions,
                "notifications_count": len(notifications),
                "high_priority_notifications": len(
                    [
                        n
                        for n in notifications
                        if n.get("priority") in ["high", "critical"]
                    ]
                ),
            },
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "api_version": "1.0",
            },
        }

        return jsonify(response)

    except Exception as e:
        logger.error(
            f"Error getting analytics dashboard data for user {current_user.id}: {str(e)}"
        )
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/learn-behavior", methods=["POST"])
@login_required
def learn_user_behavior():
    """
    Trigger machine learning analysis of user behavior patterns.

    This endpoint initiates learning of user behavior patterns for notification optimization.
    """
    try:
        logger.info(f"Learning user behavior patterns for user {current_user.id}")

        # Learn behavior patterns
        patterns = notification_service.learn_user_behavior_patterns(current_user.id)

        # Format response
        response = {
            "user_id": current_user.id,
            "learning_completed": True,
            "patterns_learned": len(patterns.get("interaction_patterns", {})),
            "confidence_score": patterns.get("confidence_score", 0),
            "last_updated": patterns.get("last_updated"),
            "metadata": {
                "completed_at": datetime.utcnow().isoformat(),
                "api_version": "1.0",
            },
        }

        return jsonify(response)

    except Exception as e:
        logger.error(
            f"Error learning user behavior for user {current_user.id}: {str(e)}"
        )
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_notification_read(notification_id: int):
    """Mark a specific notification as read."""
    try:
        logger.info(
            f"Marking notification {notification_id} as read for user {current_user.id}"
        )

        # Track the read interaction
        notification_service.track_notification_effectiveness(
            notification_id, "read", datetime.utcnow()
        )

        return jsonify(
            {
                "notification_id": notification_id,
                "status": "read",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Error marking notification {notification_id} as read: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/notifications/mark-all-read", methods=["POST"])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read for the current user."""
    try:
        logger.info(f"Marking all notifications as read for user {current_user.id}")

        # For now, this just returns success
        # In a real implementation, you'd update all user notifications

        return jsonify(
            {
                "user_id": current_user.id,
                "status": "all_read",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Error marking all notifications as read: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/notifications/clear-all", methods=["POST"])
@login_required
def clear_all_notifications():
    """Clear all notifications for the current user."""
    try:
        logger.info(f"Clearing all notifications for user {current_user.id}")

        # For now, this just returns success
        # In a real implementation, you'd delete all user notifications

        return jsonify(
            {
                "user_id": current_user.id,
                "status": "all_cleared",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Error clearing all notifications: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/notifications/activity", methods=["GET"])
@login_required
def get_notification_activity():
    """Get recent notification activity for the current user."""
    try:
        logger.info(f"Getting notification activity for user {current_user.id}")

        # Generate sample activity data
        activity = [
            {
                "type": "grade_update",
                "description": "New grade recorded for Math 101",
                "timestamp": (datetime.utcnow() - timedelta(minutes=15)).isoformat(),
            },
            {
                "type": "prediction",
                "description": "Grade prediction updated for Chemistry",
                "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            },
            {
                "type": "sync",
                "description": "Canvas assignments synchronized",
                "timestamp": (datetime.utcnow() - timedelta(hours=6)).isoformat(),
            },
        ]

        return jsonify({"status": "success", "activities": activity})

    except Exception as e:
        logger.error(f"Error getting notification activity: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/performance-distribution", methods=["GET"])
@login_required
def get_performance_distribution():
    """Get performance grade distribution for charts."""
    try:
        logger.info(f"Getting performance distribution for user {current_user.id}")

        # Generate sample distribution data
        distribution = {"A": 8, "B": 12, "C": 5, "D": 2, "F": 1}

        return jsonify({"status": "success", "distribution": distribution})

    except Exception as e:
        logger.error(f"Error getting performance distribution: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/export", methods=["POST"])
@login_required
def export_analytics_report():
    """Export analytics report in specified format."""
    try:
        logger.info(f"Exporting analytics report for user {current_user.id}")

        data = request.get_json()
        format_type = data.get("format", "pdf") if data else "pdf"

        # For now, simulate successful export initiation
        return jsonify(
            {
                "status": "success",
                "message": f"Export initiated in {format_type} format",
                "export_id": f"export_{current_user.id}_{int(datetime.utcnow().timestamp())}",
            }
        )

    except Exception as e:
        logger.error(f"Error exporting analytics report: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/predictions", methods=["GET"])
@login_required
def get_all_predictions():
    """Get predictions for all user courses."""
    try:
        logger.info(f"Getting all predictions for user {current_user.id}")

        # Get user courses and generate predictions
        user_courses = (
            Course.query.join(Term).filter(Term.user_id == current_user.id).all()
        )

        predictions = []
        for course in user_courses:
            try:
                prediction = predictive_engine.predict_final_grade(
                    course.id, current_user.id
                )

                if prediction:
                    predictions.append(
                        {
                            "course_id": course.id,
                            "course_name": course.name,
                            "predicted_grade": prediction.predicted_grade,
                            "confidence": prediction.confidence,
                        }
                    )
            except Exception as e:
                logger.warning(
                    f"Could not generate prediction for course {course.id}: {str(e)}"
                )
                continue

        return jsonify({"status": "success", "predictions": predictions})

    except Exception as e:
        logger.error(f"Error getting predictions: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


# Advanced ML API Endpoints


@analytics_bp.route("/forecasting/<int:course_id>", methods=["GET"])
@login_required
def get_time_series_forecast(course_id: int):
    """
    Get time series forecast for student performance trajectory

    Query Parameters:
    - periods: Number of periods to forecast (default: 4)
    """
    try:
        logger.info(
            f"Getting time series forecast for course {course_id}, user {current_user.id}"
        )

        # Parse query parameters
        periods = request.args.get("periods", default=4, type=int)

        if periods < 1 or periods > 12:
            return jsonify({"error": "periods must be between 1 and 12"}), 400

        # Validate course ownership
        course = (
            Course.query.join(Term)
            .filter(Course.id == course_id, Term.user_id == current_user.id)
            .first()
        )

        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Generate forecast
        forecast = predictive_engine.generate_time_series_forecast(
            course_id, current_user.id, periods
        )

        if not forecast:
            return jsonify(
                {
                    "error": "Unable to generate forecast",
                    "message": "Insufficient historical data for time series analysis",
                }
            ), 400

        # Format response
        response = {
            "course_id": course_id,
            "course_name": course.name,
            "forecast": forecast,
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "api_version": "2.0",
                "forecast_periods": periods,
            },
        }

        return jsonify(response)

    except Exception as e:
        logger.error(
            f"Error getting time series forecast for course {course_id}: {str(e)}"
        )
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/explanations/<int:course_id>", methods=["GET"])
@login_required
def get_model_explanations(course_id: int):
    """
    Get detailed explanations for model predictions using SHAP/LIME
    """
    try:
        logger.info(
            f"Getting model explanations for course {course_id}, user {current_user.id}"
        )

        # Validate course ownership
        course = (
            Course.query.join(Term)
            .filter(Course.id == course_id, Term.user_id == current_user.id)
            .first()
        )

        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Get model explanations
        explanations = predictive_engine.get_model_explanations(
            course_id, current_user.id
        )

        if not explanations:
            return jsonify(
                {
                    "error": "Unable to generate explanations",
                    "message": "No recent predictions found or advanced ML not available",
                }
            ), 400

        # Format response
        response = {
            "course_id": course_id,
            "course_name": course.name,
            "explanations": explanations,
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "api_version": "2.0",
            },
        }

        return jsonify(response)

    except Exception as e:
        logger.error(
            f"Error getting model explanations for course {course_id}: {str(e)}"
        )
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/monitoring/<int:course_id>", methods=["POST"])
@login_required
def monitor_model_performance(course_id: int):
    """
    Monitor model performance and detect drift

    Request Body:
    {
        "actual_grade": 85.5
    }
    """
    try:
        logger.info(
            f"Monitoring model performance for course {course_id}, user {current_user.id}"
        )

        # Parse request data
        data = request.get_json()
        if not data or "actual_grade" not in data:
            return jsonify({"error": "actual_grade is required in request body"}), 400

        actual_grade = data["actual_grade"]
        if (
            not isinstance(actual_grade, (int, float))
            or actual_grade < 0
            or actual_grade > 100
        ):
            return jsonify(
                {"error": "actual_grade must be a number between 0 and 100"}
            ), 400

        # Validate course ownership
        course = (
            Course.query.join(Term)
            .filter(Course.id == course_id, Term.user_id == current_user.id)
            .first()
        )

        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Monitor model performance
        monitoring_result = predictive_engine.monitor_model_performance(
            course_id, current_user.id, actual_grade
        )

        # Format response
        response = {
            "course_id": course_id,
            "course_name": course.name,
            "monitoring_result": monitoring_result,
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "api_version": "2.0",
            },
        }

        return jsonify(response)

    except Exception as e:
        logger.error(
            f"Error monitoring model performance for course {course_id}: {str(e)}"
        )
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/ab-test/<int:course_id>", methods=["GET"])
@login_required
def get_ab_test_assignment(course_id: int):
    """
    Get A/B test variant assignment for model comparison

    Query Parameters:
    - experiment: Experiment name (default: "grade_prediction_models")
    """
    try:
        logger.info(
            f"Getting A/B test assignment for course {course_id}, user {current_user.id}"
        )

        # Parse query parameters
        experiment_name = request.args.get(
            "experiment", default="grade_prediction_models"
        )

        # Validate course ownership
        course = (
            Course.query.join(Term)
            .filter(Course.id == course_id, Term.user_id == current_user.id)
            .first()
        )

        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Get A/B test assignment
        variant_id = predictive_engine.run_ab_test_assignment(
            course_id, current_user.id, experiment_name
        )

        # Format response
        response = {
            "course_id": course_id,
            "course_name": course.name,
            "ab_test": {
                "experiment_name": experiment_name,
                "variant_id": variant_id,
                "model_type": "advanced_ml"
                if "advanced" in variant_id
                else "traditional",
            },
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "api_version": "2.0",
            },
        }

        return jsonify(response)

    except Exception as e:
        logger.error(
            f"Error getting A/B test assignment for course {course_id}: {str(e)}"
        )
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/external-data", methods=["GET"])
@login_required
def get_external_data():
    """
    Get current external data that influences predictions
    """
    try:
        logger.info(f"Getting external data for user {current_user.id}")

        # Check if advanced ML is available
        if (
            not predictive_engine.advanced_ml_enabled
            or not predictive_engine.external_data_service
        ):
            return jsonify(
                {
                    "error": "External data service not available",
                    "message": "Advanced ML features are not enabled",
                }
            ), 503

        # Collect external data
        external_data = predictive_engine.external_data_service.collect_all_data()

        # Format response
        response = {
            "external_data": external_data,
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "api_version": "2.0",
                "data_freshness": "real_time",
            },
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error getting external data: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/model-health", methods=["GET"])
@login_required
def get_model_health():
    """
    Get overall model health and performance metrics

    Query Parameters:
    - days_back: Number of days to analyze (default: 7)
    """
    try:
        logger.info(f"Getting model health for user {current_user.id}")

        # Parse query parameters
        days_back = request.args.get("days_back", default=7, type=int)

        if days_back < 1 or days_back > 90:
            return jsonify({"error": "days_back must be between 1 and 90"}), 400

        # Check if ML monitoring is available
        if (
            not predictive_engine.advanced_ml_enabled
            or not predictive_engine.ml_monitoring
        ):
            return jsonify(
                {
                    "model_health": "unknown",
                    "message": "ML monitoring not available",
                    "advanced_ml_enabled": False,
                }
            )

        # Get model health for user courses
        user_courses = (
            Course.query.join(Term).filter(Term.user_id == current_user.id).all()
        )

        model_health_reports = {}
        overall_health_score = 0.0

        for course in user_courses:
            try:
                model_id = f"grade_predictor_{course.id}"
                health_report = predictive_engine.ml_monitoring.get_model_health_report(
                    model_id, days_back
                )

                if health_report.get("health_scores"):
                    model_health_reports[course.id] = {
                        "course_name": course.name,
                        "health_report": health_report,
                    }
                    overall_health_score += health_report["health_scores"].get(
                        "overall_health", 0
                    )
            except Exception as course_error:
                logger.warning(
                    f"Error getting health for course {course.id}: {str(course_error)}"
                )
                continue

        # Calculate overall health
        if model_health_reports:
            overall_health_score /= len(model_health_reports)

        health_status = (
            "excellent"
            if overall_health_score > 0.8
            else "good"
            if overall_health_score > 0.6
            else "fair"
            if overall_health_score > 0.4
            else "poor"
        )

        # Format response
        response = {
            "overall_health": {
                "score": overall_health_score,
                "status": health_status,
                "models_monitored": len(model_health_reports),
            },
            "model_reports": model_health_reports,
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "api_version": "2.0",
                "analysis_period_days": days_back,
            },
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error getting model health: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/advanced-features", methods=["GET"])
@login_required
def get_advanced_features_status():
    """
    Get status of advanced ML features and capabilities
    """
    try:
        logger.info(f"Getting advanced features status for user {current_user.id}")

        # Check feature availability
        features_status = {
            "advanced_ml_enabled": predictive_engine.advanced_ml_enabled,
            "external_data_integration": predictive_engine.external_data_service
            is not None,
            "time_series_forecasting": predictive_engine.forecasting_engine is not None,
            "model_interpretability": predictive_engine.interpretability_engine
            is not None,
            "ab_testing": predictive_engine.ab_testing is not None,
            "ml_monitoring": predictive_engine.ml_monitoring is not None,
        }

        # Count available features
        available_features = sum(features_status.values())
        total_features = len(features_status)

        # Format response
        response = {
            "features_status": features_status,
            "summary": {
                "available_features": available_features,
                "total_features": total_features,
                "availability_percentage": (available_features / total_features) * 100,
                "overall_status": "fully_available"
                if available_features == total_features
                else "partially_available"
                if available_features > 0
                else "unavailable",
            },
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "api_version": "2.0",
            },
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error getting advanced features status: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


# Error handlers for analytics blueprint
@analytics_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors within analytics blueprint."""
    return jsonify(
        {
            "error": "Analytics endpoint not found",
            "message": "The requested analytics endpoint does not exist",
        }
    ), 404


@analytics_bp.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors within analytics blueprint."""
    return jsonify(
        {
            "error": "Method not allowed",
            "message": "The HTTP method is not allowed for this analytics endpoint",
        }
    ), 405


@analytics_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors within analytics blueprint."""
    return jsonify(
        {
            "error": "Analytics service error",
            "message": "An internal error occurred in the analytics service",
        }
    ), 500
