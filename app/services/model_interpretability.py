"""
Model Interpretability and Explainability for Academic ML
========================================================

This module provides comprehensive model interpretability and explainability including:
- SHAP (SHapley Additive exPlanations) values
- LIME (Local Interpretable Model-agnostic Explanations)
- Feature importance analysis and visualization
- Counterfactual explanations
- Decision tree approximation
- Natural language explanations
- Interactive explanation dashboards

Author: ML Interpretability Team
Date: 2024-12-20
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass, asdict
import json
import math
import warnings

warnings.filterwarnings("ignore")

# Core ML explainability libraries (with fallbacks)
try:
    import shap

    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False

try:
    import lime
    from lime import lime_tabular

    HAS_LIME = True
except ImportError:
    HAS_LIME = False

# Visualization libraries
try:
    import matplotlib.pyplot as plt
    import seaborn as sns

    HAS_VISUALIZATION = True
except ImportError:
    HAS_VISUALIZATION = False

# ML libraries for approximation models
try:
    from sklearn.tree import DecisionTreeRegressor, export_text
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

logger = logging.getLogger(__name__)


@dataclass
class FeatureContribution:
    """Individual feature contribution to a prediction."""

    feature_name: str
    feature_value: float
    contribution: float
    contribution_percentage: float
    importance_rank: int
    description: str


@dataclass
class ModelExplanation:
    """Comprehensive model explanation for a single prediction."""

    prediction_value: float
    base_value: float
    feature_contributions: List[FeatureContribution]
    explanation_method: str
    confidence_score: float
    natural_language_explanation: str
    counterfactual_scenarios: List[Dict[str, Any]]
    decision_path: List[str]
    uncertainty_factors: List[str]


@dataclass
class GlobalModelInsights:
    """Global insights about model behavior and patterns."""

    model_type: str
    feature_importance_ranking: List[Tuple[str, float]]
    interaction_effects: List[Dict[str, Any]]
    model_biases: List[Dict[str, Any]]
    performance_by_segment: Dict[str, float]
    common_prediction_patterns: List[str]
    model_limitations: List[str]
    recommended_improvements: List[str]


class ModelExplainer:
    """
    Comprehensive model interpretability and explainability system.
    """

    def __init__(self):
        self.explainers = {}
        self.feature_descriptions = {}
        self.explanation_cache = {}
        self.approximation_models = {}

        # Initialize feature descriptions
        self._initialize_feature_descriptions()

    def _initialize_feature_descriptions(self):
        """Initialize human-readable descriptions for features."""
        self.feature_descriptions = {
            "grade": "Current assignment grade",
            "grade_ma_3": "Average grade over last 3 assignments",
            "grade_ma_5": "Average grade over last 5 assignments",
            "grade_std_3": "Grade consistency (lower = more consistent)",
            "grade_trend": "Recent grade improvement trend",
            "assignment_weight": "Assignment weight in course grade",
            "is_major_assignment": "Whether this is a major assignment (exam/project)",
            "day_of_week": "Day of week when assignment was completed",
            "weather_comfort": "Weather comfort index (affects cognitive performance)",
            "economic_stress": "Economic stress level in environment",
            "academic_stress": "Academic calendar stress (midterms, finals)",
            "study_time": "Estimated study time spent on assignment",
            "consecutive_good": "Number of consecutive good grades",
            "completion_rate": "Recent assignment completion rate",
            "course_difficulty": "Course difficulty rating",
            "instructor_rating": "Instructor quality rating",
        }

    def explain_prediction(
        self,
        model: Any,
        X_instance: pd.DataFrame,
        X_background: Optional[pd.DataFrame] = None,
        model_type: str = "unknown",
        feature_names: Optional[List[str]] = None,
    ) -> ModelExplanation:
        """
        Generate comprehensive explanation for a single prediction.

        Args:
            model: Trained model to explain
            X_instance: Single instance to explain
            X_background: Background data for SHAP explanations
            model_type: Type of model for method selection
            feature_names: Names of features

        Returns:
            Comprehensive model explanation
        """
        try:
            logger.info(f"Generating explanation for {model_type} model")

            # Get prediction
            if hasattr(model, "predict"):
                prediction = model.predict(X_instance.values.reshape(1, -1))[0]
            else:
                prediction = 0.0

            feature_names = feature_names or list(X_instance.index)

            # Generate explanations using available methods
            feature_contributions = []
            explanation_method = "basic"
            base_value = 0.0
            confidence_score = 0.5

            # SHAP explanations (preferred)
            if HAS_SHAP and X_background is not None:
                try:
                    shap_explanation = self._generate_shap_explanation(
                        model, X_instance, X_background, feature_names
                    )
                    feature_contributions = shap_explanation["contributions"]
                    base_value = shap_explanation["base_value"]
                    explanation_method = "SHAP"
                    confidence_score = 0.9

                except Exception as e:
                    logger.warning(f"SHAP explanation failed: {str(e)}")

            # LIME explanations (fallback)
            if not feature_contributions and HAS_LIME:
                try:
                    lime_explanation = self._generate_lime_explanation(
                        model, X_instance, X_background, feature_names
                    )
                    feature_contributions = lime_explanation["contributions"]
                    explanation_method = "LIME"
                    confidence_score = 0.8

                except Exception as e:
                    logger.warning(f"LIME explanation failed: {str(e)}")

            # Feature importance fallback
            if not feature_contributions:
                feature_contributions = self._generate_feature_importance_explanation(
                    model, X_instance, feature_names
                )
                explanation_method = "feature_importance"
                confidence_score = 0.6

            # Generate natural language explanation
            nl_explanation = self._generate_natural_language_explanation(
                prediction, feature_contributions, model_type
            )

            # Generate counterfactual scenarios
            counterfactuals = self._generate_counterfactual_scenarios(
                model, X_instance, feature_names
            )

            # Generate decision path
            decision_path = self._generate_decision_path(
                prediction, feature_contributions
            )

            # Identify uncertainty factors
            uncertainty_factors = self._identify_uncertainty_factors(
                feature_contributions, X_instance, feature_names
            )

            return ModelExplanation(
                prediction_value=prediction,
                base_value=base_value,
                feature_contributions=feature_contributions,
                explanation_method=explanation_method,
                confidence_score=confidence_score,
                natural_language_explanation=nl_explanation,
                counterfactual_scenarios=counterfactuals,
                decision_path=decision_path,
                uncertainty_factors=uncertainty_factors,
            )

        except Exception as e:
            logger.error(f"Explanation generation failed: {str(e)}")
            return self._generate_fallback_explanation(X_instance, feature_names)

    def _generate_shap_explanation(
        self,
        model: Any,
        X_instance: pd.DataFrame,
        X_background: pd.DataFrame,
        feature_names: List[str],
    ) -> Dict[str, Any]:
        """Generate SHAP-based explanations."""

        # Select appropriate explainer based on model type
        if hasattr(model, "feature_importances_"):
            # Tree-based model
            explainer = shap.TreeExplainer(model)
        else:
            # Use KernelExplainer for other models
            explainer = shap.KernelExplainer(
                model.predict,
                X_background.values[:100],  # Sample for efficiency
            )

        # Generate SHAP values
        shap_values = explainer.shap_values(X_instance.values.reshape(1, -1))

        if isinstance(shap_values, list):
            shap_values = shap_values[0]  # For multi-output models

        # Convert to feature contributions
        contributions = []
        total_contribution = np.sum(np.abs(shap_values[0]))

        for i, (feature, value) in enumerate(zip(feature_names, X_instance.values)):
            contrib = shap_values[0][i]
            contrib_pct = (
                (abs(contrib) / total_contribution * 100)
                if total_contribution > 0
                else 0
            )

            contributions.append(
                FeatureContribution(
                    feature_name=feature,
                    feature_value=value,
                    contribution=contrib,
                    contribution_percentage=contrib_pct,
                    importance_rank=i + 1,
                    description=self.feature_descriptions.get(feature, feature),
                )
            )

        # Sort by absolute contribution
        contributions.sort(key=lambda x: abs(x.contribution), reverse=True)

        # Update ranks
        for i, contrib in enumerate(contributions):
            contrib.importance_rank = i + 1

        return {
            "contributions": contributions,
            "base_value": explainer.expected_value
            if hasattr(explainer, "expected_value")
            else 0.0,
        }

    def _generate_lime_explanation(
        self,
        model: Any,
        X_instance: pd.DataFrame,
        X_background: pd.DataFrame,
        feature_names: List[str],
    ) -> Dict[str, Any]:
        """Generate LIME-based explanations."""

        # Create LIME explainer
        explainer = lime_tabular.LimeTabularExplainer(
            X_background.values, feature_names=feature_names, mode="regression"
        )

        # Generate explanation
        explanation = explainer.explain_instance(
            X_instance.values, model.predict, num_features=len(feature_names)
        )

        # Convert to feature contributions
        contributions = []
        lime_list = explanation.as_list()

        for feature_name, contrib in lime_list:
            # Find feature value
            feature_idx = (
                feature_names.index(feature_name)
                if feature_name in feature_names
                else 0
            )
            feature_value = (
                X_instance.values[feature_idx]
                if feature_idx < len(X_instance.values)
                else 0
            )

            contributions.append(
                FeatureContribution(
                    feature_name=feature_name,
                    feature_value=feature_value,
                    contribution=contrib,
                    contribution_percentage=abs(contrib) * 10,  # Approximate percentage
                    importance_rank=0,  # Will be set later
                    description=self.feature_descriptions.get(
                        feature_name, feature_name
                    ),
                )
            )

        # Sort and rank
        contributions.sort(key=lambda x: abs(x.contribution), reverse=True)
        for i, contrib in enumerate(contributions):
            contrib.importance_rank = i + 1

        return {"contributions": contributions, "base_value": 0.0}

    def _generate_feature_importance_explanation(
        self, model: Any, X_instance: pd.DataFrame, feature_names: List[str]
    ) -> List[FeatureContribution]:
        """Generate explanation based on feature importance (fallback)."""

        contributions = []

        if hasattr(model, "feature_importances_"):
            # Use model's feature importance
            importances = model.feature_importances_
        elif hasattr(model, "coef_"):
            # Use coefficients for linear models
            importances = np.abs(model.coef_)
        else:
            # Equal importance fallback
            importances = np.ones(len(feature_names)) / len(feature_names)

        for i, (feature, value) in enumerate(zip(feature_names, X_instance.values)):
            importance = importances[i] if i < len(importances) else 0.1

            # Estimate contribution as importance * normalized feature value
            normalized_value = (value - 50) / 50  # Rough normalization
            contrib = importance * normalized_value * 10  # Scale factor

            contributions.append(
                FeatureContribution(
                    feature_name=feature,
                    feature_value=value,
                    contribution=contrib,
                    contribution_percentage=importance * 100,
                    importance_rank=i + 1,
                    description=self.feature_descriptions.get(feature, feature),
                )
            )

        # Sort by absolute contribution
        contributions.sort(key=lambda x: abs(x.contribution), reverse=True)

        # Update ranks
        for i, contrib in enumerate(contributions):
            contrib.importance_rank = i + 1

        return contributions

    def _generate_natural_language_explanation(
        self,
        prediction: float,
        contributions: List[FeatureContribution],
        model_type: str,
    ) -> str:
        """Generate human-readable explanation."""

        if not contributions:
            return f"The model predicts a grade of {prediction:.1f}%."

        # Get top positive and negative contributions
        positive_contribs = [c for c in contributions if c.contribution > 0][:3]
        negative_contribs = [c for c in contributions if c.contribution < 0][:3]

        explanation_parts = []

        # Overall prediction
        explanation_parts.append(f"The model predicts a grade of {prediction:.1f}%.")

        # Positive factors
        if positive_contribs:
            explanation_parts.append("Factors that help your grade:")
            for contrib in positive_contribs:
                factor_explanation = self._explain_feature_contribution(
                    contrib, "positive"
                )
                explanation_parts.append(f"• {factor_explanation}")

        # Negative factors
        if negative_contribs:
            explanation_parts.append("Factors that hurt your grade:")
            for contrib in negative_contribs:
                factor_explanation = self._explain_feature_contribution(
                    contrib, "negative"
                )
                explanation_parts.append(f"• {factor_explanation}")

        # Top factor insight
        if contributions:
            top_factor = contributions[0]
            impact_direction = (
                "positively" if top_factor.contribution > 0 else "negatively"
            )
            explanation_parts.append(
                f"The most important factor is {top_factor.description}, "
                f"which impacts your grade {impact_direction}."
            )

        return " ".join(explanation_parts)

    def _explain_feature_contribution(
        self, contrib: FeatureContribution, direction: str
    ) -> str:
        """Generate natural language explanation for a single feature."""

        feature = contrib.feature_name
        value = contrib.feature_value

        explanations = {
            "grade_ma_3": {
                "positive": f"Your recent average grade of {value:.1f}% is strong",
                "negative": f"Your recent average grade of {value:.1f}% needs improvement",
            },
            "grade_trend": {
                "positive": f"Your grades are trending upward ({value:.1f} point improvement)",
                "negative": f"Your grades are trending downward ({abs(value):.1f} point decline)",
            },
            "consecutive_good": {
                "positive": f"You have {int(value)} consecutive good grades",
                "negative": f"Recent inconsistent performance affects prediction",
            },
            "weather_comfort": {
                "positive": f"Favorable study conditions (weather comfort: {value:.1f})",
                "negative": f"Challenging study conditions (weather comfort: {value:.1f})",
            },
            "study_time": {
                "positive": f"Adequate study time invested ({value:.1f} hours)",
                "negative": f"Insufficient study time ({value:.1f} hours)",
            },
            "assignment_weight": {
                "positive": f"This important assignment (weight: {value:.1f}) helps your grade",
                "negative": f"This important assignment (weight: {value:.1f}) hurts your grade",
            },
            "course_difficulty": {
                "positive": f"Course difficulty level ({value:.1f}) is manageable for you",
                "negative": f"Course difficulty level ({value:.1f}) is challenging for you",
            },
        }

        if feature in explanations and direction in explanations[feature]:
            return explanations[feature][direction]
        else:
            return f"{contrib.description} (value: {value:.1f}) {direction}ly affects your grade"

    def _generate_counterfactual_scenarios(
        self, model: Any, X_instance: pd.DataFrame, feature_names: List[str]
    ) -> List[Dict[str, Any]]:
        """Generate counterfactual 'what-if' scenarios."""

        counterfactuals = []

        try:
            # Get baseline prediction
            baseline_pred = model.predict(X_instance.values.reshape(1, -1))[0]

            # Test key feature changes
            scenarios = [
                {
                    "name": "Improved Study Habits",
                    "changes": {"study_time": +2.0, "grade_trend": +3.0},
                },
                {
                    "name": "Better Time Management",
                    "changes": {"completion_rate": +0.2, "consecutive_good": +1.0},
                },
                {
                    "name": "Consistent Performance",
                    "changes": {"grade_std_3": -5.0, "grade_ma_3": +5.0},
                },
                {
                    "name": "Optimal Conditions",
                    "changes": {"weather_comfort": 0.9, "academic_stress": 0.2},
                },
            ]

            for scenario in scenarios:
                modified_instance = X_instance.copy()
                changes_made = []

                for feature, change in scenario["changes"].items():
                    if feature in feature_names:
                        idx = feature_names.index(feature)
                        old_value = modified_instance.iloc[idx]

                        if feature.endswith("_rate"):
                            # For rate features, add change
                            new_value = min(1.0, max(0.0, old_value + change))
                        elif "comfort" in feature:
                            # For comfort features, set to value
                            new_value = change
                        else:
                            # For other features, add change
                            new_value = old_value + change

                        modified_instance.iloc[idx] = new_value
                        changes_made.append(
                            {
                                "feature": feature,
                                "old_value": old_value,
                                "new_value": new_value,
                                "change": new_value - old_value,
                            }
                        )

                # Get new prediction
                new_pred = model.predict(modified_instance.values.reshape(1, -1))[0]
                grade_improvement = new_pred - baseline_pred

                counterfactuals.append(
                    {
                        "scenario_name": scenario["name"],
                        "baseline_grade": baseline_pred,
                        "predicted_grade": new_pred,
                        "grade_improvement": grade_improvement,
                        "changes": changes_made,
                        "feasibility": "high"
                        if abs(grade_improvement) < 15
                        else "medium",
                        "recommendation": f"Could improve grade by {grade_improvement:.1f} points",
                    }
                )

        except Exception as e:
            logger.warning(f"Counterfactual generation failed: {str(e)}")

        return counterfactuals

    def _generate_decision_path(
        self, prediction: float, contributions: List[FeatureContribution]
    ) -> List[str]:
        """Generate step-by-step decision path."""

        path = []

        try:
            # Start with base assessment
            path.append("Starting from baseline academic performance expectations...")

            # Process top contributions
            for i, contrib in enumerate(contributions[:5]):
                if abs(contrib.contribution) > 0.5:  # Significant contribution
                    direction = "increases" if contrib.contribution > 0 else "decreases"
                    impact = (
                        "significantly"
                        if abs(contrib.contribution) > 2
                        else "moderately"
                    )

                    path.append(
                        f"{i + 1}. {contrib.description} (value: {contrib.feature_value:.1f}) "
                        f"{impact} {direction} the predicted grade"
                    )

            # Final prediction
            if prediction >= 90:
                path.append(
                    f"Final prediction: Excellent performance ({prediction:.1f}%)"
                )
            elif prediction >= 80:
                path.append(f"Final prediction: Good performance ({prediction:.1f}%)")
            elif prediction >= 70:
                path.append(
                    f"Final prediction: Satisfactory performance ({prediction:.1f}%)"
                )
            else:
                path.append(
                    f"Final prediction: Performance needs improvement ({prediction:.1f}%)"
                )

        except Exception as e:
            logger.warning(f"Decision path generation failed: {str(e)}")
            path.append(f"Model predicts grade of {prediction:.1f}%")

        return path

    def _identify_uncertainty_factors(
        self,
        contributions: List[FeatureContribution],
        X_instance: pd.DataFrame,
        feature_names: List[str],
    ) -> List[str]:
        """Identify factors that contribute to prediction uncertainty."""

        uncertainty_factors = []

        try:
            # Check for conflicting signals
            positive_contribs = [c for c in contributions if c.contribution > 0]
            negative_contribs = [c for c in contributions if c.contribution < 0]

            if positive_contribs and negative_contribs:
                pos_sum = sum(c.contribution for c in positive_contribs)
                neg_sum = sum(abs(c.contribution) for c in negative_contribs)

                if abs(pos_sum - neg_sum) < 1.0:
                    uncertainty_factors.append(
                        "Mixed positive and negative signals create uncertainty"
                    )

            # Check for missing data indicators
            if any(pd.isna(X_instance.values)):
                uncertainty_factors.append("Missing data reduces prediction confidence")

            # Check for extreme values
            for i, value in enumerate(X_instance.values):
                feature_name = (
                    feature_names[i] if i < len(feature_names) else f"feature_{i}"
                )

                if feature_name in ["grade", "grade_ma_3", "grade_ma_5"]:
                    if value < 20 or value > 100:
                        uncertainty_factors.append(
                            f"Unusual {feature_name} value affects confidence"
                        )
                elif "time" in feature_name.lower():
                    if value < 0 or value > 20:  # Study time range
                        uncertainty_factors.append(
                            f"Unusual study time value affects confidence"
                        )

            # Check for low-importance features dominating
            if contributions:
                top_contrib = contributions[0]
                if top_contrib.contribution_percentage < 20:
                    uncertainty_factors.append(
                        "No single factor strongly dominates the prediction"
                    )

            # Add default if no specific factors found
            if not uncertainty_factors:
                uncertainty_factors.append("Standard prediction uncertainty applies")

        except Exception as e:
            logger.warning(f"Uncertainty factor identification failed: {str(e)}")
            uncertainty_factors.append("Unable to assess prediction uncertainty")

        return uncertainty_factors

    def _generate_fallback_explanation(
        self, X_instance: pd.DataFrame, feature_names: Optional[List[str]]
    ) -> ModelExplanation:
        """Generate basic fallback explanation when advanced methods fail."""

        feature_names = feature_names or [
            f"feature_{i}" for i in range(len(X_instance))
        ]

        # Simple feature contributions based on values
        contributions = []
        for i, value in enumerate(X_instance.values):
            feature_name = feature_names[i]

            # Estimate contribution based on feature value
            if "grade" in feature_name.lower():
                contrib = (value - 75) / 10  # Normalize around 75%
            elif "time" in feature_name.lower():
                contrib = (value - 5) / 5  # Normalize around 5 hours
            else:
                contrib = (value - 0.5) * 2  # Generic normalization

            contributions.append(
                FeatureContribution(
                    feature_name=feature_name,
                    feature_value=value,
                    contribution=contrib,
                    contribution_percentage=abs(contrib) * 10,
                    importance_rank=i + 1,
                    description=self.feature_descriptions.get(
                        feature_name, feature_name
                    ),
                )
            )

        # Estimate prediction
        avg_grade = np.mean(
            [
                c.feature_value
                for c in contributions
                if "grade" in c.feature_name.lower()
            ]
            or [75.0]
        )

        return ModelExplanation(
            prediction_value=avg_grade,
            base_value=75.0,
            feature_contributions=contributions,
            explanation_method="fallback",
            confidence_score=0.3,
            natural_language_explanation=f"Basic prediction of {avg_grade:.1f}% based on available data.",
            counterfactual_scenarios=[],
            decision_path=[f"Estimated grade: {avg_grade:.1f}%"],
            uncertainty_factors=[
                "Limited explanation method - install SHAP/LIME for better insights"
            ],
        )

    def generate_global_insights(
        self,
        model: Any,
        X_data: pd.DataFrame,
        y_data: pd.Series,
        feature_names: List[str],
    ) -> GlobalModelInsights:
        """Generate global insights about model behavior."""

        try:
            logger.info("Generating global model insights")

            # Feature importance ranking
            if hasattr(model, "feature_importances_"):
                importance_pairs = list(zip(feature_names, model.feature_importances_))
            elif hasattr(model, "coef_"):
                importance_pairs = list(zip(feature_names, np.abs(model.coef_)))
            else:
                importance_pairs = [(name, 0.1) for name in feature_names]

            importance_pairs.sort(key=lambda x: x[1], reverse=True)

            # Interaction effects (simplified analysis)
            interactions = self._analyze_feature_interactions(
                X_data, y_data, feature_names
            )

            # Model biases
            biases = self._detect_model_biases(model, X_data, y_data, feature_names)

            # Performance by segments
            performance_segments = self._analyze_performance_segments(
                model, X_data, y_data, feature_names
            )

            # Common patterns
            patterns = self._identify_prediction_patterns(model, X_data, feature_names)

            # Model limitations
            limitations = self._identify_model_limitations(model, X_data, y_data)

            # Improvement recommendations
            recommendations = self._generate_improvement_recommendations(
                importance_pairs, interactions, biases
            )

            return GlobalModelInsights(
                model_type=type(model).__name__,
                feature_importance_ranking=importance_pairs,
                interaction_effects=interactions,
                model_biases=biases,
                performance_by_segment=performance_segments,
                common_prediction_patterns=patterns,
                model_limitations=limitations,
                recommended_improvements=recommendations,
            )

        except Exception as e:
            logger.error(f"Global insights generation failed: {str(e)}")
            return GlobalModelInsights(
                model_type="unknown",
                feature_importance_ranking=[],
                interaction_effects=[],
                model_biases=[],
                performance_by_segment={},
                common_prediction_patterns=[],
                model_limitations=["Unable to analyze model behavior"],
                recommended_improvements=[
                    "Ensure model and data are properly formatted"
                ],
            )

    def _analyze_feature_interactions(
        self, X_data: pd.DataFrame, y_data: pd.Series, feature_names: List[str]
    ) -> List[Dict[str, Any]]:
        """Analyze interactions between features."""

        interactions = []

        try:
            if len(feature_names) < 2:
                return interactions

            # Analyze correlations between top features
            correlation_matrix = X_data.corr()

            for i in range(min(5, len(feature_names))):
                for j in range(i + 1, min(5, len(feature_names))):
                    feature_i = feature_names[i]
                    feature_j = feature_names[j]

                    correlation = correlation_matrix.loc[feature_i, feature_j]

                    if abs(correlation) > 0.3:  # Significant correlation
                        interactions.append(
                            {
                                "feature_1": feature_i,
                                "feature_2": feature_j,
                                "interaction_type": "correlation",
                                "strength": abs(correlation),
                                "description": f"{feature_i} and {feature_j} are {'positively' if correlation > 0 else 'negatively'} correlated",
                            }
                        )

        except Exception as e:
            logger.warning(f"Interaction analysis failed: {str(e)}")

        return interactions

    def _detect_model_biases(
        self,
        model: Any,
        X_data: pd.DataFrame,
        y_data: pd.Series,
        feature_names: List[str],
    ) -> List[Dict[str, Any]]:
        """Detect potential biases in model behavior."""

        biases = []

        try:
            # Make predictions
            predictions = model.predict(X_data.values)

            # Check for systematic over/under-prediction
            residuals = y_data.values - predictions
            mean_residual = np.mean(residuals)

            if abs(mean_residual) > 2.0:
                bias_type = (
                    "over-prediction" if mean_residual < 0 else "under-prediction"
                )
                biases.append(
                    {
                        "bias_type": "systematic_prediction",
                        "description": f"Model shows systematic {bias_type} by {abs(mean_residual):.1f} points",
                        "severity": "high" if abs(mean_residual) > 5 else "moderate",
                    }
                )

            # Check for prediction range bias
            pred_range = np.max(predictions) - np.min(predictions)
            actual_range = np.max(y_data) - np.min(y_data)

            if pred_range < actual_range * 0.7:
                biases.append(
                    {
                        "bias_type": "range_compression",
                        "description": "Model compresses prediction range compared to actual grades",
                        "severity": "moderate",
                    }
                )

        except Exception as e:
            logger.warning(f"Bias detection failed: {str(e)}")

        return biases

    def _analyze_performance_segments(
        self,
        model: Any,
        X_data: pd.DataFrame,
        y_data: pd.Series,
        feature_names: List[str],
    ) -> Dict[str, float]:
        """Analyze model performance across different segments."""

        segments = {}

        try:
            predictions = model.predict(X_data.values)

            # Performance by grade ranges
            high_performers = y_data >= 80
            medium_performers = (y_data >= 60) & (y_data < 80)
            low_performers = y_data < 60

            from sklearn.metrics import mean_absolute_error

            if high_performers.any():
                segments["high_performers"] = mean_absolute_error(
                    y_data[high_performers], predictions[high_performers]
                )

            if medium_performers.any():
                segments["medium_performers"] = mean_absolute_error(
                    y_data[medium_performers], predictions[medium_performers]
                )

            if low_performers.any():
                segments["low_performers"] = mean_absolute_error(
                    y_data[low_performers], predictions[low_performers]
                )

        except Exception as e:
            logger.warning(f"Performance segment analysis failed: {str(e)}")

        return segments

    def _identify_prediction_patterns(
        self, model: Any, X_data: pd.DataFrame, feature_names: List[str]
    ) -> List[str]:
        """Identify common patterns in model predictions."""

        patterns = []

        try:
            predictions = model.predict(X_data.values)

            # Check prediction distribution
            pred_std = np.std(predictions)
            pred_mean = np.mean(predictions)

            if pred_std < 5:
                patterns.append(
                    "Model predictions have low variance - may be under-confident"
                )

            if pred_mean > 80:
                patterns.append("Model tends to predict high grades")
            elif pred_mean < 60:
                patterns.append("Model tends to predict low grades")
            else:
                patterns.append(
                    "Model predictions are well-centered around average grades"
                )

            # Check for clustering
            grade_ranges = {
                "A_range": np.sum((predictions >= 90) & (predictions <= 100)),
                "B_range": np.sum((predictions >= 80) & (predictions < 90)),
                "C_range": np.sum((predictions >= 70) & (predictions < 80)),
                "D_range": np.sum((predictions >= 60) & (predictions < 70)),
                "F_range": np.sum(predictions < 60),
            }

            max_range = max(grade_ranges.values())
            if max_range > len(predictions) * 0.5:
                dominant_range = max(grade_ranges.items(), key=lambda x: x[1])[0]
                patterns.append(
                    f"Most predictions fall in {dominant_range.replace('_', ' ')}"
                )

        except Exception as e:
            logger.warning(f"Pattern identification failed: {str(e)}")

        return patterns

    def _identify_model_limitations(
        self, model: Any, X_data: pd.DataFrame, y_data: pd.Series
    ) -> List[str]:
        """Identify model limitations and areas for improvement."""

        limitations = []

        try:
            # Data size limitations
            if len(X_data) < 100:
                limitations.append("Limited training data may affect model reliability")

            # Feature limitations
            if X_data.shape[1] < 5:
                limitations.append("Limited features may miss important factors")

            # Check for overfitting indicators
            if hasattr(model, "score"):
                try:
                    train_score = model.score(X_data.values, y_data.values)
                    if train_score > 0.98:
                        limitations.append(
                            "High training accuracy may indicate overfitting"
                        )
                except:
                    pass

            # Check data quality
            if X_data.isnull().any().any():
                limitations.append("Missing data in features may affect predictions")

            # Prediction range check
            predictions = model.predict(X_data.values)
            if np.min(predictions) < 0 or np.max(predictions) > 100:
                limitations.append("Model produces grades outside realistic range")

        except Exception as e:
            logger.warning(f"Limitation identification failed: {str(e)}")

        return limitations

    def _generate_improvement_recommendations(
        self,
        importance_ranking: List[Tuple[str, float]],
        interactions: List[Dict[str, Any]],
        biases: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate recommendations for model improvement."""

        recommendations = []

        try:
            # Feature-based recommendations
            if importance_ranking:
                top_feature = importance_ranking[0][0]
                recommendations.append(
                    f"Focus on improving data quality for {top_feature} (most important feature)"
                )

                if len(importance_ranking) > 3:
                    low_importance = [
                        name for name, imp in importance_ranking[5:] if imp < 0.05
                    ]
                    if low_importance:
                        recommendations.append(
                            f"Consider removing low-importance features: {', '.join(low_importance[:3])}"
                        )

            # Interaction-based recommendations
            if interactions:
                recommendations.append(
                    "Consider adding interaction terms between correlated features"
                )

            # Bias-based recommendations
            for bias in biases:
                if bias["bias_type"] == "systematic_prediction":
                    recommendations.append(
                        "Consider calibrating model predictions to reduce systematic bias"
                    )
                elif bias["bias_type"] == "range_compression":
                    recommendations.append(
                        "Consider using ensemble methods to improve prediction range"
                    )

            # General recommendations
            recommendations.append(
                "Collect more diverse training data to improve model robustness"
            )
            recommendations.append(
                "Implement cross-validation to better assess model performance"
            )

        except Exception as e:
            logger.warning(f"Recommendation generation failed: {str(e)}")

        return recommendations


# Global explainer instance
model_explainer = ModelExplainer()
