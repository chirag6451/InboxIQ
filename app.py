from flask import Flask, request, redirect, url_for, jsonify
import os
import logging
from gmail_auth import GmailAuthenticator
from gmail_handler import GmailHandler
from config import Config

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Domain configuration
# When deploying, replace this with your actual domain
DOMAIN = os.environ.get('APP_DOMAIN', 'localhost:8080')
USE_HTTPS = False  # Force HTTP for local development
PROTOCOL = 'https' if USE_HTTPS else 'http'
CALLBACK_URL = f"{PROTOCOL}://{DOMAIN}/oauth2callback"

print(f"\nCallback URL will be: {CALLBACK_URL}")
print("Make sure to:")
print("1. Set APP_DOMAIN environment variable to your domain")
print("2. Add this callback URL to Google Cloud Console authorized redirect URIs")

# Initialize the authenticator with required scopes using the new method
authenticator = GmailAuthenticator(Config.get_gmail_scopes())

@app.route('/')
def index():
    return "Gmail Authentication Service"

@app.route('/auth')
def auth():
    """Start the OAuth flow"""
    auth_url = authenticator.get_authorization_url()
    return redirect(auth_url)

@app.route('/oauth2callback')
def oauth2callback():
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')

        if error:
            logging.error(f"OAuth error: {error}")
            error_message = "Authorization failed. Common issues:\n"
            error_message += "1. Redirect URI mismatch\n"
            error_message += "2. Application not properly configured in Google Cloud Console\n"
            error_message += f"Current error: {error}"
            return error_message, 400

        if code:
            authenticator.handle_oauth2_callback(code, state)
            return redirect(url_for('emails'))
        return "No authorization code received", 400

    except Exception as e:
        logging.error(f"Error in OAuth callback: {str(e)}")
        return str(e), 500

@app.route('/emails')
def emails():
    """Fetch and display emails"""
    try:
        handler = GmailHandler()
        messages = handler.fetch_emails(max_results=10)  # Fetch last 10 emails
        return jsonify(messages)
    except Exception as e:
        logging.error(f"Error fetching emails: {str(e)}")
        return str(e), 500

if __name__ == '__main__':
    print(f"\nCallback URL configured as: {CALLBACK_URL}")
    print("Make sure this URL is added to the authorized redirect URIs in Google Cloud Console")
    app.run(host='0.0.0.0', port=8080)