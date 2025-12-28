# ===========================================
# Flask Grade Tracker - Production Dockerfile with UV
# ===========================================

FROM python:3.11-slim-bullseye

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    FLASK_APP=app.py \
    DEBIAN_FRONTEND=noninteractive \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Set working directory
WORKDIR /app

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy Python dependencies and project configuration
COPY requirements.txt requirements-docker.txt pyproject.toml ./

# Install dependencies using uv (faster than pip)
RUN uv pip install --system --no-cache \
    -r requirements.txt \
    -r requirements-docker.txt

# Alternative: Use uv with pyproject.toml (uncomment to use instead of requirements.txt)
# RUN uv sync --frozen --no-cache

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs static/css static/js \
    && chmod -R 755 static \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Expose port
EXPOSE 5000

# Default command - can be overridden in docker-compose
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--worker-class", "gevent", "--timeout", "120", "app:app"]