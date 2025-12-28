"""
Google OAuth2 Authentication for Google Tasks API
"""
import os
import json
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from flask import current_app, session, url_for, request, redirect, flash
import secrets

# Google Tasks API scopes
SCOPES = ['https://www.googleapis.com/auth/tasks']

class GoogleAuthManager:
    """Manages Google OAuth2 authentication for Tasks API"""
    
    def __init__(self):
        self.credentials_file = os.path.join(current_app.instance_path, 'google_credentials.json')
        self.token_file = os.path.join(current_app.instance_path, 'google_token.json')
    
    def has_credentials_file(self) -> bool:
        """Check if Google credentials file exists"""
        return os.path.exists(self.credentials_file)
    
    def get_credentials(self) -> Optional[Credentials]:
        """Get valid Google credentials"""
        creds = None
        
        # Check if token file exists
        if os.path.exists(self.token_file):
            try:
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            except Exception as e:
                current_app.logger.error(f'Error loading Google credentials from file: {e}')
                # Remove corrupted token file
                try:
                    os.remove(self.token_file)
                except:
                    pass
                return None
        
        # If there are no valid credentials available, return None
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    # Save the refreshed credentials
                    self.save_credentials(creds)
                except Exception as e:
                    current_app.logger.error(f'Error refreshing Google credentials: {e}')
                    return None
            else:
                return None
        
        return creds
    
    def save_credentials(self, creds: Credentials):
        """Save credentials to token file"""
        try:
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        except Exception as e:
            current_app.logger.error(f'Error saving Google credentials: {e}')
    
    def get_authorization_url(self) -> Optional[str]:
        """Get Google OAuth2 authorization URL"""
        if not self.has_credentials_file():
            return None
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_file, SCOPES
            )
            
            # Generate state parameter for security
            state = secrets.token_urlsafe(32)
            session['google_auth_state'] = state
            
            # Set redirect URI
            redirect_uri = url_for('main.google_auth_callback', _external=True)
            flow.redirect_uri = redirect_uri
            
            authorization_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent',
                state=state
            )
            
            # Store flow data needed for callback
            session['google_auth_flow_data'] = {
                'redirect_uri': redirect_uri,
                'state': state
            }
            
            return authorization_url
        except Exception as e:
            current_app.logger.error(f'Error getting Google authorization URL: {e}')
            return None
    
    def handle_auth_callback(self, code: str, state: str) -> tuple[bool, str]:
        """Handle OAuth2 callback and save credentials"""
        try:
            # Verify state parameter
            if state != session.get('google_auth_state'):
                current_app.logger.error('Invalid state parameter in Google auth callback')
                return False, 'Invalid state parameter'
            
            # Get flow data from session
            flow_data = session.get('google_auth_flow_data')
            if not flow_data:
                current_app.logger.error('No flow data found in session')
                return False, 'No flow data found in session'
            
            # Create new flow for token exchange
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_file, SCOPES
            )
            flow.redirect_uri = flow_data['redirect_uri']
            
            # Exchange authorization code for credentials
            flow.fetch_token(code=code)
            creds = flow.credentials
            
            # Save credentials
            self.save_credentials(creds)
            
            # Clean up session
            session.pop('google_auth_state', None)
            session.pop('google_auth_flow_data', None)
            
            return True, 'Successfully authenticated with Google Tasks'
        except Exception as e:
            current_app.logger.error(f'Error handling Google auth callback: {e}')
            return False, str(e)
    
    def revoke_credentials(self):
        """Revoke and remove stored credentials"""
        try:
            # Get current credentials
            creds = self.get_credentials()
            if creds:
                # Revoke the credentials
                Request().post('https://oauth2.googleapis.com/revoke',
                    params={'token': creds.token},
                    headers={'content-type': 'application/x-www-form-urlencoded'})
            
            # Remove token file
            if os.path.exists(self.token_file):
                os.remove(self.token_file)
                
        except Exception as e:
            current_app.logger.error(f'Error revoking Google credentials: {e}')
    
    def get_tasks_service(self):
        """Get authenticated Google Tasks service"""
        creds = self.get_credentials()
        if not creds:
            return None
        
        try:
            service = build('tasks', 'v1', credentials=creds)
            return service
        except Exception as e:
            current_app.logger.error(f'Error building Google Tasks service: {e}')
            return None

def setup_google_credentials_instructions():
    """Return instructions for setting up Google credentials"""
    return {
        'title': 'Google Tasks Setup Required',
        'steps': [
            '1. Go to the Google Cloud Console (https://console.cloud.google.com/)',
            '2. Create a new project or select an existing one',
            '3. Enable the Google Tasks API',
            '4. Create OAuth 2.0 credentials (Desktop application type)',
            '5. Download the credentials JSON file',
            '6. Save it as "google_credentials.json" in the instance folder',
            '7. Return to this page and click "Connect to Google Tasks"'
        ]
    }