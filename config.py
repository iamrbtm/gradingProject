import os
from datetime import timedelta


class Config:
    """Base configuration."""

    SECRET_KEY = os.environ.get(
        "FLASK_SECRET_KEY", "dev-secret-key-change-in-production"
    )
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://onlymyli:Braces4me%23%23@jeremyguill.com:3306/onlymyli_grades",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_MAX_OVERFLOW = 20
    SQLALCHEMY_POOL_RECYCLE = 3600

    # Session configuration
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    SESSION_COOKIE_NAME = "grades_session"  # Custom session cookie name

    # CSRF configuration
    WTF_CSRF_TIME_LIMIT = None  # Don't expire CSRF tokens (default is 3600 seconds)
    WTF_CSRF_CHECK_DEFAULT = True  # Enable CSRF protection by default

    # Mail configuration
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")

    # Caching
    CACHE_TYPE = "simple"  # Use Redis in production

    # Feature flags
    ENABLE_NOTIFICATIONS = (
        os.environ.get("ENABLE_NOTIFICATIONS", "False").lower() == "true"
    )
    ENABLE_ANALYTICS = os.environ.get("ENABLE_ANALYTICS", "True").lower() == "true"
    ENABLE_MOBILE_OPTIMIZATION = (
        os.environ.get("ENABLE_MOBILE_OPTIMIZATION", "False").lower() == "true"
    )

    # Rate limiting
    RATELIMIT_STORAGE_URL = os.environ.get("RATELIMIT_STORAGE_URL", "memory://")

    # Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    SESSION_COOKIE_SECURE = False
    # Use MySQL for development - same as production database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://onlymyli:Braces4me%23%23@jeremyguill.com:3306/onlymyli_grades",
    )


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    # Only use secure cookies if HTTPS is enabled
    SESSION_COOKIE_SECURE = os.environ.get("USE_HTTPS", "False").lower() == "true"

    # CSRF configuration
    WTF_CSRF_TIME_LIMIT = None  # Don't expire CSRF tokens
    WTF_CSRF_SSL_STRICT = False  # Allow CSRF over HTTP (for development/testing)

    # Use more secure cache in production
    CACHE_TYPE = os.environ.get("CACHE_TYPE", "redis")
    CACHE_REDIS_URL = os.environ.get("CACHE_REDIS_URL")

    # Stricter rate limiting
    RATELIMIT_STORAGE_URL = os.environ.get(
        "RATELIMIT_STORAGE_URL", "redis://redis:6379/0"
    )


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL")
    WTF_CSRF_ENABLED = False
    CACHE_TYPE = "null"  # Disable caching in tests


# Configuration mapping
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
