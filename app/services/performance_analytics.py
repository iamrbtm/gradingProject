"""
Academic Performance Analytics Suite
=====================================

This module provides comprehensive performance metrics calculation, trend analysis,
and comparative analytics for academic tracking.

Key Features:
- GPA calculation and trending
- Course performance metrics
- Study efficiency analysis
- Workload balance assessment
- Comparative performance analysis
- Performance forecasting and insights

Author: Analytics Team
Date: 2024-12-19
"""

import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta, date
from dataclasses import dataclass
import json
import statistics
from collections import defaultdict

try:
    import numpy as np
    import matplotlib.pyplot as plt
    import seaborn as sns

    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    # Fallback: use basic statistics
    np = None

from sqlalchemy import or_

from ..models import (
    db,
    User,
    Course,
    Term,
    Assignment,
    GradeCategory,
    PerformanceMetric,
    PerformanceTrend,
    AuditLog,
)
from .grade_calculator import GradeCalculatorService

logger = logging.getLogger(__name__)


@dataclass
class PerformanceSnapshot:
    """Data class for current performance snapshot."""

    overall_gpa: float
    term_gpa: float
    course_grades: Dict[int, float]  # course_id -> grade
    completion_rates: Dict[int, float]  # course_id -> completion_rate
    trend_direction: str  # 'improving', 'declining', 'stable'
    risk_courses: List[int]  # course_ids of at-risk courses
    strength_areas: List[str]
    improvement_areas: List[str]
    last_updated: datetime


@dataclass
class TrendAnalysis:
    """Data class for trend analysis results."""

    metric_name: str
    trend_direction: str
    trend_strength: float  # 0-1 scale
    data_points: List[Tuple[datetime, float]]
    statistical_significance: float
    forecast_next_period: Optional[float]
    confidence_interval: Optional[Tuple[float, float]]


@dataclass
class ComparativeAnalysis:
    """Data class for comparative performance analysis."""

    user_performance: float
    cohort_average: float
    percentile_rank: int  # 1-100
    performance_gap: float  # positive means above average
    areas_of_excellence: List[str]
    areas_for_improvement: List[str]
    recommended_actions: List[str]


