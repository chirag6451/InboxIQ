import os
import pickle
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
import logging
import json

class GmailAuthenticator:
    """Handles Gmail API authentication using OAuth2"""

    def __init__(self, scopes):
        self.scopes = scopes
        self.logger = logging.getLogger(__name__)
        self._setup_oauth_config()
        self._current_flow = None

    def _setup_oauth_config(self):
        """Setup OAuth configuration"""
        # Load the client configuration
        if os.path.exists('credentials.json'):
            with open('credentials.json', 'r') as f:
                self.client_config = json.load(f)
                self.logger.info("Loaded OAuth client configuration")
        else:
            raise FileNotFoundError("OAuth client configuration file not found")

    def _get_redirect_uri(self):
        """Get the correct redirect URI from client configuration"""
        try:
            # Get the redirect URI from the client configuration
            redirect_uri = self.client_config['web']['redirect_uris'][0]
            self.logger.info(f"Using configured redirect URI: {redirect_uri}")
            return redirect_uri
        except (KeyError, IndexError) as e:
            self.logger.error(f"Error getting redirect URI from config: {str(e)}")
            raise

    def get_authorization_url(self):
        """Get the authorization URL to start OAuth flow"""
        self._current_flow = Flow.from_client_config(
            self.client_config,
            scopes=self.scopes,
            redirect_uri=self._get_redirect_uri()
        )
        auth_url, _ = self._current_flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        return auth_url

    def _load_credentials_from_token(self):
        """Load credentials from token file if it exists."""
        if os.path.exists('token.json'):
            try:
                with open('token.json', 'r') as token:
                    creds_info = token.read()
                    self.logger.info("Found existing token.json")
                    return Credentials.from_authorized_user_info(eval(creds_info), self.scopes)
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

    def handle_oauth2_callback(self, code, state):
        """Handle the OAuth2 callback"""
        try:
            # Exchange the authorization code for credentials
            self._current_flow.fetch_token(code=code)
            creds = self._current_flow.credentials
            self._save_credentials(creds)
            return creds
        except Exception as e:
            self.logger.error(f"Error handling OAuth callback: {str(e)}")
            raise

    def revoke_credentials(self):
        """Revoke the current credentials and remove stored tokens."""
        try:
            if os.path.exists('token.json'):
                os.remove('token.json')
                self.logger.info("Removed token.json file")
            self.logger.info("Successfully revoked credentials")
            return True
        except Exception as e:
            self.logger.error(f"Error revoking credentials: {str(e)}")
            return False