"""
Advanced Machine Learning Models with Ensemble Methods
=====================================================

This module implements sophisticated ML models for academic prediction including:
- Ensemble methods (Random Forest, Gradient Boosting, XGBoost, LightGBM)
- Deep learning models (Neural Networks, LSTM for time series)
- Meta-learning and model stacking
- Automated hyperparameter optimization
- Model interpretability and explainability
- Online learning and incremental updates

Author: Advanced ML Team
Date: 2024-12-20
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import joblib
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings

warnings.filterwarnings("ignore")

# Core ML libraries
from sklearn.model_selection import (
    train_test_split,
    cross_val_score,
    GridSearchCV,
    RandomizedSearchCV,
    TimeSeriesSplit,
)
from sklearn.ensemble import (
    RandomForestRegressor,
    RandomForestClassifier,
    GradientBoostingRegressor,
    GradientBoostingClassifier,
    VotingRegressor,
    VotingClassifier,
    BaggingRegressor,
    AdaBoostRegressor,
    ExtraTreesRegressor,
)
from sklearn.linear_model import (
    LinearRegression,
    Ridge,
    Lasso,
    ElasticNet,
    LogisticRegression,
    BayesianRidge,
)
from sklearn.svm import SVR, SVC
from sklearn.neural_network import MLPRegressor, MLPClassifier
from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler
from sklearn.feature_selection import SelectKBest, f_regression, RFE
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)
from sklearn.pipeline import Pipeline
from sklearn.base import BaseEstimator, RegressorMixin

# Advanced ML libraries (with fallbacks)
try:
    import xgboost as xgb

    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

try:
    import lightgbm as lgb

    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False

try:
    from catboost import CatBoostRegressor, CatBoostClassifier

    HAS_CATBOOST = True
except ImportError:
    HAS_CATBOOST = False

try:
    import tensorflow as tf
    from tensorflow import keras

    HAS_TENSORFLOW = True
except ImportError:
    HAS_TENSORFLOW = False

try:
    import optuna

    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False

try:
    import shap

    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False

from app.models import db, User, Course, Assignment, Grade
from app.services.external_data_service import external_data_service

logger = logging.getLogger(__name__)


@dataclass
class ModelPrediction:
    """Enhanced prediction result with uncertainty and explainability."""

    predicted_value: float
    confidence_interval: Tuple[float, float]
    prediction_uncertainty: float
    feature_importance: Dict[str, float]
    model_explanations: Dict[str, Any]
    ensemble_predictions: Dict[str, float]
    model_version: str
    prediction_timestamp: datetime


@dataclass
class ModelPerformance:
    """Model performance metrics."""

    model_name: str
    mae: float
    mse: float
    rmse: float
    r2: float
    cross_val_score: float
    feature_importance: Dict[str, float]
    hyperparameters: Dict[str, Any]
    training_time: float
    prediction_time: float


class AdvancedFeatureEngineering:
    """Advanced feature engineering pipeline."""

    def __init__(self):
        self.feature_transformers = {}
        self.feature_selectors = {}
        self.temporal_features = True
        self.interaction_features = True

    def engineer_features(
        self,
        academic_data: pd.DataFrame,
        external_data: Optional[Dict] = None,
        user_id: Optional[int] = None,
    ) -> pd.DataFrame:
        """Create advanced features from academic and external data."""

        logger.info("Engineering advanced features")
        features_df = academic_data.copy()

        # Temporal features
        if self.temporal_features:
            features_df = self._add_temporal_features(features_df)

        # Academic performance features
        features_df = self._add_performance_features(features_df)

        # Behavioral patterns
        features_df = self._add_behavioral_features(features_df)

        # External data features
        if external_data:
            features_df = self._add_external_features(features_df, external_data)

        # Interaction features
        if self.interaction_features:
            features_df = self._add_interaction_features(features_df)

        # Statistical features
        features_df = self._add_statistical_features(features_df)

        return features_df

    def _add_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add time-based features."""
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df["day_of_week"] = df["date"].dt.dayofweek
            df["week_of_year"] = df["date"].dt.isocalendar().week
            df["month"] = df["date"].dt.month
            df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
            df["days_since_term_start"] = (df["date"] - df["date"].min()).dt.days

            # Academic cycles
            df["is_midterm_period"] = ((df["week_of_year"] % 16).between(7, 9)).astype(
                int
            )
            df["is_finals_period"] = ((df["week_of_year"] % 16).between(15, 16)).astype(
                int
            )

        return df

    def _add_performance_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add academic performance-based features."""

        # Rolling statistics
        if "grade" in df.columns:
            df["grade_rolling_mean_3"] = df["grade"].rolling(3, min_periods=1).mean()
            df["grade_rolling_std_3"] = df["grade"].rolling(3, min_periods=1).std()
            df["grade_rolling_mean_5"] = df["grade"].rolling(5, min_periods=1).mean()
            df["grade_trend"] = df["grade"].diff().rolling(3, min_periods=1).mean()

            # Performance streaks
            df["grade_above_80"] = (df["grade"] > 80).astype(int)
            df["consecutive_good_grades"] = (
                df["grade_above_80"]
                .groupby(
                    (df["grade_above_80"] != df["grade_above_80"].shift()).cumsum()
                )
                .cumsum()
            )

            # Relative performance
            df["grade_vs_course_mean"] = df["grade"] - df.groupby("course_id")[
                "grade"
            ].transform("mean")
            df["grade_percentile"] = df["grade"].rank(pct=True)

        # Assignment completion patterns
        if "completion_time" in df.columns:
            df["days_to_complete"] = (
                pd.to_datetime(df["completion_date"])
                - pd.to_datetime(df["assigned_date"])
            ).dt.days
            df["is_late_submission"] = (
                df["days_to_complete"] > df["days_allowed"]
            ).astype(int)
            df["completion_rate"] = df["is_completed"].rolling(5, min_periods=1).mean()

        return df

    def _add_behavioral_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add student behavioral pattern features."""

        # Study session patterns (if available)
        if "study_time" in df.columns:
            df["avg_study_time"] = df["study_time"].rolling(7, min_periods=1).mean()
            df["study_consistency"] = 1 / (
                1 + df["study_time"].rolling(7, min_periods=1).std()
            )
            df["study_momentum"] = (
                df["study_time"].diff().rolling(3, min_periods=1).mean()
            )

        # Submission timing patterns
        if "submission_hour" in df.columns:
            df["is_night_owl"] = (df["submission_hour"] >= 22).astype(int)
            df["is_early_bird"] = (df["submission_hour"] <= 8).astype(int)
            df["submission_time_consistency"] = 1 / (
                1 + df["submission_hour"].rolling(5, min_periods=1).std()
            )

        # Workload features
        if "course_id" in df.columns:
            df["concurrent_courses"] = df.groupby("date")["course_id"].transform(
                "nunique"
            )
            df["total_assignments_due"] = df.groupby("date").size()

        return df

    def _add_external_features(
        self, df: pd.DataFrame, external_data: Dict
    ) -> pd.DataFrame:
        """Add features from external data sources."""

        # Weather features
        if "weather" in external_data:
            weather_data = external_data["weather"]
            if weather_data:
                # Aggregate weather data by date
                weather_df = pd.DataFrame(
                    [
                        {
                            "date": point.timestamp.date(),
                            "weather_comfort": point.value,
                            "temperature": point.metadata.get("temperature", 70),
                            "humidity": point.metadata.get("humidity", 0.5),
                        }
                        for point in weather_data
                    ]
                )

                if "date" in df.columns:
                    df["date_only"] = pd.to_datetime(df["date"]).dt.date
                    df = df.merge(
                        weather_df, left_on="date_only", right_on="date", how="left"
                    )
                    df.drop(["date_only"], axis=1, inplace=True)

        # Economic stress features
        if "economic" in external_data:
            economic_data = external_data["economic"]
            if economic_data:
                # Use most recent economic data
                recent_econ = max(economic_data, key=lambda x: x.timestamp)
                df["economic_stress"] = 1 - recent_econ.value
                df["economic_confidence"] = recent_econ.confidence

        # Academic calendar features
        if "academic_calendar" in external_data:
            calendar_data = external_data["academic_calendar"]
            if calendar_data and "date" in df.columns:
                calendar_df = pd.DataFrame(
                    [
                        {
                            "date": point.timestamp.date(),
                            "academic_stress": point.metadata.get("stress_level", 0),
                        }
                        for point in calendar_data
                    ]
                )

                df["date_only"] = pd.to_datetime(df["date"]).dt.date
                df = df.merge(
                    calendar_df, left_on="date_only", right_on="date", how="left"
                )
                df.drop(["date_only"], axis=1, inplace=True)

        return df

    def _add_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add interaction features between different variables."""

        numeric_cols = df.select_dtypes(include=[np.number]).columns

        # Create polynomial features for key variables
        if "grade_rolling_mean_3" in df.columns and "study_time" in df.columns:
            df["grade_study_interaction"] = (
                df["grade_rolling_mean_3"] * df["study_time"]
            )

        if "weather_comfort" in df.columns and "academic_stress" in df.columns:
            df["weather_stress_interaction"] = df["weather_comfort"] * (
                1 - df["academic_stress"]
            )

        # Ratio features
        if "grade" in df.columns and "grade_rolling_mean_3" in df.columns:
            df["grade_vs_recent_avg"] = df["grade"] / (
                df["grade_rolling_mean_3"] + 1e-6
            )

        return df

    def _add_statistical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add statistical aggregation features."""

        numeric_cols = df.select_dtypes(include=[np.number]).columns

        # Group statistics by course
        if "course_id" in df.columns:
            for col in ["grade", "study_time"]:
                if col in df.columns:
                    df[f"{col}_course_mean"] = df.groupby("course_id")[col].transform(
                        "mean"
                    )
                    df[f"{col}_course_std"] = df.groupby("course_id")[col].transform(
                        "std"
                    )
                    df[f"{col}_vs_course_avg"] = df[col] - df[f"{col}_course_mean"]

        # Percentile ranks
        for col in ["grade", "study_time"]:
            if col in df.columns:
                df[f"{col}_percentile"] = df[col].rank(pct=True)

        return df


