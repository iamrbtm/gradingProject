# Advanced ML Tasks Documentation

## Overview
This document describes the advanced machine learning background tasks that have been integrated into the grade tracking system. These tasks provide sophisticated AI capabilities including ensemble learning, time series forecasting, model interpretability, and automated experimentation.

## New Celery Tasks

### 1. External Data Collection
**Task**: `app.tasks.ml.collect_external_data`
**Schedule**: Every 6 hours
**Purpose**: Collects external contextual data to enhance ML predictions

**Data Sources**:
- Weather data (affects cognitive performance)
- Economic indicators (student stress factors)
- Academic calendar events
- Social sentiment analysis
- Course difficulty metrics
- Job market trends
- Campus events
- Industry trends

**Usage**:
```python
# Manual execution
from app.tasks.ml import collect_external_data
result = collect_external_data.delay()
```

### 2. Advanced ML Model Training
**Task**: `app.tasks.ml.train_advanced_ml_models`
**Schedule**: Daily at 3 AM
**Purpose**: Trains ensemble models using multiple algorithms with hyperparameter optimization

**Features**:
- Random Forest, XGBoost, LightGBM, CatBoost ensemble
- Neural network integration (MLPRegressor)
- Optuna hyperparameter optimization
- External data feature engineering
- Model stacking and meta-learning

**Usage**:
```python
# Train models for specific course
from app.tasks.ml import train_advanced_ml_models
result = train_advanced_ml_models.delay(course_id=123)

# Train for all courses
result = train_advanced_ml_models.delay()
```

### 3. Time Series Forecasting
**Task**: `app.tasks.ml.generate_time_series_forecasts`
**Schedule**: Daily at 1 AM
**Purpose**: Generates student performance trajectory forecasts

**Capabilities**:
- LSTM/GRU neural networks for sequence modeling
- ARIMA time series analysis
- Prophet forecasting for trend detection
- Risk period identification
- Intervention recommendation generation
- Anomaly detection in performance patterns

**Usage**:
```python
# Generate forecasts for specific user
from app.tasks.ml import generate_time_series_forecasts
result = generate_time_series_forecasts.delay(user_id=456)
```

### 4. Model Performance Monitoring
**Task**: `app.tasks.ml.monitor_model_performance`
**Schedule**: Every 2 hours
**Purpose**: Monitors ML models for data drift and performance degradation

**Monitoring Features**:
- KL divergence for data drift detection
- Kolmogorov-Smirnov tests for distribution changes
- Performance baseline tracking
- Concept drift detection
- Automated retraining triggers
- Model health scoring

**Usage**:
```python
# Monitor all active models
from app.tasks.ml import monitor_model_performance
result = monitor_model_performance.delay()
```

### 5. A/B Testing Management
**Task**: `app.tasks.ml.manage_ab_tests`
**Schedule**: Every 4 hours
**Purpose**: Manages A/B tests for model variants

**A/B Testing Features**:
- Champion vs challenger model testing
- Statistical significance testing (t-tests, Mann-Whitney U)
- Multi-armed bandit algorithms
- Automatic model promotion
- User segment analysis
- Experiment tracking

**Usage**:
```python
# Manage active A/B tests
from app.tasks.ml import manage_ab_tests
result = manage_ab_tests.delay()
```

### 6. Model Explanations Update
**Task**: `app.tasks.ml.update_model_explanations`
**Schedule**: Daily at 4 AM
**Purpose**: Updates SHAP/LIME explanations for model interpretability

**Explainability Features**:
- SHAP (SHapley Additive exPlanations) integration
- LIME (Local Interpretable Model-Agnostic Explanations)
- Natural language explanation generation
- Counterfactual analysis ("What if" scenarios)
- Global feature importance tracking
- Decision path visualization data

**Usage**:
```python
# Update explanations for specific course
from app.tasks.ml import update_model_explanations
result = update_model_explanations.delay(course_id=123)
```

