import sys
import os

# Add the project directory to the sys.path
project_path = '/home/onlymyli/public_html/grades'
if project_path not in sys.path:
    sys.path.insert(0, project_path)

# Load environment variables from .env file FIRST
from dotenv import load_dotenv
dotenv_path = os.path.join(project_path, '.env')
load_dotenv(dotenv_path)

# Verify critical environment variables are loaded
required_vars = ['FLASK_SECRET_KEY', 'API_TOKEN_ENCRYPTION_KEY', 'DATABASE_URL']
missing_vars = [var for var in required_vars if not os.environ.get(var)]
if missing_vars:
    print(f"WARNING: Missing required environment variables: {', '.join(missing_vars)}")
    print(f"Checked .env file at: {dotenv_path}")

# Set environment variables for production (override if needed)
os.environ['FLASK_ENV'] = 'production'
# DATABASE_URL and API_TOKEN_ENCRYPTION_KEY should come from .env file

from app import create_app

class ScriptNameMiddleware:
    def __init__(self, app, script_name):
        self.app = app
        self.script_name = script_name

    def __call__(self, environ, start_response):
        environ['SCRIPT_NAME'] = self.script_name
        return self.app(environ, start_response)

# Create the Flask app
app = create_app('production')

# Wrap the app with middleware to set SCRIPT_NAME
application = ScriptNameMiddleware(app, '/grades')