# Advanced ML Dependencies & Installation Guide

## Overview
The advanced ML system is designed to work with graceful fallbacks, meaning the application will function even if advanced ML dependencies are not installed. However, to unlock the full power of the system, you may want to install the optional advanced dependencies.

## Dependency Levels

### 🟢 **Basic Mode** (No additional dependencies required)
The application works out-of-the-box with traditional ML capabilities:
- Basic statistical analysis and predictions
- Simple linear regression models
- Performance tracking and analytics
- Grade calculation and risk assessment

### 🟡 **Enhanced Mode** (Scikit-learn available)
With scikit-learn installed, you get:
- Random Forest and Gradient Boosting models
- Cross-validation and model evaluation
- Feature scaling and preprocessing
- More sophisticated prediction algorithms

### 🔥 **Advanced Mode** (All dependencies available)
With full dependencies, you unlock enterprise-grade capabilities:
- Ensemble learning with XGBoost, LightGBM, CatBoost
- Deep learning with TensorFlow/PyTorch
- Time series forecasting with LSTM networks
- Model interpretability with SHAP and LIME
- A/B testing and automated experimentation
- External data integration (weather, economic, social)
- Advanced drift detection and monitoring

## Installation Options

### Option 1: Quick Start (Basic Mode)
No additional installation needed. The app works immediately with basic functionality.

### Option 2: Enhanced Mode
```bash
# Install basic ML dependencies
pip install scikit-learn pandas numpy

# Restart the application
python app.py
```

### Option 3: Full Advanced Mode

#### For macOS (Apple Silicon/Intel)
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install OpenMP (required for LightGBM)
brew install libomp

# Install all advanced ML dependencies
pip install -r requirements-ml.txt
```

#### For Linux/Ubuntu
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install build-essential cmake

# Install all advanced ML dependencies
pip install -r requirements-ml.txt
```

#### For Windows
```bash
# Install Visual Studio Build Tools (if not already installed)
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Install all advanced ML dependencies
pip install -r requirements-ml.txt
```

## Advanced Dependencies List

Create a `requirements-ml.txt` file with the following content:

```txt
# Core ML Libraries
scikit-learn>=1.0.0
pandas>=1.3.0
numpy>=1.21.0

# Advanced ML Algorithms
xgboost>=1.6.0
lightgbm>=3.3.0
catboost>=1.1.0

# Deep Learning
tensorflow>=2.8.0
# OR alternatively use PyTorch:
# torch>=1.11.0
# torchvision>=0.12.0

# Hyperparameter Optimization
optuna>=3.0.0

# Model Interpretability
shap>=0.41.0
lime>=0.2.0

# Time Series Forecasting
prophet>=1.1.0
statsmodels>=0.13.0

# Statistical Testing
scipy>=1.8.0

# External Data Collection
requests>=2.27.0
beautifulsoup4>=4.11.0

# Performance Monitoring
psutil>=5.9.0

# Caching
redis>=4.0.0

# Background Tasks
celery>=5.2.0

# Data Quality
pandas-profiling>=3.2.0
```

## Troubleshooting Common Issues

### 1. LightGBM Installation Issues on macOS

**Problem**: `Library not loaded: @rpath/libomp.dylib`

**Solution**:
```bash
# Install OpenMP via Homebrew
brew install libomp

# If still having issues, try:
export LDFLAGS="-L$(brew --prefix)/lib"
export CPPFLAGS="-I$(brew --prefix)/include"
pip install lightgbm --no-cache-dir
```

### 2. TensorFlow Installation Issues

**For Apple Silicon Macs**:
```bash
# Install TensorFlow optimized for Apple Silicon
pip install tensorflow-macos tensorflow-metal
```

**For Other Systems**:
```bash
# Install standard TensorFlow
pip install tensorflow
```

### 3. Memory Issues During Installation

