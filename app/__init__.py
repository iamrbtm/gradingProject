import os
from datetime import datetime

# Load environment variables FIRST before any other imports
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, request
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect, generate_csrf

# from flask_limiter import Limiter
from flask_migrate import Migrate
from flask_caching import Cache
from flask_mail import Mail
from .models import db


def create_app(config_name="production"):
    """Application factory pattern."""
    app = Flask(__name__, template_folder="templates", static_folder="../static")

    # Configuration - Use MySQL for production
    app.config["SECRET_KEY"] = os.environ.get(
        "FLASK_SECRET_KEY", "change-this-in-production"
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://onlymyli:Braces4me%23%23@jeremyguill.com:3306/onlymyli_grades",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_POOL_SIZE"] = 10
    app.config["SQLALCHEMY_MAX_OVERFLOW"] = 20
    app.config["SQLALCHEMY_POOL_RECYCLE"] = 3600

    # Secure session configuration
    app.config["SESSION_COOKIE_SECURE"] = (
        config_name == "production"
    )  # Only secure in production (HTTPS)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["PERMANENT_SESSION_LIFETIME"] = 3600  # 1 hour

    # Mail configuration
    app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
    app.config["MAIL_USE_TLS"] = (
        os.environ.get("MAIL_USE_TLS", "True").lower() == "true"
    )
    app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
    app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")

    # Initialize extensions
    from .models import db

    db.init_app(app)

    # Initialize CSRF protection
    csrf = CSRFProtect()
    csrf.init_app(app)
    app.jinja_env.globals["csrf_token"] = generate_csrf

    # Initialize rate limiter
    # limiter = Limiter(key_func=lambda: request.remote_addr)
    # limiter.init_app(app)

    # Initialize Flask-Migrate
    migrate = Migrate()
    migrate.init_app(app, db)

    # Initialize caching
    cache = Cache(config={"CACHE_TYPE": "simple"})
    cache.init_app(app)

    # Initialize mail
    mail = Mail()
    mail.init_app(app)

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        from .models import User

        return User.query.get(int(user_id))

    # Register Blueprints
    from .blueprints.auth import auth_bp
    from .blueprints.main import main_bp
    from .routes import routes

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(routes)

    # Register analytics blueprint if available
    try:
        from .blueprints.analytics.routes import analytics_bp

        app.register_blueprint(analytics_bp)
    except ImportError:
        app.logger.warning("Analytics blueprint not available")

    # Register enhanced Canvas sync blueprint
    try:
        from .routes_enhanced import enhanced_canvas_bp

        app.register_blueprint(enhanced_canvas_bp)
        app.logger.info("Enhanced Canvas sync blueprint registered successfully")
    except ImportError as e:
        app.logger.warning(f"Enhanced Canvas sync blueprint not available: {e}")

    # Initialize error handlers and logging
    from .error_handlers import init_error_handlers, setup_logging

    init_error_handlers(app)
    setup_logging(app)

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
        from .sync_commands import init_sync_commands

        init_sync_commands(app)
    except ImportError:
        app.logger.warning(
            "Sync commands not available. Install required dependencies."
        )

    # Create database tables
    with app.app_context():
        db.create_all()

        # Add performance indexes inline to avoid circular import
        try:
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_assignment_due_date ON assignment(due_date);",
                "CREATE INDEX IF NOT EXISTS idx_assignment_course_id ON assignment(course_id);",
                "CREATE INDEX IF NOT EXISTS idx_assignment_score ON assignment(score);",
                "CREATE INDEX IF NOT EXISTS idx_assignment_category_id ON assignment(category_id);",
                "CREATE INDEX IF NOT EXISTS idx_term_user_id ON term(user_id);",
                "CREATE INDEX IF NOT EXISTS idx_term_active ON term(active);",
                "CREATE INDEX IF NOT EXISTS idx_term_user_active ON term(user_id, active);",
                "CREATE INDEX IF NOT EXISTS idx_term_year_season ON term(year, season);",
                "CREATE INDEX IF NOT EXISTS idx_course_term_id ON course(term_id);",
                "CREATE INDEX IF NOT EXISTS idx_course_name ON course(name);",
                "CREATE INDEX IF NOT EXISTS idx_todo_due_date ON todo_item(due_date);",
                "CREATE INDEX IF NOT EXISTS idx_todo_completed ON todo_item(is_completed);",
                "CREATE INDEX IF NOT EXISTS idx_todo_course_id ON todo_item(course_id);",
                "CREATE INDEX IF NOT EXISTS idx_grade_category_course_id ON grade_category(course_id);",
                "CREATE INDEX IF NOT EXISTS idx_assignment_course_score ON assignment(course_id, score);",
                "CREATE INDEX IF NOT EXISTS idx_assignment_due_score ON assignment(due_date, score);",
            ]

            for index_sql in indexes:
                try:
                    db.session.execute(db.text(index_sql))
                except:
                    pass  # Index might already exist

            db.session.commit()
        except Exception as e:
            app.logger.warning(f"Could not add performance indexes: {e}")

    return app


# Create application instance for compatibility
app = create_app(os.environ.get("FLASK_ENV", "production"))
