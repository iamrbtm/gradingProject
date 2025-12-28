"""
Predictive Grade Analytics Engine
=================================

This module provides machine learning capabilities for predicting academic outcomes,
assessing risks, and generating performance forecasts.

Key Features:
- Grade prediction using statistical analysis
- Risk assessment with intervention recommendations
- Performance forecasting and scenario analysis
- Model training and accuracy tracking

Author: Analytics Team
Date: 2024-12-19
"""

import logging
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import statistics

try:
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.linear_model import LinearRegression, Ridge
    from sklearn.model_selection import cross_val_score, train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    # Fallback: use basic statistical methods
    np = None
    pd = None

from ..models import (
    db,
    Assignment,
    Course,
    Term,
    User,
    GradeCategory,
    AuditLog,
    PredictionModel,
    GradePrediction,
    RiskAssessment,
)
from .grade_calculator import GradeCalculatorService


# Import advanced ML services with lazy loading to prevent startup errors
def _get_advanced_ml_system():
    """Lazy import of AdvancedMLSystem."""
    try:
        from .advanced_ml_models import AdvancedMLSystem

        return AdvancedMLSystem()
    except ImportError as e:
        logger.warning(f"AdvancedMLSystem not available: {e}")
        return None


def _get_time_series_forecaster():
    """Lazy import of TimeSeriesForecastingEngine."""
    try:
        from .time_series_forecasting import TimeSeriesForecaster

        return TimeSeriesForecaster()
    except ImportError as e:
        logger.warning(f"TimeSeriesForecaster not available: {e}")
        return None


def _get_interpretability_service():
    """Lazy import of ModelInterpretabilityService."""
    try:
        from .model_interpretability import ModelInterpretabilityService

        return ModelInterpretabilityService()
    except ImportError as e:
        logger.warning(f"ModelInterpretabilityService not available: {e}")
        return None


def _get_external_data_service():
    """Lazy import of ExternalDataService."""
    try:
        from .external_data_service import ExternalDataService

        return ExternalDataService()
    except ImportError as e:
        logger.warning(f"ExternalDataService not available: {e}")
        return None


def _get_ab_testing_framework():
    """Lazy import of ABTestingFramework."""
    try:
        from .ab_testing_framework import ABTestingFramework

        return ABTestingFramework()
    except ImportError as e:
        logger.warning(f"ABTestingFramework not available: {e}")
        return None


def _get_monitoring_service():
    """Lazy import of MLMonitoringService."""
    try:
        from .ml_monitoring_drift import MLMonitoringService

        return MLMonitoringService()
    except ImportError as e:
        logger.warning(f"MLMonitoringService not available: {e}")
        return None


logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """Data class for prediction results."""

    predicted_grade: float
    confidence: float
    grade_range: Tuple[float, float]
    contributing_factors: Dict[str, float]
    model_version: str
    prediction_date: datetime


@dataclass
class RiskAssessmentResult:
    """Data class for risk assessment results."""

    risk_level: str  # 'low', 'medium', 'high', 'critical'
    risk_score: float
    risk_factors: Dict[str, Union[float, str]]
    recommendations: List[str]
    intervention_priority: int