class PerformanceAnalyticsService:
    """
    Comprehensive service for academic performance analytics.

    This class handles calculation of performance metrics, trend analysis,
    and comparative analytics for academic tracking and improvement.
    """

    def __init__(self):
        """Initialize the performance analytics service."""
        self.grade_calculator = GradeCalculatorService()
        self.metrics_cache = {}
        self.cache_ttl = timedelta(hours=1)  # Cache metrics for 1 hour

    def get_performance_snapshot(
        self, user_id: int, term_id: Optional[int] = None
    ) -> PerformanceSnapshot:
        """
        Generate a comprehensive performance snapshot for a user.

        Args:
            user_id: The user ID to analyze
            term_id: Optional specific term to analyze (defaults to current term)

        Returns:
            PerformanceSnapshot with comprehensive performance data
        """
        try:
            logger.info(f"Generating performance snapshot for user {user_id}")

            user = User.query.get(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            # Get target term
            if term_id:
                term = Term.query.filter_by(id=term_id, user_id=user_id).first()
            else:
                # Get most recent term
                term = (
                    Term.query.filter_by(user_id=user_id)
                    .order_by(Term.start_date.desc())
                    .first()
                )

            if not term:
                # Return empty state for users with no academic data
                logger.info(
                    f"No terms found for user {user_id}, returning empty snapshot"
                )
                return PerformanceSnapshot(
                    overall_gpa=0.0,
                    term_gpa=0.0,
                    course_grades={},
                    completion_rates={},
                    trend_direction="stable",
                    risk_courses=[],
                    strength_areas=[],
                    improvement_areas=[
                        "Set up your first term and courses to start tracking performance"
                    ],
                    last_updated=datetime.utcnow(),
                )

            # Calculate overall and term GPA
            overall_gpa = self._calculate_overall_gpa(user_id)
            term_gpa = self.grade_calculator.calculate_term_gpa(term)

            # Get course grades and completion rates
            course_grades = {}
            completion_rates = {}

            for course in term.courses:
                grade = self.grade_calculator.calculate_course_grade(course)
                completion_rate = self.grade_calculator.calculate_percentage_complete(
                    course
                )

                course_grades[course.id] = grade
                completion_rates[course.id] = completion_rate

            # Analyze trend direction
            trend_direction = self._analyze_gpa_trend(user_id)

            # Identify risk courses (below 70%)
            risk_courses = [
                course_id for course_id, grade in course_grades.items() if grade < 70.0
            ]

            # Identify strengths and improvement areas
            strength_areas, improvement_areas = self._analyze_performance_areas(
                user_id, course_grades
            )

            snapshot = PerformanceSnapshot(
                overall_gpa=overall_gpa,
                term_gpa=term_gpa,
                course_grades=course_grades,
                completion_rates=completion_rates,
                trend_direction=trend_direction,
                risk_courses=risk_courses,
                strength_areas=strength_areas,
                improvement_areas=improvement_areas,
                last_updated=datetime.utcnow(),
            )

            logger.info(
                f"Generated performance snapshot: GPA {overall_gpa:.2f}, Trend: {trend_direction}"
            )
            return snapshot

        except Exception as e:
            logger.error(
                f"Error generating performance snapshot for user {user_id}: {str(e)}"
            )
            raise

    def calculate_performance_metrics(
        self, user_id: int, metric_types: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """
        Calculate various performance metrics for a user.

        Args:
            user_id: The user ID to analyze
            metric_types: List of specific metrics to calculate (optional)

        Returns:
            Dictionary mapping metric names to values
        """
        try:
            logger.info(f"Calculating performance metrics for user {user_id}")

            # Default metrics to calculate
            if not metric_types:
                metric_types = [
                    "overall_gpa",
                    "consistency_score",
                    "workload_balance",
                    "submission_timeliness",
                    "improvement_rate",
                    "study_efficiency",
                ]

            metrics = {}

            for metric_type in metric_types:
                try:
                    if metric_type == "overall_gpa":
                        metrics[metric_type] = self._calculate_overall_gpa(user_id)
                    elif metric_type == "consistency_score":
                        metrics[metric_type] = self._calculate_consistency_score(
                            user_id
                        )
                    elif metric_type == "workload_balance":
                        metrics[metric_type] = self._calculate_workload_balance(user_id)
                    elif metric_type == "submission_timeliness":
                        metrics[metric_type] = self._calculate_submission_timeliness(
                            user_id
                        )
                    elif metric_type == "improvement_rate":
                        metrics[metric_type] = self._calculate_improvement_rate(user_id)
                    elif metric_type == "study_efficiency":
                        metrics[metric_type] = self._calculate_study_efficiency(user_id)
                    else:
                        logger.warning(f"Unknown metric type: {metric_type}")

                except Exception as e:
                    logger.error(f"Error calculating {metric_type}: {str(e)}")
                    metrics[metric_type] = 0.0

            # Store calculated metrics in database
            self._store_performance_metrics(user_id, metrics)

            logger.info(f"Calculated {len(metrics)} performance metrics")
            return metrics

        except Exception as e:
            logger.error(
                f"Error calculating performance metrics for user {user_id}: {str(e)}"
            )
            return {}

    def analyze_performance_trends(
        self, user_id: int, lookback_days: int = 90
    ) -> Dict[str, TrendAnalysis]:
        """
        Analyze performance trends over time.

        Args:
            user_id: The user ID to analyze
            lookback_days: Number of days to look back for trend analysis

        Returns:
            Dictionary mapping metric names to trend analyses
        """
        try:
            logger.info(f"Analyzing performance trends for user {user_id}")

            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

            # Get historical performance metrics
            metrics = (
                PerformanceMetric.query.filter(
                    PerformanceMetric.user_id == user_id,
                    PerformanceMetric.calculation_date >= cutoff_date,
                )
                .order_by(PerformanceMetric.calculation_date)
                .all()
            )

            # Group metrics by type
            metric_groups = defaultdict(list)
            for metric in metrics:
                metric_groups[metric.metric_type].append(
                    (metric.calculation_date, float(metric.metric_value))
                )

            trend_analyses = {}

            for metric_type, data_points in metric_groups.items():
                if len(data_points) < 3:  # Need at least 3 points for trend analysis
                    continue

                trend_analysis = self._perform_trend_analysis(metric_type, data_points)
                trend_analyses[metric_type] = trend_analysis

            # Store trend analyses
            self._store_trend_analyses(user_id, trend_analyses)

            logger.info(f"Analyzed trends for {len(trend_analyses)} metrics")
            return trend_analyses

        except Exception as e:
            logger.error(f"Error analyzing trends for user {user_id}: {str(e)}")
            return {}

    def generate_comparative_analysis(
        self, user_id: int, comparison_group: str = "term_cohort"
    ) -> ComparativeAnalysis:
        """
        Generate comparative performance analysis.

        Args:
            user_id: The user ID to analyze
            comparison_group: Type of comparison ('term_cohort', 'course_peers', 'historical_self')

        Returns:
            ComparativeAnalysis with comparative performance insights
        """
        try:
            logger.info(f"Generating comparative analysis for user {user_id}")

            user_performance = self._calculate_overall_gpa(user_id)

            if comparison_group == "term_cohort":
                cohort_performance = self._get_term_cohort_performance(user_id)
            elif comparison_group == "course_peers":
                cohort_performance = self._get_course_peers_performance(user_id)
            else:  # historical_self
                cohort_performance = self._get_historical_self_performance(user_id)

            cohort_average = (
                statistics.mean(cohort_performance)
                if cohort_performance
                else user_performance
            )

            # Calculate percentile rank
            if cohort_performance:
                better_count = sum(
                    1 for perf in cohort_performance if user_performance > perf
                )
                percentile_rank = int((better_count / len(cohort_performance)) * 100)
            else:
                percentile_rank = 50  # Default to median

            performance_gap = user_performance - cohort_average

            # Analyze strengths and improvement areas
            excellence_areas, improvement_areas = self._comparative_analysis_areas(
                user_id, cohort_average
            )

            # Generate recommendations
            recommendations = self._generate_performance_recommendations(
                user_performance, cohort_average, excellence_areas, improvement_areas
            )

            analysis = ComparativeAnalysis(
                user_performance=user_performance,
                cohort_average=cohort_average,
                percentile_rank=percentile_rank,
                performance_gap=performance_gap,
                areas_of_excellence=excellence_areas,
                areas_for_improvement=improvement_areas,
                recommended_actions=recommendations,
            )

            logger.info(
                f"Comparative analysis: {percentile_rank}th percentile, gap: {performance_gap:.2f}"
            )
            return analysis

        except Exception as e:
            logger.error(
                f"Error generating comparative analysis for user {user_id}: {str(e)}"
            )
            raise

    def get_performance_insights(self, user_id: int) -> Dict[str, Any]:
        """
        Generate comprehensive performance insights and recommendations.

        Args:
            user_id: The user ID to analyze

        Returns:
            Dictionary with performance insights, recommendations, and action items
        """
        try:
            logger.info(f"Generating performance insights for user {user_id}")

            # Get performance snapshot
            snapshot = self.get_performance_snapshot(user_id)

            # Get trend analysis
            trends = self.analyze_performance_trends(user_id)

            # Get comparative analysis
            comparative = self.generate_comparative_analysis(user_id)

            # Generate insights
            insights = {
                "current_status": {
                    "overall_gpa": snapshot.overall_gpa,
                    "term_gpa": snapshot.term_gpa,
                    "trend_direction": snapshot.trend_direction,
                    "courses_at_risk": len(snapshot.risk_courses),
                    "percentile_rank": comparative.percentile_rank,
                },
                "key_trends": self._summarize_key_trends(trends),
                "strengths": snapshot.strength_areas + comparative.areas_of_excellence,
                "improvement_opportunities": snapshot.improvement_areas
                + comparative.areas_for_improvement,
                "action_items": comparative.recommended_actions,
                "forecasts": self._generate_performance_forecasts(trends),
                "alerts": self._generate_performance_alerts(snapshot, trends),
                "study_recommendations": self._generate_study_recommendations(
                    user_id, snapshot, trends
                ),
            }

            # Remove duplicates from lists
            insights["strengths"] = list(set(insights["strengths"]))
            insights["improvement_opportunities"] = list(
                set(insights["improvement_opportunities"])
            )

            logger.info("Generated comprehensive performance insights")
            return insights

        except Exception as e:
            logger.error(
                f"Error generating performance insights for user {user_id}: {str(e)}"
            )
            return {}

    def _calculate_overall_gpa(self, user_id: int) -> float:
        """Calculate overall GPA across all terms."""
        try:
            terms = Term.query.filter_by(user_id=user_id).all()
            if not terms:
                return 0.0

            total_quality_points = 0.0
            total_credits = 0.0

            for term in terms:
                term_gpa = self.grade_calculator.calculate_term_gpa(term)
                term_credits = sum(
                    course.credits for course in term.courses if course.credits
                )

                if term_credits > 0:
                    total_quality_points += term_gpa * term_credits
                    total_credits += term_credits

            return total_quality_points / total_credits if total_credits > 0 else 0.0

        except Exception as e:
            logger.error(f"Error calculating overall GPA for user {user_id}: {str(e)}")
            return 0.0

    def _calculate_consistency_score(self, user_id: int) -> float:
        """Calculate consistency score based on grade variability."""
        try:
            # Get all graded assignments for the user
            assignments = (
                db.session.query(Assignment)
                .join(Course)
                .join(Term)
                .filter(
                    Term.user_id == user_id,
                    Assignment.score.isnot(None),
                    Assignment.last_modified >= datetime.utcnow() - timedelta(days=30),
                )
                .all()
            )

            if len(assignments) < 3:
                return 0.0

            # Calculate percentage scores
            percentages = [
                (assignment.score / assignment.max_score) * 100
                for assignment in assignments
            ]

            # Calculate coefficient of variation (lower = more consistent)
            if percentages:
                mean_score = statistics.mean(percentages)
                std_dev = statistics.stdev(percentages) if len(percentages) > 1 else 0

                if mean_score > 0:
                    cv = std_dev / mean_score
                    # Convert to consistency score (0-1, higher = more consistent)
                    consistency_score = max(
                        0, 1 - (cv / 0.5)
                    )  # Normalize assuming max CV of 0.5
                    return min(1.0, consistency_score)

            return 0.0

        except Exception as e:
            logger.error(
                f"Error calculating consistency score for user {user_id}: {str(e)}"
            )
            return 0.0

    def _calculate_workload_balance(self, user_id: int) -> float:
        """Calculate workload balance score."""
        try:
            # Get current term courses
            current_term = (
                Term.query.filter_by(user_id=user_id)
                .order_by(Term.start_date.desc())
                .first()
            )
            if not current_term:
                return 0.0

            courses = current_term.courses
            if len(courses) < 2:
                return 1.0  # Perfect balance with one course

            # Calculate workload distribution
            course_workloads = []
            for course in courses:
                # Estimate workload based on credits and assignment frequency
                credits = course.credits or 3
                assignment_count = len(course.assignments)
                workload = credits * (1 + assignment_count * 0.1)  # Simple heuristic
                course_workloads.append(workload)

            if course_workloads:
                # Calculate balance using coefficient of variation
                mean_workload = statistics.mean(course_workloads)
                std_workload = (
                    statistics.stdev(course_workloads)
                    if len(course_workloads) > 1
                    else 0
                )

                if mean_workload > 0:
                    cv = std_workload / mean_workload
                    # Convert to balance score (0-1, higher = better balanced)
                    balance_score = max(0, 1 - (cv / 0.5))
                    return min(1.0, balance_score)

            return 0.0

        except Exception as e:
            logger.error(
                f"Error calculating workload balance for user {user_id}: {str(e)}"
            )
            return 0.0

    def _calculate_submission_timeliness(self, user_id: int) -> float:
        """Calculate submission timeliness score."""
        try:
            # Get recent assignments (last 90 days)
            cutoff_date = datetime.utcnow() - timedelta(days=90)

            assignments = (
                db.session.query(Assignment)
                .join(Course)
                .join(Term)
                .filter(
                    Term.user_id == user_id,
                    Assignment.score.isnot(None),
                    Assignment.due_date >= cutoff_date,
                )
                .all()
            )

            if not assignments:
                return 0.0

            # Calculate timeliness
            on_time_count = sum(
                1 for assignment in assignments if not assignment.late_submission
            )
            timeliness_score = on_time_count / len(assignments)

            return timeliness_score

        except Exception as e:
            logger.error(
                f"Error calculating submission timeliness for user {user_id}: {str(e)}"
            )
            return 0.0

    def _calculate_improvement_rate(self, user_id: int) -> float:
        """Calculate improvement rate over time."""
        try:
            # Get performance metrics over time
            metrics = (
                PerformanceMetric.query.filter(
                    PerformanceMetric.user_id == user_id,
                    PerformanceMetric.metric_type == "overall_gpa",
                )
                .order_by(PerformanceMetric.calculation_date)
                .all()
            )

            if len(metrics) < 2:
                return 0.0

            # Calculate trend
            values = [float(metric.metric_value) for metric in metrics]

            # Simple improvement calculation (recent vs older performance)
            if len(values) >= 4:
                recent_avg = statistics.mean(values[-2:])  # Last 2 values
                older_avg = statistics.mean(values[:2])  # First 2 values

                if older_avg > 0:
                    improvement_rate = (recent_avg - older_avg) / older_avg
                    # Normalize to 0-1 scale
                    return max(0, min(1, (improvement_rate + 0.5) / 1.0))

            return 0.0

        except Exception as e:
            logger.error(
                f"Error calculating improvement rate for user {user_id}: {str(e)}"
            )
            return 0.0

    def _calculate_study_efficiency(self, user_id: int) -> float:
        """Calculate study efficiency based on performance vs effort indicators."""
        try:
            recent_assignments = (
                db.session.query(Assignment)
                .join(Course)
                .join(Term)
                .filter(
                    Term.user_id == user_id,
                    Assignment.score.isnot(None),
                    Assignment.last_modified >= datetime.utcnow() - timedelta(days=30),
                )
                .order_by(Assignment.last_modified.desc())
                .all()
            )

            if not recent_assignments:
                return 0.0

            total_score = sum(
                (assignment.score / assignment.max_score) * 100
                for assignment in recent_assignments
                if assignment.max_score and assignment.max_score > 0
            )

            avg_efficiency = total_score / len(recent_assignments)
            return min(1.0, avg_efficiency / 100.0)

        except Exception as e:
            logger.error(
                f"Error calculating study efficiency for user {user_id}: {str(e)}"
            )
            return 0.0

    def _analyze_gpa_trend(self, user_id: int) -> str:
        """Analyze GPA trend direction."""
        try:
            # Get recent GPA metrics
            metrics = (
                PerformanceMetric.query.filter(
                    PerformanceMetric.user_id == user_id,
                    PerformanceMetric.metric_type == "overall_gpa",
                )
                .order_by(PerformanceMetric.calculation_date.desc())
                .limit(5)
                .all()
            )

            if len(metrics) < 3:
                return "stable"

            values = [float(metric.metric_value) for metric in reversed(metrics)]

            # Simple trend analysis
            recent_values = values[-3:]
            if len(recent_values) >= 3:
                if all(
                    recent_values[i] > recent_values[i - 1]
                    for i in range(1, len(recent_values))
                ):
                    return "improving"
                elif all(
                    recent_values[i] < recent_values[i - 1]
                    for i in range(1, len(recent_values))
                ):
                    return "declining"

            return "stable"

        except Exception as e:
            logger.error(f"Error analyzing GPA trend for user {user_id}: {str(e)}")
            return "stable"

    def _analyze_performance_areas(
        self, user_id: int, course_grades: Dict[int, float]
    ) -> Tuple[List[str], List[str]]:
        """Analyze performance to identify strength and improvement areas."""
        try:
            strengths = []
            improvements = []

            # Analyze course performance
            high_performing_courses = [
                course_id for course_id, grade in course_grades.items() if grade >= 85.0
            ]

            low_performing_courses = [
                course_id for course_id, grade in course_grades.items() if grade < 75.0
            ]

            if len(high_performing_courses) >= len(course_grades) * 0.6:
                strengths.append("Strong overall course performance")

            if low_performing_courses:
                improvements.append("Focus on struggling courses")

            # Analyze assignment patterns
            recent_assignments = (
                db.session.query(Assignment)
                .join(Course)
                .join(Term)
                .filter(
                    Term.user_id == user_id,
                    Assignment.score.isnot(None),
                    Assignment.last_modified >= datetime.utcnow() - timedelta(days=30),
                )
                .all()
            )

            if recent_assignments:
                late_rate = sum(
                    1 for a in recent_assignments if a.late_submission
                ) / len(recent_assignments)

                if late_rate < 0.1:
                    strengths.append("Excellent time management")
                elif late_rate > 0.3:
                    improvements.append("Improve assignment timeliness")

            return strengths, improvements

        except Exception as e:
            logger.error(
                f"Error analyzing performance areas for user {user_id}: {str(e)}"
            )
            return [], []

    def _perform_trend_analysis(
        self, metric_type: str, data_points: List[Tuple[datetime, float]]
    ) -> TrendAnalysis:
        """Perform statistical trend analysis on data points."""
        try:
            if len(data_points) < 3:
                return TrendAnalysis(
                    metric_name=metric_type,
                    trend_direction="insufficient_data",
                    trend_strength=0.0,
                    data_points=data_points,
                    statistical_significance=0.0,
                    forecast_next_period=None,
                    confidence_interval=None,
                )

            # Extract values and calculate trend
            values = [point[1] for point in data_points]

            # Simple trend calculation
            if len(values) >= 2:
                first_half = statistics.mean(values[: len(values) // 2])
                second_half = statistics.mean(values[len(values) // 2 :])

                trend_strength = abs(second_half - first_half) / max(first_half, 0.001)
                trend_strength = min(1.0, trend_strength)

                if second_half > first_half * 1.05:
                    trend_direction = "improving"
                elif second_half < first_half * 0.95:
                    trend_direction = "declining"
                else:
                    trend_direction = "stable"
            else:
                trend_direction = "stable"
                trend_strength = 0.0

            # Simple forecast (last value + trend)
            if len(values) >= 2:
                recent_trend = values[-1] - values[-2]
                forecast = values[-1] + recent_trend
            else:
                forecast = values[-1] if values else 0.0

            return TrendAnalysis(
                metric_name=metric_type,
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                data_points=data_points,
                statistical_significance=0.8 if len(data_points) >= 5 else 0.5,
                forecast_next_period=forecast,
                confidence_interval=(forecast * 0.9, forecast * 1.1),
            )

        except Exception as e:
            logger.error(f"Error performing trend analysis for {metric_type}: {str(e)}")
            return TrendAnalysis(
                metric_name=metric_type,
                trend_direction="error",
                trend_strength=0.0,
                data_points=data_points,
                statistical_significance=0.0,
                forecast_next_period=None,
                confidence_interval=None,
            )

    def _get_term_cohort_performance(self, user_id: int) -> List[float]:
        """Get performance data for term cohort comparison."""
        try:
            # This would typically compare with other users in the same term/institution
            # For now, return simulated cohort data
            return [2.8, 3.1, 2.9, 3.3, 2.7, 3.5, 3.0, 2.6, 3.2, 2.9]

        except Exception as e:
            logger.error(f"Error getting term cohort performance: {str(e)}")
            return []

    def _get_course_peers_performance(self, user_id: int) -> List[float]:
        """Get performance data for course peers comparison."""
        try:
            # This would typically compare with other users in similar courses
            # For now, return simulated peer data
            return [2.9, 3.0, 3.1, 2.8, 3.2, 2.7, 3.4, 2.9, 3.1, 3.0]

        except Exception as e:
            logger.error(f"Error getting course peers performance: {str(e)}")
            return []

    def _get_historical_self_performance(self, user_id: int) -> List[float]:
        """Get historical performance data for self-comparison."""
        try:
            metrics = (
                PerformanceMetric.query.filter(
                    PerformanceMetric.user_id == user_id,
                    PerformanceMetric.metric_type == "overall_gpa",
                )
                .order_by(PerformanceMetric.calculation_date)
                .all()
            )

            return [float(metric.metric_value) for metric in metrics]

        except Exception as e:
            logger.error(
                f"Error getting historical self performance for user {user_id}: {str(e)}"
            )
            return []

    def _comparative_analysis_areas(
        self, user_id: int, cohort_average: float
    ) -> Tuple[List[str], List[str]]:
        """Analyze areas of excellence and improvement compared to cohort."""
        try:
            user_gpa = self._calculate_overall_gpa(user_id)

            excellence_areas = []
            improvement_areas = []

            if user_gpa > cohort_average * 1.1:
                excellence_areas.append("Overall academic performance")
            elif user_gpa < cohort_average * 0.9:
                improvement_areas.append("Overall academic performance")

            # Additional analysis could be added here for specific subject areas,
            # study habits, etc.

            return excellence_areas, improvement_areas

        except Exception as e:
            logger.error(
                f"Error analyzing comparative areas for user {user_id}: {str(e)}"
            )
            return [], []

    def _generate_performance_recommendations(
        self,
        user_performance: float,
        cohort_average: float,
        excellence_areas: List[str],
        improvement_areas: List[str],
    ) -> List[str]:
        """Generate performance improvement recommendations."""
        try:
            recommendations = []

            performance_gap = user_performance - cohort_average

            if performance_gap < -0.3:
                recommendations.append(
                    "Consider seeking academic tutoring or counseling"
                )
                recommendations.append(
                    "Review study methods and time management strategies"
                )
            elif performance_gap < -0.1:
                recommendations.append("Focus on consistent daily study habits")
                recommendations.append(
                    "Identify and address specific challenging areas"
                )
            elif performance_gap > 0.2:
                recommendations.append(
                    "Consider peer tutoring or leadership opportunities"
                )
                recommendations.append("Maintain current successful strategies")
            else:
                recommendations.append("Continue steady progress with current approach")

            if improvement_areas:
                recommendations.append(
                    f"Focus improvement efforts on: {', '.join(improvement_areas)}"
                )

            if excellence_areas:
                recommendations.append(
                    f"Leverage your strengths in: {', '.join(excellence_areas)}"
                )

            return recommendations

        except Exception as e:
            logger.error(f"Error generating performance recommendations: {str(e)}")
            return ["Review current study strategies and seek guidance as needed"]

    def _summarize_key_trends(self, trends: Dict[str, TrendAnalysis]) -> List[str]:
        """Summarize key trends for insights."""
        try:
            key_trends = []

            for metric_name, trend in trends.items():
                if trend.trend_strength > 0.3:  # Significant trend
                    direction_desc = {
                        "improving": "improving significantly",
                        "declining": "declining notably",
                        "stable": "remaining stable",
                    }.get(trend.trend_direction, trend.trend_direction)

                    key_trends.append(
                        f"{metric_name.replace('_', ' ').title()} is {direction_desc}"
                    )

            return key_trends[:5]  # Return top 5 trends

        except Exception as e:
            logger.error(f"Error summarizing key trends: {str(e)}")
            return []

    def _generate_performance_forecasts(
        self, trends: Dict[str, TrendAnalysis]
    ) -> Dict[str, Any]:
        """Generate performance forecasts based on trends."""
        try:
            forecasts = {}

            for metric_name, trend in trends.items():
                if trend.forecast_next_period is not None:
                    forecasts[metric_name] = {
                        "predicted_value": trend.forecast_next_period,
                        "confidence_interval": trend.confidence_interval,
                        "trend_direction": trend.trend_direction,
                    }

            return forecasts

        except Exception as e:
            logger.error(f"Error generating performance forecasts: {str(e)}")
            return {}

    def _generate_performance_alerts(
        self, snapshot: PerformanceSnapshot, trends: Dict[str, TrendAnalysis]
    ) -> List[str]:
        """Generate performance alerts and warnings."""
        try:
            alerts = []

            # GPA alerts
            if snapshot.overall_gpa < 2.0:
                alerts.append(
                    "CRITICAL: Overall GPA below 2.0 - immediate action required"
                )
            elif snapshot.overall_gpa < 2.5:
                alerts.append(
                    "WARNING: Overall GPA below 2.5 - consider academic support"
                )

            # Risk course alerts
            if snapshot.risk_courses:
                alerts.append(
                    f"ALERT: {len(snapshot.risk_courses)} course(s) at risk (below 70%)"
                )

            # Trend alerts
            gpa_trend = trends.get("overall_gpa")
            if (
                gpa_trend
                and gpa_trend.trend_direction == "declining"
                and gpa_trend.trend_strength > 0.3
            ):
                alerts.append("TREND ALERT: GPA showing declining trend")

            return alerts

        except Exception as e:
            logger.error(f"Error generating performance alerts: {str(e)}")
            return []

    def _generate_study_recommendations(
        self,
        user_id: int,
        snapshot: PerformanceSnapshot,
        trends: Dict[str, TrendAnalysis],
    ) -> List[str]:
        """Generate specific study recommendations."""
        try:
            recommendations = []

            # Based on performance level
            if snapshot.overall_gpa >= 3.5:
                recommendations.append(
                    "Maintain excellent study habits and consider advanced challenges"
                )
            elif snapshot.overall_gpa >= 3.0:
                recommendations.append(
                    "Strong performance - focus on consistency and challenging areas"
                )
            elif snapshot.overall_gpa >= 2.5:
                recommendations.append(
                    "Good foundation - identify specific improvement opportunities"
                )
            else:
                recommendations.append(
                    "Focus on fundamental study skills and seek academic support"
                )

            # Based on trends
            consistency_trend = trends.get("consistency_score")
            if consistency_trend and consistency_trend.trend_direction == "declining":
                recommendations.append("Work on consistent daily study routines")

            # Based on completion rates
            low_completion_courses = [
                course_id
                for course_id, rate in snapshot.completion_rates.items()
                if rate < 0.8
            ]
            if low_completion_courses:
                recommendations.append(
                    "Prioritize completing assignments in all courses"
                )

            return recommendations

        except Exception as e:
            logger.error(f"Error generating study recommendations: {str(e)}")
            return []

    def _store_performance_metrics(
        self, user_id: int, metrics: Dict[str, float]
    ) -> None:
        """Store calculated performance metrics in database."""
        try:
            for metric_type, value in metrics.items():
                metric = PerformanceMetric(
                    user_id=user_id,
                    metric_type=metric_type,
                    metric_value=value,
                    calculation_date=datetime.utcnow(),
                    metric_metadata={"calculation_method": "automated"},
                )
                db.session.add(metric)

            db.session.commit()
            logger.info(f"Stored {len(metrics)} performance metrics for user {user_id}")

        except Exception as e:
            logger.error(f"Error storing performance metrics: {str(e)}")
            db.session.rollback()

    def _store_trend_analyses(
        self, user_id: int, trend_analyses: Dict[str, TrendAnalysis]
    ) -> None:
        """Store trend analyses in database."""
        try:
            for metric_type, analysis in trend_analyses.items():
                trend = PerformanceTrend(
                    user_id=user_id,
                    trend_type=metric_type,
                    trend_direction=analysis.trend_direction,
                    trend_strength=analysis.trend_strength,
                    start_date=analysis.data_points[0][0].date()
                    if analysis.data_points
                    else date.today(),
                    end_date=analysis.data_points[-1][0].date()
                    if analysis.data_points
                    else date.today(),
                    data_points=[
                        {"date": point[0].isoformat(), "value": point[1]}
                        for point in analysis.data_points
                    ],
                    statistical_significance=analysis.statistical_significance,
                )
                db.session.add(trend)

            db.session.commit()
            logger.info(
                f"Stored {len(trend_analyses)} trend analyses for user {user_id}"
            )

        except Exception as e:
            logger.error(f"Error storing trend analyses: {str(e)}")
            db.session.rollback()
