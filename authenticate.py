import os
import logging
from gmail_auth import GmailAuthenticator
from config import Config
from utils import setup_logging

def main():
    """Main authentication process"""
    try:
        # Setup logging
        setup_logging()
        logger = logging.getLogger(__name__)
        
        # Load config
        config = Config()
        
        # Initialize authenticator
        authenticator = GmailAuthenticator(config)
        
        # Get credentials
        credentials = authenticator.get_credentials()
        
        if credentials and credentials.valid:
            logger.info("Authentication successful!")
            logger.info(f"Token saved to {os.path.join(os.getcwd(), 'token.json')}")
            return 0
        else:
            logger.error("Failed to obtain valid credentials")
            return 1
            
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())
