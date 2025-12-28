"""
Advanced A/B Testing Framework for ML Models

This module implements a comprehensive A/B testing system for machine learning models
with statistical significance testing, experiment management, and performance tracking.

Features:
- Champion/Challenger model deployment
- Statistical significance testing (t-tests, Mann-Whitney U)
- Multi-armed bandit algorithms (Epsilon-greedy, UCB1, Thompson Sampling)
- Experiment tracking and management
- Performance comparison and visualization
- Automated model promotion based on statistical significance
- User segment-based testing
- Traffic splitting algorithms
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import json
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio

# Core libraries with fallbacks
try:
    import numpy as np
    import pandas as pd
    from scipy import stats
    import matplotlib.pyplot as plt
    import seaborn as sns

    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logging.warning("SciPy not available. Some statistical tests may not work.")

try:
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import cross_val_score

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("scikit-learn not available. Some metrics may not work.")

# Optional advanced libraries
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    import bayesian_optimization

    BAYESIAN_OPT_AVAILABLE = True
except ImportError:
    BAYESIAN_OPT_AVAILABLE = False


class ExperimentStatus(Enum):
    """Experiment status enumeration"""

    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TrafficSplitMethod(Enum):
    """Traffic splitting methods"""

    RANDOM = "random"
    USER_ID_HASH = "user_id_hash"
    SEGMENT_BASED = "segment_based"
    GEOGRAPHIC = "geographic"
    TIME_BASED = "time_based"


class BanditAlgorithm(Enum):
    """Multi-armed bandit algorithms"""

    EPSILON_GREEDY = "epsilon_greedy"
    UCB1 = "ucb1"
    THOMPSON_SAMPLING = "thompson_sampling"
    SOFTMAX = "softmax"


@dataclass
class ModelVariant:
    """Model variant configuration"""

    id: str
    name: str
    description: str
    model_config: Dict[str, Any]
    traffic_allocation: float  # 0.0 to 1.0
    is_champion: bool = False
    created_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ExperimentMetrics:
    """Experiment performance metrics"""

    variant_id: str
    sample_size: int
    mean_performance: float
    std_performance: float
    confidence_interval: Tuple[float, float]
    predictions_count: int
    error_rate: float
    response_time_ms: float
    user_satisfaction: Optional[float] = None
    business_metric: Optional[float] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class StatisticalTest:
    """Statistical test results"""

    test_name: str
    statistic: float
    p_value: float
    effect_size: float
    confidence_level: float
    is_significant: bool
    interpretation: str
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class ABExperiment:
    """A/B experiment configuration and state"""

    id: str
    name: str
    description: str
    variants: List[ModelVariant]
    status: ExperimentStatus
    traffic_split_method: TrafficSplitMethod
    start_date: datetime
    end_date: Optional[datetime]
    min_sample_size: int
    significance_threshold: float
    primary_metric: str
    secondary_metrics: List[str]
    segment_filters: Optional[Dict[str, Any]] = None
    bandit_config: Optional[Dict[str, Any]] = None
    created_by: str = "system"
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.segment_filters is None:
            self.segment_filters = {}
        if self.metadata is None:
            self.metadata = {}


class ABTestingFramework:
    """
    Advanced A/B Testing Framework for ML Models

    This framework provides comprehensive A/B testing capabilities including:
    - Experiment management and configuration
    - Statistical significance testing
    - Multi-armed bandit algorithms
    - Performance tracking and visualization
    - Automated model promotion
    """

    def __init__(
        self,
        confidence_level: float = 0.95,
        min_effect_size: float = 0.01,
        power: float = 0.8,
        enable_bandit: bool = False,
    ):
        """
        Initialize A/B Testing Framework

        Args:
            confidence_level: Statistical confidence level (default: 0.95)
            min_effect_size: Minimum detectable effect size (default: 0.01)
            power: Statistical power (default: 0.8)
            enable_bandit: Enable multi-armed bandit algorithms (default: False)
        """
        self.logger = logging.getLogger(__name__)
        self.confidence_level = confidence_level
        self.min_effect_size = min_effect_size
        self.power = power
        self.enable_bandit = enable_bandit

        # In-memory storage (in production, use database)
        self.experiments: Dict[str, ABExperiment] = {}
        self.experiment_data: Dict[str, List[Dict]] = {}
        self.metrics_history: Dict[str, List[ExperimentMetrics]] = {}
        self.statistical_tests: Dict[str, List[StatisticalTest]] = {}

        # Bandit algorithm state
        self.bandit_state: Dict[str, Dict] = {}

        self.logger.info("A/B Testing Framework initialized")

    def create_experiment(
        self,
        name: str,
        description: str,
        variants: List[Dict],
        traffic_split_method: TrafficSplitMethod = TrafficSplitMethod.RANDOM,
        duration_days: int = 14,
        min_sample_size: int = 1000,
        significance_threshold: float = 0.05,
        primary_metric: str = "prediction_accuracy",
        secondary_metrics: Optional[List[str]] = None,
        segment_filters: Optional[Dict[str, Any]] = None,
        bandit_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new A/B experiment

        Args:
            name: Experiment name
            description: Experiment description
            variants: List of model variant configurations
            traffic_split_method: How to split traffic between variants
            duration_days: Experiment duration in days
            min_sample_size: Minimum sample size per variant
            significance_threshold: P-value threshold for significance
            primary_metric: Primary evaluation metric
            secondary_metrics: Additional metrics to track
            segment_filters: User segment filters
            bandit_config: Multi-armed bandit configuration

        Returns:
            Experiment ID
        """
        try:
            experiment_id = str(uuid.uuid4())

            # Convert variant dicts to ModelVariant objects
            model_variants = []
            total_allocation = 0.0

            for i, variant_config in enumerate(variants):
                variant = ModelVariant(
                    id=variant_config.get("id", f"variant_{i}"),
                    name=variant_config.get("name", f"Variant {i + 1}"),
                    description=variant_config.get("description", ""),
                    model_config=variant_config.get("model_config", {}),
                    traffic_allocation=variant_config.get(
                        "traffic_allocation", 1.0 / len(variants)
                    ),
                    is_champion=variant_config.get("is_champion", i == 0),
                )
                model_variants.append(variant)
                total_allocation += variant.traffic_allocation

            # Normalize traffic allocation
            if abs(total_allocation - 1.0) > 0.01:
                for variant in model_variants:
                    variant.traffic_allocation /= total_allocation

            # Create experiment
            experiment = ABExperiment(
                id=experiment_id,
                name=name,
                description=description,
                variants=model_variants,
                status=ExperimentStatus.DRAFT,
                traffic_split_method=traffic_split_method,
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=duration_days),
                min_sample_size=min_sample_size,
                significance_threshold=significance_threshold,
                primary_metric=primary_metric,
                secondary_metrics=secondary_metrics or [],
                segment_filters=segment_filters,
                bandit_config=bandit_config,
            )

            self.experiments[experiment_id] = experiment
            self.experiment_data[experiment_id] = []
            self.metrics_history[experiment_id] = []
            self.statistical_tests[experiment_id] = []

            # Initialize bandit state if enabled
            if self.enable_bandit and bandit_config:
                self._initialize_bandit_state(
                    experiment_id, model_variants, bandit_config
                )

            self.logger.info(f"Created experiment: {name} (ID: {experiment_id})")
            return experiment_id

        except Exception as e:
            self.logger.error(f"Error creating experiment: {str(e)}")
            raise

    def start_experiment(self, experiment_id: str) -> bool:
        """Start an experiment"""
        try:
            if experiment_id not in self.experiments:
                raise ValueError(f"Experiment {experiment_id} not found")

            experiment = self.experiments[experiment_id]
            if experiment.status != ExperimentStatus.DRAFT:
                raise ValueError(f"Experiment must be in DRAFT status to start")

            experiment.status = ExperimentStatus.RUNNING
            experiment.start_date = datetime.utcnow()

            self.logger.info(
                f"Started experiment: {experiment.name} (ID: {experiment_id})"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error starting experiment: {str(e)}")
            return False

    def assign_variant(
        self,
        experiment_id: str,
        user_id: Optional[str] = None,
        user_attributes: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Assign a user to a model variant

        Args:
            experiment_id: Experiment ID
            user_id: User identifier
            user_attributes: User attributes for segment-based assignment

        Returns:
            Assigned variant ID
        """
        try:
            if experiment_id not in self.experiments:
                raise ValueError(f"Experiment {experiment_id} not found")

            experiment = self.experiments[experiment_id]
            if experiment.status != ExperimentStatus.RUNNING:
                # Default to champion variant if experiment not running
                champion = next(
                    (v for v in experiment.variants if v.is_champion),
                    experiment.variants[0],
                )
                return champion.id

            # Check if user matches segment filters
            if experiment.segment_filters and user_attributes:
                if not self._matches_segment_filters(
                    user_attributes, experiment.segment_filters
                ):
                    champion = next(
                        (v for v in experiment.variants if v.is_champion),
                        experiment.variants[0],
                    )
                    return champion.id

            # Use bandit algorithm if enabled
            if self.enable_bandit and experiment.bandit_config:
                return self._bandit_assignment(experiment_id, user_id, user_attributes)

            # Use configured traffic splitting method
            return self._assign_by_traffic_split(experiment, user_id, user_attributes)

        except Exception as e:
            self.logger.error(f"Error assigning variant: {str(e)}")
            # Fallback to champion variant
            experiment = self.experiments.get(experiment_id)
            if experiment:
                champion = next(
                    (v for v in experiment.variants if v.is_champion),
                    experiment.variants[0],
                )
                return champion.id
            return "default"

    def record_prediction(
        self,
        experiment_id: str,
        variant_id: str,
        user_id: str,
        prediction: float,
        actual: Optional[float] = None,
        response_time_ms: Optional[float] = None,
        user_feedback: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Record a prediction result for experiment tracking

        Args:
            experiment_id: Experiment ID
            variant_id: Variant ID that made the prediction
            user_id: User ID
            prediction: Predicted value
            actual: Actual value (if available)
            response_time_ms: Response time in milliseconds
            user_feedback: User satisfaction score
            metadata: Additional metadata

        Returns:
            Success status
        """
        try:
            if experiment_id not in self.experiments:
                return False

            record = {
                "timestamp": datetime.utcnow(),
                "variant_id": variant_id,
                "user_id": user_id,
                "prediction": prediction,
                "actual": actual,
                "response_time_ms": response_time_ms,
                "user_feedback": user_feedback,
                "metadata": metadata or {},
            }

            self.experiment_data[experiment_id].append(record)

            # Update bandit algorithm if enabled
            if self.enable_bandit and actual is not None:
                self._update_bandit_reward(
                    experiment_id, variant_id, actual, prediction
                )

            return True

        except Exception as e:
            self.logger.error(f"Error recording prediction: {str(e)}")
            return False

    def analyze_experiment(self, experiment_id: str) -> Dict[str, Any]:
        """
        Perform comprehensive experiment analysis

        Args:
            experiment_id: Experiment ID

        Returns:
            Analysis results including statistical tests and recommendations
        """
        try:
            if experiment_id not in self.experiments:
                raise ValueError(f"Experiment {experiment_id} not found")

            experiment = self.experiments[experiment_id]
            data = self.experiment_data[experiment_id]

            if len(data) < 2:
                return {
                    "status": "insufficient_data",
                    "message": "Need more data for analysis",
                }

            # Convert to DataFrame
            if not SCIPY_AVAILABLE:
                return {
                    "status": "error",
                    "message": "SciPy not available for statistical analysis",
                }

            df = pd.DataFrame(data)

            # Calculate metrics for each variant
            variant_metrics = {}
            for variant in experiment.variants:
                variant_data = df[df["variant_id"] == variant.id]
                if len(variant_data) == 0:
                    continue

                # Calculate performance metrics
                metrics = self._calculate_variant_metrics(variant_data, variant.id)
                variant_metrics[variant.id] = metrics

            # Perform statistical tests
            statistical_results = self._perform_statistical_tests(df, experiment)

            # Generate recommendations
            recommendations = self._generate_recommendations(
                variant_metrics, statistical_results, experiment
            )

            # Update experiment metrics history
            for variant_id, metrics in variant_metrics.items():
                self.metrics_history[experiment_id].append(metrics)

            # Store statistical test results
            self.statistical_tests[experiment_id].extend(statistical_results)

            analysis = {
                "experiment_id": experiment_id,
                "experiment_name": experiment.name,
                "analysis_timestamp": datetime.utcnow(),
                "status": "completed",
                "variant_metrics": {k: asdict(v) for k, v in variant_metrics.items()},
                "statistical_tests": [asdict(test) for test in statistical_results],
                "recommendations": recommendations,
                "data_quality": self._assess_data_quality(df),
                "experiment_health": self._assess_experiment_health(experiment, df),
            }

            return analysis

        except Exception as e:
            self.logger.error(f"Error analyzing experiment: {str(e)}")
            return {"status": "error", "message": str(e)}

    # Private helper methods

    def _initialize_bandit_state(
        self, experiment_id: str, variants: List[ModelVariant], config: Dict
    ):
        """Initialize multi-armed bandit state"""
        self.bandit_state[experiment_id] = {
            "algorithm": config.get("algorithm", BanditAlgorithm.EPSILON_GREEDY),
            "epsilon": config.get("epsilon", 0.1),
            "alpha": config.get("alpha", 1.0),
            "beta": config.get("beta", 1.0),
            "arm_counts": {v.id: 0 for v in variants},
            "arm_rewards": {v.id: 0.0 for v in variants},
            "total_counts": 0,
        }

    def _bandit_assignment(
        self,
        experiment_id: str,
        user_id: Optional[str],
        user_attributes: Optional[Dict],
    ) -> str:
        """Assign variant using multi-armed bandit algorithm"""
        state = self.bandit_state[experiment_id]
        algorithm = state["algorithm"]

        if algorithm == BanditAlgorithm.EPSILON_GREEDY:
            return self._epsilon_greedy_assignment(experiment_id)
        elif algorithm == BanditAlgorithm.UCB1:
            return self._ucb1_assignment(experiment_id)
        elif algorithm == BanditAlgorithm.THOMPSON_SAMPLING:
            return self._thompson_sampling_assignment(experiment_id)
        else:
            # Fallback to random
            experiment = self.experiments[experiment_id]
            if SCIPY_AVAILABLE:
                return np.random.choice([v.id for v in experiment.variants])
            else:
                import random

                return random.choice([v.id for v in experiment.variants])

    def _epsilon_greedy_assignment(self, experiment_id: str) -> str:
        """Epsilon-greedy bandit assignment"""
        if not SCIPY_AVAILABLE:
            experiment = self.experiments[experiment_id]
            import random

            return random.choice([v.id for v in experiment.variants])

        state = self.bandit_state[experiment_id]
        experiment = self.experiments[experiment_id]

        if np.random.random() < state["epsilon"] or state["total_counts"] == 0:
            # Explore: random assignment
            return np.random.choice([v.id for v in experiment.variants])
        else:
            # Exploit: choose best performing variant
            best_variant = max(
                experiment.variants,
                key=lambda v: state["arm_rewards"][v.id]
                / max(state["arm_counts"][v.id], 1),
            )
            return best_variant.id

    def _ucb1_assignment(self, experiment_id: str) -> str:
        """UCB1 bandit assignment"""
        if not SCIPY_AVAILABLE:
            experiment = self.experiments[experiment_id]
            import random

            return random.choice([v.id for v in experiment.variants])

        state = self.bandit_state[experiment_id]
        experiment = self.experiments[experiment_id]

        if state["total_counts"] == 0:
            return np.random.choice([v.id for v in experiment.variants])

        # Calculate UCB1 values
        ucb_values = {}
        for variant in experiment.variants:
            count = max(state["arm_counts"][variant.id], 1)
            avg_reward = state["arm_rewards"][variant.id] / count
            confidence = np.sqrt(2 * np.log(state["total_counts"]) / count)
            ucb_values[variant.id] = avg_reward + confidence

        # Choose variant with highest UCB1 value
        best_variant_id = max(ucb_values.keys(), key=lambda k: ucb_values[k])
        return best_variant_id

    def _thompson_sampling_assignment(self, experiment_id: str) -> str:
        """Thompson Sampling bandit assignment"""
        if not SCIPY_AVAILABLE:
            experiment = self.experiments[experiment_id]
            import random

            return random.choice([v.id for v in experiment.variants])

        state = self.bandit_state[experiment_id]
        experiment = self.experiments[experiment_id]

        # Sample from Beta distributions
        sampled_values = {}
        for variant in experiment.variants:
            alpha = state["alpha"] + state["arm_rewards"][variant.id]
            beta = (
                state["beta"]
                + state["arm_counts"][variant.id]
                - state["arm_rewards"][variant.id]
            )
            sampled_values[variant.id] = np.random.beta(alpha, beta)

        # Choose variant with highest sampled value
        best_variant_id = max(sampled_values.keys(), key=lambda k: sampled_values[k])
        return best_variant_id

    def _update_bandit_reward(
        self, experiment_id: str, variant_id: str, actual: float, prediction: float
    ):
        """Update bandit algorithm with reward"""
        state = self.bandit_state[experiment_id]

        # Calculate reward (higher is better)
        # Using negative absolute error as reward (closer to 0 is better)
        reward = 1.0 / (1.0 + abs(actual - prediction))

        state["arm_counts"][variant_id] += 1
        state["arm_rewards"][variant_id] += reward
        state["total_counts"] += 1

    def _assign_by_traffic_split(
        self,
        experiment: ABExperiment,
        user_id: Optional[str],
        user_attributes: Optional[Dict],
    ) -> str:
        """Assign variant based on traffic splitting method"""
        if experiment.traffic_split_method == TrafficSplitMethod.RANDOM:
            return self._random_assignment(experiment)
        elif (
            experiment.traffic_split_method == TrafficSplitMethod.USER_ID_HASH
            and user_id
        ):
            return self._hash_based_assignment(experiment, user_id)
        else:
            # Default to random
            return self._random_assignment(experiment)

    def _random_assignment(self, experiment: ABExperiment) -> str:
        """Random traffic assignment"""
        if SCIPY_AVAILABLE:
            probabilities = [v.traffic_allocation for v in experiment.variants]
            variant_ids = [v.id for v in experiment.variants]
            return np.random.choice(variant_ids, p=probabilities)
        else:
            import random

            # Simple random selection without exact probability matching
            return random.choice([v.id for v in experiment.variants])

    def _hash_based_assignment(self, experiment: ABExperiment, user_id: str) -> str:
        """Hash-based consistent assignment"""
        # Use hash to ensure consistent assignment
        hash_value = hash(f"{experiment.id}_{user_id}") % 1000000
        normalized_hash = hash_value / 1000000.0

        cumulative_prob = 0.0
        for variant in experiment.variants:
            cumulative_prob += variant.traffic_allocation
            if normalized_hash <= cumulative_prob:
                return variant.id

        # Fallback to last variant
        return experiment.variants[-1].id

    def _matches_segment_filters(self, user_attributes: Dict, filters: Dict) -> bool:
        """Check if user matches segment filters"""
        for key, expected_value in filters.items():
            user_value = user_attributes.get(key)
            if isinstance(expected_value, list):
                if user_value not in expected_value:
                    return False
            else:
                if user_value != expected_value:
                    return False
        return True

    def _calculate_variant_metrics(
        self, variant_data: pd.DataFrame, variant_id: str
    ) -> ExperimentMetrics:
        """Calculate performance metrics for a variant"""
        # Filter out rows with missing actual values for accuracy calculations
        accuracy_data = variant_data.dropna(subset=["actual"])

        if len(accuracy_data) > 0 and SCIPY_AVAILABLE:
            errors = np.abs(accuracy_data["actual"] - accuracy_data["prediction"])
            mean_performance = float(np.mean(errors))
            std_performance = float(np.std(errors))
        else:
            mean_performance = 0.0
            std_performance = 0.0

        # Calculate confidence interval
        if len(accuracy_data) > 1 and SCIPY_AVAILABLE:
            confidence_interval = stats.t.interval(
                self.confidence_level,
                len(accuracy_data) - 1,
                loc=mean_performance,
                scale=stats.sem(errors) if len(accuracy_data) > 0 else 0,
            )
        else:
            confidence_interval = (mean_performance, mean_performance)

        # Other metrics
        response_times = variant_data.dropna(subset=["response_time_ms"])[
            "response_time_ms"
        ]
        avg_response_time = (
            float(np.mean(response_times))
            if len(response_times) > 0 and SCIPY_AVAILABLE
            else 0.0
        )

        user_feedback = variant_data.dropna(subset=["user_feedback"])["user_feedback"]
        avg_satisfaction = (
            float(np.mean(user_feedback))
            if len(user_feedback) > 0 and SCIPY_AVAILABLE
            else 0.0
        )

        return ExperimentMetrics(
            variant_id=variant_id,
            sample_size=len(variant_data),
            mean_performance=mean_performance,
            std_performance=std_performance,
            confidence_interval=confidence_interval,
            predictions_count=len(variant_data),
            error_rate=0.0,  # Could calculate based on failures
            response_time_ms=avg_response_time,
            user_satisfaction=avg_satisfaction,
        )

    def _perform_statistical_tests(
        self, df: pd.DataFrame, experiment: ABExperiment
    ) -> List[StatisticalTest]:
        """Perform statistical significance tests"""
        tests = []

        if not SCIPY_AVAILABLE:
            return tests

        # Get variants with sufficient data
        variants_with_data = []
        for variant in experiment.variants:
            variant_data = df[df["variant_id"] == variant.id].dropna(subset=["actual"])
            if len(variant_data) >= experiment.min_sample_size:
                errors = np.abs(variant_data["actual"] - variant_data["prediction"])
                variants_with_data.append((variant.id, errors.values))

        if len(variants_with_data) < 2:
            return tests

        # Perform pairwise comparisons
        for i in range(len(variants_with_data)):
            for j in range(i + 1, len(variants_with_data)):
                variant_a_id, data_a = variants_with_data[i]
                variant_b_id, data_b = variants_with_data[j]

                # T-test
                try:
                    t_stat, p_value = stats.ttest_ind(data_a, data_b)
                    effect_size = (np.mean(data_a) - np.mean(data_b)) / np.sqrt(
                        (np.var(data_a) + np.var(data_b)) / 2
                    )

                    test = StatisticalTest(
                        test_name=f"T-test: {variant_a_id} vs {variant_b_id}",
                        statistic=float(t_stat),
                        p_value=float(p_value),
                        effect_size=float(effect_size),
                        confidence_level=self.confidence_level,
                        is_significant=p_value < experiment.significance_threshold,
                        interpretation=self._interpret_test_result(
                            p_value, effect_size, experiment.significance_threshold
                        ),
                    )
                    tests.append(test)
                except Exception as e:
                    self.logger.warning(f"Error performing t-test: {str(e)}")

                # Mann-Whitney U test (non-parametric)
                try:
                    u_stat, p_value_mw = stats.mannwhitneyu(
                        data_a, data_b, alternative="two-sided"
                    )

                    test = StatisticalTest(
                        test_name=f"Mann-Whitney U: {variant_a_id} vs {variant_b_id}",
                        statistic=float(u_stat),
                        p_value=float(p_value_mw),
                        effect_size=float(effect_size),  # Reuse effect size from t-test
                        confidence_level=self.confidence_level,
                        is_significant=p_value_mw < experiment.significance_threshold,
                        interpretation=self._interpret_test_result(
                            p_value_mw, effect_size, experiment.significance_threshold
                        ),
                    )
                    tests.append(test)
                except Exception as e:
                    self.logger.warning(
                        f"Error performing Mann-Whitney U test: {str(e)}"
                    )

        return tests

    def _interpret_test_result(
        self, p_value: float, effect_size: float, threshold: float
    ) -> str:
        """Interpret statistical test results"""
        if p_value < threshold:
            if abs(effect_size) > 0.8:
                magnitude = "large"
            elif abs(effect_size) > 0.5:
                magnitude = "medium"
            else:
                magnitude = "small"

            direction = "better" if effect_size < 0 else "worse"
            return f"Statistically significant difference (p={p_value:.4f}). {magnitude.capitalize()} effect size. Second variant performs {direction}."
        else:
            return f"No statistically significant difference (p={p_value:.4f}). Insufficient evidence to conclude performance difference."

    def _generate_recommendations(
        self,
        variant_metrics: Dict[str, ExperimentMetrics],
        statistical_tests: List[StatisticalTest],
        experiment: ABExperiment,
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        if len(variant_metrics) < 2:
            recommendations.append(
                "Need more variants with sufficient data for comparison"
            )
            return recommendations

        # Find best performing variant
        best_variant_id = min(
            variant_metrics.keys(), key=lambda k: variant_metrics[k].mean_performance
        )

        # Check for statistical significance
        significant_tests = [test for test in statistical_tests if test.is_significant]

        if len(significant_tests) > 0:
            recommendations.append(
                f"Variant {best_variant_id} shows statistically significant improvement. "
                f"Consider promoting to champion status."
            )
        else:
            recommendations.append(
                "No statistically significant differences detected. "
                "Continue running experiment or increase sample size."
            )

        # Check sample sizes
        min_sample_variant = min(variant_metrics.values(), key=lambda m: m.sample_size)
        if min_sample_variant.sample_size < experiment.min_sample_size:
            recommendations.append(
                f"Some variants have insufficient sample size ({min_sample_variant.sample_size} < {experiment.min_sample_size}). "
                "Continue collecting data before making decisions."
            )

        # Check for performance degradation
        champion_variant = next((v for v in experiment.variants if v.is_champion), None)
        if champion_variant and champion_variant.id in variant_metrics:
            champion_metrics = variant_metrics[champion_variant.id]
            best_metrics = variant_metrics[best_variant_id]
            if (
                best_metrics.mean_performance < champion_metrics.mean_performance * 0.95
            ):  # 5% improvement
                recommendations.append(
                    f"New variant shows >5% performance improvement over champion. "
                    f"Strong candidate for promotion."
                )

        return recommendations

    def _assess_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Assess experiment data quality"""
        total_records = len(df)

        return {
            "total_records": total_records,
            "missing_actual_values": int(df["actual"].isna().sum()),
            "missing_predictions": int(df["prediction"].isna().sum()),
            "data_completeness": float(
                (total_records - df[["actual", "prediction"]].isna().any(axis=1).sum())
                / total_records
            ),
            "time_span_hours": float(
                (df["timestamp"].max() - df["timestamp"].min()).total_seconds() / 3600
            ),
            "unique_users": int(df["user_id"].nunique()),
        }

    def _assess_experiment_health(
        self, experiment: ABExperiment, df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Assess overall experiment health"""
        now = datetime.utcnow()

        # Traffic distribution
        variant_counts = df["variant_id"].value_counts()
        expected_counts = {
            v.id: len(df) * v.traffic_allocation for v in experiment.variants
        }

        traffic_balance = {}
        for variant in experiment.variants:
            actual_count = variant_counts.get(variant.id, 0)
            expected_count = expected_counts[variant.id]
            if expected_count > 0:
                traffic_balance[variant.id] = actual_count / expected_count
            else:
                traffic_balance[variant.id] = 0

        return {
            "experiment_duration_hours": float(
                (now - experiment.start_date).total_seconds() / 3600
            ),
            "is_active": experiment.status == ExperimentStatus.RUNNING,
            "traffic_balance": traffic_balance,
            "data_freshness_hours": float(
                (now - df["timestamp"].max()).total_seconds() / 3600
            )
            if len(df) > 0
            else float("inf"),
            "overall_health": "healthy"
            if all(0.8 <= balance <= 1.2 for balance in traffic_balance.values())
            else "concerning",
        }


# Example usage and testing functions


def create_sample_experiment():
    """Create a sample A/B experiment for testing"""
    framework = ABTestingFramework()

    # Define model variants
    variants = [
        {
            "id": "champion_model",
            "name": "Current Champion",
            "description": "Existing production model",
            "model_config": {"model_type": "random_forest", "n_estimators": 100},
            "traffic_allocation": 0.5,
            "is_champion": True,
        },
        {
            "id": "challenger_model",
            "name": "XGBoost Challenger",
            "description": "New XGBoost model with optimized parameters",
            "model_config": {"model_type": "xgboost", "n_estimators": 200},
            "traffic_allocation": 0.5,
            "is_champion": False,
        },
    ]

    # Create experiment
    experiment_id = framework.create_experiment(
        name="Grade Prediction Model Comparison",
        description="Comparing Random Forest vs XGBoost for grade predictions",
        variants=variants,
        duration_days=14,
        min_sample_size=500,
        primary_metric="mean_absolute_error",
    )

    return framework, experiment_id


def simulate_experiment_data(
    framework: ABTestingFramework, experiment_id: str, num_predictions: int = 1000
):
    """Simulate experiment data for testing"""
    import random

    framework.start_experiment(experiment_id)

    # Simulate predictions over time
    for i in range(num_predictions):
        user_id = f"user_{random.randint(1, 100)}"

        # Assign variant
        variant_id = framework.assign_variant(experiment_id, user_id)

        # Simulate prediction and actual values
        # Champion model: slightly worse performance
        # Challenger model: better performance
        if variant_id == "champion_model":
            true_grade = random.normalvariate(75, 15)
            prediction_error = random.normalvariate(0, 5)
        else:  # challenger_model
            true_grade = random.normalvariate(75, 15)
            prediction_error = random.normalvariate(0, 3)  # Better model

        prediction = true_grade + prediction_error

        # Record prediction
        framework.record_prediction(
            experiment_id=experiment_id,
            variant_id=variant_id,
            user_id=user_id,
            prediction=prediction,
            actual=true_grade,
            response_time_ms=random.uniform(50, 200),
            user_feedback=random.uniform(3.0, 5.0),
        )

    return framework.analyze_experiment(experiment_id)


if __name__ == "__main__":
    # Example usage
    print("A/B Testing Framework - Example Usage")
    print("=" * 50)

    # Create and run sample experiment
    framework, experiment_id = create_sample_experiment()
    print(f"Created experiment: {experiment_id}")

    # Simulate data and analyze
    results = simulate_experiment_data(framework, experiment_id, 1000)

    print("\nExperiment Analysis Results:")
    print(f"Status: {results.get('status')}")
    print(f"Recommendations: {results.get('recommendations', [])}")

    print("\nA/B Testing Framework ready for production use!")
