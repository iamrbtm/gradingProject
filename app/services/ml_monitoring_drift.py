"""
ML Monitoring & Drift Detection System

This module implements comprehensive monitoring for machine learning models in production,
including data drift detection, model performance monitoring, and automated alerting.

Features:
- Real-time data drift detection (population stability, KL divergence, KS tests)
- Model performance monitoring with degradation alerts
- Concept drift detection using statistical methods
- Feature distribution monitoring and analysis
- Automated model retraining triggers
- Performance baseline establishment and tracking
- Comprehensive alerting and notification system
- Model health dashboards and metrics
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
import warnings

# Core libraries with fallbacks
try:
    import numpy as np
    import pandas as pd
    from scipy import stats

    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logging.warning("SciPy not available. Some statistical tests may not work.")

try:
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("scikit-learn not available. Some metrics may not work.")

# Optional libraries for advanced drift detection
try:
    from alibi_detect import KSDrift, MMDDrift, ChiSquareDrift

    ALIBI_AVAILABLE = True
except ImportError:
    ALIBI_AVAILABLE = False
    logging.warning("Alibi Detect not available. Advanced drift detection unavailable.")

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


class DriftType(Enum):
    """Types of drift detection"""

    DATA_DRIFT = "data_drift"
    CONCEPT_DRIFT = "concept_drift"
    PREDICTION_DRIFT = "prediction_drift"
    TARGET_DRIFT = "target_drift"


class AlertSeverity(Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class MonitoringStatus(Enum):
    """Monitoring system status"""

    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class DriftAlert:
    """Data drift detection alert"""

    id: str
    drift_type: DriftType
    severity: AlertSeverity
    feature_name: Optional[str]
    drift_score: float
    threshold: float
    p_value: Optional[float]
    message: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PerformanceMetrics:
    """Model performance metrics snapshot"""

    model_id: str
    timestamp: datetime
    mae: float
    mse: float
    rmse: float
    r2_score: float
    sample_size: int
    prediction_count: int
    error_rate: float
    response_time_ms: float
    confidence_intervals: Dict[str, Tuple[float, float]]
    feature_importance: Optional[Dict[str, float]] = None
    custom_metrics: Optional[Dict[str, float]] = None

    def __post_init__(self):
        if self.feature_importance is None:
            self.feature_importance = {}
        if self.custom_metrics is None:
            self.custom_metrics = {}


@dataclass
class BaselineMetrics:
    """Baseline performance metrics for comparison"""

    model_id: str
    established_date: datetime
    baseline_mae: float
    baseline_mse: float
    baseline_r2: float
    performance_std: float
    sample_size: int
    confidence_level: float
    feature_distributions: Dict[str, Dict[str, float]]
    target_distribution: Dict[str, float]


@dataclass
class MonitoringConfig:
    """Monitoring configuration"""

    model_id: str
    monitoring_frequency: int  # minutes
    drift_detection_methods: List[str]
    performance_threshold: float
    drift_threshold: float
    min_sample_size: int
    lookback_window: int  # days
    alert_channels: List[str]
    retrain_trigger_threshold: float
    feature_monitoring: bool = True
    target_monitoring: bool = True
    enable_alerts: bool = True


class MLMonitoringSystem:
    """
    Comprehensive ML Monitoring and Drift Detection System

    This system provides:
    - Data drift detection using multiple statistical methods
    - Model performance monitoring with baseline comparison
    - Concept drift detection and alerting
    - Automated model retraining triggers
    - Performance degradation alerts
    """

    def __init__(self):
        """Initialize ML Monitoring System"""
        self.logger = logging.getLogger(__name__)

        # Storage for monitoring data
        self.monitoring_configs: Dict[str, MonitoringConfig] = {}
        self.performance_history: Dict[str, List[PerformanceMetrics]] = {}
        self.baseline_metrics: Dict[str, BaselineMetrics] = {}
        self.drift_alerts: Dict[str, List[DriftAlert]] = {}

        # Drift detectors (will be initialized per model)
        self.drift_detectors: Dict[str, Dict[str, Any]] = {}

        # System status
        self.status = MonitoringStatus.ACTIVE

        self.logger.info("ML Monitoring System initialized")

    def register_model(
        self, model_id: str, monitoring_config: MonitoringConfig
    ) -> bool:
        """
        Register a model for monitoring

        Args:
            model_id: Unique model identifier
            monitoring_config: Monitoring configuration

        Returns:
            Success status
        """
        try:
            self.monitoring_configs[model_id] = monitoring_config
            self.performance_history[model_id] = []
            self.drift_alerts[model_id] = []

            # Initialize drift detectors if available
            if ALIBI_AVAILABLE:
                self._initialize_drift_detectors(model_id, monitoring_config)

            self.logger.info(f"Registered model for monitoring: {model_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error registering model {model_id}: {str(e)}")
            return False

    def establish_baseline(
        self,
        model_id: str,
        reference_data: pd.DataFrame,
        target_column: str,
        predictions: Optional[np.ndarray] = None,
    ) -> bool:
        """
        Establish baseline metrics for model monitoring

        Args:
            model_id: Model identifier
            reference_data: Reference dataset for baseline
            target_column: Target variable column name
            predictions: Model predictions on reference data

        Returns:
            Success status
        """
        try:
            if model_id not in self.monitoring_configs:
                raise ValueError(f"Model {model_id} not registered")

            # Calculate feature distributions
            feature_distributions = {}
            features = [col for col in reference_data.columns if col != target_column]

            for feature in features:
                if reference_data[feature].dtype in ["int64", "float64"]:
                    # Numerical features
                    feature_distributions[feature] = {
                        "mean": float(reference_data[feature].mean()),
                        "std": float(reference_data[feature].std()),
                        "min": float(reference_data[feature].min()),
                        "max": float(reference_data[feature].max()),
                        "percentiles": {
                            "25": float(reference_data[feature].quantile(0.25)),
                            "50": float(reference_data[feature].quantile(0.5)),
                            "75": float(reference_data[feature].quantile(0.75)),
                        },
                    }
                else:
                    # Categorical features
                    value_counts = reference_data[feature].value_counts(normalize=True)
                    feature_distributions[feature] = {
                        "categories": value_counts.to_dict(),
                        "unique_count": int(reference_data[feature].nunique()),
                    }

            # Calculate target distribution
            if reference_data[target_column].dtype in ["int64", "float64"]:
                target_distribution = {
                    "mean": float(reference_data[target_column].mean()),
                    "std": float(reference_data[target_column].std()),
                    "min": float(reference_data[target_column].min()),
                    "max": float(reference_data[target_column].max()),
                }
            else:
                value_counts = reference_data[target_column].value_counts(
                    normalize=True
                )
                target_distribution = {"categories": value_counts.to_dict()}

            # Calculate baseline performance metrics if predictions available
            if predictions is not None and SKLEARN_AVAILABLE:
                y_true = reference_data[target_column].values
                baseline_mae = float(mean_absolute_error(y_true, predictions))
                baseline_mse = float(mean_squared_error(y_true, predictions))
                baseline_r2 = float(r2_score(y_true, predictions))

                # Calculate performance standard deviation using bootstrap
                performance_samples = []
                if len(y_true) > 100:  # Only if we have enough data
                    for _ in range(100):
                        if SCIPY_AVAILABLE:
                            indices = np.random.choice(
                                len(y_true), size=min(1000, len(y_true)), replace=True
                            )
                        else:
                            import random

                            indices = [
                                random.randint(0, len(y_true) - 1)
                                for _ in range(min(1000, len(y_true)))
                            ]

                        sample_mae = float(
                            mean_absolute_error(y_true[indices], predictions[indices])
                        )
                        performance_samples.append(sample_mae)

                    performance_std = (
                        float(np.std(performance_samples)) if SCIPY_AVAILABLE else 0.0
                    )
                else:
                    performance_std = 0.0
            else:
                baseline_mae = baseline_mse = baseline_r2 = performance_std = 0.0

            # Create baseline metrics
            baseline = BaselineMetrics(
                model_id=model_id,
                established_date=datetime.utcnow(),
                baseline_mae=baseline_mae,
                baseline_mse=baseline_mse,
                baseline_r2=baseline_r2,
                performance_std=performance_std,
                sample_size=len(reference_data),
                confidence_level=0.95,
                feature_distributions=feature_distributions,
                target_distribution=target_distribution,
            )

            self.baseline_metrics[model_id] = baseline

            self.logger.info(f"Established baseline for model {model_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error establishing baseline for {model_id}: {str(e)}")
            return False

    def monitor_prediction_batch(
        self,
        model_id: str,
        features: pd.DataFrame,
        predictions: np.ndarray,
        actuals: Optional[np.ndarray] = None,
        response_times: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """
        Monitor a batch of predictions for drift and performance

        Args:
            model_id: Model identifier
            features: Input features
            predictions: Model predictions
            actuals: True target values (if available)
            response_times: Prediction response times

        Returns:
            Monitoring results including alerts and metrics
        """
        try:
            if model_id not in self.monitoring_configs:
                raise ValueError(f"Model {model_id} not registered")

            monitoring_results = {
                "timestamp": datetime.utcnow(),
                "model_id": model_id,
                "batch_size": len(features),
                "alerts": [],
                "drift_scores": {},
                "performance_metrics": None,
                "recommendations": [],
            }

            # Check for data drift
            drift_results = self._detect_data_drift(model_id, features)
            monitoring_results["drift_scores"] = drift_results["drift_scores"]
            monitoring_results["alerts"].extend(drift_results["alerts"])

            # Check for prediction drift
            prediction_drift = self._detect_prediction_drift(model_id, predictions)
            if prediction_drift:
                monitoring_results["alerts"].extend(prediction_drift)

            # Calculate performance metrics if actuals available
            if actuals is not None:
                performance_metrics = self._calculate_performance_metrics(
                    model_id, predictions, actuals, response_times
                )
                monitoring_results["performance_metrics"] = asdict(performance_metrics)

                # Store performance metrics
                self.performance_history[model_id].append(performance_metrics)

                # Check for performance degradation
                performance_alerts = self._check_performance_degradation(
                    model_id, performance_metrics
                )
                monitoring_results["alerts"].extend(performance_alerts)

            # Generate recommendations based on monitoring results
            recommendations = self._generate_monitoring_recommendations(
                monitoring_results
            )
            monitoring_results["recommendations"] = recommendations

            # Store alerts
            for alert in monitoring_results["alerts"]:
                self.drift_alerts[model_id].append(alert)

            return monitoring_results

        except Exception as e:
            self.logger.error(f"Error monitoring batch for {model_id}: {str(e)}")
            return {
                "timestamp": datetime.utcnow(),
                "model_id": model_id,
                "error": str(e),
                "alerts": [],
            }

    def get_model_health_report(
        self, model_id: str, days_back: int = 7
    ) -> Dict[str, Any]:
        """
        Generate comprehensive model health report

        Args:
            model_id: Model identifier
            days_back: Number of days to include in report

        Returns:
            Health report with metrics, trends, and recommendations
        """
        try:
            if model_id not in self.monitoring_configs:
                raise ValueError(f"Model {model_id} not registered")

            cutoff_date = datetime.utcnow() - timedelta(days=days_back)

            # Get recent performance metrics
            recent_performance = [
                m
                for m in self.performance_history[model_id]
                if m.timestamp >= cutoff_date
            ]

            # Get recent alerts
            recent_alerts = [
                alert
                for alert in self.drift_alerts[model_id]
                if alert.timestamp >= cutoff_date
            ]

            # Calculate health scores
            health_scores = self._calculate_health_scores(
                model_id, recent_performance, recent_alerts
            )

            # Performance trends
            performance_trends = self._analyze_performance_trends(recent_performance)

            # Alert summary
            alert_summary = self._summarize_alerts(recent_alerts)

            # Generate recommendations
            recommendations = self._generate_health_recommendations(
                model_id, health_scores, performance_trends, alert_summary
            )

            report = {
                "model_id": model_id,
                "report_date": datetime.utcnow(),
                "reporting_period_days": days_back,
                "health_scores": health_scores,
                "performance_trends": performance_trends,
                "alert_summary": alert_summary,
                "recent_performance": [
                    asdict(m) for m in recent_performance[-10:]
                ],  # Last 10
                "recent_alerts": [
                    asdict(alert) for alert in recent_alerts[-10:]
                ],  # Last 10
                "recommendations": recommendations,
                "monitoring_config": asdict(self.monitoring_configs[model_id]),
            }

            return report

        except Exception as e:
            self.logger.error(
                f"Error generating health report for {model_id}: {str(e)}"
            )
            return {
                "model_id": model_id,
                "error": str(e),
                "report_date": datetime.utcnow(),
            }

    # Private helper methods

    def _initialize_drift_detectors(self, model_id: str, config: MonitoringConfig):
        """Initialize drift detection algorithms"""
        if not ALIBI_AVAILABLE:
            return

        self.drift_detectors[model_id] = {}

        for method in config.drift_detection_methods:
            if method == "ks":
                # Kolmogorov-Smirnov test
                self.drift_detectors[model_id]["ks"] = KSDrift(
                    p_val=config.drift_threshold
                )
            elif method == "mmd":
                # Maximum Mean Discrepancy
                self.drift_detectors[model_id]["mmd"] = MMDDrift(
                    p_val=config.drift_threshold
                )
            elif method == "chi2":
                # Chi-square test for categorical features
                self.drift_detectors[model_id]["chi2"] = ChiSquareDrift(
                    p_val=config.drift_threshold
                )

    def _detect_data_drift(
        self, model_id: str, current_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Detect data drift using statistical methods"""
        results = {"drift_scores": {}, "alerts": []}

        if model_id not in self.baseline_metrics:
            return results

        baseline = self.baseline_metrics[model_id]
        config = self.monitoring_configs[model_id]

        # Check each feature for drift
        for feature in current_data.columns:
            if feature not in baseline.feature_distributions:
                continue

            baseline_dist = baseline.feature_distributions[feature]
            current_values = current_data[feature].dropna()

            if len(current_values) < config.min_sample_size:
                continue

            # Numerical feature drift detection
            if "mean" in baseline_dist:
                drift_score, p_value = self._detect_numerical_drift(
                    current_values, baseline_dist
                )

                results["drift_scores"][feature] = {
                    "drift_score": drift_score,
                    "p_value": p_value,
                    "drift_detected": p_value < config.drift_threshold
                    if p_value is not None
                    else False,
                }

                if p_value is not None and p_value < config.drift_threshold:
                    alert = DriftAlert(
                        id=str(uuid.uuid4()),
                        drift_type=DriftType.DATA_DRIFT,
                        severity=AlertSeverity.WARNING,
                        feature_name=feature,
                        drift_score=drift_score,
                        threshold=config.drift_threshold,
                        p_value=p_value,
                        message=f"Significant drift detected in feature '{feature}' (p={p_value:.4f})",
                        timestamp=datetime.utcnow(),
                    )
                    results["alerts"].append(alert)

            # Categorical feature drift detection
            elif "categories" in baseline_dist:
                drift_score = self._detect_categorical_drift(
                    current_values, baseline_dist["categories"]
                )

                results["drift_scores"][feature] = {
                    "drift_score": drift_score,
                    "drift_detected": drift_score > config.drift_threshold,
                }

                if drift_score > config.drift_threshold:
                    alert = DriftAlert(
                        id=str(uuid.uuid4()),
                        drift_type=DriftType.DATA_DRIFT,
                        severity=AlertSeverity.WARNING,
                        feature_name=feature,
                        drift_score=drift_score,
                        threshold=config.drift_threshold,
                        p_value=None,
                        message=f"Categorical drift detected in feature '{feature}' (score={drift_score:.4f})",
                        timestamp=datetime.utcnow(),
                    )
                    results["alerts"].append(alert)

        return results

    def _detect_numerical_drift(
        self, current_values: pd.Series, baseline_dist: Dict
    ) -> Tuple[float, Optional[float]]:
        """Detect drift in numerical features"""
        if not SCIPY_AVAILABLE:
            # Simple mean comparison
            current_mean = float(current_values.mean())
            baseline_mean = baseline_dist["mean"]
            drift_score = abs(current_mean - baseline_mean) / baseline_dist["std"]
            return drift_score, None

        # Statistical tests for numerical drift
        baseline_mean = baseline_dist["mean"]
        baseline_std = baseline_dist["std"]

        # Z-test for mean shift
        current_mean = float(np.mean(current_values))
        current_std = float(np.std(current_values))
        n = len(current_values)

        # Calculate z-score for mean difference
        z_score = (current_mean - baseline_mean) / (baseline_std / np.sqrt(n))
        p_value_mean = 2 * (1 - stats.norm.cdf(abs(z_score)))  # Two-tailed test

        # Kolmogorov-Smirnov test for distribution change
        # Generate sample from baseline distribution for comparison
        baseline_sample = np.random.normal(
            baseline_mean, baseline_std, len(current_values)
        )
        ks_stat, p_value_ks = stats.ks_2samp(current_values, baseline_sample)

        # Use the more sensitive test
        if p_value_mean < p_value_ks:
            return float(abs(z_score)), float(p_value_mean)
        else:
            return float(ks_stat), float(p_value_ks)

    def _detect_categorical_drift(
        self, current_values: pd.Series, baseline_categories: Dict
    ) -> float:
        """Detect drift in categorical features using Population Stability Index"""
        # Calculate Population Stability Index (PSI)
        current_counts = current_values.value_counts(normalize=True)

        psi = 0.0
        for category, baseline_pct in baseline_categories.items():
            current_pct = current_counts.get(
                category, 0.001
            )  # Small value to avoid log(0)
            baseline_pct = max(baseline_pct, 0.001)  # Ensure non-zero

            if SCIPY_AVAILABLE:
                psi += (current_pct - baseline_pct) * np.log(current_pct / baseline_pct)
            else:
                import math

                psi += (current_pct - baseline_pct) * math.log(
                    current_pct / baseline_pct
                )

        return float(abs(psi))

    def _detect_prediction_drift(
        self, model_id: str, predictions: np.ndarray
    ) -> List[DriftAlert]:
        """Detect drift in model predictions"""
        alerts = []

        if (
            model_id not in self.performance_history
            or len(self.performance_history[model_id]) == 0
        ):
            return alerts

        # Get recent predictions for comparison
        recent_metrics = self.performance_history[model_id][-10:]  # Last 10 batches

        if not recent_metrics:
            return alerts

        # Calculate current prediction statistics
        if SCIPY_AVAILABLE:
            current_mean = float(np.mean(predictions))
            current_std = float(np.std(predictions))

            # Compare with recent prediction distributions
            recent_predictions_mean = np.mean(
                [m.mae for m in recent_metrics]
            )  # Using MAE as proxy
            recent_predictions_std = np.std([m.mae for m in recent_metrics])

            # Simple threshold-based detection
            config = self.monitoring_configs[model_id]
            if abs(current_mean - recent_predictions_mean) > 2 * recent_predictions_std:
                alert = DriftAlert(
                    id=str(uuid.uuid4()),
                    drift_type=DriftType.PREDICTION_DRIFT,
                    severity=AlertSeverity.WARNING,
                    feature_name=None,
                    drift_score=abs(current_mean - recent_predictions_mean)
                    / recent_predictions_std,
                    threshold=2.0,
                    p_value=None,
                    message=f"Prediction distribution shift detected (mean: {current_mean:.3f} vs recent: {recent_predictions_mean:.3f})",
                    timestamp=datetime.utcnow(),
                )
                alerts.append(alert)

        return alerts

    def _calculate_performance_metrics(
        self,
        model_id: str,
        predictions: np.ndarray,
        actuals: np.ndarray,
        response_times: Optional[List[float]] = None,
    ) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        if SKLEARN_AVAILABLE:
            mae = float(mean_absolute_error(actuals, predictions))
            mse = float(mean_squared_error(actuals, predictions))
            rmse = float(np.sqrt(mse)) if SCIPY_AVAILABLE else float(mse**0.5)
            r2 = float(r2_score(actuals, predictions))
        else:
            # Manual calculations
            errors = actuals - predictions
            mae = (
                float(np.mean(np.abs(errors)))
                if SCIPY_AVAILABLE
                else float(sum(abs(e) for e in errors) / len(errors))
            )
            mse = (
                float(np.mean(errors**2))
                if SCIPY_AVAILABLE
                else float(sum(e**2 for e in errors) / len(errors))
            )
            rmse = float(mse**0.5)

            # Simple R2 calculation
            ss_res = sum(
                (actuals[i] - predictions[i]) ** 2 for i in range(len(actuals))
            )
            actuals_mean = sum(actuals) / len(actuals)
            ss_tot = sum((actuals[i] - actuals_mean) ** 2 for i in range(len(actuals)))
            r2 = float(1 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0

        # Calculate confidence intervals
        confidence_intervals = {}
        if len(actuals) > 10 and SCIPY_AVAILABLE:
            errors = np.abs(actuals - predictions)
            ci_lower, ci_upper = stats.t.interval(
                0.95, len(errors) - 1, loc=np.mean(errors), scale=stats.sem(errors)
            )
            confidence_intervals["mae"] = (float(ci_lower), float(ci_upper))

        # Response time metrics
        avg_response_time = 0.0
        if response_times:
            avg_response_time = float(sum(response_times) / len(response_times))

        return PerformanceMetrics(
            model_id=model_id,
            timestamp=datetime.utcnow(),
            mae=mae,
            mse=mse,
            rmse=rmse,
            r2_score=r2,
            sample_size=len(actuals),
            prediction_count=len(predictions),
            error_rate=0.0,  # Could calculate based on error thresholds
            response_time_ms=avg_response_time,
            confidence_intervals=confidence_intervals,
        )

    def _check_performance_degradation(
        self, model_id: str, current_metrics: PerformanceMetrics
    ) -> List[DriftAlert]:
        """Check for performance degradation compared to baseline"""
        alerts = []

        if model_id not in self.baseline_metrics:
            return alerts

        baseline = self.baseline_metrics[model_id]
        config = self.monitoring_configs[model_id]

        # Check MAE degradation
        mae_degradation = (
            current_metrics.mae - baseline.baseline_mae
        ) / baseline.baseline_mae
        if mae_degradation > config.performance_threshold:
            severity = (
                AlertSeverity.CRITICAL
                if mae_degradation > 0.5
                else AlertSeverity.WARNING
            )

            alert = DriftAlert(
                id=str(uuid.uuid4()),
                drift_type=DriftType.CONCEPT_DRIFT,
                severity=severity,
                feature_name=None,
                drift_score=mae_degradation,
                threshold=config.performance_threshold,
                p_value=None,
                message=f"Performance degradation detected: MAE increased by {mae_degradation:.1%} "
                f"(current: {current_metrics.mae:.3f}, baseline: {baseline.baseline_mae:.3f})",
                timestamp=datetime.utcnow(),
                metadata={
                    "metric": "mae",
                    "baseline_value": baseline.baseline_mae,
                    "current_value": current_metrics.mae,
                },
            )
            alerts.append(alert)

        # Check for model retraining trigger
        if mae_degradation > config.retrain_trigger_threshold:
            alert = DriftAlert(
                id=str(uuid.uuid4()),
                drift_type=DriftType.CONCEPT_DRIFT,
                severity=AlertSeverity.EMERGENCY,
                feature_name=None,
                drift_score=mae_degradation,
                threshold=config.retrain_trigger_threshold,
                p_value=None,
                message=f"Model retraining required: Performance degraded by {mae_degradation:.1%}",
                timestamp=datetime.utcnow(),
                metadata={"action_required": "retrain_model"},
            )
            alerts.append(alert)

        return alerts

    def _generate_monitoring_recommendations(
        self, monitoring_results: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on monitoring results"""
        recommendations = []

        # Count alerts by severity
        alert_counts = {}
        for alert in monitoring_results["alerts"]:
            severity = alert.severity
            alert_counts[severity] = alert_counts.get(severity, 0) + 1

        # High-level recommendations
        if alert_counts.get(AlertSeverity.EMERGENCY, 0) > 0:
            recommendations.append(
                "🚨 URGENT: Immediate model retraining required due to severe performance degradation"
            )

        if alert_counts.get(AlertSeverity.CRITICAL, 0) > 0:
            recommendations.append(
                "⚠️ Critical performance issues detected. Consider model retraining within 24 hours"
            )

        if alert_counts.get(AlertSeverity.WARNING, 0) >= 3:
            recommendations.append(
                "📊 Multiple drift warnings detected. Increase monitoring frequency and prepare for retraining"
            )

        # Data drift recommendations
        drift_features = [
            alert.feature_name
            for alert in monitoring_results["alerts"]
            if alert.drift_type == DriftType.DATA_DRIFT and alert.feature_name
        ]

        if len(drift_features) > 5:
            recommendations.append(
                f"🔄 Significant data drift in {len(drift_features)} features. Consider feature engineering or data pipeline review"
            )
        elif len(drift_features) > 0:
            recommendations.append(
                f"📈 Data drift detected in features: {', '.join(drift_features[:3])}{'...' if len(drift_features) > 3 else ''}"
            )

        # Performance recommendations
        if monitoring_results.get("performance_metrics"):
            perf = monitoring_results["performance_metrics"]
            if perf["r2_score"] < 0.5:
                recommendations.append(
                    "📉 Low model performance detected (R² < 0.5). Investigate data quality and model architecture"
                )

        # Default recommendation if no issues
        if not recommendations:
            recommendations.append(
                "✅ Model health is good. Continue current monitoring schedule"
            )

        return recommendations

    def _calculate_health_scores(
        self,
        model_id: str,
        recent_performance: List[PerformanceMetrics],
        recent_alerts: List[DriftAlert],
    ) -> Dict[str, float]:
        """Calculate overall model health scores"""
        health_scores = {
            "overall_health": 1.0,
            "performance_health": 1.0,
            "data_quality_health": 1.0,
            "stability_health": 1.0,
        }

        # Performance health based on recent metrics
        if recent_performance and model_id in self.baseline_metrics:
            baseline = self.baseline_metrics[model_id]
            recent_mae = [m.mae for m in recent_performance[-5:]]  # Last 5 measurements

            if recent_mae:
                avg_recent_mae = sum(recent_mae) / len(recent_mae)
                performance_ratio = (
                    baseline.baseline_mae / avg_recent_mae
                    if avg_recent_mae > 0
                    else 1.0
                )
                health_scores["performance_health"] = min(1.0, performance_ratio)

        # Data quality health based on drift alerts
        drift_alerts = [
            a for a in recent_alerts if a.drift_type == DriftType.DATA_DRIFT
        ]
        if len(recent_alerts) > 0:
            drift_penalty = len(drift_alerts) * 0.1
            health_scores["data_quality_health"] = max(0.0, 1.0 - drift_penalty)

        # Stability health based on alert frequency and severity
        critical_alerts = [
            a
            for a in recent_alerts
            if a.severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY]
        ]
        if len(recent_alerts) > 0:
            stability_penalty = (
                len(critical_alerts) * 0.3
                + (len(recent_alerts) - len(critical_alerts)) * 0.1
            )
            health_scores["stability_health"] = max(0.0, 1.0 - stability_penalty)

        # Overall health as weighted average
        health_scores["overall_health"] = (
            0.4 * health_scores["performance_health"]
            + 0.3 * health_scores["data_quality_health"]
            + 0.3 * health_scores["stability_health"]
        )

        return health_scores

    def _analyze_performance_trends(
        self, recent_performance: List[PerformanceMetrics]
    ) -> Dict[str, Any]:
        """Analyze performance trends over time"""
        if len(recent_performance) < 2:
            return {"trend": "insufficient_data", "direction": "unknown"}

        # Sort by timestamp
        sorted_perf = sorted(recent_performance, key=lambda x: x.timestamp)

        # Calculate trend in MAE
        mae_values = [m.mae for m in sorted_perf]

        if SCIPY_AVAILABLE and len(mae_values) >= 3:
            # Linear regression to determine trend
            x = np.array(range(len(mae_values)))
            y = np.array(mae_values)
            slope, _, r_value, p_value, _ = stats.linregress(x, y)

            # Determine trend direction and significance
            if p_value < 0.05:  # Statistically significant trend
                if slope > 0:
                    direction = "degrading"
                    trend = "significant_degradation"
                else:
                    direction = "improving"
                    trend = "significant_improvement"
            else:
                direction = "stable"
                trend = "stable"

            return {
                "trend": trend,
                "direction": direction,
                "slope": float(slope),
                "r_squared": float(r_value**2),
                "p_value": float(p_value),
                "recent_mae": mae_values[-1],
                "mae_change": mae_values[-1] - mae_values[0],
            }
        else:
            # Simple comparison
            if mae_values[-1] > mae_values[0] * 1.1:
                direction = "degrading"
                trend = "degradation"
            elif mae_values[-1] < mae_values[0] * 0.9:
                direction = "improving"
                trend = "improvement"
            else:
                direction = "stable"
                trend = "stable"

            return {
                "trend": trend,
                "direction": direction,
                "recent_mae": mae_values[-1],
                "mae_change": mae_values[-1] - mae_values[0],
            }

    def _summarize_alerts(self, recent_alerts: List[DriftAlert]) -> Dict[str, Any]:
        """Summarize recent alerts"""
        if not recent_alerts:
            return {"total_alerts": 0, "by_severity": {}, "by_type": {}}

        # Count by severity
        severity_counts = {}
        for alert in recent_alerts:
            severity = alert.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        # Count by type
        type_counts = {}
        for alert in recent_alerts:
            drift_type = alert.drift_type.value
            type_counts[drift_type] = type_counts.get(drift_type, 0) + 1

        return {
            "total_alerts": len(recent_alerts),
            "by_severity": severity_counts,
            "by_type": type_counts,
            "most_recent": asdict(recent_alerts[-1]) if recent_alerts else None,
        }

    def _generate_health_recommendations(
        self,
        model_id: str,
        health_scores: Dict[str, float],
        performance_trends: Dict[str, Any],
        alert_summary: Dict[str, Any],
    ) -> List[str]:
        """Generate health-based recommendations"""
        recommendations = []

        # Overall health recommendations
        overall_health = health_scores["overall_health"]
        if overall_health < 0.3:
            recommendations.append(
                "🚨 CRITICAL: Model health is severely compromised. Immediate intervention required."
            )
        elif overall_health < 0.6:
            recommendations.append(
                "⚠️ WARNING: Model health is declining. Schedule maintenance and monitoring review."
            )
        elif overall_health < 0.8:
            recommendations.append(
                "📊 Model health is fair. Consider optimization and closer monitoring."
            )
        else:
            recommendations.append(
                "✅ Model health is good. Maintain current monitoring schedule."
            )

        # Performance trend recommendations
        if performance_trends["direction"] == "degrading":
            recommendations.append(
                f"📉 Performance is degrading. Recent MAE change: {performance_trends['mae_change']:.4f}"
            )
        elif performance_trends["direction"] == "improving":
            recommendations.append(
                f"📈 Performance is improving. Recent MAE change: {performance_trends['mae_change']:.4f}"
            )

        # Alert-based recommendations
        if alert_summary["total_alerts"] > 10:
            recommendations.append(
                "🔔 High alert frequency detected. Consider adjusting monitoring thresholds or investigating root causes."
            )

        critical_alerts = alert_summary["by_severity"].get(
            "critical", 0
        ) + alert_summary["by_severity"].get("emergency", 0)
        if critical_alerts > 0:
            recommendations.append(
                f"🚨 {critical_alerts} critical alerts require immediate attention."
            )

        return recommendations


# Example usage and testing functions


def create_monitoring_setup():
    """Create example monitoring setup"""
    monitor = MLMonitoringSystem()

    # Configuration for a grade prediction model
    config = MonitoringConfig(
        model_id="grade_predictor_v1",
        monitoring_frequency=60,  # Check every hour
        drift_detection_methods=["ks", "chi2"],
        performance_threshold=0.15,  # 15% degradation threshold
        drift_threshold=0.05,  # p-value threshold
        min_sample_size=100,
        lookback_window=7,  # 7 days
        alert_channels=["email", "slack"],
        retrain_trigger_threshold=0.25,  # 25% degradation triggers retraining
        feature_monitoring=True,
        target_monitoring=True,
        enable_alerts=True,
    )

    return monitor, config


def simulate_monitoring_scenario():
    """Simulate a monitoring scenario with drift"""
    monitor, config = create_monitoring_setup()

    # Register model
    monitor.register_model("grade_predictor_v1", config)

    # Create baseline data
    if SCIPY_AVAILABLE:
        np.random.seed(42)
        baseline_features = pd.DataFrame(
            {
                "study_hours": np.random.normal(5, 2, 1000),
                "attendance": np.random.normal(0.85, 0.15, 1000),
                "previous_grade": np.random.normal(75, 10, 1000),
            }
        )
        baseline_targets = (
            baseline_features["previous_grade"]
            + baseline_features["study_hours"] * 2
            + np.random.normal(0, 5, 1000)
        )

        baseline_predictions = baseline_targets + np.random.normal(0, 3, 1000)

        # Establish baseline
        baseline_data = baseline_features.copy()
        baseline_data["grade"] = baseline_targets

        monitor.establish_baseline(
            "grade_predictor_v1", baseline_data, "grade", baseline_predictions
        )

        # Simulate current data with drift
        current_features = pd.DataFrame(
            {
                "study_hours": np.random.normal(
                    4, 2.5, 500
                ),  # Mean shifted down, variance increased
                "attendance": np.random.normal(
                    0.80, 0.20, 500
                ),  # Mean and variance shifted
                "previous_grade": np.random.normal(73, 12, 500),  # Slight shift
            }
        )

        current_targets = (
            current_features["previous_grade"]
            + current_features["study_hours"] * 1.8
            + np.random.normal(0, 7, 500)
        )  # Concept drift

        current_predictions = current_targets + np.random.normal(
            0, 5, 500
        )  # Worse predictions

        # Monitor batch
        results = monitor.monitor_prediction_batch(
            "grade_predictor_v1",
            current_features,
            current_predictions,
            current_targets,
            [50 + np.random.random() * 100 for _ in range(500)],  # Response times
        )

        return monitor, results
    else:
        return monitor, {"message": "NumPy not available for simulation"}


if __name__ == "__main__":
    print("ML Monitoring & Drift Detection System")
    print("=" * 50)

    # Run simulation
    monitor, results = simulate_monitoring_scenario()

    print(f"Monitoring Results:")
    print(f"- Alerts generated: {len(results.get('alerts', []))}")
    print(f"- Features monitored: {len(results.get('drift_scores', {}))}")

    if results.get("alerts"):
        print("\nSample Alert:")
        alert = results["alerts"][0]
        print(f"- Type: {alert.drift_type.value}")
        print(f"- Severity: {alert.severity.value}")
        print(f"- Message: {alert.message}")

    # Generate health report
    health_report = monitor.get_model_health_report("grade_predictor_v1")
    print(
        f"\nModel Health Score: {health_report.get('health_scores', {}).get('overall_health', 0):.2f}"
    )

    print("\nML Monitoring System ready for production!")
