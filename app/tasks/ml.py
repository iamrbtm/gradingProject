"""
Machine Learning Background Tasks
===============================

This module contains Celery tasks for advanced ML model training and updates.
Implements sophisticated ML pipelines for academic analytics.

Features:
- Automated model training and retraining
- Hyperparameter optimization
- Cross-validation and model evaluation
- Model versioning and deployment
- Feature engineering automation
- Ensemble model management

Author: Analytics Team
Date: 2024-12-19
"""

import logging
import pickle
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional

try:
    from celery import shared_task

    CELERY_AVAILABLE = True
except ImportError:
    # Fallback decorator for environments without Celery
    def shared_task(func):
        return func

    CELERY_AVAILABLE = False

import numpy as np
import pandas as pd
from sklearn.model_selection import GridSearchCV, cross_val_score, TimeSeriesSplit
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.pipeline import Pipeline

try:
    import xgboost as xgb
    import lightgbm as lgb

    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

try:
    import joblib

    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

from ..models import (
    db,
    User,
    Term,
    Course,
    Assignment,
    PredictionModel,
    GradePrediction,
    RiskAssessment,
    PerformanceMetric,
    PerformanceTrend,
)
from ..services.predictive_analytics import PredictiveAnalyticsEngine

# Import advanced ML services with fallback handling
try:
    from ..services.external_data_service import ExternalDataService
    from ..services.advanced_ml_models import AdvancedMLSystem
    from ..services.time_series_forecasting import TimeSeriesForecaster
    from ..services.model_interpretability import ModelInterpretabilityService
    from ..services.ab_testing_framework import ABTestingFramework
    from ..services.ml_monitoring_drift import MLMonitoringService

    ADVANCED_ML_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)  # Ensure logger is available for this warning
    logger.warning(f"Advanced ML services not available: {e}")
    ADVANCED_ML_AVAILABLE = False

# Import advanced ML services
try:
    from ..services.external_data_service import ExternalDataService
    from ..services.advanced_ml_models import AdvancedMLSystem
    from ..services.time_series_forecasting import TimeSeriesForecaster
    from ..services.model_interpretability import ModelInterpretabilityService
    from ..services.ab_testing_framework import ABTestingFramework
    from ..services.ml_monitoring_drift import MLMonitoringService

    ADVANCED_ML_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Advanced ML services not available: {e}")
    ADVANCED_ML_AVAILABLE = False

logger = logging.getLogger(__name__)


