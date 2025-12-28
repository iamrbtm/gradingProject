"""
Advanced Time Series Forecasting for Academic Performance
========================================================

This module provides sophisticated time series forecasting capabilities including:
- LSTM and GRU neural networks for grade sequence prediction
- ARIMA and seasonal decomposition
- Prophet for trend and seasonality analysis
- Multi-step ahead forecasting
- Uncertainty quantification
- Regime change detection
- Personalized student trajectory modeling

Author: Time Series ML Team
Date: 2024-12-20
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import warnings

warnings.filterwarnings("ignore")

# Core time series libraries
try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.seasonal import seasonal_decompose
    from statsmodels.tsa.stattools import adfuller
    from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

try:
    from prophet import Prophet

    HAS_PROPHET = True
except ImportError:
    HAS_PROPHET = False

# Deep learning for time series (with fallbacks)
try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras.layers import LSTM, GRU, Dense, Dropout, BatchNormalization
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

    HAS_TENSORFLOW = True
except ImportError:
    HAS_TENSORFLOW = False

try:
    from sklearn.preprocessing import MinMaxScaler, StandardScaler
    from sklearn.metrics import mean_absolute_error, mean_squared_error

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

from app.models import db, User, Course, Assignment, Grade

logger = logging.getLogger(__name__)


@dataclass
class TimeSeriesForecast:
    """Time series forecast result with confidence intervals."""

    forecasted_values: List[float]
    confidence_intervals: List[Tuple[float, float]]
    forecast_dates: List[datetime]
    model_type: str
    forecast_horizon: int
    model_confidence: float
    trend_analysis: Dict[str, Any]
    seasonality_analysis: Dict[str, Any]
    anomaly_detection: List[Dict[str, Any]]


@dataclass
class StudentTrajectory:
    """Complete student performance trajectory analysis."""

    user_id: int
    historical_performance: pd.Series
    trend_direction: str
    trend_strength: float
    seasonal_patterns: Dict[str, float]
    performance_volatility: float
    risk_periods: List[Dict[str, Any]]
    improvement_periods: List[Dict[str, Any]]
    projected_trajectory: TimeSeriesForecast
    intervention_recommendations: List[str]


class AdvancedTimeSeriesForecaster:
    """
    Advanced time series forecasting system for academic performance prediction.
    """

    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.is_trained = False
        self.sequence_length = 10  # Look back 10 time periods
        self.forecast_horizon = 5  # Predict 5 periods ahead

    def prepare_time_series_data(
        self, user_id: int, course_id: Optional[int] = None, min_data_points: int = 15
    ) -> pd.DataFrame:
        """
        Prepare time series data for a specific user and optionally course.

        Args:
            user_id: User ID for time series
            course_id: Optional course ID for course-specific analysis
            min_data_points: Minimum required data points

        Returns:
            DataFrame with time series data
        """
        try:
            # Query grade data
            query = db.session.query(Grade).join(Assignment).join(Course)
            query = query.filter(Course.term.has(user_id=user_id))

            if course_id:
                query = query.filter(Course.id == course_id)

            grades = query.order_by(Grade.date_recorded).all()

            if len(grades) < min_data_points:
                logger.warning(
                    f"Insufficient data points for user {user_id}: {len(grades)}"
                )
                return pd.DataFrame()

            # Create time series DataFrame
            data = []
            for grade in grades:
                data.append(
                    {
                        "date": grade.date_recorded,
                        "grade": float(grade.grade),
                        "assignment_type": grade.assignment.assignment_type,
                        "course_id": grade.assignment.course_id,
                        "course_name": grade.assignment.course.name,
                        "assignment_weight": float(grade.assignment.weight or 1.0),
                        "is_major_assignment": grade.assignment.assignment_type
                        in ["exam", "project"],
                    }
                )

            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)

            # Add time-based features
            df["day_of_week"] = df["date"].dt.dayofweek
            df["week_of_year"] = df["date"].dt.isocalendar().week
            df["month"] = df["date"].dt.month
            df["days_since_start"] = (df["date"] - df["date"].min()).dt.days

            # Add rolling statistics
            df["grade_ma_3"] = df["grade"].rolling(3, min_periods=1).mean()
            df["grade_ma_5"] = df["grade"].rolling(5, min_periods=1).mean()
            df["grade_std_3"] = df["grade"].rolling(3, min_periods=1).std()
            df["grade_trend"] = df["grade"].diff().rolling(3, min_periods=1).mean()

            # Performance streaks
            df["above_80"] = (df["grade"] > 80).astype(int)
            df["consecutive_good"] = (
                df["above_80"]
                .groupby((df["above_80"] != df["above_80"].shift()).cumsum())
                .cumsum()
            )

            return df

        except Exception as e:
            logger.error(f"Error preparing time series data: {str(e)}")
            return pd.DataFrame()

    def create_lstm_sequences(
        self, data: np.ndarray, sequence_length: int, forecast_horizon: int = 1
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for LSTM training."""

        X, y = [], []

        for i in range(len(data) - sequence_length - forecast_horizon + 1):
            # Input sequence
            X.append(data[i : (i + sequence_length)])

            # Target (next forecast_horizon values)
            if forecast_horizon == 1:
                y.append(data[i + sequence_length])
            else:
                y.append(
                    data[
                        (i + sequence_length) : (i + sequence_length + forecast_horizon)
                    ]
                )

        return np.array(X), np.array(y)

    def build_lstm_model(
        self, input_shape: Tuple[int, int], forecast_horizon: int = 1
    ) -> keras.Model:
        """Build LSTM model for grade prediction."""

        if not HAS_TENSORFLOW:
            raise ImportError("TensorFlow required for LSTM models")

        model = Sequential(
            [
                LSTM(100, return_sequences=True, input_shape=input_shape),
                Dropout(0.2),
                BatchNormalization(),
                LSTM(50, return_sequences=True),
                Dropout(0.2),
                BatchNormalization(),
                LSTM(25, return_sequences=False),
                Dropout(0.2),
                Dense(25, activation="relu"),
                Dropout(0.1),
                Dense(forecast_horizon),
            ]
        )

        model.compile(optimizer=Adam(learning_rate=0.001), loss="mse", metrics=["mae"])

        return model

    def build_gru_model(
        self, input_shape: Tuple[int, int], forecast_horizon: int = 1
    ) -> keras.Model:
        """Build GRU model for grade prediction."""

        if not HAS_TENSORFLOW:
            raise ImportError("TensorFlow required for GRU models")

        model = Sequential(
            [
                GRU(80, return_sequences=True, input_shape=input_shape),
                Dropout(0.2),
                BatchNormalization(),
                GRU(40, return_sequences=True),
                Dropout(0.2),
                BatchNormalization(),
                GRU(20, return_sequences=False),
                Dropout(0.2),
                Dense(20, activation="relu"),
                Dropout(0.1),
                Dense(forecast_horizon),
            ]
        )

        model.compile(optimizer=Adam(learning_rate=0.001), loss="mse", metrics=["mae"])

        return model

    def train_neural_network_models(
        self, df: pd.DataFrame, target_column: str = "grade"
    ) -> Dict[str, Any]:
        """Train LSTM and GRU models on time series data."""

        if not HAS_TENSORFLOW or not HAS_SKLEARN:
            logger.warning(
                "TensorFlow or scikit-learn not available for neural network training"
            )
            return {}

        try:
            # Prepare features
            feature_columns = [
                "grade",
                "grade_ma_3",
                "grade_ma_5",
                "grade_std_3",
                "assignment_weight",
                "is_major_assignment",
                "day_of_week",
            ]

            # Use available columns only
            available_columns = [col for col in feature_columns if col in df.columns]
            if not available_columns:
                logger.warning("No suitable feature columns found")
                return {}

            # Scale data
            scaler = MinMaxScaler()
            scaled_data = scaler.fit_transform(df[available_columns])
            self.scalers["neural_network"] = scaler

            # Create sequences
            X, y = self.create_lstm_sequences(
                scaled_data, self.sequence_length, self.forecast_horizon
            )

            if len(X) < 10:  # Minimum samples for training
                logger.warning("Insufficient sequences for neural network training")
                return {}

            # Split data
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]

            models = {}

            # Train LSTM model
            try:
                lstm_model = self.build_lstm_model(
                    (self.sequence_length, len(available_columns)),
                    self.forecast_horizon,
                )

                # Callbacks
                early_stopping = EarlyStopping(
                    monitor="val_loss", patience=10, restore_best_weights=True
                )

                reduce_lr = ReduceLROnPlateau(
                    monitor="val_loss", factor=0.5, patience=5, min_lr=1e-6
                )

                # Train LSTM
                lstm_history = lstm_model.fit(
                    X_train,
                    y_train,
                    epochs=100,
                    batch_size=16,
                    validation_data=(X_test, y_test),
                    callbacks=[early_stopping, reduce_lr],
                    verbose=0,
                )

                models["lstm"] = {
                    "model": lstm_model,
                    "history": lstm_history.history,
                    "type": "lstm",
                }

                logger.info("LSTM model trained successfully")

            except Exception as e:
                logger.warning(f"LSTM training failed: {str(e)}")

            # Train GRU model
            try:
                gru_model = self.build_gru_model(
                    (self.sequence_length, len(available_columns)),
                    self.forecast_horizon,
                )

                # Train GRU
                gru_history = gru_model.fit(
                    X_train,
                    y_train,
                    epochs=100,
                    batch_size=16,
                    validation_data=(X_test, y_test),
                    callbacks=[early_stopping, reduce_lr],
                    verbose=0,
                )

                models["gru"] = {
                    "model": gru_model,
                    "history": gru_history.history,
                    "type": "gru",
                }

                logger.info("GRU model trained successfully")

            except Exception as e:
                logger.warning(f"GRU training failed: {str(e)}")

            # Store models and metadata
            self.models.update(models)
            self.feature_columns = available_columns

            return models

        except Exception as e:
            logger.error(f"Neural network training failed: {str(e)}")
            return {}

    def train_prophet_model(self, df: pd.DataFrame) -> Optional[Prophet]:
        """Train Prophet model for trend and seasonality analysis."""

        if not HAS_PROPHET:
            logger.warning("Prophet not available for time series forecasting")
            return None

        try:
            # Prepare Prophet data format
            prophet_df = pd.DataFrame({"ds": df["date"], "y": df["grade"]})

            # Remove any duplicate dates by aggregating
            prophet_df = prophet_df.groupby("ds")["y"].mean().reset_index()

            if len(prophet_df) < 10:
                logger.warning("Insufficient data for Prophet model")
                return None

            # Initialize and fit Prophet
            model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=True,
                daily_seasonality=False,
                changepoint_prior_scale=0.1,
                seasonality_prior_scale=10.0,
            )

            # Add custom seasonalities
            model.add_seasonality(name="monthly", period=30.5, fourier_order=5)
            model.add_seasonality(name="semester", period=120, fourier_order=3)

            model.fit(prophet_df)

            self.models["prophet"] = model
            logger.info("Prophet model trained successfully")

            return model

        except Exception as e:
            logger.error(f"Prophet training failed: {str(e)}")
            return None

    def train_arima_model(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Train ARIMA model for classical time series analysis."""

        if not HAS_STATSMODELS:
            logger.warning("Statsmodels not available for ARIMA modeling")
            return None

        try:
            # Prepare time series
            ts = (
                df.set_index("date")["grade"]
                .resample("D")
                .mean()
                .fillna(method="ffill")
            )

            if len(ts) < 20:
                logger.warning("Insufficient data for ARIMA model")
                return None

            # Check stationarity
            adf_result = adfuller(ts.dropna())
            is_stationary = adf_result[1] < 0.05

            # Difference if not stationary
            if not is_stationary:
                ts_diff = ts.diff().dropna()
                d = 1
            else:
                ts_diff = ts
                d = 0

            # Simple ARIMA parameter selection
            # In production, would use auto_arima or grid search
            p, q = 1, 1  # Simple AR(1) MA(1) model

            try:
                model = ARIMA(ts, order=(p, d, q))
                fitted_model = model.fit()

                arima_result = {
                    "model": fitted_model,
                    "order": (p, d, q),
                    "aic": fitted_model.aic,
                    "bic": fitted_model.bic,
                    "is_stationary": is_stationary,
                }

                self.models["arima"] = arima_result
                logger.info(f"ARIMA({p},{d},{q}) model trained successfully")

                return arima_result

            except Exception as e:
                logger.warning(f"ARIMA fitting failed: {str(e)}")
                return None

        except Exception as e:
            logger.error(f"ARIMA training failed: {str(e)}")
            return None

    def generate_ensemble_forecast(
        self, df: pd.DataFrame, forecast_horizon: int = 5
    ) -> TimeSeriesForecast:
        """Generate ensemble forecast using all available models."""

        try:
            forecasts = {}
            forecast_dates = [
                df["date"].max() + timedelta(days=i * 7)
                for i in range(1, forecast_horizon + 1)
            ]

            # Prophet forecast
            if "prophet" in self.models:
                try:
                    future = self.models["prophet"].make_future_dataframe(
                        periods=forecast_horizon, freq="W"
                    )
                    prophet_forecast = self.models["prophet"].predict(future)

                    # Extract forecasted values
                    prophet_values = (
                        prophet_forecast["yhat"].tail(forecast_horizon).tolist()
                    )
                    prophet_lower = (
                        prophet_forecast["yhat_lower"].tail(forecast_horizon).tolist()
                    )
                    prophet_upper = (
                        prophet_forecast["yhat_upper"].tail(forecast_horizon).tolist()
                    )

                    forecasts["prophet"] = {
                        "values": prophet_values,
                        "confidence_intervals": list(zip(prophet_lower, prophet_upper)),
                    }

                except Exception as e:
                    logger.warning(f"Prophet forecast failed: {str(e)}")

            # ARIMA forecast
            if "arima" in self.models:
                try:
                    arima_model = self.models["arima"]["model"]
                    arima_forecast = arima_model.forecast(steps=forecast_horizon)
                    arima_conf_int = arima_model.get_forecast(
                        steps=forecast_horizon
                    ).conf_int()

                    forecasts["arima"] = {
                        "values": arima_forecast.tolist(),
                        "confidence_intervals": [
                            (arima_conf_int.iloc[i, 0], arima_conf_int.iloc[i, 1])
                            for i in range(len(arima_conf_int))
                        ],
                    }

                except Exception as e:
                    logger.warning(f"ARIMA forecast failed: {str(e)}")

            # Neural network forecasts
            for model_name in ["lstm", "gru"]:
                if model_name in self.models:
                    try:
                        nn_forecast = self._predict_neural_network(
                            df, model_name, forecast_horizon
                        )
                        forecasts[model_name] = nn_forecast

                    except Exception as e:
                        logger.warning(f"{model_name} forecast failed: {str(e)}")

            # Ensemble the forecasts
            if not forecasts:
                # Fallback: simple trend extrapolation
                recent_grades = df["grade"].tail(5).tolist()
                trend = np.mean(np.diff(recent_grades)) if len(recent_grades) > 1 else 0
                last_grade = recent_grades[-1] if recent_grades else 75.0

                ensemble_values = [
                    max(0, min(100, last_grade + trend * i))
                    for i in range(1, forecast_horizon + 1)
                ]

                confidence_intervals = [
                    (max(0, val - 10), min(100, val + 10)) for val in ensemble_values
                ]

                model_confidence = 0.3  # Low confidence for fallback

            else:
                # Weighted ensemble
                ensemble_values = []
                confidence_intervals = []

                # Equal weights for now (could be performance-based)
                weights = {model: 1.0 / len(forecasts) for model in forecasts.keys()}

                for i in range(forecast_horizon):
                    weighted_value = sum(
                        forecasts[model]["values"][i] * weights[model]
                        for model in forecasts.keys()
                        if i < len(forecasts[model]["values"])
                    )

                    # Ensemble confidence interval
                    all_lowers = [
                        forecasts[model]["confidence_intervals"][i][0]
                        for model in forecasts.keys()
                        if i < len(forecasts[model]["confidence_intervals"])
                    ]
                    all_uppers = [
                        forecasts[model]["confidence_intervals"][i][1]
                        for model in forecasts.keys()
                        if i < len(forecasts[model]["confidence_intervals"])
                    ]

                    ensemble_lower = (
                        np.mean(all_lowers) if all_lowers else weighted_value - 5
                    )
                    ensemble_upper = (
                        np.mean(all_uppers) if all_uppers else weighted_value + 5
                    )

                    ensemble_values.append(weighted_value)
                    confidence_intervals.append((ensemble_lower, ensemble_upper))

                model_confidence = 0.8 if len(forecasts) > 2 else 0.6

            # Trend and seasonality analysis
            trend_analysis = self._analyze_trend(df)
            seasonality_analysis = self._analyze_seasonality(df)
            anomaly_detection = self._detect_anomalies(df)

            return TimeSeriesForecast(
                forecasted_values=ensemble_values,
                confidence_intervals=confidence_intervals,
                forecast_dates=forecast_dates,
                model_type="ensemble",
                forecast_horizon=forecast_horizon,
                model_confidence=model_confidence,
                trend_analysis=trend_analysis,
                seasonality_analysis=seasonality_analysis,
                anomaly_detection=anomaly_detection,
            )

        except Exception as e:
            logger.error(f"Ensemble forecast generation failed: {str(e)}")

            # Fallback forecast
            last_grade = df["grade"].iloc[-1] if not df.empty else 75.0
            return TimeSeriesForecast(
                forecasted_values=[last_grade] * forecast_horizon,
                confidence_intervals=[(last_grade - 10, last_grade + 10)]
                * forecast_horizon,
                forecast_dates=forecast_dates,
                model_type="fallback",
                forecast_horizon=forecast_horizon,
                model_confidence=0.2,
                trend_analysis={"direction": "stable", "strength": 0.0},
                seasonality_analysis={"seasonal_strength": 0.0},
                anomaly_detection=[],
            )

    def _predict_neural_network(
        self, df: pd.DataFrame, model_name: str, forecast_horizon: int
    ) -> Dict[str, Any]:
        """Generate predictions from neural network models."""

        if model_name not in self.models or "neural_network" not in self.scalers:
            raise ValueError(f"Model {model_name} not trained or scaler not available")

        model = self.models[model_name]["model"]
        scaler = self.scalers["neural_network"]

        # Prepare last sequence
        feature_data = df[self.feature_columns].tail(self.sequence_length)
        scaled_data = scaler.transform(feature_data)

        # Reshape for model input
        X = scaled_data.reshape(1, self.sequence_length, len(self.feature_columns))

        # Generate prediction
        prediction = model.predict(X, verbose=0)

        # Inverse transform (approximate)
        # Note: This assumes the first feature is the target grade
        if prediction.shape[1] == 1:
            # Single step prediction
            dummy_features = np.zeros((1, len(self.feature_columns)))
            dummy_features[0, 0] = prediction[0, 0]
            inverse_pred = scaler.inverse_transform(dummy_features)[0, 0]

            values = [inverse_pred]
        else:
            # Multi-step prediction
            values = []
            for i in range(prediction.shape[1]):
                dummy_features = np.zeros((1, len(self.feature_columns)))
                dummy_features[0, 0] = prediction[0, i]
                inverse_pred = scaler.inverse_transform(dummy_features)[0, 0]
                values.append(inverse_pred)

        # Estimate confidence intervals (simple approach)
        uncertainty = np.std(df["grade"].tail(10)) * 0.5  # Reduced uncertainty
        confidence_intervals = [
            (val - uncertainty, val + uncertainty) for val in values
        ]

        return {"values": values, "confidence_intervals": confidence_intervals}

    def _analyze_trend(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze overall trend in the data."""

        if len(df) < 5:
            return {"direction": "insufficient_data", "strength": 0.0}

        # Linear trend analysis
        x = np.arange(len(df))
        y = df["grade"].values

        # Simple linear regression
        slope = np.corrcoef(x, y)[0, 1] * (np.std(y) / np.std(x))

        # Determine trend direction and strength
        if abs(slope) < 0.1:
            direction = "stable"
        elif slope > 0:
            direction = "improving"
        else:
            direction = "declining"

        strength = min(1.0, abs(slope) / 5.0)  # Normalize to 0-1

        return {
            "direction": direction,
            "strength": strength,
            "slope": slope,
            "recent_change": df["grade"].tail(3).mean() - df["grade"].head(3).mean(),
        }

    def _analyze_seasonality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze seasonal patterns in the data."""

        if len(df) < 20:
            return {"seasonal_strength": 0.0}

        try:
            # Weekly seasonality
            df_copy = df.copy()
            df_copy["week_grade_avg"] = df_copy.groupby("day_of_week")[
                "grade"
            ].transform("mean")
            weekly_variance = df_copy["week_grade_avg"].var()

            # Monthly seasonality (if applicable)
            if "month" in df.columns:
                df_copy["month_grade_avg"] = df_copy.groupby("month")[
                    "grade"
                ].transform("mean")
                monthly_variance = df_copy["month_grade_avg"].var()
            else:
                monthly_variance = 0

            # Seasonal strength
            total_variance = df["grade"].var()
            seasonal_strength = (weekly_variance + monthly_variance) / (
                total_variance + 1e-6
            )

            return {
                "seasonal_strength": min(1.0, seasonal_strength),
                "weekly_variance": weekly_variance,
                "monthly_variance": monthly_variance,
                "strongest_day": df.groupby("day_of_week")["grade"].mean().idxmax(),
                "weakest_day": df.groupby("day_of_week")["grade"].mean().idxmin(),
            }

        except Exception as e:
            logger.warning(f"Seasonality analysis failed: {str(e)}")
            return {"seasonal_strength": 0.0}

    def _detect_anomalies(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect anomalies in the grade time series."""

        if len(df) < 10:
            return []

        try:
            # Statistical anomaly detection using Z-score
            mean_grade = df["grade"].mean()
            std_grade = df["grade"].std()

            anomalies = []

            for idx, row in df.iterrows():
                z_score = abs(row["grade"] - mean_grade) / (std_grade + 1e-6)

                if z_score > 2.5:  # 2.5 sigma threshold
                    anomaly_type = "high" if row["grade"] > mean_grade else "low"

                    anomalies.append(
                        {
                            "date": row["date"].isoformat(),
                            "grade": row["grade"],
                            "z_score": z_score,
                            "anomaly_type": anomaly_type,
                            "severity": "high" if z_score > 3 else "moderate",
                        }
                    )

            return anomalies

        except Exception as e:
            logger.warning(f"Anomaly detection failed: {str(e)}")
            return []

    def generate_student_trajectory(
        self, user_id: int, course_id: Optional[int] = None
    ) -> Optional[StudentTrajectory]:
        """Generate comprehensive student performance trajectory analysis."""

        try:
            # Prepare data
            df = self.prepare_time_series_data(user_id, course_id)

            if df.empty:
                logger.warning(
                    f"No data available for trajectory analysis: user {user_id}"
                )
                return None

            # Train models if not already trained
            if not self.is_trained:
                self.train_neural_network_models(df)
                self.train_prophet_model(df)
                self.train_arima_model(df)
                self.is_trained = True

            # Generate forecast
            forecast = self.generate_ensemble_forecast(df)

            # Analyze historical performance
            historical_series = pd.Series(data=df["grade"].values, index=df["date"])

            # Performance analysis
            trend_analysis = self._analyze_trend(df)
            seasonality_analysis = self._analyze_seasonality(df)

            # Performance volatility
            performance_volatility = df["grade"].std() / df["grade"].mean()

            # Risk and improvement periods
            risk_periods = self._identify_risk_periods(df)
            improvement_periods = self._identify_improvement_periods(df)

            # Intervention recommendations
            recommendations = self._generate_intervention_recommendations(
                df, trend_analysis, performance_volatility, forecast
            )

            return StudentTrajectory(
                user_id=user_id,
                historical_performance=historical_series,
                trend_direction=trend_analysis["direction"],
                trend_strength=trend_analysis["strength"],
                seasonal_patterns=seasonality_analysis,
                performance_volatility=performance_volatility,
                risk_periods=risk_periods,
                improvement_periods=improvement_periods,
                projected_trajectory=forecast,
                intervention_recommendations=recommendations,
            )

        except Exception as e:
            logger.error(f"Student trajectory generation failed: {str(e)}")
            return None

    def _identify_risk_periods(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Identify periods where student performance was at risk."""

        risk_periods = []

        try:
            # Define risk threshold (e.g., below 70%)
            risk_threshold = 70.0

            # Find consecutive periods below threshold
            below_threshold = df["grade"] < risk_threshold
            risk_groups = below_threshold.groupby(
                (below_threshold != below_threshold.shift()).cumsum()
            )

            for group_id, group in risk_groups:
                if group.any():  # This group has risk periods
                    risk_indices = group[group].index
                    if len(risk_indices) >= 2:  # At least 2 consecutive low grades
                        start_date = df.loc[risk_indices[0], "date"]
                        end_date = df.loc[risk_indices[-1], "date"]
                        avg_grade = df.loc[risk_indices, "grade"].mean()

                        risk_periods.append(
                            {
                                "start_date": start_date.isoformat(),
                                "end_date": end_date.isoformat(),
                                "duration_days": (end_date - start_date).days,
                                "avg_grade": avg_grade,
                                "min_grade": df.loc[risk_indices, "grade"].min(),
                                "severity": "high" if avg_grade < 60 else "moderate",
                            }
                        )

        except Exception as e:
            logger.warning(f"Risk period identification failed: {str(e)}")

        return risk_periods

    def _identify_improvement_periods(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Identify periods of significant improvement."""

        improvement_periods = []

        try:
            # Calculate rolling improvement (grade increase over time)
            df_copy = df.copy()
            df_copy["grade_change"] = df_copy["grade"].diff()
            df_copy["improvement_trend"] = df_copy["grade_change"].rolling(3).mean()

            # Find periods of sustained improvement
            improving = (
                df_copy["improvement_trend"] > 2.0
            )  # 2+ point improvement per period
            improvement_groups = improving.groupby(
                (improving != improving.shift()).cumsum()
            )

            for group_id, group in improvement_groups:
                if group.any():
                    improvement_indices = group[group].index
                    if len(improvement_indices) >= 2:
                        start_date = df.loc[improvement_indices[0], "date"]
                        end_date = df.loc[improvement_indices[-1], "date"]
                        total_improvement = (
                            df.loc[improvement_indices[-1], "grade"]
                            - df.loc[improvement_indices[0], "grade"]
                        )

                        improvement_periods.append(
                            {
                                "start_date": start_date.isoformat(),
                                "end_date": end_date.isoformat(),
                                "duration_days": (end_date - start_date).days,
                                "total_improvement": total_improvement,
                                "avg_improvement_rate": total_improvement
                                / len(improvement_indices),
                            }
                        )

        except Exception as e:
            logger.warning(f"Improvement period identification failed: {str(e)}")

        return improvement_periods

    def _generate_intervention_recommendations(
        self,
        df: pd.DataFrame,
        trend_analysis: Dict[str, Any],
        volatility: float,
        forecast: TimeSeriesForecast,
    ) -> List[str]:
        """Generate personalized intervention recommendations."""

        recommendations = []

        try:
            current_grade = df["grade"].iloc[-1]
            recent_avg = df["grade"].tail(5).mean()

            # Grade-based recommendations
            if current_grade < 70:
                recommendations.append(
                    "Immediate academic support needed - consider tutoring or office hours"
                )
            elif current_grade < 80:
                recommendations.append(
                    "Focus on improving study habits and assignment completion"
                )

            # Trend-based recommendations
            if trend_analysis["direction"] == "declining":
                recommendations.append(
                    "Declining trend detected - review study schedule and seek help"
                )
                recommendations.append(
                    "Consider meeting with academic advisor to discuss course load"
                )
            elif trend_analysis["direction"] == "improving":
                recommendations.append(
                    "Great improvement trend - maintain current study strategies"
                )

            # Volatility-based recommendations
            if volatility > 0.2:  # High volatility
                recommendations.append(
                    "Performance is inconsistent - focus on consistent study habits"
                )
                recommendations.append(
                    "Consider stress management techniques and regular study schedule"
                )

            # Forecast-based recommendations
            avg_forecast = np.mean(forecast.forecasted_values)
            if avg_forecast < current_grade:
                recommendations.append(
                    "Predicted performance decline - proactive intervention needed"
                )

            # Seasonal patterns
            if (
                df["day_of_week"].value_counts().iloc[0] > len(df) * 0.5
            ):  # Most work on one day
                recommendations.append(
                    "Diversify study schedule across different days of the week"
                )

            # Default recommendations if none generated
            if not recommendations:
                recommendations.append(
                    "Continue current performance level with regular progress monitoring"
                )

        except Exception as e:
            logger.warning(f"Recommendation generation failed: {str(e)}")
            recommendations.append("Regular academic progress monitoring recommended")

        return recommendations


# Global time series forecaster instance
time_series_forecaster = AdvancedTimeSeriesForecaster()