class PredictiveAnalyticsEngine:
    """
    Main engine for predictive analytics in academic performance.

    This class handles grade prediction, risk assessment, and performance forecasting
    using statistical methods (with ML fallback when sklearn is available).
    """

    def __init__(self):
        """Initialize the predictive analytics engine."""
        if SKLEARN_AVAILABLE:
            self.models = {
                "weighted_courses": {
                    "primary": RandomForestRegressor(n_estimators=100, random_state=42),
                    "backup": GradientBoostingRegressor(random_state=42),
                },
                "unweighted_courses": {
                    "primary": Ridge(alpha=1.0),
                    "backup": LinearRegression(),
                },
            }
            self.scaler = StandardScaler()
        else:
            logger.warning(
                "scikit-learn not available. Using statistical fallback methods."
            )
            self.models = None
            self.scaler = None

        self.grade_calculator = GradeCalculatorService()
        self.min_samples_for_prediction = 3  # Minimum assignments needed for prediction

        # Advanced ML Components (with lazy loading and fallback handling)
        self.advanced_ml = None
        self.forecasting_engine = None
        self.interpretability_engine = None
        self.external_data_service = None
        self.ab_testing = None
        self.ml_monitoring = None
        self.advanced_ml_enabled = False

        # We'll initialize these lazily when needed
        logger.info(
            "PredictiveAnalyticsEngine initialized with lazy loading for advanced ML"
        )

    def _get_advanced_ml(self):
        """Lazy initialization of AdvancedMLSystem."""
        if self.advanced_ml is None:
            self.advanced_ml = _get_advanced_ml_system()
        return self.advanced_ml

    def _get_forecasting_engine(self):
        """Lazy initialization of TimeSeriesForecaster."""
        if self.forecasting_engine is None:
            self.forecasting_engine = _get_time_series_forecaster()
        return self.forecasting_engine

    def _get_interpretability_engine(self):
        """Lazy initialization of ModelInterpretabilityService."""
        if self.interpretability_engine is None:
            self.interpretability_engine = _get_interpretability_service()
        return self.interpretability_engine

    def _get_external_data_service(self):
        """Lazy initialization of ExternalDataService."""
        if self.external_data_service is None:
            self.external_data_service = _get_external_data_service()
        return self.external_data_service

    def _get_ab_testing(self):
        """Lazy initialization of ABTestingFramework."""
        if self.ab_testing is None:
            self.ab_testing = _get_ab_testing_framework()
        return self.ab_testing

    def _get_ml_monitoring(self):
        """Lazy initialization of MLMonitoringService."""
        if self.ml_monitoring is None:
            self.ml_monitoring = _get_monitoring_service()
        return self.ml_monitoring

    def predict_final_grade(
        self, course_id: int, user_id: int, use_advanced_ml: bool = True
    ) -> Optional[PredictionResult]:
        """
        Predict the final grade for a course based on current performance.

        Args:
            course_id: The course ID to predict for
            user_id: The user ID (for validation)
            use_advanced_ml: Whether to use advanced ML models (default: True)

        Returns:
            PredictionResult with prediction details or None if insufficient data
        """
        try:
            logger.info(
                f"Generating grade prediction for course {course_id}, user {user_id}"
            )

            # Validate course ownership
            course = (
                Course.query.join(Term)
                .filter(Course.id == course_id, Term.user_id == user_id)
                .first()
            )

            if not course:
                logger.warning(f"Course {course_id} not found for user {user_id}")
                return None

            # Try advanced ML prediction first if enabled
            if use_advanced_ml:
                advanced_ml = self._get_advanced_ml()
                if advanced_ml is not None:
                    try:
                        advanced_result = self._predict_with_advanced_ml(
                            course, user_id
                        )
                        if advanced_result:
                            return advanced_result
                    except Exception as e:
                        logger.warning(
                            f"Advanced ML prediction failed: {str(e)}, falling back to traditional method"
                        )

            # Extract features and validate data sufficiency
            features = self._extract_course_features(course)
            if not self._validate_prediction_data(features):
                logger.info(f"Insufficient data for prediction - course {course_id}")
                return None

            # Generate prediction using traditional method
            if course.is_weighted:
                prediction = self._predict_weighted_course(course, features)
            else:
                prediction = self._predict_unweighted_course(course, features)

            # Create prediction result
            result = PredictionResult(
                predicted_grade=prediction["grade"],
                confidence=prediction["confidence"],
                grade_range=(prediction["grade_min"], prediction["grade_max"]),
                contributing_factors=prediction["factors"],
                model_version=self._get_model_version(),
                prediction_date=datetime.utcnow(),
            )

            # Store prediction in database
            self._store_prediction(course_id, user_id, result)

            logger.info(
                f"Generated prediction: {result.predicted_grade:.1f}% (confidence: {result.confidence:.2f})"
            )
            return result

        except Exception as e:
            logger.error(f"Error predicting grade for course {course_id}: {str(e)}")
            return None

    def assess_course_risk(
        self, course_id: int, user_id: int
    ) -> Optional[RiskAssessmentResult]:
        """
        Assess academic risk for a course and provide intervention recommendations.

        Args:
            course_id: The course ID to assess
            user_id: The user ID (for validation)

        Returns:
            RiskAssessmentResult with risk analysis or None if insufficient data
        """
        try:
            logger.info(f"Assessing risk for course {course_id}, user {user_id}")

            # Get course and validate ownership
            course = (
                Course.query.join(Term)
                .filter(Course.id == course_id, Term.user_id == user_id)
                .first()
            )

            if not course:
                logger.warning(f"Course {course_id} not found for user {user_id}")
                return None

            # Calculate risk factors
            risk_factors = self._calculate_risk_factors(course)

            # Determine risk level and score
            risk_score = self._calculate_composite_risk_score(risk_factors)
            risk_level = self._categorize_risk_level(risk_score)

            # Generate recommendations
            recommendations = self._generate_risk_recommendations(
                risk_factors, risk_level
            )

            # Calculate intervention priority
            priority = self._calculate_intervention_priority(risk_score, course)

            result = RiskAssessmentResult(
                risk_level=risk_level,
                risk_score=risk_score,
                risk_factors=risk_factors,
                recommendations=recommendations,
                intervention_priority=priority,
            )

            # Store risk assessment
            self._store_risk_assessment(course_id, user_id, result)

            logger.info(f"Risk assessment: {risk_level} (score: {risk_score:.3f})")
            return result

        except Exception as e:
            logger.error(f"Error assessing risk for course {course_id}: {str(e)}")
            return None

    def generate_scenario_analysis(
        self, course_id: int, user_id: int
    ) -> Dict[str, Any]:
        """
        Generate what-if scenarios for remaining assignments.

        Args:
            course_id: The course ID to analyze
            user_id: The user ID (for validation)

        Returns:
            Dictionary with different performance scenarios
        """
        try:
            logger.info(f"Generating scenario analysis for course {course_id}")

            course = (
                Course.query.join(Term)
                .filter(Course.id == course_id, Term.user_id == user_id)
                .first()
            )

            if not course:
                return {}

            # Get remaining assignments
            remaining_assignments = Assignment.query.filter(
                Assignment.course_id == course_id,
                Assignment.due_date > datetime.utcnow(),
                Assignment.score.is_(None),
            ).all()

            if not remaining_assignments:
                logger.info("No remaining assignments for scenario analysis")
                return {"message": "No remaining assignments to analyze"}

            # Calculate current grade
            current_grade = self.grade_calculator.calculate_course_grade(course)

            # Generate scenarios
            scenarios = {
                "current_status": {
                    "current_grade": current_grade,
                    "assignments_remaining": len(remaining_assignments),
                    "total_points_remaining": sum(
                        a.max_score for a in remaining_assignments
                    ),
                },
                "optimistic": self._calculate_scenario(
                    course, remaining_assignments, 0.95
                ),
                "realistic": self._calculate_scenario(
                    course, remaining_assignments, 0.85
                ),
                "conservative": self._calculate_scenario(
                    course, remaining_assignments, 0.75
                ),
                "minimum_passing": self._calculate_minimum_required(
                    course, remaining_assignments, 70.0
                ),
                "target_grade": self._calculate_target_scenarios(
                    course, remaining_assignments
                ),
            }

            logger.info(f"Generated {len(scenarios)} scenario analyses")
            return scenarios

        except Exception as e:
            logger.error(f"Error generating scenario analysis: {str(e)}")
            return {}

    def _extract_course_features(self, course: Course) -> Dict:
        """Extract features for machine learning from course data."""
        assignments = Assignment.query.filter_by(course_id=course.id).all()

        # Basic assignment statistics
        total_assignments = len(assignments)
        completed_assignments = [a for a in assignments if a.score is not None]
        completion_rate = (
            len(completed_assignments) / total_assignments
            if total_assignments > 0
            else 0
        )

        # Performance metrics
        if completed_assignments:
            scores = [
                a.score / a.max_score for a in completed_assignments if a.max_score > 0
            ]
            avg_performance = statistics.mean(scores) if scores else 0
            performance_std = statistics.stdev(scores) if len(scores) > 1 else 0

            # Recent performance trend (last 30 days)
            recent_cutoff = datetime.utcnow() - timedelta(days=30)
            recent_assignments = [
                a
                for a in completed_assignments
                if a.due_date and a.due_date >= recent_cutoff
            ]

            if len(recent_assignments) >= 2:
                recent_scores = [
                    a.score / a.max_score for a in recent_assignments if a.max_score > 0
                ]
                # Simple trend calculation (difference between first and last)
                if recent_scores and len(recent_scores) >= 2:
                    recent_trend = recent_scores[-1] - recent_scores[0]
                else:
                    recent_trend = 0
            else:
                recent_trend = 0
        else:
            avg_performance = 0
            performance_std = 0
            recent_trend = 0

        # Temporal features
        current_time = datetime.utcnow()
        if course.term.start_date and course.term.end_date:
            term_progress = (current_time - course.term.start_date).days / (
                course.term.end_date - course.term.start_date
            ).days
            term_progress = max(0, min(1, term_progress))
        else:
            term_progress = 0.5  # Assume mid-term if no dates available

        # Assignment pattern features
        late_submissions = len([a for a in completed_assignments if a.late_submission])
        late_submission_rate = (
            late_submissions / len(completed_assignments)
            if completed_assignments
            else 0
        )

        # Missing assignments
        overdue_assignments = Assignment.query.filter(
            Assignment.course_id == course.id,
            Assignment.due_date < current_time,
            Assignment.score.is_(None),
        ).count()

        # Category performance (for weighted courses)
        category_performance = {}
        if course.is_weighted:
            categories = list(course.grade_categories)  # Convert to list
            for category in categories:
                cat_assignments = [
                    a for a in completed_assignments if a.category_id == category.id
                ]
                if cat_assignments:
                    cat_scores = [
                        a.score / a.max_score
                        for a in cat_assignments
                        if a.max_score > 0
                    ]
                    category_performance[f"category_{category.id}_avg"] = (
                        statistics.mean(cat_scores) if cat_scores else 0
                    )
                    category_performance[f"category_{category.id}_count"] = len(
                        cat_assignments
                    )

        # Course characteristics
        features = {
            # Basic metrics
            "total_assignments": total_assignments,
            "completion_rate": completion_rate,
            "avg_performance": avg_performance,
            "performance_variability": performance_std,
            "recent_trend": recent_trend,
            # Temporal features
            "term_progress": term_progress,
            "days_since_term_start": (current_time - course.term.start_date).days
            if course.term.start_date
            else 0,
            # Behavioral features
            "late_submission_rate": late_submission_rate,
            "overdue_assignments": overdue_assignments,
            # Course features
            "is_weighted": 1 if course.is_weighted else 0,
            "course_credits": course.credits or 3,
            "num_categories": len(list(course.grade_categories))
            if course.grade_categories
            else 0,
            # Current grade
            "current_grade": self.grade_calculator.calculate_course_grade(course) or 0,
        }

        # Add category-specific features
        features.update(category_performance)

        return features

    def _validate_prediction_data(self, features: Dict) -> bool:
        """Validate that we have sufficient data for reliable prediction."""
        # Need minimum number of completed assignments
        if (
            features.get("completion_rate", 0) * features.get("total_assignments", 0)
            < self.min_samples_for_prediction
        ):
            return False

        # Need some term progress to make meaningful predictions
        if features.get("term_progress", 0) < 0.1:
            return False

        # Need valid performance data
        if (
            features.get("avg_performance", 0) == 0
            and features.get("current_grade", 0) == 0
        ):
            return False

        return True

    def _predict_weighted_course(self, course: Course, features: Dict) -> Dict:
        """Generate prediction for weighted course using ensemble method."""
        # For weighted courses, we use a more sophisticated approach
        # considering category performance and weights

        category_predictions = {}
        overall_confidence = 0.8  # Start with base confidence

        # Analyze each category
        categories = list(course.grade_categories)  # Convert to list
        for category in categories:
            cat_avg_key = f"category_{category.id}_avg"
            cat_count_key = f"category_{category.id}_count"

            if cat_avg_key in features:
                cat_performance = features[cat_avg_key]
                cat_sample_size = features.get(cat_count_key, 0)

                # Adjust performance based on trend and variability
                adjusted_performance = self._adjust_for_trend_and_difficulty(
                    cat_performance, features, category
                )

                category_predictions[category.id] = {
                    "predicted_avg": adjusted_performance,
                    "weight": category.weight,
                    "confidence": min(
                        0.95, 0.5 + (cat_sample_size * 0.1)
                    ),  # More samples = higher confidence
                }

                # Update overall confidence
                overall_confidence *= category_predictions[category.id]["confidence"]

        # Calculate weighted average prediction
        if category_predictions:
            predicted_grade = sum(
                pred["predicted_avg"] * pred["weight"] * 100
                for pred in category_predictions.values()
            )
        else:
            # Fallback to current grade with trend adjustment
            predicted_grade = features["current_grade"] * (
                1 + features["recent_trend"] * 0.5
            )

        # Ensure grade is within valid bounds
        predicted_grade = max(0, min(100, predicted_grade))

        # Calculate confidence and range
        confidence = max(
            0.3, overall_confidence**0.5
        )  # Square root to avoid very low confidence
        grade_range_width = (1 - confidence) * 20  # Lower confidence = wider range

        return {
            "grade": predicted_grade,
            "confidence": confidence,
            "grade_min": max(0, predicted_grade - grade_range_width),
            "grade_max": min(100, predicted_grade + grade_range_width),
            "factors": self._identify_contributing_factors(
                features, category_predictions
            ),
        }

    def _predict_unweighted_course(self, course: Course, features: Dict) -> Dict:
        """Generate prediction for unweighted course using simpler linear model."""
        # For unweighted courses, use current performance with trend analysis

        current_grade = features["current_grade"]
        recent_trend = features["recent_trend"]
        completion_rate = features["completion_rate"]
        term_progress = features["term_progress"]

        # Adjust prediction based on trend and remaining work
        remaining_work_factor = 1 - term_progress
        trend_adjustment = (
            recent_trend * remaining_work_factor * 10
        )  # Scale trend impact

        predicted_grade = current_grade + trend_adjustment

        # Adjust for consistent performance vs. variability
        performance_stability = 1 - features.get("performance_variability", 0)
        confidence = min(
            0.9, 0.4 + (completion_rate * 0.3) + (performance_stability * 0.2)
        )

        # Ensure grade is within valid bounds
        predicted_grade = max(0, min(100, predicted_grade))

        # Calculate range based on confidence and variability
        grade_range_width = (1 - confidence) * 15 + features.get(
            "performance_variability", 0
        ) * 10

        return {
            "grade": predicted_grade,
            "confidence": confidence,
            "grade_min": max(0, predicted_grade - grade_range_width),
            "grade_max": min(100, predicted_grade + grade_range_width),
            "factors": {
                "current_performance": current_grade / 100,
                "trend_impact": trend_adjustment / 100,
                "consistency": performance_stability,
                "completion_rate": completion_rate,
            },
        }

    def _adjust_for_trend_and_difficulty(
        self, base_performance: float, features: Dict, category: GradeCategory
    ) -> float:
        """Adjust performance prediction based on trends and course difficulty."""
        adjusted = base_performance

        # Apply recent trend
        trend_impact = features["recent_trend"] * 0.1  # Moderate trend impact
        adjusted += trend_impact

        # Adjust for time remaining in term
        term_progress = features["term_progress"]
        if term_progress > 0.8:  # Late in term, less room for improvement
            adjusted *= 0.95
        elif term_progress < 0.3:  # Early in term, more uncertainty
            adjusted = (adjusted + 0.8) / 2  # Regress toward mean

        # Ensure within bounds
        return max(0, min(1, adjusted))

    def _identify_contributing_factors(
        self, features: Dict, category_predictions: Optional[Dict] = None
    ) -> Dict[str, float]:
        """Identify the main factors contributing to the prediction."""
        factors = {}

        # Performance-based factors
        factors["current_performance"] = min(1.0, features["avg_performance"])
        factors["consistency"] = max(0, 1 - features["performance_variability"])
        factors["recent_trend"] = max(-1, min(1, features["recent_trend"]))

        # Behavioral factors
        factors["completion_rate"] = features["completion_rate"]
        factors["timeliness"] = max(0, 1 - features["late_submission_rate"])

        # Course progress factors
        factors["term_progress"] = features["term_progress"]

        if category_predictions:
            # Category-specific factors for weighted courses
            for cat_id, pred in category_predictions.items():
                factors[f"category_{cat_id}_impact"] = (
                    pred["predicted_avg"] * pred["weight"]
                )

        return factors

    def _calculate_risk_factors(self, course: Course) -> Dict[str, Union[float, str]]:
        """Calculate various risk factors for academic performance."""
        assignments = Assignment.query.filter_by(course_id=course.id).all()
        current_time = datetime.utcnow()

        risk_factors = {}

        # Grade trend analysis
        completed_assignments = [
            a for a in assignments if a.score is not None and a.due_date
        ]
        if len(completed_assignments) >= 3:
            # Sort by due date and calculate trend
            completed_assignments.sort(key=lambda x: x.due_date)
            recent_scores = [
                a.score / a.max_score
                for a in completed_assignments[-5:]
                if a.max_score > 0
            ]

            if len(recent_scores) >= 3:
                # Simple trend calculation
                if len(recent_scores) >= 2:
                    trend_slope = recent_scores[-1] - recent_scores[0]
                else:
                    trend_slope = 0

                risk_factors["grade_trend"] = (
                    "declining"
                    if trend_slope < -0.05
                    else "stable"
                    if trend_slope < 0.05
                    else "improving"
                )
                risk_factors["trend_severity"] = abs(trend_slope)
            else:
                risk_factors["grade_trend"] = "insufficient_data"
                risk_factors["trend_severity"] = 0
        else:
            risk_factors["grade_trend"] = "insufficient_data"
            risk_factors["trend_severity"] = 0

        # Missing assignments
        overdue_assignments = [
            a for a in assignments if a.due_date < current_time and a.score is None
        ]
        risk_factors["missing_assignments_count"] = len(overdue_assignments)
        risk_factors["missing_assignments_weight"] = sum(
            a.max_score for a in overdue_assignments
        )

        # Late submission pattern
        late_assignments = [a for a in completed_assignments if a.late_submission]
        risk_factors["late_submission_rate"] = (
            len(late_assignments) / len(completed_assignments)
            if completed_assignments
            else 0
        )

        # Current performance level
        current_grade = self.grade_calculator.calculate_course_grade(course)
        risk_factors["current_grade"] = current_grade or 0

        # Performance variability
        if len(completed_assignments) >= 3:
            scores = [
                a.score / a.max_score for a in completed_assignments if a.max_score > 0
            ]
            risk_factors["performance_variability"] = (
                statistics.stdev(scores) if len(scores) > 1 else 0
            )
        else:
            risk_factors["performance_variability"] = 0

        # Category struggles (for weighted courses)
        if course.is_weighted:
            struggling_categories = []
            categories = list(course.grade_categories)  # Convert to list
            for category in categories:
                cat_assignments = [
                    a for a in completed_assignments if a.category_id == category.id
                ]
                if cat_assignments:
                    cat_avg = statistics.mean(
                        [
                            a.score / a.max_score
                            for a in cat_assignments
                            if a.max_score > 0
                        ]
                    )
                    if cat_avg < 0.7:  # Below 70% average
                        struggling_categories.append(category.name)

            risk_factors["struggling_categories"] = struggling_categories
            risk_factors["category_struggles_count"] = len(struggling_categories)

        # Time pressure assessment
        remaining_assignments = [
            a for a in assignments if a.due_date > current_time and a.score is None
        ]
        if remaining_assignments:
            days_to_next_due = min(
                (a.due_date - current_time).days for a in remaining_assignments
            )
            risk_factors["time_pressure"] = (
                "high"
                if days_to_next_due < 3
                else "medium"
                if days_to_next_due < 7
                else "low"
            )
        else:
            risk_factors["time_pressure"] = "none"

        return risk_factors

    def _calculate_composite_risk_score(self, risk_factors: Dict) -> float:
        """Calculate a composite risk score from individual risk factors."""
        score = 0.0

        # Grade-based risk (40% of total score)
        current_grade = risk_factors.get("current_grade", 0)
        if current_grade < 60:
            score += 0.4  # High risk if failing
        elif current_grade < 70:
            score += 0.3  # Medium-high risk if close to failing
        elif current_grade < 80:
            score += 0.1  # Low risk if below average

        # Trend-based risk (25% of total score)
        if risk_factors.get("grade_trend") == "declining":
            trend_severity = risk_factors.get("trend_severity", 0)
            score += min(0.25, trend_severity * 2)  # Scale trend impact

        # Missing assignments risk (20% of total score)
        missing_count = risk_factors.get("missing_assignments_count", 0)
        if missing_count > 0:
            score += min(0.2, missing_count * 0.05)  # Each missing assignment adds risk

        # Behavioral risk (10% of total score)
        late_rate = risk_factors.get("late_submission_rate", 0)
        score += late_rate * 0.1

        # Variability risk (5% of total score)
        variability = risk_factors.get("performance_variability", 0)
        score += min(0.05, variability * 0.2)

        return min(1.0, score)  # Cap at 1.0

    def _categorize_risk_level(self, risk_score: float) -> str:
        """Categorize risk score into risk levels."""
        if risk_score >= 0.7:
            return "critical"
        elif risk_score >= 0.5:
            return "high"
        elif risk_score >= 0.3:
            return "medium"
        else:
            return "low"

    def _generate_risk_recommendations(
        self, risk_factors: Dict, risk_level: str
    ) -> List[str]:
        """Generate personalized recommendations based on risk factors."""
        recommendations = []

        # Grade-based recommendations
        current_grade = risk_factors.get("current_grade", 0)
        if current_grade < 70:
            recommendations.append(
                "Schedule a meeting with your instructor to discuss your current standing"
            )
            recommendations.append(
                "Consider seeking tutoring or academic support services"
            )

        # Missing assignments
        missing_count = risk_factors.get("missing_assignments_count", 0)
        if missing_count > 0:
            recommendations.append(
                f"Complete {missing_count} overdue assignment(s) as soon as possible"
            )
            recommendations.append(
                "Contact your instructor about late submission policies"
            )

        # Trend-based recommendations
        if risk_factors.get("grade_trend") == "declining":
            recommendations.append(
                "Review recent assignments to identify areas for improvement"
            )
            recommendations.append("Adjust your study strategies and time management")

        # Late submission pattern
        late_rate = risk_factors.get("late_submission_rate", 0)
        if late_rate > 0.3:
            recommendations.append("Improve time management and assignment planning")
            recommendations.append(
                "Set up assignment reminders and deadlines in your calendar"
            )

        # Category-specific recommendations
        struggling_categories = risk_factors.get("struggling_categories", [])
        if struggling_categories:
            recommendations.append(
                f"Focus extra attention on: {', '.join(struggling_categories)}"
            )

        # Performance variability
        variability = risk_factors.get("performance_variability", 0)
        if variability > 0.3:
            recommendations.append(
                "Work on consistency in your preparation and performance"
            )

        # Time pressure recommendations
        time_pressure = risk_factors.get("time_pressure", "none")
        if time_pressure == "high":
            recommendations.append(
                "Prioritize upcoming assignments and manage your time carefully"
            )

        # Default recommendations if no specific issues found
        if not recommendations:
            recommendations.append(
                "Continue your current study habits and stay consistent"
            )
            recommendations.append("Consider ways to further improve your performance")

        return recommendations

    def _calculate_intervention_priority(
        self, risk_score: float, course: Course
    ) -> int:
        """Calculate intervention priority (1-10 scale)."""
        priority = int(risk_score * 10)

        # Adjust based on course credits (more credits = higher priority)
        if course.credits and course.credits > 3:
            priority += 1

        # Adjust based on term progress
        current_time = datetime.utcnow()
        if course.term.end_date:
            days_remaining = (course.term.end_date - current_time).days
            if days_remaining < 30:  # Less than a month remaining
                priority += 1

        return min(10, max(1, priority))

    def _calculate_scenario(
        self,
        course: Course,
        remaining_assignments: List[Assignment],
        performance_level: float,
    ) -> Dict:
        """Calculate grade outcome for a specific performance scenario."""
        try:
            # Get current grade
            current_grade = self.grade_calculator.calculate_course_grade(course) or 0

            # Simulate scoring remaining assignments at the given performance level
            simulated_assignments = []
            for assignment in remaining_assignments:
                simulated_score = assignment.max_score * performance_level
                simulated_assignments.append(
                    {
                        "id": assignment.id,
                        "max_score": assignment.max_score,
                        "simulated_score": simulated_score,
                        "category_id": assignment.category_id,
                    }
                )

            # Calculate projected final grade
            projected_grade = self._simulate_final_grade(course, simulated_assignments)

            return {
                "performance_level": f"{performance_level * 100:.0f}%",
                "projected_final_grade": projected_grade,
                "grade_change": projected_grade - current_grade,
                "assignments_count": len(remaining_assignments),
                "total_points": sum(a.max_score for a in remaining_assignments),
            }

        except Exception as e:
            logger.error(f"Error calculating scenario: {str(e)}")
            return {
                "error": str(e),
                "performance_level": f"{performance_level * 100:.0f}%",
            }

    def _calculate_minimum_required(
        self,
        course: Course,
        remaining_assignments: List[Assignment],
        target_grade: float,
    ) -> Dict:
        """Calculate minimum performance needed on remaining assignments to achieve target grade."""
        try:
            current_grade = self.grade_calculator.calculate_course_grade(course) or 0

            if current_grade >= target_grade:
                return {
                    "target_grade": target_grade,
                    "required_performance": 0,
                    "message": "Target grade already achieved",
                    "feasible": True,
                }

            # Binary search to find minimum required performance
            low, high = 0.0, 1.0
            tolerance = 0.001
            projected = 0.0

            for _ in range(50):  # Maximum iterations
                mid = (low + high) / 2
                projected = self._simulate_final_grade(
                    course,
                    [
                        {
                            "id": a.id,
                            "max_score": a.max_score,
                            "simulated_score": a.max_score * mid,
                            "category_id": a.category_id,
                        }
                        for a in remaining_assignments
                    ],
                )

                if abs(projected - target_grade) < tolerance:
                    break
                elif projected < target_grade:
                    low = mid
                else:
                    high = mid

            required_performance = (low + high) / 2

            return {
                "target_grade": target_grade,
                "required_performance": f"{required_performance * 100:.1f}%",
                "projected_grade": projected,
                "feasible": required_performance <= 1.0,
                "difficulty": self._assess_feasibility(required_performance),
            }

        except Exception as e:
            logger.error(f"Error calculating minimum required: {str(e)}")
            return {"error": str(e), "target_grade": target_grade}

    def _calculate_target_scenarios(
        self, course: Course, remaining_assignments: List[Assignment]
    ) -> Dict:
        """Calculate performance needed for various target grades."""
        targets = [70, 75, 80, 85, 90, 95]
        scenarios = {}

        for target in targets:
            scenario = self._calculate_minimum_required(
                course, remaining_assignments, target
            )
            scenarios[f"target_{target}"] = scenario

        return scenarios

    def _simulate_final_grade(
        self, course: Course, simulated_assignments: List[Dict]
    ) -> float:
        """Simulate final grade with additional assignments."""
        # This would integrate with the existing grade calculator
        # For now, we'll implement a simplified version

        # Get current assignments
        current_assignments = Assignment.query.filter_by(course_id=course.id).all()

        if course.is_weighted:
            return self._simulate_weighted_grade(
                course, current_assignments, simulated_assignments
            )
        else:
            return self._simulate_unweighted_grade(
                current_assignments, simulated_assignments
            )

    def _simulate_weighted_grade(
        self,
        course: Course,
        current_assignments: List[Assignment],
        simulated_assignments: List[Dict],
    ) -> float:
        """Simulate weighted grade calculation."""
        category_grades = {}

        categories = list(course.grade_categories)  # Convert to list
        for category in categories:
            # Get current assignments in category
            cat_assignments = [
                a
                for a in current_assignments
                if a.category_id == category.id and a.score is not None
            ]

            # Add simulated assignments
            sim_cat_assignments = [
                a for a in simulated_assignments if a["category_id"] == category.id
            ]

            # Calculate category average
            total_points = sum(a.score for a in cat_assignments) + sum(
                a["simulated_score"] for a in sim_cat_assignments
            )
            total_possible = sum(a.max_score for a in cat_assignments) + sum(
                a["max_score"] for a in sim_cat_assignments
            )

            if total_possible > 0:
                category_grades[category.id] = {
                    "average": (total_points / total_possible) * 100,
                    "weight": category.weight,
                }

        # Calculate weighted average
        if category_grades:
            weighted_sum = sum(
                grade["average"] * grade["weight"] for grade in category_grades.values()
            )
            return weighted_sum

        return 0

    def _simulate_unweighted_grade(
        self, current_assignments: List[Assignment], simulated_assignments: List[Dict]
    ) -> float:
        """Simulate unweighted grade calculation."""
        # Get current points
        current_points = sum(
            a.score for a in current_assignments if a.score is not None
        )
        current_possible = sum(
            a.max_score for a in current_assignments if a.score is not None
        )

        # Add simulated points
        sim_points = sum(a["simulated_score"] for a in simulated_assignments)
        sim_possible = sum(a["max_score"] for a in simulated_assignments)

        total_points = current_points + sim_points
        total_possible = current_possible + sim_possible

        if total_possible > 0:
            return (total_points / total_possible) * 100

        return 0

    def _assess_feasibility(self, required_performance: float) -> str:
        """Assess the feasibility of required performance."""
        if required_performance <= 0.8:
            return "achievable"
        elif required_performance <= 0.9:
            return "challenging"
        elif required_performance <= 1.0:
            return "very_difficult"
        else:
            return "impossible"

    def _store_prediction(
        self, course_id: int, user_id: int, result: PredictionResult
    ) -> None:
        """Store prediction result in database."""
        try:
            prediction = GradePrediction(
                course_id=course_id,
                user_id=user_id,
                predicted_grade=result.predicted_grade,
                confidence_score=result.confidence,
                grade_range_min=result.grade_range[0],
                grade_range_max=result.grade_range[1],
                contributing_factors=result.contributing_factors,
                model_version=result.model_version,
            )

            db.session.add(prediction)
            db.session.commit()
            logger.info(f"Stored prediction for course {course_id}")

        except Exception as e:
            logger.error(f"Error storing prediction: {str(e)}")
            db.session.rollback()

    def _store_risk_assessment(
        self, course_id: int, user_id: int, result: RiskAssessmentResult
    ) -> None:
        """Store risk assessment result in database."""
        try:
            assessment = RiskAssessment(
                course_id=course_id,
                user_id=user_id,
                risk_level=result.risk_level,
                risk_score=result.risk_score,
                risk_factors=result.risk_factors,
                recommendations="\\n".join(result.recommendations),
                intervention_suggested=result.risk_level in ["high", "critical"],
            )

            db.session.add(assessment)
            db.session.commit()
            logger.info(f"Stored risk assessment for course {course_id}")

        except Exception as e:
            logger.error(f"Error storing risk assessment: {str(e)}")
            db.session.rollback()

    def _get_model_version(self) -> str:
        """Get current model version."""
        version = "1.0.0"
        if self.advanced_ml_enabled:
            version = "2.0.0-advanced"
        return version

    # Advanced ML Integration Methods

    def _predict_with_advanced_ml(
        self, course: Course, user_id: int
    ) -> Optional[PredictionResult]:
        """
        Generate prediction using advanced ML system with external data integration

        Args:
            course: Course object
            user_id: User ID for data collection

        Returns:
            PredictionResult with advanced ML prediction or None if insufficient data
        """
        try:
            # Get advanced ML system (lazy initialization)
            advanced_ml = self._get_advanced_ml()
            if advanced_ml is None:
                return None

            # Collect external data
            external_data = {}
            external_service = self._get_external_data_service()
            if external_service:
                try:
                    external_data = external_service.collect_all_data()
                except Exception as e:
                    logger.warning(f"Failed to collect external data: {str(e)}")
                    external_data = {}

            # Prepare feature data for advanced ML
            features = self._extract_course_features(course)

            # Convert to the format expected by advanced ML system
            feature_data = {
                "student_id": user_id,
                "course_id": course.id,
                "current_grade": features.get("current_grade", 0),
                "completion_rate": features.get("completion_rate", 0),
                "avg_performance": features.get("avg_performance", 0),
                "performance_variability": features.get("performance_variability", 0),
                "recent_trend": features.get("recent_trend", 0),
                "term_progress": features.get("term_progress", 0),
                "late_submission_rate": features.get("late_submission_rate", 0),
                "overdue_assignments": features.get("overdue_assignments", 0),
                "is_weighted": features.get("is_weighted", 0),
                "course_credits": features.get("course_credits", 3),
                "num_categories": features.get("num_categories", 0),
            }

            # Add external data features
            if external_data:
                feature_data.update(
                    {
                        "weather_comfort_index": external_data.get("weather", {}).get(
                            "comfort_index", 0.5
                        ),
                        "economic_stress_index": external_data.get("economic", {}).get(
                            "stress_index", 0.5
                        ),
                        "academic_stress_level": external_data.get(
                            "academic_calendar", {}
                        ).get("stress_level", 0.5),
                        "social_sentiment": external_data.get(
                            "social_sentiment", {}
                        ).get("sentiment_score", 0.5),
                    }
                )

            # Generate prediction using advanced ML
            prediction_result = advanced_ml.predict_grade(feature_data)

            if not prediction_result:
                return None

            # Generate explainable results
            explanation = None
            interpretability_engine = self._get_interpretability_engine()
            if interpretability_engine:
                try:
                    explanation = interpretability_engine.explain_prediction(
                        feature_data,
                        prediction_result["prediction"],
                        model_type="ensemble",
                    )
                except Exception as e:
                    logger.warning(f"Failed to generate explanation: {str(e)}")

            # Extract confidence and range from advanced ML result
            predicted_grade = prediction_result["prediction"]
            confidence = prediction_result.get("confidence", 0.8)
            uncertainty = prediction_result.get("uncertainty", 5.0)

            # Calculate grade range based on uncertainty
            grade_min = max(0, predicted_grade - uncertainty)
            grade_max = min(100, predicted_grade + uncertainty)

            # Combine traditional and advanced factors
            contributing_factors = {}
            if explanation and "feature_importance" in explanation:
                contributing_factors.update(explanation["feature_importance"])

            # Add traditional factors as backup
            traditional_factors = self._identify_contributing_factors(features)
            for key, value in traditional_factors.items():
                if key not in contributing_factors:
                    contributing_factors[key] = value

            return PredictionResult(
                predicted_grade=predicted_grade,
                confidence=confidence,
                grade_range=(grade_min, grade_max),
                contributing_factors=contributing_factors,
                model_version=self._get_model_version(),
                prediction_date=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Error in advanced ML prediction: {str(e)}")
            return None

    def generate_time_series_forecast(
        self, course_id: int, user_id: int, forecast_periods: int = 4
    ) -> Optional[Dict[str, Any]]:
        """
        Generate time series forecast for student performance trajectory

        Args:
            course_id: Course ID
            user_id: User ID
            forecast_periods: Number of periods to forecast ahead

        Returns:
            Dictionary with forecast results and trajectory analysis
        """
        try:
            # Get forecasting engine (lazy initialization)
            forecasting_engine = self._get_forecasting_engine()
            if forecasting_engine is None:
                return None

            # Get course and validate
            course = (
                Course.query.join(Term)
                .filter(Course.id == course_id, Term.user_id == user_id)
                .first()
            )

            if not course:
                return None

            # Prepare historical performance data
            assignments = (
                Assignment.query.filter_by(course_id=course_id)
                .order_by(Assignment.due_date)
                .all()
            )

            performance_data = []
            for assignment in assignments:
                if assignment.score is not None and assignment.due_date:
                    performance_data.append(
                        {
                            "timestamp": assignment.due_date,
                            "performance": assignment.score / assignment.max_score
                            if assignment.max_score > 0
                            else 0,
                            "assignment_type": assignment.category_id
                            if assignment.category_id
                            else "general",
                            "points": assignment.score,
                            "max_points": assignment.max_score,
                        }
                    )

            if len(performance_data) < 3:  # Need minimum data for forecasting
                return None

            # Generate forecast
            forecast_result = forecasting_engine.forecast_student_trajectory(
                student_id=user_id,
                historical_data=performance_data,
                forecast_periods=forecast_periods,
                course_context={
                    "course_id": course_id,
                    "is_weighted": course.is_weighted,
                },
            )

            return forecast_result

        except Exception as e:
            logger.error(f"Error generating time series forecast: {str(e)}")
            return None

    def get_model_explanations(
        self, course_id: int, user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed explanations for model predictions

        Args:
            course_id: Course ID
            user_id: User ID

        Returns:
            Dictionary with model explanations and insights
        """
        try:
            # Get interpretability service (lazy initialization)
            interpretability_engine = self._get_interpretability_engine()
            if interpretability_engine is None:
                return None

            # Get recent prediction for explanation
            recent_prediction = (
                GradePrediction.query.filter_by(course_id=course_id, user_id=user_id)
                .order_by(GradePrediction.created_at.desc())
                .first()
            )

            if not recent_prediction:
                # Generate a prediction first
                prediction_result = self.predict_final_grade(course_id, user_id)
                if not prediction_result:
                    return None

            # Get course features for explanation
            course = (
                Course.query.join(Term)
                .filter(Course.id == course_id, Term.user_id == user_id)
                .first()
            )

            if not course:
                return None

            features = self._extract_course_features(course)

            # Generate comprehensive explanation
            explanation = interpretability_engine.generate_comprehensive_explanation(
                features,
                recent_prediction.predicted_grade
                if recent_prediction
                else prediction_result.predicted_grade,
                model_type="ensemble",
            )

            return explanation

        except Exception as e:
            logger.error(f"Error generating model explanations: {str(e)}")
            return None

    def monitor_model_performance(
        self, course_id: int, user_id: int, actual_grade: float
    ) -> Dict[str, Any]:
        """
        Monitor model performance and detect drift

        Args:
            course_id: Course ID
            user_id: User ID
            actual_grade: Actual final grade for monitoring

        Returns:
            Dictionary with monitoring results
        """
        try:
            if not self.advanced_ml_enabled or not self.ml_monitoring:
                return {"status": "monitoring_not_available"}

            # Get course features for monitoring
            course = (
                Course.query.join(Term)
                .filter(Course.id == course_id, Term.user_id == user_id)
                .first()
            )

            if not course:
                return {"error": "course_not_found"}

            # Get recent prediction
            recent_prediction = (
                GradePrediction.query.filter_by(course_id=course_id, user_id=user_id)
                .order_by(GradePrediction.created_at.desc())
                .first()
            )

            if not recent_prediction:
                return {"error": "no_recent_prediction"}

            # Prepare features for monitoring
            features = self._extract_course_features(course)

            # Convert to DataFrame format expected by monitoring system
            import pandas as pd

            feature_df = pd.DataFrame([features])
            predictions = [recent_prediction.predicted_grade]
            actuals = [actual_grade]

            # Monitor the prediction batch
            monitoring_result = self.ml_monitoring.monitor_prediction_batch(
                model_id=f"grade_predictor_{course_id}",
                features=feature_df,
                predictions=predictions,
                actuals=actuals,
            )

            return monitoring_result

        except Exception as e:
            logger.error(f"Error monitoring model performance: {str(e)}")
            return {"error": str(e)}

    def run_ab_test_assignment(
        self,
        course_id: int,
        user_id: int,
        experiment_name: str = "grade_prediction_models",
    ) -> str:
        """
        Assign user to A/B test variant for model comparison

        Args:
            course_id: Course ID
            user_id: User ID
            experiment_name: Name of the A/B test experiment

        Returns:
            Variant ID assigned to the user
        """
        try:
            if not self.advanced_ml_enabled or not self.ab_testing:
                return "traditional_model"  # Default fallback

            # Create user attributes for segment-based assignment
            course = (
                Course.query.join(Term)
                .filter(Course.id == course_id, Term.user_id == user_id)
                .first()
            )

            user_attributes = {
                "user_id": user_id,
                "course_type": "weighted"
                if course and course.is_weighted
                else "unweighted",
                "term_id": course.term.id if course and course.term else None,
                "credits": course.credits if course else 3,
            }

            # Check if experiment exists, create if not
            if experiment_name not in self.ab_testing.experiments:
                # Create experiment with traditional vs advanced models
                variants = [
                    {
                        "id": "traditional_model",
                        "name": "Traditional Statistical Model",
                        "description": "Original grade prediction using statistical methods",
                        "model_config": {"type": "statistical"},
                        "traffic_allocation": 0.5,
                        "is_champion": True,
                    },
                    {
                        "id": "advanced_ml_model",
                        "name": "Advanced ML with External Data",
                        "description": "Ensemble ML models with external data integration",
                        "model_config": {"type": "advanced_ml"},
                        "traffic_allocation": 0.5,
                        "is_champion": False,
                    },
                ]

                self.ab_testing.create_experiment(
                    name=experiment_name,
                    description="Compare traditional vs advanced ML models for grade prediction",
                    variants=variants,
                    duration_days=30,
                    min_sample_size=100,
                    primary_metric="prediction_accuracy",
                )

                self.ab_testing.start_experiment(experiment_name)

            # Assign variant
            variant_id = self.ab_testing.assign_variant(
                experiment_name, str(user_id), user_attributes
            )

            return variant_id

        except Exception as e:
            logger.error(f"Error in A/B test assignment: {str(e)}")
            return "traditional_model"
