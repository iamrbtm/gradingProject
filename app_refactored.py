# app_refactored.py - Refactored main application file
import os
from datetime import datetime
from flask import Flask
from flask_login import LoginManager

def create_app(config_name='development'):
    """Application factory pattern."""
    app = Flask(__name__, template_folder='app/templates', static_folder='static')
    
    # Configuration
    if config_name == 'production':
        app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'change-this-in-production')
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///grade_tracker.db')
    else:
        app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///grade_tracker.db'
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    from app.models import db
    db.init_app(app)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))
    
    # Register Blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.main import main_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    
    # Initialize error handlers and logging
    from app.error_handlers import init_error_handlers, setup_logging
    init_error_handlers(app)
    setup_logging(app)
    
    # Global template context
    @app.context_processor
    def inject_current_year():
        current_month = datetime.now().month
        if current_month in [9, 10, 11, 12]:
            current_season = 'Fall'
        elif current_month in [1, 2, 3]:
            current_season = 'Winter'
        elif current_month in [4, 5, 6]:
            current_season = 'Spring'
        else:
            current_season = 'Summer'
        return {'current_year': datetime.now().year, 'current_season': current_season}
    
    # Custom Jinja2 filters
    def format_score(value):
        if value is None:
            return '--'
        if value == int(value):
            return int(value)
        return value
    
    app.jinja_env.filters['format_score'] = format_score
    
    # Initialize sync commands (optional)
    try:
        from app.sync_commands import init_sync_commands
        init_sync_commands(app)
    except ImportError:
        app.logger.warning("Sync commands not available. Install required dependencies.")
    
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
app = create_app(os.environ.get('FLASK_ENV', 'development'))

if __name__ == '__main__':
    # Development server
    app.run(debug=True, port=12345)