### 7. Comprehensive ML Maintenance
**Task**: `app.tasks.ml.comprehensive_ml_maintenance`
**Schedule**: Weekly on Sunday at 5 AM
**Purpose**: Orchestrates complete ML system maintenance

**Maintenance Operations**:
1. Collect fresh external data
2. Monitor model performance and detect drift
3. Manage A/B test conclusions and promotions
4. Update model explanations
5. Generate time series forecasts
6. Clean up old models and data
7. Generate system health reports

**Usage**:
```python
# Run comprehensive maintenance
from app.tasks.ml import comprehensive_ml_maintenance
result = comprehensive_ml_maintenance.delay()
```

## Task Scheduling

The advanced ML tasks are automatically scheduled using Celery Beat:

```
┌─────────────────────────────────────────┐
│           ML Task Schedule              │
├─────────────────────────────────────────┤
│ 01:00 - Time series forecasting        │
│ 02:00 - Traditional ML training        │
│ 03:00 - Advanced ML training           │
│ 04:00 - Model explanations update      │
│ 05:00 - Comprehensive maintenance      │ (Sundays)
│ 06:00 - Data cleanup                   │
│ 07:00 - Model cleanup                  │ (Sundays)
│                                         │
│ Every 2 hours - Performance monitoring  │
│ Every 4 hours - A/B test management     │
│ Every 6 hours - External data          │
└─────────────────────────────────────────┘
```

## Manual Task Execution

For testing or immediate execution without Celery:

```python
from app.tasks.ml import (
    run_external_data_collection_sync,
    run_advanced_training_sync,
    run_model_monitoring_sync,
    run_ab_test_management_sync
)

# Run tasks synchronously
external_result = run_external_data_collection_sync()
training_result = run_advanced_training_sync(course_id=123)
monitoring_result = run_model_monitoring_sync()
ab_test_result = run_ab_test_management_sync()
```

## Integration with Existing Services

The tasks integrate seamlessly with the existing `PredictiveAnalyticsEngine`:

```python
from app.services.predictive_analytics import PredictiveAnalyticsEngine

engine = PredictiveAnalyticsEngine()

# Uses advanced ML if available, falls back to traditional ML
predictions = engine.predict_final_grade(user_id=123, course_id=456)

# Generate explanations using SHAP/LIME
explanations = engine.get_model_explanations(user_id=123, course_id=456)

# Get time series forecast
forecast = engine.generate_time_series_forecast(user_id=123, course_id=456)
```

## Error Handling and Fallbacks

All advanced ML tasks include comprehensive error handling:

1. **Dependency Checks**: Tasks check if advanced ML services are available
2. **Graceful Fallbacks**: Fall back to traditional ML if advanced features unavailable
3. **Error Logging**: Detailed logging for debugging and monitoring
4. **Result Tracking**: Task results stored with status and error information
5. **Retry Logic**: Automatic retries for transient failures

## Performance Considerations

- **Task Queuing**: Advanced ML tasks use dedicated `ml_tasks` queue
- **Memory Management**: Worker memory limits prevent OOM issues
- **Timeouts**: Extended timeouts for complex ML operations
- **Concurrency**: Controlled concurrency to prevent resource exhaustion
- **Caching**: External data caching reduces API calls
- **Batch Processing**: Efficient batch processing for multiple entities

## Monitoring and Alerting

The system provides comprehensive monitoring:

- **Task Success/Failure Rates**: Celery monitoring integration
- **Model Performance Metrics**: Drift detection and performance tracking
- **System Health**: Overall ML system health scoring
- **Resource Usage**: Memory and CPU monitoring
- **Data Quality**: Input data validation and quality checks

## Dependencies

Advanced features require additional packages:
- `xgboost`, `lightgbm`, `catboost` for ensemble models
- `tensorflow` or `pytorch` for neural networks
- `optuna` for hyperparameter optimization
- `shap`, `lime` for model interpretability
- `prophet` for time series forecasting
- `scipy`, `statsmodels` for statistical tests

All dependencies are optional with graceful fallbacks to basic functionality.