# app_refactored.py - Refactored main application file
import os
from datetime import datetime

# Load environment variables FIRST before any other imports
from dotenv import load_dotenv

load_dotenv()

# Explicitly set DATABASE_URL to ensure MySQL is used
os.environ["DATABASE_URL"] = (
    "mysql+pymysql://onlymyli:Braces4me%23%23@jeremyguill.com:3306/onlymyli_grades"
)

from flask import Flask, request
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_limiter import Limiter
from flask_migrate import Migrate
from flask_caching import Cache
from flask_mail import Mail


def create_app(config_name="development"):
    """Application factory pattern."""
    app = Flask(__name__, template_folder="app/templates", static_folder="static")

    # Load configuration
    from config import config

    app.config.from_object(config.get(config_name, config["default"]))

    # Initialize extensions
    from app.models import db

    db.init_app(app)

    # Initialize Flask-Migrate
    migrate = Migrate()
    migrate.init_app(app, db)

    # Initialize caching
    cache = Cache(
        config={
            "CACHE_TYPE": app.config["CACHE_TYPE"],
            "CACHE_REDIS_URL": app.config.get("CACHE_REDIS_URL"),
        }
    )
    cache.init_app(app)

    # Initialize mail
    mail = Mail(app)

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    # Initialize CSRF protection
    csrf = CSRFProtect()
    csrf.init_app(app)

    # Initialize rate limiter
    limiter = Limiter(
        key_func=lambda: request.remote_addr,
        storage_uri=app.config["RATELIMIT_STORAGE_URL"],
    )
    limiter.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User

        return User.query.get(int(user_id))

    # Register Blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.main import main_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.courses import courses_bp
    from app.routes import routes
    from app.blueprints.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(courses_bp)
    app.register_blueprint(routes)
    app.register_blueprint(api_bp)

    # Register analytics blueprint
    try:
        from app.blueprints.analytics.routes import analytics_bp

        app.register_blueprint(analytics_bp)
        app.logger.info("Analytics blueprint registered successfully")
    except ImportError as e:
        app.logger.warning(f"Analytics blueprint not available: {e}")

    # Register enhanced Canvas sync blueprint
    try:
        from app.routes_enhanced import enhanced_canvas_bp

        app.register_blueprint(enhanced_canvas_bp)
        app.logger.info("Enhanced Canvas sync blueprint registered successfully")
    except ImportError as e:
        app.logger.warning(f"Enhanced Canvas sync blueprint not available: {e}")

    # Initialize error handlers and logging
    from app.error_handlers import init_error_handlers, setup_logging

    init_error_handlers(app)
    setup_logging(app)

    # Global template context
    @app.context_processor
    def inject_current_year():
        current_month = datetime.now().month
        if current_month in [9, 10, 11, 12]:
            current_season = "Fall"
        elif current_month in [1, 2, 3]:
            current_season = "Winter"
        elif current_month in [4, 5, 6]:
            current_season = "Spring"
        else:
            current_season = "Summer"
        return {
            "current_year": datetime.now().year,
            "current_season": current_season,
            "csrf_token": generate_csrf,
        }

    # Custom Jinja2 filters
    def format_score(value):
        if value is None:
            return "--"
        if value == int(value):
            return int(value)
        return value

    app.jinja_env.filters["format_score"] = format_score

    # Initialize sync commands (optional)
    try:
        from app.sync_commands import init_sync_commands

        init_sync_commands(app)
    except ImportError:
        app.logger.warning(
            "Sync commands not available. Install required dependencies."
        )

    # Health check endpoint
    @app.route("/health")
    def health_check():
        try:
            # Check database connection
            db.session.execute(db.text("SELECT 1"))
            return {"status": "healthy", "database": "connected"}, 200
        except Exception as e:
            app.logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "database": "disconnected"}, 500

    # Create database tables
    with app.app_context():
        db.create_all()

        # Add performance indexes
        try:
            from add_indexes import add_performance_indexes

            add_performance_indexes()
        except Exception as e:
            app.logger.warning(f"Could not add performance indexes: {e}")

    return app


# Create application instance
app = create_app(os.environ.get("FLASK_ENV", "development"))

if __name__ == "__main__":
    # Development server
    app.run(debug=True, port=12345)
