import os
import pickle
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
import logging
import json
from flask import session
import os

# Allow HTTP for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Configure logging
logger = logging.getLogger(__name__)

class GmailAuthenticator:
    """Handles Gmail API authentication using OAuth2"""

    def __init__(self, scopes):
        self.scopes = scopes
        self.logger = logger
        self._setup_oauth_config()
        self._flow = None

    def _setup_oauth_config(self):
        """Setup OAuth configuration"""
        # Load the client configuration
        if os.path.exists('credentials.json'):
            with open('credentials.json', 'r') as f:
                self.client_config = json.load(f)
                # Remove metadata scope if present as it conflicts with full access
                if isinstance(self.scopes, list):
                    self.scopes = [scope for scope in self.scopes 
                                 if 'gmail.metadata' not in scope]
                self.logger.info("Loaded OAuth client configuration")
                self.logger.debug(f"Client config: {self.client_config}")
        else:
            self.logger.error("credentials.json not found")
            raise FileNotFoundError("OAuth client configuration file not found")

    def _get_redirect_uri(self):
        """Get the correct redirect URI from client configuration"""
        redirect_uri = os.environ.get("OAUTH_CALLBACK_URL")
        if not redirect_uri:
            raise ValueError("OAUTH_CALLBACK_URL environment variable is required")
        self.logger.debug(f"Using redirect URI: {redirect_uri}")
        return redirect_uri

    def get_authorization_url(self):
        """Get the authorization URL to start OAuth flow"""
        try:
            self.logger.debug("Creating OAuth flow")
            self._flow = Flow.from_client_config(
                self.client_config,
                scopes=self.scopes,
                redirect_uri=self._get_redirect_uri()
            )
            
            self.logger.debug("Generating authorization URL")
            auth_url, state = self._flow.authorization_url(
                access_type='offline',
                include_granted_scopes='false',  # Don't include previously granted scopes
                prompt='consent'  # Force consent screen to get refresh token
            )
            
            # Store the state and scopes in the session
            session['oauth_state'] = state
            session['oauth_scopes'] = self.scopes
            self.logger.debug(f"Stored state in session: {state}")
            self.logger.debug(f"Stored scopes in session: {self.scopes}")
            
            return auth_url
        except Exception as e:
            self.logger.error(f"Error generating authorization URL: {str(e)}")
            raise

    def _load_credentials_from_token(self):
        """Load credentials from token file if it exists."""
        try:
            if os.path.exists('token.json'):
                with open('token.json', 'r') as token:
                    creds_info = token.read()
                    self.logger.info("Found existing token.json")
                    self.logger.debug(f"Token info: {creds_info}")
                    return Credentials.from_authorized_user_info(eval(creds_info), self.scopes)
            else:
                self.logger.debug("No token.json found")
        except Exception as e:
            self.logger.error(f"Error loading token.json: {str(e)}")
            if os.path.exists('token.json'):
                os.remove('token.json')
                self.logger.info("Removed invalid token.json")
        return None

    def _save_credentials(self, creds):
        """Save credentials to token file."""
        try:
            creds_data = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes,
            }
            with open('token.json', 'w') as token:
                token.write(str(creds_data))
            self.logger.info("Saved credentials to token.json")
        except Exception as e:
            self.logger.error(f"Error saving credentials: {str(e)}")
            raise

    def get_credentials(self):
        """Get valid user credentials from storage or initiate OAuth2 flow."""
        creds = self._load_credentials_from_token()

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    self.logger.info("Refreshed expired credentials")
                except Exception as e:
                    self.logger.error(f"Error refreshing credentials: {str(e)}")
                    creds = None

            if not creds:
                try:
                    auth_url = self.get_authorization_url()
                    print("\n" + "="*80)
                    print("Please visit this URL to authorize the application:")
                    print("="*80)
                    print(auth_url)
                    print("\nAfter authorization, you will be redirected to the callback URL.")
                    print("="*80 + "\n")

                    self.logger.info("Authorization URL generated and displayed")
                    return None

                except Exception as e:
                    self.logger.error(f"Error in OAuth2 flow: {str(e)}")
                    raise

        return creds

    def handle_oauth2_callback(self, request_url: str, state: str = None):
        """Handle OAuth2 callback and save credentials"""
        try:
            self.logger.debug(f"Handling OAuth callback with state: {state}")
            self.logger.debug(f"Session state: {session.get('oauth_state')}")
            
            # Ensure scopes match
            if 'oauth_scopes' in session:
                original_scopes = set(session['oauth_scopes'])
                current_scopes = set(self.scopes)
                if original_scopes != current_scopes:
                    self.logger.warning("Scopes have changed during authentication")
                    self.scopes = list(original_scopes)  # Use original scopes
            
            # Fetch the token
            self._flow.fetch_token(authorization_response=request_url)
            
            # Get credentials from flow
            creds = self._flow.credentials
            
            # Save credentials
            creds_data = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': self.scopes  # Use our scopes instead of creds.scopes
            }
            
            with open('token.json', 'w') as token:
                token.write(str(creds_data))
            self.logger.info("Saved credentials to token.json")
            
            return creds
            
        except Exception as e:
            self.logger.error(f"Error handling OAuth callback: {str(e)}")
            raise

    def revoke_credentials(self):
        """Revoke the current credentials and remove stored tokens."""
        try:
            # Try to load existing credentials
            creds = self._load_credentials_from_token()
            if creds:
                # Revoke access
                import google.oauth2.credentials
                import google.auth.transport.requests
                import requests
                
                # Build the revoke request
                revoke_url = "https://accounts.google.com/o/oauth2/revoke"
                params = {'token': creds.token}
                headers = {'content-type': 'application/x-www-form-urlencoded'}
                
                # Make the request
                response = requests.post(revoke_url, params=params, headers=headers)
                
                # Remove the token file regardless of the response
                if os.path.exists('token.json'):
                    os.remove('token.json')
                    self.logger.info("Removed token.json file")
                
                if response.status_code == 200:
                    self.logger.info("Successfully revoked credentials")
                    return True
                else:
                    self.logger.error(f"Failed to revoke credentials. Status code: {response.status_code}")
                    return False
            else:
                # If no credentials exist, just return True
                self.logger.info("No credentials found to revoke")
                return True
                
        except Exception as e:
            self.logger.error(f"Error revoking credentials: {str(e)}")
            # Try to remove the token file anyway
            if os.path.exists('token.json'):
                os.remove('token.json')
                self.logger.info("Removed token.json file")
            return False

    def get_user_email(self):
        """Get the email address of the authenticated user."""
        try:
            creds = self._load_credentials_from_token()
            if not creds:
                return None
                
            from googleapiclient.discovery import build
            service = build('gmail', 'v1', credentials=creds)
            
            # Get the user's profile
            profile = service.users().getProfile(userId='me').execute()
            return profile.get('emailAddress')
            
        except Exception as e:
            self.logger.error(f"Error getting user email: {str(e)}")
            return None