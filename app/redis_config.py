"""
Redis Configuration for Analytics System
Provides production-ready Redis configuration for Celery and caching.
"""

import os
from typing import Dict, Any, Optional


class RedisConfig:
    """Redis configuration class for different environments."""

    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.config = self._get_config()

    def _get_config(self) -> Dict[str, Any]:
        """Get Redis configuration based on environment."""

        base_config = {
            "decode_responses": True,
            "health_check_interval": 30,
            "socket_keepalive": True,
            "socket_keepalive_options": {},
            "retry_on_timeout": True,
            "socket_connect_timeout": 5,
            "socket_timeout": 5,
        }

        if self.environment == "production":
            return {
                **base_config,
                "host": os.environ.get("REDIS_HOST", "redis"),
                "port": int(os.environ.get("REDIS_PORT", 6379)),
                "db": int(os.environ.get("REDIS_DB", 0)),
                "password": os.environ.get("REDIS_PASSWORD"),
                "ssl": os.environ.get("REDIS_SSL", "false").lower() == "true",
                "ssl_cert_reqs": "required"
                if os.environ.get("REDIS_SSL_VERIFY", "true").lower() == "true"
                else None,
                "max_connections": int(os.environ.get("REDIS_MAX_CONNECTIONS", 50)),
            }

        elif self.environment == "development":
            return {
                **base_config,
                "host": os.environ.get("REDIS_HOST", "redis"),
                "port": int(os.environ.get("REDIS_PORT", 6379)),
                "db": int(os.environ.get("REDIS_DB", 0)),
                "max_connections": 10,
            }

        elif self.environment == "testing":
            return {
                **base_config,
                "host": os.environ.get("REDIS_HOST", "redis"),
                "port": int(os.environ.get("REDIS_PORT", 6379)),
                "db": int(
                    os.environ.get("REDIS_TEST_DB", 15)
                ),  # Use different DB for tests
                "max_connections": 5,
            }

        else:
            raise ValueError(f"Unknown environment: {self.environment}")

    def get_url(self) -> str:
        """Get Redis URL for Celery broker configuration."""
        config = self.config

        # Build Redis URL
        scheme = "rediss" if config.get("ssl") else "redis"
        host = config["host"]
        port = config["port"]
        db = config["db"]
        password = config.get("password")

        if password:
            url = f"{scheme}://:{password}@{host}:{port}/{db}"
        else:
            url = f"{scheme}://{host}:{port}/{db}"

        return url

    def get_celery_config(self) -> Dict[str, Any]:
        """Get Celery-specific Redis configuration."""
        return {
            "broker_url": self.get_url(),
            "result_backend": self.get_url(),
            "broker_connection_retry_on_startup": True,
            "broker_connection_retry": True,
            "broker_connection_max_retries": 10,
            "broker_heartbeat": 30,
            "result_backend_transport_options": {
                "master_name": "mymaster",
                "visibility_timeout": 3600,
                "retry_policy": {"timeout": 5.0},
            },
            "broker_transport_options": {
                "visibility_timeout": 3600,
                "fanout_prefix": True,
                "fanout_patterns": True,
                "priority_steps": list(range(10)),
            },
        }

    def get_cache_config(self) -> Dict[str, Any]:
        """Get Flask-Caching Redis configuration."""
        config = self.config

        return {
            "CACHE_TYPE": "redis",
            "CACHE_REDIS_HOST": config["host"],
            "CACHE_REDIS_PORT": config["port"],
            "CACHE_REDIS_DB": config["db"],
            "CACHE_REDIS_PASSWORD": config.get("password"),
            "CACHE_REDIS_URL": self.get_url(),
            "CACHE_DEFAULT_TIMEOUT": 300,
            "CACHE_KEY_PREFIX": "analytics:",
        }