**Solution**:
```bash
# Install one package at a time to avoid memory issues
pip install --no-cache-dir xgboost
pip install --no-cache-dir lightgbm
pip install --no-cache-dir catboost
# ... continue with other packages
```

### 4. Version Conflicts

**Solution**:
```bash
# Create a fresh virtual environment
python -m venv fresh_env
source fresh_env/bin/activate  # On Windows: fresh_env\Scripts\activate
pip install --upgrade pip
pip install -r requirements-ml.txt
```

## Checking Installation Status

The application provides built-in diagnostics to check which advanced features are available:

### Via Web Interface
Visit `/analytics/model-health` to see a comprehensive status report of all ML capabilities.

### Via Python Code
```python
from app.services.predictive_analytics import PredictiveAnalyticsEngine

engine = PredictiveAnalyticsEngine()

# Check what's available
advanced_ml = engine._get_advanced_ml()
if advanced_ml:
    print("✅ Advanced ML System available")
else:
    print("❌ Advanced ML System not available")

forecaster = engine._get_forecasting_engine()
if forecaster:
    print("✅ Time Series Forecasting available")
else:
    print("❌ Time Series Forecasting not available")

# And so on for other components...
```

### Via Command Line
```python
python -c "
from app.services.predictive_analytics import PredictiveAnalyticsEngine
engine = PredictiveAnalyticsEngine()
components = {
    'Advanced ML': engine._get_advanced_ml(),
    'Forecasting': engine._get_forecasting_engine(),
    'Interpretability': engine._get_interpretability_engine(),
    'External Data': engine._get_external_data_service(),
    'A/B Testing': engine._get_ab_testing(),
    'Monitoring': engine._get_ml_monitoring()
}
for name, component in components.items():
    status = '✅' if component else '❌'
    print(f'{status} {name}')
"
```

## Performance Recommendations

### For Development
- **Basic Mode** is sufficient for development and testing
- Install scikit-learn for enhanced local development
- Use SQLite database for simplicity

### For Production
- **Full Advanced Mode** recommended for production deployments
- Use Redis for caching and Celery task queue
- Use PostgreSQL or MySQL for the database
- Consider GPU-enabled servers for deep learning features
- Set up proper monitoring and logging

### For Educational/Demo Use
- **Enhanced Mode** provides a good balance of features and simplicity
- Demonstrates most ML capabilities without complex setup
- Works well on most laptop/desktop environments

## Migration Path

You can start with any mode and upgrade later:

1. **Start Basic** → Install scikit-learn → **Enhanced Mode**
2. **Enhanced Mode** → Install full dependencies → **Advanced Mode**
3. The application will automatically detect and use newly available features after restart

## Resource Requirements

### Basic Mode
- RAM: 512MB minimum, 1GB recommended
- CPU: Any modern processor
- Disk: 100MB for application

### Enhanced Mode
- RAM: 1GB minimum, 2GB recommended
- CPU: Multi-core recommended for ML training
- Disk: 500MB for dependencies

### Advanced Mode
- RAM: 4GB minimum, 8GB+ recommended for large datasets
- CPU: Multi-core with high clock speed
- GPU: Optional but recommended for deep learning
- Disk: 2GB+ for all dependencies and models
- Network: Required for external data collection

## Security Considerations

When installing advanced dependencies:

1. **Use Virtual Environments**: Always isolate dependencies
2. **Review Package Sources**: Install from trusted repositories
3. **Update Regularly**: Keep dependencies up to date for security
4. **External Data**: Review external API keys and data collection
5. **Model Storage**: Secure trained models if they contain sensitive patterns

## Support and Troubleshooting

If you encounter issues:

1. Check the application logs for specific error messages
2. Visit `/analytics/model-health` for system diagnostics
3. Try installing dependencies one at a time
4. Use virtual environments to avoid conflicts
5. Check system-specific requirements (especially for LightGBM on macOS)

The system is designed to be resilient - if something doesn't work, it will fall back gracefully to simpler alternatives while still providing value!