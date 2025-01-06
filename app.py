from flask import Flask, request, redirect, url_for, jsonify, session
import os
import logging
from gmail_auth import GmailAuthenticator
from gmail_handler import GmailHandler
from config import Config

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# Domain configuration
DOMAIN = os.environ.get('APP_DOMAIN', 'localhost:8989')  
USE_HTTPS = False  # Force HTTP for local development
PROTOCOL = 'https' if USE_HTTPS else 'http'
CALLBACK_URL = f"{PROTOCOL}://{DOMAIN}/oauth2callback"

print(f"\nCallback URL will be: {CALLBACK_URL}")
print("Make sure to:")
print("1. Set APP_DOMAIN environment variable to your domain")
print("2. Add this callback URL to Google Cloud Console authorized redirect URIs")

try:
    # Initialize the authenticator with required scopes
    authenticator = GmailAuthenticator(Config.get_gmail_scopes())
except FileNotFoundError:
    print("\nError: credentials.json file is missing!")
    print("\nTo fix this:")
    print("1. Go to Google Cloud Console (https://console.cloud.google.com)")
    print("2. Create or select your project")
    print("3. Enable Gmail API")
    print("4. Create OAuth 2.0 credentials")
    print("5. Download the credentials and save as 'credentials.json' in the project root directory")
    print("6. Make sure to add this callback URL to authorized redirect URIs:", CALLBACK_URL)
    exit(1)

def get_html_template(token_exists, user_email, env_exists, creds_exists):
    """Generate the HTML template with proper status"""
    authenticated_content = '''
        <div class="setup-step">
            <h3>3. Running the Scanner</h3>
            <p>You can now run the invoice scanner in two ways:</p>
            <ol>
                <li><strong>Manual Execution:</strong><br>
                    Run <code>python check_invoice_emails.py</code> in your terminal</li>
                <li><strong>Automated Scanning:</strong><br>
                    Set up a cron job (see README.md for instructions)</li>
            </ol>
        </div>
    ''' if token_exists else ''

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            .status {{ margin: 20px 0; }}
            .button-group {{ display: flex; gap: 10px; margin: 20px 0; }}
            .button {{ padding: 10px; text-decoration: none; border-radius: 4px; color: white; }}
            .button.primary {{ background: #4285f4; }}
            .button.danger {{ background: #db4437; }}
            .setup-guide {{ background: #f8f9fa; padding: 20px; border-radius: 4px; margin: 20px 0; }}
            .setup-step {{ margin: 10px 0; }}
            .warning {{ color: #db4437; }}
            .success {{ color: #0f9d58; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Gmail Invoice Scanner</h1>
            
            <div class="status">
                {'<p class="success">✓ Currently authenticated with Gmail</p>' if token_exists else '<p class="warning">✗ Not authenticated with Gmail</p>'}
                {f'<p>Authenticated account: <strong>{user_email}</strong></p>' if user_email else ''}
            </div>
            
            <div class="button-group">
                <a href="/auth" class="button primary">
                    {'Switch Gmail Account' if token_exists else 'Authenticate with Gmail'}
                </a>
                {'<a href="/revoke" class="button danger">Revoke Access</a>' if token_exists else ''}
            </div>
            
            <div class="setup-guide">
                <h2>Setup Status & Next Steps</h2>
                
                <div class="setup-step">
                    <h3>1. Configuration Files</h3>
                    <p>{'✓' if env_exists else '✗'} .env file: {'.env file is present' if env_exists else '<span class="warning">Missing .env file. Copy .env.example to .env and configure it.</span>'}</p>
                    <p>{'✓' if creds_exists else '✗'} credentials.json: {'Google credentials file is present' if creds_exists else '<span class="warning">Missing credentials.json. Download from Google Cloud Console.</span>'}</p>
                </div>
                
                <div class="setup-step">
                    <h3>2. Gmail Authentication</h3>
                    {'<p class="success">✓ Gmail authentication complete. The scanner can now access your emails.</p>' if token_exists else '<p class="warning">✗ Please authenticate with Gmail using the button above.</p>'}
                </div>
                
                {authenticated_content}
                
                <div class="setup-step">
                    <h3>Documentation</h3>
                    <p>For detailed setup instructions, configuration options, and troubleshooting:</p>
                    <ol>
                        <li>Read the <code>README.md</code> file in the project root</li>
                        <li>Check <code>.env</code> file comments for configuration options</li>
                        <li>Review <code>config.py</code> for advanced settings</li>
                    </ol>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/')
def index():
    # Check if we have valid credentials
    token_exists = os.path.exists('token.json')
    user_email = authenticator.get_user_email() if token_exists else None
    
    # Get configuration status
    env_exists = os.path.exists('.env')
    creds_exists = os.path.exists('credentials.json')
    
    return get_html_template(token_exists, user_email, env_exists, creds_exists)

@app.route('/auth')
def auth():
    """Start the OAuth flow"""
    try:
        auth_url = authenticator.get_authorization_url()
        logger.debug(f"Generated auth URL: {auth_url}")
        logger.debug(f"Session after auth: {session}")
        return redirect(auth_url)
    except Exception as e:
        logger.error(f"Error in auth route: {str(e)}")
        return str(e), 500

@app.route('/oauth2callback')
def oauth2callback():
    """Handle OAuth2 callback"""
    try:
        # Get state from request
        state = request.args.get('state')
        
        # Handle the callback
        creds = authenticator.handle_oauth2_callback(
            request_url=request.url,
            state=state
        )
        
        # Try to get user email
        try:
            handler = GmailHandler(creds)
            user_email = handler.get_authenticated_email()
            session['user_email'] = user_email
        except Exception as e:
            logger.error(f"Error getting user email: {str(e)}")
            session['user_email'] = None
        
        return redirect(url_for('index'))
        
    except Exception as e:
        logger.error(f"Error in OAuth callback: {str(e)}")
        return f"Error in OAuth callback: {str(e)}", 500

@app.route('/revoke')
def revoke():
    """Revoke the current Gmail authorization"""
    try:
        if authenticator.revoke_credentials():
            return """
            <h1>Authorization Revoked</h1>
            <p>Successfully revoked Gmail access.</p>
            <p><a href="/" style="color: #4285f4;">Return to Home</a></p>
            """
        else:
            return """
            <h1>Error</h1>
            <p>Failed to revoke authorization.</p>
            <p><a href="/" style="color: #4285f4;">Return to Home</a></p>
            """, 400
    except Exception as e:
        logger.error(f"Error revoking credentials: {str(e)}")
        return str(e), 500

if __name__ == '__main__':
    print(f"\nCallback URL configured as: {CALLBACK_URL}")
    print("Make sure this URL is added to the authorized redirect URIs in Google Cloud Console")
    app.run(host='0.0.0.0', port=8989)  