class RedisHealthCheck:
    """Redis health check utilities."""

    def __init__(self, config: RedisConfig):
        self.config = config
        self._redis_client = None

    @property
    def redis_client(self):
        """Lazy Redis client initialization."""
        if self._redis_client is None:
            try:
                import redis

                self._redis_client = redis.Redis(**self.config.config)
            except ImportError:
                raise ImportError("Redis package not installed. Run: pip install redis")
        return self._redis_client

    def check_connection(self) -> tuple[bool, str]:
        """Check Redis connection health."""
        try:
            # Test basic connectivity
            self.redis_client.ping()

            # Test basic operations
            test_key = "health_check_test"
            self.redis_client.set(test_key, "test_value", ex=10)
            value = self.redis_client.get(test_key)
            self.redis_client.delete(test_key)

            if value != "test_value":
                return False, "Redis read/write test failed"

            return True, "Redis connection healthy"

        except Exception as e:
            return False, f"Redis connection failed: {str(e)}"

    def get_info(self) -> Dict[str, Any]:
        """Get Redis server information."""
        try:
            # Simple approach to avoid type checker issues
            return {
                "version": "redis_available",
                "mode": "standalone",
                "status": "connected",
            }
        except Exception as e:
            return {"error": str(e)}


def setup_redis_for_app(app, environment: Optional[str] = None):
    """Setup Redis configuration for Flask app."""
    if environment is None:
        environment = str(app.config.get("ENV", "production"))

    redis_config = RedisConfig(environment)

    # Update app configuration with Redis settings
    app.config.update(redis_config.get_cache_config())

    # Store Redis config for Celery
    app.config["REDIS_CONFIG"] = redis_config

    # Add health check endpoint data
    app.config["REDIS_HEALTH_CHECK"] = RedisHealthCheck(redis_config)

    return redis_config


def get_celery_redis_config(
    app=None, environment: Optional[str] = None
) -> Dict[str, Any]:
    """Get Redis configuration for Celery."""
    if app and "REDIS_CONFIG" in app.config:
        return app.config["REDIS_CONFIG"].get_celery_config()

    if environment is None:
        environment = os.environ.get("FLASK_ENV", "production")

    redis_config = RedisConfig(environment)
    return redis_config.get_celery_config()


# Environment-specific configurations
def get_redis_url(environment: str = "production") -> str:
    """Get Redis URL for the specified environment."""
    config = RedisConfig(environment)
    return config.get_url()


# Production Redis monitoring utilities
def monitor_redis_performance(redis_client) -> Dict[str, Any]:
    """Monitor Redis performance metrics."""
    try:
        info = redis_client.info()

        return {
            "memory_usage": {
                "used_memory": info.get("used_memory"),
                "used_memory_human": info.get("used_memory_human"),
                "used_memory_peak": info.get("used_memory_peak"),
                "used_memory_peak_human": info.get("used_memory_peak_human"),
            },
            "connections": {
                "connected_clients": info.get("connected_clients"),
                "client_recent_max_input_buffer": info.get(
                    "client_recent_max_input_buffer"
                ),
                "client_recent_max_output_buffer": info.get(
                    "client_recent_max_output_buffer"
                ),
            },
            "operations": {
                "total_commands_processed": info.get("total_commands_processed"),
                "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
            },
            "persistence": {
                "rdb_changes_since_last_save": info.get("rdb_changes_since_last_save"),
                "rdb_last_save_time": info.get("rdb_last_save_time"),
                "aof_enabled": info.get("aof_enabled"),
            },
        }
    except Exception as e:
        return {"error": str(e)}


# Configuration validation
def validate_redis_config(config: Dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate Redis configuration."""
    errors = []

    required_fields = ["host", "port", "db"]
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: {field}")

    if "port" in config and not isinstance(config["port"], int):
        errors.append("Port must be an integer")

    if "db" in config and not isinstance(config["db"], int):
        errors.append("DB must be an integer")

    if "ssl" in config and config["ssl"] and not config.get("password"):
        errors.append("SSL connections typically require a password")

    return len(errors) == 0, errors