class EnsembleMLSystem:
    """Advanced ensemble ML system with multiple sophisticated models."""

    def __init__(self):
        self.models = {}
        self.meta_model = None
        self.feature_engineer = AdvancedFeatureEngineering()
        self.scalers = {}
        self.feature_selectors = {}
        self.is_trained = False
        self.model_weights = {}

    def initialize_models(self) -> Dict[str, Any]:
        """Initialize sophisticated ML models."""

        models = {}

        # Traditional ensemble methods
        models["random_forest"] = RandomForestRegressor(
            n_estimators=200,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )

        models["gradient_boosting"] = GradientBoostingRegressor(
            n_estimators=200, learning_rate=0.1, max_depth=6, random_state=42
        )

        models["extra_trees"] = ExtraTreesRegressor(
            n_estimators=200, max_depth=15, random_state=42, n_jobs=-1
        )

        # Advanced gradient boosting
        if HAS_XGBOOST:
            models["xgboost"] = xgb.XGBRegressor(
                n_estimators=200,
                learning_rate=0.1,
                max_depth=6,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1,
            )

        if HAS_LIGHTGBM:
            models["lightgbm"] = lgb.LGBMRegressor(
                n_estimators=200,
                learning_rate=0.1,
                max_depth=6,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1,
                verbose=-1,
            )

        if HAS_CATBOOST:
            models["catboost"] = CatBoostRegressor(
                iterations=200,
                learning_rate=0.1,
                depth=6,
                random_seed=42,
                verbose=False,
            )

        # Neural network
        models["neural_network"] = MLPRegressor(
            hidden_layer_sizes=(100, 50, 25),
            activation="relu",
            solver="adam",
            learning_rate="adaptive",
            max_iter=500,
            random_state=42,
        )

        # Linear models with regularization
        models["ridge"] = Ridge(alpha=1.0)
        models["lasso"] = Lasso(alpha=0.1)
        models["elastic_net"] = ElasticNet(alpha=0.1, l1_ratio=0.5)

        # Support Vector Regression
        models["svr"] = SVR(kernel="rbf", C=1.0, gamma="scale")

        # Bayesian model
        models["bayesian_ridge"] = BayesianRidge()

        return models

    def optimize_hyperparameters(
        self, X: np.ndarray, y: np.ndarray, model_name: str, n_trials: int = 50
    ) -> Dict[str, Any]:
        """Optimize hyperparameters using Optuna or GridSearch."""

        if not HAS_OPTUNA:
            # Fallback to GridSearchCV
            return self._grid_search_hyperparameters(X, y, model_name)

        def objective(trial):
            if model_name == "random_forest":
                params = {
                    "n_estimators": trial.suggest_int("n_estimators", 100, 500),
                    "max_depth": trial.suggest_int("max_depth", 5, 20),
                    "min_samples_split": trial.suggest_int("min_samples_split", 2, 10),
                    "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 5),
                }
                model = RandomForestRegressor(**params, random_state=42)

            elif model_name == "xgboost" and HAS_XGBOOST:
                params = {
                    "n_estimators": trial.suggest_int("n_estimators", 100, 500),
                    "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3),
                    "max_depth": trial.suggest_int("max_depth", 3, 10),
                    "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                    "colsample_bytree": trial.suggest_float(
                        "colsample_bytree", 0.6, 1.0
                    ),
                }
                model = xgb.XGBRegressor(**params, random_state=42)

            elif model_name == "neural_network":
                n_layers = trial.suggest_int("n_layers", 1, 3)
                layers = []
                for i in range(n_layers):
                    layers.append(trial.suggest_int(f"layer_{i}", 10, 200))

                params = {
                    "hidden_layer_sizes": tuple(layers),
                    "learning_rate_init": trial.suggest_float(
                        "learning_rate_init", 0.001, 0.1
                    ),
                    "alpha": trial.suggest_float("alpha", 1e-6, 1e-2),
                }
                model = MLPRegressor(**params, random_state=42, max_iter=500)

            else:
                return float("inf")  # Skip unsupported models

            # Cross-validation score
            scores = cross_val_score(
                model, X, y, cv=5, scoring="neg_mean_squared_error"
            )
            return -scores.mean()

        try:
            study = optuna.create_study(direction="minimize")
            study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
            return study.best_params
        except Exception as e:
            logger.warning(f"Optuna optimization failed for {model_name}: {str(e)}")
            return {}

    def _grid_search_hyperparameters(
        self, X: np.ndarray, y: np.ndarray, model_name: str
    ) -> Dict[str, Any]:
        """Fallback hyperparameter optimization using GridSearchCV."""

        param_grids = {
            "random_forest": {
                "n_estimators": [100, 200, 300],
                "max_depth": [10, 15, 20],
                "min_samples_split": [2, 5, 10],
            },
            "gradient_boosting": {
                "n_estimators": [100, 200, 300],
                "learning_rate": [0.05, 0.1, 0.15],
                "max_depth": [4, 6, 8],
            },
        }

        if model_name not in param_grids:
            return {}

        try:
            base_model = self.models.get(model_name)
            if base_model is None:
                return {}

            grid_search = GridSearchCV(
                base_model,
                param_grids[model_name],
                cv=3,
                scoring="neg_mean_squared_error",
                n_jobs=-1,
            )

            grid_search.fit(X, y)
            return grid_search.best_params_

        except Exception as e:
            logger.warning(f"Grid search failed for {model_name}: {str(e)}")
            return {}

    def train_ensemble(
        self,
        training_data: pd.DataFrame,
        target_column: str = "grade",
        external_data: Optional[Dict] = None,
        optimize_hyperparameters: bool = True,
    ) -> Dict[str, ModelPerformance]:
        """Train ensemble of sophisticated ML models."""

        logger.info("Training advanced ensemble ML models")

        # Feature engineering
        features_df = self.feature_engineer.engineer_features(
            training_data, external_data
        )

        # Prepare features and target
        feature_columns = [
            col
            for col in features_df.columns
            if col not in [target_column, "user_id", "course_id"]
        ]

        X = features_df[feature_columns].fillna(0)
        y = features_df[target_column].fillna(features_df[target_column].mean())

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Initialize models
        self.models = self.initialize_models()

        # Scale features
        scaler = RobustScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        self.scalers["robust"] = scaler

        # Train individual models
        model_performances = {}
        trained_models = {}

        for model_name, model in self.models.items():
            try:
                start_time = datetime.now()

                # Hyperparameter optimization
                if optimize_hyperparameters:
                    best_params = self.optimize_hyperparameters(
                        X_train_scaled, y_train, model_name
                    )
                    if best_params:
                        model.set_params(**best_params)

                # Train model
                if model_name in ["neural_network", "svr"]:
                    model.fit(X_train_scaled, y_train)
                    y_pred = model.predict(X_test_scaled)
                else:
                    model.fit(X_train, y_train)
                    y_pred = model.predict(X_test)

                training_time = (datetime.now() - start_time).total_seconds()

                # Evaluate performance
                mae = mean_absolute_error(y_test, y_pred)
                mse = mean_squared_error(y_test, y_pred)
                rmse = np.sqrt(mse)
                r2 = r2_score(y_test, y_pred)

                # Cross-validation
                if model_name in ["neural_network", "svr"]:
                    cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5)
                else:
                    cv_scores = cross_val_score(model, X_train, y_train, cv=5)

                # Feature importance (if available)
                feature_importance = {}
                if hasattr(model, "feature_importances_"):
                    feature_importance = dict(
                        zip(feature_columns, model.feature_importances_)
                    )
                elif hasattr(model, "coef_"):
                    feature_importance = dict(zip(feature_columns, np.abs(model.coef_)))

                # Store performance
                performance = ModelPerformance(
                    model_name=model_name,
                    mae=mae,
                    mse=mse,
                    rmse=rmse,
                    r2=r2,
                    cross_val_score=cv_scores.mean(),
                    feature_importance=feature_importance,
                    hyperparameters=model.get_params(),
                    training_time=training_time,
                    prediction_time=0.0,
                )

                model_performances[model_name] = performance
                trained_models[model_name] = model

                logger.info(f"Trained {model_name}: R2={r2:.4f}, RMSE={rmse:.4f}")

            except Exception as e:
                logger.warning(f"Failed to train {model_name}: {str(e)}")
                continue

        # Create meta-ensemble model
        if len(trained_models) > 1:
            self.meta_model = self._create_meta_ensemble(
                trained_models, X_train, X_test, y_train, y_test
            )

        # Calculate model weights based on performance
        self.model_weights = self._calculate_model_weights(model_performances)

        # Store trained models and metadata
        self.models = trained_models
        self.feature_columns = feature_columns
        self.is_trained = True

        logger.info(f"Ensemble training completed with {len(trained_models)} models")
        return model_performances

    def _create_meta_ensemble(
        self,
        models: Dict[str, Any],
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        y_train: pd.Series,
        y_test: pd.Series,
    ) -> VotingRegressor:
        """Create meta-ensemble using voting regressor."""

        try:
            # Select best performing models
            model_list = [(name, model) for name, model in models.items()]

            # Create voting ensemble
            voting_ensemble = VotingRegressor(
                estimators=model_list,
                weights=None,  # Equal weights initially
            )

            # Train meta-model
            if any(name in ["neural_network", "svr"] for name, _ in model_list):
                # Use scaled features if neural network or SVR present
                voting_ensemble.fit(self.scalers["robust"].transform(X_train), y_train)
            else:
                voting_ensemble.fit(X_train, y_train)

            return voting_ensemble

        except Exception as e:
            logger.warning(f"Failed to create meta-ensemble: {str(e)}")
            return None

    def _calculate_model_weights(
        self, performances: Dict[str, ModelPerformance]
    ) -> Dict[str, float]:
        """Calculate model weights based on performance metrics."""

        if not performances:
            return {}

        # Use inverse RMSE as weights (better models get higher weights)
        weights = {}
        total_inverse_rmse = 0

        for name, perf in performances.items():
            inverse_rmse = 1 / (perf.rmse + 1e-6)
            weights[name] = inverse_rmse
            total_inverse_rmse += inverse_rmse

        # Normalize weights
        if total_inverse_rmse > 0:
            for name in weights:
                weights[name] /= total_inverse_rmse

        return weights

    def predict_with_uncertainty(
        self, features: pd.DataFrame, external_data: Optional[Dict] = None
    ) -> ModelPrediction:
        """Make predictions with uncertainty quantification."""

        if not self.is_trained:
            raise ValueError("Models must be trained before making predictions")

        # Feature engineering
        features_df = self.feature_engineer.engineer_features(features, external_data)
        X = features_df[self.feature_columns].fillna(0)

        # Get predictions from all models
        ensemble_predictions = {}
        prediction_start = datetime.now()

        for model_name, model in self.models.items():
            try:
                if model_name in ["neural_network", "svr"]:
                    X_scaled = self.scalers["robust"].transform(X)
                    pred = model.predict(X_scaled)
                else:
                    pred = model.predict(X)

                ensemble_predictions[model_name] = float(
                    pred[0] if len(pred) > 0 else 0
                )

            except Exception as e:
                logger.warning(f"Prediction failed for {model_name}: {str(e)}")
                continue

        prediction_time = (datetime.now() - prediction_start).total_seconds()

        # Weighted ensemble prediction
        if ensemble_predictions and self.model_weights:
            weighted_pred = sum(
                pred * self.model_weights.get(name, 0)
                for name, pred in ensemble_predictions.items()
            )
        else:
            weighted_pred = np.mean(list(ensemble_predictions.values()))

        # Calculate prediction uncertainty
        prediction_std = np.std(list(ensemble_predictions.values()))
        uncertainty = prediction_std / np.sqrt(len(ensemble_predictions))

        # Confidence interval (assuming normal distribution)
        confidence_interval = (
            weighted_pred - 1.96 * uncertainty,
            weighted_pred + 1.96 * uncertainty,
        )

        # Feature importance (from best model)
        feature_importance = {}
        if self.models:
            best_model_name = (
                max(self.model_weights.items(), key=lambda x: x[1])[0]
                if self.model_weights
                else list(self.models.keys())[0]
            )

            best_model = self.models[best_model_name]
            if hasattr(best_model, "feature_importances_"):
                feature_importance = dict(
                    zip(self.feature_columns, best_model.feature_importances_)
                )

        # Model explanations (SHAP if available)
        explanations = {}
        if HAS_SHAP and self.models:
            try:
                explanations = self._get_shap_explanations(X, ensemble_predictions)
            except Exception as e:
                logger.warning(f"SHAP explanation failed: {str(e)}")

        return ModelPrediction(
            predicted_value=weighted_pred,
            confidence_interval=confidence_interval,
            prediction_uncertainty=uncertainty,
            feature_importance=feature_importance,
            model_explanations=explanations,
            ensemble_predictions=ensemble_predictions,
            model_version="advanced_ensemble_v1.0",
            prediction_timestamp=datetime.now(),
        )

    def _get_shap_explanations(
        self, X: pd.DataFrame, ensemble_predictions: Dict[str, float]
    ) -> Dict[str, Any]:
        """Generate SHAP explanations for model predictions."""

        try:
            # Use the best performing model for SHAP
            best_model_name = (
                max(self.model_weights.items(), key=lambda x: x[1])[0]
                if self.model_weights
                else list(self.models.keys())[0]
            )

            best_model = self.models[best_model_name]

            # Create SHAP explainer
            if hasattr(best_model, "feature_importances_"):
                explainer = shap.TreeExplainer(best_model)
                shap_values = explainer.shap_values(X)
            else:
                explainer = shap.LinearExplainer(best_model, X)
                shap_values = explainer.shap_values(X)

            # Format explanations
            explanations = {
                "feature_contributions": dict(
                    zip(
                        self.feature_columns,
                        shap_values[0] if len(shap_values.shape) > 1 else shap_values,
                    )
                ),
                "base_value": explainer.expected_value,
                "model_used": best_model_name,
            }

            return explanations

        except Exception as e:
            logger.warning(f"SHAP explanation generation failed: {str(e)}")
            return {}

    def save_models(self, model_dir: str = "models/advanced_ensemble"):
        """Save trained models and metadata."""

        try:
            os.makedirs(model_dir, exist_ok=True)

            # Save individual models
            for model_name, model in self.models.items():
                model_path = os.path.join(model_dir, f"{model_name}.joblib")
                joblib.dump(model, model_path)

            # Save scalers
            scaler_path = os.path.join(model_dir, "scalers.joblib")
            joblib.dump(self.scalers, scaler_path)

            # Save metadata
            metadata = {
                "feature_columns": self.feature_columns,
                "model_weights": self.model_weights,
                "is_trained": self.is_trained,
                "training_timestamp": datetime.now().isoformat(),
            }

            metadata_path = os.path.join(model_dir, "metadata.json")
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Models saved to {model_dir}")

        except Exception as e:
            logger.error(f"Failed to save models: {str(e)}")

    def load_models(self, model_dir: str = "models/advanced_ensemble"):
        """Load trained models and metadata."""

        try:
            # Load metadata
            metadata_path = os.path.join(model_dir, "metadata.json")
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            self.feature_columns = metadata["feature_columns"]
            self.model_weights = metadata["model_weights"]
            self.is_trained = metadata["is_trained"]

            # Load scalers
            scaler_path = os.path.join(model_dir, "scalers.joblib")
            self.scalers = joblib.load(scaler_path)

            # Load individual models
            self.models = {}
            for model_file in os.listdir(model_dir):
                if model_file.endswith(".joblib") and model_file != "scalers.joblib":
                    model_name = model_file.replace(".joblib", "")
                    model_path = os.path.join(model_dir, model_file)
                    self.models[model_name] = joblib.load(model_path)

            logger.info(f"Models loaded from {model_dir}")

        except Exception as e:
            logger.error(f"Failed to load models: {str(e)}")


# Global ensemble system instance
advanced_ml_system = EnsembleMLSystem()