class AdvancedMLTrainer:
    """Advanced ML model trainer with hyperparameter optimization."""

    def __init__(self):
        self.models_dir = "models"
        self.ensure_models_directory()

    def ensure_models_directory(self):
        """Ensure models directory exists."""
        if not os.path.exists(self.models_dir):
            os.makedirs(self.models_dir)

    def get_model_configs(self) -> Dict[str, Dict]:
        """Get configuration for different ML models."""
        configs = {
            "random_forest": {
                "model": RandomForestRegressor(random_state=42),
                "params": {
                    "n_estimators": [50, 100, 200],
                    "max_depth": [5, 10, None],
                    "min_samples_split": [2, 5, 10],
                    "min_samples_leaf": [1, 2, 4],
                },
            },
            "gradient_boosting": {
                "model": GradientBoostingRegressor(random_state=42),
                "params": {
                    "n_estimators": [100, 200],
                    "max_depth": [3, 5, 7],
                    "learning_rate": [0.01, 0.1, 0.2],
                    "subsample": [0.8, 1.0],
                },
            },
            "ridge_regression": {
                "model": Ridge(random_state=42),
                "params": {"alpha": [0.1, 1.0, 10.0, 100.0]},
            },
        }

        if XGB_AVAILABLE:
            configs["xgboost"] = {
                "model": xgb.XGBRegressor(random_state=42),
                "params": {
                    "n_estimators": [100, 200],
                    "max_depth": [3, 5, 7],
                    "learning_rate": [0.01, 0.1, 0.2],
                    "subsample": [0.8, 1.0],
                },
            }

            configs["lightgbm"] = {
                "model": lgb.LGBMRegressor(random_state=42, verbose=-1),
                "params": {
                    "n_estimators": [100, 200],
                    "max_depth": [3, 5, 7],
                    "learning_rate": [0.01, 0.1, 0.2],
                    "num_leaves": [31, 50, 100],
                },
            }

        return configs

    def extract_features(self, user_id: int) -> pd.DataFrame:
        """Extract comprehensive features for ML training."""
        features = []

        # Get user's academic data
        user = User.query.get(user_id)
        if not user:
            return pd.DataFrame()

        for term in user.terms:
            for course in term.courses:
                assignments = course.assignments

                if not assignments:
                    continue

                # Course-level features
                total_assignments = len(assignments)
                completed_assignments = len(
                    [a for a in assignments if a.score is not None]
                )

                if completed_assignments == 0:
                    continue

                # Calculate various metrics
                scores = [a.score for a in assignments if a.score is not None]
                avg_score = np.mean(scores) if scores else 0
                std_score = np.std(scores) if len(scores) > 1 else 0
                min_score = min(scores) if scores else 0
                max_score = max(scores) if scores else 0

                # Time-based features
                due_dates = [a.due_date for a in assignments if a.due_date]
                if due_dates:
                    days_span = (max(due_dates) - min(due_dates)).days
                else:
                    days_span = 0

                # Trend features
                if len(scores) >= 3:
                    recent_scores = scores[-3:]
                    early_scores = scores[:3]
                    trend = np.mean(recent_scores) - np.mean(early_scores)
                else:
                    trend = 0

                # Assignment type features
                categories = {}
                for assignment in assignments:
                    if assignment.category:
                        cat_name = assignment.category.name
                        if cat_name not in categories:
                            categories[cat_name] = []
                        if assignment.score is not None:
                            categories[cat_name].append(assignment.score)

                # Create feature row
                feature_row = {
                    "user_id": user_id,
                    "course_id": course.id,
                    "term_id": term.id,
                    "total_assignments": total_assignments,
                    "completed_assignments": completed_assignments,
                    "completion_rate": completed_assignments / total_assignments,
                    "avg_score": avg_score,
                    "std_score": std_score,
                    "min_score": min_score,
                    "max_score": max_score,
                    "score_trend": trend,
                    "days_span": days_span,
                    "workload_intensity": total_assignments / max(days_span, 1),
                    # Category-specific features
                    "exam_avg": np.mean(categories.get("Exams", [0]))
                    if categories.get("Exams")
                    else 0,
                    "homework_avg": np.mean(categories.get("Homework", [0]))
                    if categories.get("Homework")
                    else 0,
                    "project_avg": np.mean(categories.get("Projects", [0]))
                    if categories.get("Projects")
                    else 0,
                    "quiz_avg": np.mean(categories.get("Quizzes", [0]))
                    if categories.get("Quizzes")
                    else 0,
                    # Target variable (final course grade)
                    "final_grade": avg_score,  # This would be the actual final grade in a real scenario
                }

                features.append(feature_row)

        return pd.DataFrame(features)

    def train_model(
        self, model_name: str, X: pd.DataFrame, y: pd.Series
    ) -> Dict[str, Any]:
        """Train a specific model with hyperparameter optimization."""
        logger.info(f"Training {model_name} model with {len(X)} samples")

        configs = self.get_model_configs()
        if model_name not in configs:
            raise ValueError(f"Unknown model: {model_name}")

        config = configs[model_name]

        # Create pipeline with preprocessing
        pipeline = Pipeline([("scaler", StandardScaler()), ("model", config["model"])])

        # Prepare parameters for grid search (add 'model__' prefix)
        param_grid = {f"model__{k}": v for k, v in config["params"].items()}

        # Use time series split for temporal data
        cv = TimeSeriesSplit(n_splits=3) if len(X) > 10 else 3

        # Hyperparameter optimization
        grid_search = GridSearchCV(
            pipeline,
            param_grid,
            cv=cv,
            scoring="neg_mean_squared_error",
            n_jobs=-1,
            verbose=0,
        )

        try:
            grid_search.fit(X, y)

            # Get best model
            best_model = grid_search.best_estimator_

            # Evaluate model
            cv_scores = cross_val_score(
                best_model, X, y, cv=cv, scoring="neg_mean_squared_error"
            )

            # Make predictions for additional metrics
            y_pred = best_model.predict(X)

            metrics = {
                "mse": mean_squared_error(y, y_pred),
                "mae": mean_absolute_error(y, y_pred),
                "r2": r2_score(y, y_pred),
                "cv_score_mean": -cv_scores.mean(),
                "cv_score_std": cv_scores.std(),
                "best_params": grid_search.best_params_,
                "n_samples": len(X),
                "n_features": len(X.columns),
            }

            logger.info(
                f"Model {model_name} trained successfully. R²: {metrics['r2']:.3f}, CV MSE: {metrics['cv_score_mean']:.3f}"
            )

            return {
                "model": best_model,
                "metrics": metrics,
                "feature_names": list(X.columns),
            }

        except Exception as e:
            logger.error(f"Error training {model_name}: {str(e)}")
            return None

    def save_model(
        self, model_data: Dict[str, Any], model_name: str, version: str
    ) -> str:
        """Save trained model to disk."""
        if not JOBLIB_AVAILABLE:
            logger.warning("joblib not available, skipping model save")
            return ""

        filename = (
            f"{model_name}_v{version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        )
        filepath = os.path.join(self.models_dir, filename)

        try:
            joblib.dump(model_data, filepath)
            logger.info(f"Model saved to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving model: {str(e)}")
            return ""

    def evaluate_ensemble(
        self, models: Dict[str, Any], X: pd.DataFrame, y: pd.Series
    ) -> Dict[str, float]:
        """Evaluate ensemble model performance."""
        predictions = []

        for name, model_data in models.items():
            if model_data and "model" in model_data:
                try:
                    pred = model_data["model"].predict(X)
                    predictions.append(pred)
                except Exception as e:
                    logger.warning(f"Error getting predictions from {name}: {str(e)}")

        if not predictions:
            return {}

        # Simple average ensemble
        ensemble_pred = np.mean(predictions, axis=0)

        return {
            "ensemble_mse": mean_squared_error(y, ensemble_pred),
            "ensemble_mae": mean_absolute_error(y, ensemble_pred),
            "ensemble_r2": r2_score(y, ensemble_pred),
            "n_models": len(predictions),
        }


@shared_task(bind=True, name="app.tasks.ml.train_all_models")
def train_all_models(self, user_id: Optional[int] = None):
    """Train all ML models for grade prediction."""
    try:
        logger.info(f"Starting ML model training for user {user_id or 'all users'}")

        trainer = AdvancedMLTrainer()

        # Get users to train for
        if user_id:
            users = [User.query.get(user_id)] if User.query.get(user_id) else []
        else:
            # Train for users with sufficient data
            users = (
                User.query.join(Term)
                .join(Course)
                .join(Assignment)
                .group_by(User.id)
                .having(db.func.count(Assignment.id) >= 10)
                .all()
            )

        results = {}

        for user in users:
            logger.info(f"Training models for user {user.id}")

            # Extract features
            df = trainer.extract_features(user.id)

            if len(df) < 3:  # Need minimum data
                logger.info(f"Insufficient data for user {user.id}: {len(df)} samples")
                continue

            # Prepare data
            feature_cols = [
                col
                for col in df.columns
                if col not in ["user_id", "course_id", "term_id", "final_grade"]
            ]
            X = df[feature_cols]
            y = df["final_grade"]

            # Train multiple models
            user_models = {}
            model_names = ["random_forest", "gradient_boosting", "ridge_regression"]

            if XGB_AVAILABLE:
                model_names.extend(["xgboost", "lightgbm"])

            for model_name in model_names:
                try:
                    model_result = trainer.train_model(model_name, X, y)
                    if model_result:
                        user_models[model_name] = model_result

                        # Save model
                        version = datetime.now().strftime("%Y%m%d")
                        filepath = trainer.save_model(
                            model_result, f"{model_name}_user{user.id}", version
                        )

                        # Store in database
                        prediction_model = PredictionModel(
                            user_id=user.id,
                            model_type=model_name,
                            model_version=version,
                            model_path=filepath,
                            accuracy_metrics=model_result["metrics"],
                            feature_importance=dict(
                                zip(
                                    model_result["feature_names"],
                                    getattr(
                                        model_result["model"].named_steps["model"],
                                        "feature_importances_",
                                        [0] * len(model_result["feature_names"]),
                                    ),
                                )
                            )
                            if hasattr(
                                model_result["model"].named_steps["model"],
                                "feature_importances_",
                            )
                            else {},
                            training_data_size=model_result["metrics"]["n_samples"],
                            is_active=True,
                        )

                        db.session.add(prediction_model)

                except Exception as e:
                    logger.error(
                        f"Error training {model_name} for user {user.id}: {str(e)}"
                    )

            # Evaluate ensemble
            if user_models:
                ensemble_metrics = trainer.evaluate_ensemble(user_models, X, y)
                results[user.id] = {
                    "models_trained": len(user_models),
                    "ensemble_metrics": ensemble_metrics,
                    "individual_models": {
                        name: data["metrics"] for name, data in user_models.items()
                    },
                }

        # Commit all model updates
        db.session.commit()

        logger.info(f"ML training completed. Results: {len(results)} users processed")
        return {
            "status": "success",
            "users_processed": len(results),
            "results": results,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in ML training task: {str(e)}")
        db.session.rollback()
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@shared_task(bind=True, name="app.tasks.ml.retrain_user_models")
def retrain_user_models(self, user_id: int):
    """Retrain models for a specific user with new data."""
    return train_all_models.delay(user_id)


@shared_task(bind=True, name="app.tasks.ml.evaluate_model_performance")
def evaluate_model_performance(self):
    """Evaluate performance of deployed models and trigger retraining if needed."""
    try:
        logger.info("Evaluating model performance")

        # Get active models
        active_models = PredictionModel.query.filter_by(is_active=True).all()

        results = {}
        retrain_needed = []

        for model in active_models:
            try:
                # Check model age
                model_age = (datetime.utcnow() - model.created_at).days

                # Check if model needs retraining based on:
                # 1. Age (older than 30 days)
                # 2. Performance degradation
                # 3. New data availability

                needs_retrain = False
                reasons = []

                if model_age > 30:
                    needs_retrain = True
                    reasons.append("model_age")

                # Check if user has new assignments since model creation
                user = User.query.get(model.user_id)
                if user:
                    new_assignments = (
                        Assignment.query.join(Course)
                        .join(Term)
                        .filter(
                            Term.user_id == user.id,
                            Assignment.created_at > model.created_at,
                        )
                        .count()
                    )

                    if new_assignments > 5:  # Threshold for retraining
                        needs_retrain = True
                        reasons.append("new_data")

                results[model.id] = {
                    "model_type": model.model_type,
                    "user_id": model.user_id,
                    "age_days": model_age,
                    "needs_retrain": needs_retrain,
                    "reasons": reasons,
                }

                if needs_retrain:
                    retrain_needed.append(model.user_id)

            except Exception as e:
                logger.error(f"Error evaluating model {model.id}: {str(e)}")

        # Trigger retraining for users who need it
        for user_id in set(retrain_needed):  # Remove duplicates
            train_all_models.delay(user_id)

        logger.info(
            f"Model evaluation completed. {len(retrain_needed)} users need retraining"
        )

        return {
            "status": "success",
            "models_evaluated": len(active_models),
            "retraining_triggered": len(set(retrain_needed)),
            "results": results,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in model evaluation task: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@shared_task(bind=True, name="app.tasks.ml.cleanup_old_models")
def cleanup_old_models(self):
    """Clean up old model files and database records."""
    try:
        logger.info("Cleaning up old ML models")

        # Remove models older than 90 days
        cutoff_date = datetime.utcnow() - timedelta(days=90)

        old_models = PredictionModel.query.filter(
            PredictionModel.created_at < cutoff_date, PredictionModel.is_active == False
        ).all()

        removed_files = 0
        removed_records = 0

        for model in old_models:
            try:
                # Remove model file
                if model.model_path and os.path.exists(model.model_path):
                    os.remove(model.model_path)
                    removed_files += 1

                # Remove database record
                db.session.delete(model)
                removed_records += 1

            except Exception as e:
                logger.error(f"Error removing model {model.id}: {str(e)}")

        db.session.commit()

        logger.info(
            f"Cleanup completed. Removed {removed_files} files and {removed_records} records"
        )

        return {
            "status": "success",
            "files_removed": removed_files,
            "records_removed": removed_records,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in model cleanup task: {str(e)}")
        db.session.rollback()
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


# Utility functions for manual testing without Celery
def run_ml_training_sync(user_id: Optional[int] = None):
    """Run ML training synchronously for testing."""
    return train_all_models(user_id)


def run_model_evaluation_sync():
    """Run model evaluation synchronously for testing."""
    return evaluate_model_performance()


# ============================================================================
# ADVANCED ML INTEGRATION TASKS
# ============================================================================
# New tasks for integrating advanced ML services


@shared_task(bind=True, name="app.tasks.ml.collect_external_data")
def collect_external_data(self):
    """Collect external data from all configured sources."""
    if not ADVANCED_ML_AVAILABLE:
        logger.warning(
            "Advanced ML services not available, skipping external data collection"
        )
        return {"status": "skipped", "reason": "advanced_ml_not_available"}

    try:
        logger.info("Starting external data collection task")

        external_service = ExternalDataService()
        results = {}

        # Collect data from all sources
        data_sources = [
            "weather",
            "economic_indicators",
            "academic_calendar",
            "social_sentiment",
            "course_difficulty",
            "job_market",
            "campus_events",
            "industry_trends",
        ]

        for source in data_sources:
            try:
                logger.info(f"Collecting data from {source}")
                data = external_service.collect_data(source)

                if data and not data.empty:
                    results[source] = {
                        "status": "success",
                        "records": len(data),
                        "features": len(data.columns)
                        if hasattr(data, "columns")
                        else 0,
                        "latest_timestamp": data.index[-1].isoformat()
                        if hasattr(data, "index") and len(data) > 0
                        else None,
                    }
                else:
                    results[source] = {"status": "no_data", "records": 0}

            except Exception as e:
                logger.error(f"Error collecting data from {source}: {str(e)}")
                results[source] = {"status": "error", "error": str(e)}

        # Update cache metrics
        cache_status = external_service.get_cache_status()

        logger.info(
            f"External data collection completed. Sources processed: {len(results)}"
        )

        return {
            "status": "success",
            "sources_processed": len(results),
            "results": results,
            "cache_status": cache_status,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in external data collection task: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@shared_task(bind=True, name="app.tasks.ml.train_advanced_ml_models")
def train_advanced_ml_models(
    self, course_id: Optional[int] = None, force_retrain: bool = False
):
    """Train advanced ML models with ensemble methods and external data."""
    if not ADVANCED_ML_AVAILABLE:
        logger.warning(
            "Advanced ML services not available, falling back to traditional training"
        )
        return train_all_models.delay()

    try:
        logger.info(
            f"Starting advanced ML model training for course {course_id or 'all courses'}"
        )

        ml_system = AdvancedMLSystem()
        results = {}

        # Get courses to train for
        if course_id:
            courses = (
                [Course.query.get(course_id)] if Course.query.get(course_id) else []
            )
        else:
            # Train for courses with sufficient data
            courses = (
                Course.query.join(Assignment)
                .group_by(Course.id)
                .having(db.func.count(Assignment.id) >= 10)
                .limit(50)
                .all()
            )  # Limit to prevent overwhelming

        for course in courses:
            try:
                logger.info(f"Training advanced models for course {course.id}")

                # Check if retraining is needed
                if not force_retrain:
                    latest_model = (
                        PredictionModel.query.filter_by(
                            course_id=course.id,
                            model_type="advanced_ensemble",
                            is_active=True,
                        )
                        .order_by(PredictionModel.created_at.desc())
                        .first()
                    )

                    if latest_model:
                        age_hours = (
                            datetime.utcnow() - latest_model.created_at
                        ).total_seconds() / 3600
                        if age_hours < 24:  # Skip if trained within 24 hours
                            logger.info(
                                f"Skipping course {course.id} - model trained {age_hours:.1f} hours ago"
                            )
                            continue

                # Train ensemble models
                model_result = ml_system.train_ensemble_models(course.id)

                if model_result and model_result.get("success"):
                    # Save model metrics
                    best_model_info = model_result.get("best_model", {})

                    prediction_model = PredictionModel(
                        course_id=course.id,
                        model_type="advanced_ensemble",
                        model_version=datetime.now().strftime("%Y%m%d_%H%M"),
                        accuracy_metrics=model_result.get("ensemble_metrics", {}),
                        feature_importance=model_result.get("feature_importance", {}),
                        training_data_size=model_result.get("training_samples", 0),
                        is_active=True,
                        metadata={
                            "models_in_ensemble": model_result.get(
                                "models_trained", []
                            ),
                            "best_individual_model": best_model_info.get("name"),
                            "external_features_used": model_result.get(
                                "external_features_count", 0
                            ),
                            "hyperparameter_optimization": True,
                        },
                    )

                    # Deactivate old models for this course
                    PredictionModel.query.filter_by(
                        course_id=course.id, is_active=True
                    ).update({"is_active": False})

                    db.session.add(prediction_model)

                    results[course.id] = {
                        "status": "success",
                        "models_trained": len(model_result.get("models_trained", [])),
                        "best_model": best_model_info.get("name"),
                        "ensemble_score": model_result.get("ensemble_metrics", {}).get(
                            "r2_score", 0
                        ),
                        "external_features": model_result.get(
                            "external_features_count", 0
                        ),
                    }

                else:
                    results[course.id] = {
                        "status": "failed",
                        "reason": "insufficient_data_or_error",
                    }

            except Exception as e:
                logger.error(
                    f"Error training advanced models for course {course.id}: {str(e)}"
                )
                results[course.id] = {"status": "error", "error": str(e)}

        db.session.commit()

        logger.info(
            f"Advanced ML training completed. Courses processed: {len(results)}"
        )

        return {
            "status": "success",
            "courses_processed": len(results),
            "results": results,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in advanced ML training task: {str(e)}")
        db.session.rollback()
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@shared_task(bind=True, name="app.tasks.ml.generate_time_series_forecasts")
def generate_time_series_forecasts(self, user_id: Optional[int] = None):
    """Generate time series forecasts for student performance trajectories."""
    if not ADVANCED_ML_AVAILABLE:
        logger.warning(
            "Advanced ML services not available, skipping time series forecasting"
        )
        return {"status": "skipped", "reason": "advanced_ml_not_available"}

    try:
        logger.info(
            f"Starting time series forecasting for user {user_id or 'all users'}"
        )

        forecaster = TimeSeriesForecaster()
        results = {}

        # Get users to forecast for
        if user_id:
            users = [User.query.get(user_id)] if User.query.get(user_id) else []
        else:
            # Get active users with recent assignment data
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            users = (
                User.query.join(Term)
                .join(Course)
                .join(Assignment)
                .filter(Assignment.created_at > cutoff_date)
                .distinct()
                .limit(100)
                .all()
            )  # Limit for performance

        for user in users:
            try:
                logger.info(f"Generating forecasts for user {user.id}")

                # Get user's courses with sufficient data
                courses_with_data = []
                for term in user.terms:
                    for course in term.courses:
                        assignment_count = len(
                            [a for a in course.assignments if a.score is not None]
                        )
                        if assignment_count >= 5:  # Minimum for time series
                            courses_with_data.append(course)

                user_forecasts = {}

                for course in courses_with_data:
                    try:
                        # Generate performance trajectory forecast
                        forecast = forecaster.forecast_student_performance(
                            user.id, course.id
                        )

                        if forecast and forecast.get("success"):
                            # Detect risk periods
                            risk_analysis = forecaster.detect_risk_periods(
                                user.id, course.id
                            )

                            # Generate intervention recommendations
                            interventions = (
                                forecaster.generate_intervention_recommendations(
                                    user.id, course.id, forecast, risk_analysis
                                )
                            )

                            user_forecasts[course.id] = {
                                "forecast": forecast,
                                "risk_analysis": risk_analysis,
                                "interventions": interventions,
                            }

                        else:
                            user_forecasts[course.id] = {
                                "status": "failed",
                                "reason": "insufficient_data",
                            }

                    except Exception as e:
                        logger.error(
                            f"Error forecasting for user {user.id}, course {course.id}: {str(e)}"
                        )
                        user_forecasts[course.id] = {"status": "error", "error": str(e)}

                results[user.id] = {
                    "status": "success",
                    "courses_forecasted": len(
                        [
                            f
                            for f in user_forecasts.values()
                            if f.get("forecast", {}).get("success")
                        ]
                    ),
                    "total_courses": len(user_forecasts),
                    "forecasts": user_forecasts,
                }

            except Exception as e:
                logger.error(f"Error generating forecasts for user {user.id}: {str(e)}")
                results[user.id] = {"status": "error", "error": str(e)}

        logger.info(
            f"Time series forecasting completed. Users processed: {len(results)}"
        )

        return {
            "status": "success",
            "users_processed": len(results),
            "results": results,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in time series forecasting task: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@shared_task(bind=True, name="app.tasks.ml.monitor_model_performance")
def monitor_model_performance(self):
    """Monitor ML model performance and detect data/concept drift."""
    if not ADVANCED_ML_AVAILABLE:
        logger.warning("Advanced ML services not available, using basic evaluation")
        return evaluate_model_performance()

    try:
        logger.info("Starting advanced model performance monitoring")

        monitoring_service = MLMonitoringService()
        results = {}

        # Get all active models
        active_models = PredictionModel.query.filter_by(is_active=True).all()

        drift_detected = []
        performance_degraded = []

        for model in active_models:
            try:
                logger.info(f"Monitoring model {model.id} - {model.model_type}")

                # Detect data drift
                drift_result = monitoring_service.detect_data_drift(
                    model.course_id if hasattr(model, "course_id") else None,
                    model.user_id if hasattr(model, "user_id") else None,
                )

                # Monitor model performance
                performance_result = monitoring_service.monitor_model_performance(
                    model.course_id if hasattr(model, "course_id") else None,
                    model.user_id if hasattr(model, "user_id") else None,
                    model.model_type,
                )

                # Check for performance degradation
                degradation_check = monitoring_service.check_performance_degradation(
                    model.course_id if hasattr(model, "course_id") else None,
                    model.user_id if hasattr(model, "user_id") else None,
                )

                # Analyze results
                drift_detected_flag = drift_result.get("drift_detected", False)
                performance_degraded_flag = degradation_check.get(
                    "degradation_detected", False
                )

                if drift_detected_flag:
                    drift_detected.append(model.id)

                if performance_degraded_flag:
                    performance_degraded.append(model.id)

                # Store monitoring results
                results[model.id] = {
                    "model_type": model.model_type,
                    "course_id": getattr(model, "course_id", None),
                    "user_id": getattr(model, "user_id", None),
                    "drift_detection": drift_result,
                    "performance_monitoring": performance_result,
                    "degradation_check": degradation_check,
                    "needs_attention": drift_detected_flag or performance_degraded_flag,
                }

            except Exception as e:
                logger.error(f"Error monitoring model {model.id}: {str(e)}")
                results[model.id] = {"status": "error", "error": str(e)}

        # Trigger retraining for models with issues
        models_to_retrain = set()

        for model_id in drift_detected + performance_degraded:
            model = PredictionModel.query.get(model_id)
            if model:
                if hasattr(model, "course_id") and model.course_id:
                    # Schedule advanced model retraining
                    train_advanced_ml_models.delay(model.course_id, force_retrain=True)
                    models_to_retrain.add(model.course_id)
                elif hasattr(model, "user_id") and model.user_id:
                    # Schedule traditional model retraining
                    train_all_models.delay(model.user_id)
                    models_to_retrain.add(f"user_{model.user_id}")

        logger.info(
            f"Model monitoring completed. Drift detected: {len(drift_detected)}, "
            f"Performance degraded: {len(performance_degraded)}, "
            f"Retraining scheduled: {len(models_to_retrain)}"
        )

        return {
            "status": "success",
            "models_monitored": len(active_models),
            "drift_detected": len(drift_detected),
            "performance_degraded": len(performance_degraded),
            "retraining_scheduled": len(models_to_retrain),
            "results": results,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in model monitoring task: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@shared_task(bind=True, name="app.tasks.ml.manage_ab_tests")
def manage_ab_tests(self):
    """Manage A/B tests for model variants."""
    if not ADVANCED_ML_AVAILABLE:
        logger.warning(
            "Advanced ML services not available, skipping A/B test management"
        )
        return {"status": "skipped", "reason": "advanced_ml_not_available"}

    try:
        logger.info("Starting A/B test management")

        ab_framework = ABTestingFramework()
        results = {}

        # Get active A/B tests
        active_tests = ab_framework.get_active_tests()

        promoted_models = []
        concluded_tests = []

        for test_name, test_info in active_tests.items():
            try:
                logger.info(f"Managing A/B test: {test_name}")

                # Check test duration and sample size
                test_duration = (
                    datetime.utcnow() - test_info.get("start_date", datetime.utcnow())
                ).days
                sample_size = test_info.get("total_samples", 0)

                # Evaluate test results if sufficient data
                if test_duration >= 7 and sample_size >= 100:  # Minimum requirements
                    evaluation = ab_framework.evaluate_test_results(test_name)

                    if evaluation.get("statistical_significance", False):
                        # Check if challenger is better than champion
                        challenger_better = evaluation.get("challenger_better", False)

                        if challenger_better:
                            # Promote challenger to champion
                            promotion_result = ab_framework.promote_challenger(
                                test_name
                            )

                            if promotion_result.get("success"):
                                promoted_models.append(test_name)
                                logger.info(f"Promoted challenger in test {test_name}")

                        # Conclude the test
                        ab_framework.conclude_test(test_name)
                        concluded_tests.append(test_name)

                        results[test_name] = {
                            "status": "concluded",
                            "duration_days": test_duration,
                            "sample_size": sample_size,
                            "challenger_promoted": challenger_better,
                            "evaluation": evaluation,
                        }
                    else:
                        # Continue test - not significant yet
                        results[test_name] = {
                            "status": "continuing",
                            "duration_days": test_duration,
                            "sample_size": sample_size,
                            "significance": evaluation.get("p_value", 1.0),
                        }
                else:
                    # Test needs more time/data
                    results[test_name] = {
                        "status": "insufficient_data",
                        "duration_days": test_duration,
                        "sample_size": sample_size,
                        "min_duration": 7,
                        "min_samples": 100,
                    }

            except Exception as e:
                logger.error(f"Error managing A/B test {test_name}: {str(e)}")
                results[test_name] = {"status": "error", "error": str(e)}

        logger.info(
            f"A/B test management completed. Tests managed: {len(results)}, "
            f"Models promoted: {len(promoted_models)}, Tests concluded: {len(concluded_tests)}"
        )

        return {
            "status": "success",
            "tests_managed": len(results),
            "models_promoted": len(promoted_models),
            "tests_concluded": len(concluded_tests),
            "promoted_models": promoted_models,
            "concluded_tests": concluded_tests,
            "results": results,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in A/B test management task: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@shared_task(bind=True, name="app.tasks.ml.update_model_explanations")
def update_model_explanations(self, course_id: Optional[int] = None):
    """Update model explanations and interpretability data."""
    if not ADVANCED_ML_AVAILABLE:
        logger.warning(
            "Advanced ML services not available, skipping explanation updates"
        )
        return {"status": "skipped", "reason": "advanced_ml_not_available"}

    try:
        logger.info(
            f"Updating model explanations for course {course_id or 'all courses'}"
        )

        interpretability_service = ModelInterpretabilityService()
        results = {}

        # Get courses to update explanations for
        if course_id:
            courses = (
                [Course.query.get(course_id)] if Course.query.get(course_id) else []
            )
        else:
            # Get courses with active models
            courses = (
                Course.query.join(PredictionModel)
                .filter(PredictionModel.is_active == True)
                .distinct()
                .limit(20)
                .all()
            )  # Limit for performance

        for course in courses:
            try:
                logger.info(f"Updating explanations for course {course.id}")

                # Generate global feature importance
                global_importance = (
                    interpretability_service.get_global_feature_importance(course.id)
                )

                # Generate model insights
                model_insights = interpretability_service.get_model_insights(course.id)

                # Update explanation cache for recent predictions
                recent_predictions = (
                    GradePrediction.query.filter_by(course_id=course.id)
                    .filter(
                        GradePrediction.created_at
                        > datetime.utcnow() - timedelta(days=7)
                    )
                    .limit(50)
                    .all()
                )

                explanation_count = 0

                for prediction in recent_predictions:
                    try:
                        # Generate SHAP explanations
                        explanations = interpretability_service.explain_prediction(
                            course.id, prediction.user_id, include_counterfactuals=True
                        )

                        if explanations:
                            # Store explanations in prediction metadata
                            if not prediction.metadata:
                                prediction.metadata = {}

                            prediction.metadata["explanations"] = explanations
                            explanation_count += 1

                    except Exception as e:
                        logger.error(
                            f"Error updating explanation for prediction {prediction.id}: {str(e)}"
                        )

                db.session.commit()

                results[course.id] = {
                    "status": "success",
                    "global_importance_features": len(
                        global_importance.get("feature_importance", {})
                    ),
                    "model_insights_generated": len(model_insights.get("insights", [])),
                    "explanations_updated": explanation_count,
                    "predictions_processed": len(recent_predictions),
                }

            except Exception as e:
                logger.error(
                    f"Error updating explanations for course {course.id}: {str(e)}"
                )
                results[course.id] = {"status": "error", "error": str(e)}

        logger.info(
            f"Model explanation updates completed. Courses processed: {len(results)}"
        )

        return {
            "status": "success",
            "courses_processed": len(results),
            "results": results,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in model explanation update task: {str(e)}")
        db.session.rollback()
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@shared_task(bind=True, name="app.tasks.ml.comprehensive_ml_maintenance")
def comprehensive_ml_maintenance(self):
    """Comprehensive ML system maintenance - orchestrates all advanced ML tasks."""
    try:
        logger.info("Starting comprehensive ML system maintenance")

        maintenance_results = {}

        # 1. Collect fresh external data
        logger.info("Step 1: Collecting external data")
        external_data_result = collect_external_data.delay()
        maintenance_results["external_data"] = external_data_result.get(
            timeout=300
        )  # 5 min timeout

        # 2. Monitor model performance and detect drift
        logger.info("Step 2: Monitoring model performance")
        monitoring_result = monitor_model_performance.delay()
        maintenance_results["monitoring"] = monitoring_result.get(
            timeout=600
        )  # 10 min timeout

        # 3. Manage A/B tests
        logger.info("Step 3: Managing A/B tests")
        ab_test_result = manage_ab_tests.delay()
        maintenance_results["ab_tests"] = ab_test_result.get(timeout=300)

        # 4. Update model explanations
        logger.info("Step 4: Updating model explanations")
        explanations_result = update_model_explanations.delay()
        maintenance_results["explanations"] = explanations_result.get(timeout=600)

        # 5. Generate time series forecasts for priority users
        logger.info("Step 5: Generating time series forecasts")
        forecasting_result = generate_time_series_forecasts.delay()
        maintenance_results["forecasting"] = forecasting_result.get(
            timeout=900
        )  # 15 min timeout

        # 6. Clean up old models and data
        logger.info("Step 6: Cleaning up old models")
        cleanup_result = cleanup_old_models.delay()
        maintenance_results["cleanup"] = cleanup_result.get(timeout=300)

        # Analyze overall system health
        total_errors = sum(
            1
            for result in maintenance_results.values()
            if result.get("status") == "error"
        )

        system_health = (
            "healthy"
            if total_errors == 0
            else ("degraded" if total_errors <= 2 else "critical")
        )

        logger.info(
            f"Comprehensive ML maintenance completed. System health: {system_health}"
        )

        return {
            "status": "success",
            "system_health": system_health,
            "total_errors": total_errors,
            "maintenance_results": maintenance_results,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in comprehensive ML maintenance: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


# Sync versions for testing without Celery
def run_external_data_collection_sync():
    """Run external data collection synchronously for testing."""
    return collect_external_data()


def run_advanced_training_sync(course_id: Optional[int] = None):
    """Run advanced ML training synchronously for testing."""
    return train_advanced_ml_models(course_id)


def run_model_monitoring_sync():
    """Run model monitoring synchronously for testing."""
    return monitor_model_performance()


def run_ab_test_management_sync():
    """Run A/B test management synchronously for testing."""
    return manage_ab_tests()


if __name__ == "__main__":
    # Test the ML training system
    print("Testing ML training system...")
    result = run_ml_training_sync()
    print(f"Result: {result}")

    if ADVANCED_ML_AVAILABLE:
        print("\nTesting advanced ML features...")

        print("External data collection...")
        ext_result = run_external_data_collection_sync()
        print(f"External data result: {ext_result.get('status')}")

        print("Advanced model training...")
        adv_result = run_advanced_training_sync()
        print(f"Advanced training result: {adv_result.get('status')}")

        print("Model monitoring...")
        mon_result = run_model_monitoring_sync()
        print(f"Monitoring result: {mon_result.get('status')}")
    else:
        print("Advanced ML features not available - using basic functionality")
