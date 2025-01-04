import base64
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from googleapiclient.discovery import build
import logging
from typing import List, Dict, Any, Optional
from config import Config
from gmail_auth import GmailAuthenticator

class GmailHandler:
    def __init__(self, config: Config = None):
        """Initialize Gmail handler with optional config"""
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing Gmail handler")
        self.config = config or Config.from_env()
        self.service = None  # Initialize service as None

        try:
            # Initialize the authenticator with required scopes
            self.authenticator = GmailAuthenticator(self.config.GMAIL_SCOPES)

            # Get credentials using OAuth2 flow
            credentials = self.authenticator.get_credentials()

            if credentials:
                # Build the Gmail service only if we have valid credentials
                self.service = build('gmail', 'v1', credentials=credentials)
                self._verify_connection()
                self.logger.info("Gmail handler initialized successfully")
            else:
                self.logger.info("No credentials available - authentication required")

        except Exception as e:
            self.logger.error(f"Failed to initialize Gmail handler: {str(e)}")
            raise

    def _verify_connection(self):
        """Verify Gmail API connection"""
        if not self.service:
            self.logger.error("Cannot verify connection - service not initialized")
            return False

        try:
            profile = self.service.users().getProfile(userId='me').execute()
            self.logger.info(f"Successfully authenticated as: {profile['emailAddress']}")
            self.logger.info(f"Email thread size: {profile.get('threadsTotal', 0)}")
            self.logger.info(f"Storage used: {profile.get('storageUsed', 0)} bytes")
            return True
        except Exception as e:
            self.logger.error(f"Failed to verify Gmail connection: {str(e)}")
            return False

    def fetch_emails(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent emails"""
        try:
            self.logger.info(f"Fetching last {max_results} emails")
            
            # List messages
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for message in messages:
                try:
                    # Get full message details
                    msg = self.service.users().messages().get(
                        userId='me',
                        id=message['id'],
                        format='full'
                    ).execute()
                    
                    # Extract headers
                    headers = msg['payload']['headers']
                    subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
                    sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
                    date = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'Unknown')
                    
                    # Extract body
                    if 'parts' in msg['payload']:
                        parts = msg['payload']['parts']
                        body = next((
                            base64.urlsafe_b64decode(p['body']['data']).decode()
                            for p in parts
                            if p['mimeType'] == 'text/plain' and 'data' in p['body']
                        ), 'No plain text body')
                    else:
                        body = base64.urlsafe_b64decode(msg['payload']['body']['data']).decode() if 'data' in msg['payload']['body'] else 'No body'
                    
                    emails.append({
                        'id': message['id'],
                        'subject': subject,
                        'from': sender,
                        'date': date,
                        'body': body[:500] + '...' if len(body) > 500 else body  # Truncate long bodies
                    })
                    
                except Exception as e:
                    self.logger.error(f"Error processing message {message['id']}: {str(e)}")
                    continue
            
            return emails
            
        except Exception as e:
            self.logger.error(f"Failed to fetch emails: {str(e)}")
            return []

    def get_unread_emails(self, email_address: str) -> List[Dict[str, Any]]:
        """Fetch unread emails from specified email address"""
        try:
            self.logger.info(f"Searching for unread emails from: {email_address}")

            # First, verify we can list labels to test permissions
            try:
                labels = self.service.users().labels().list(userId='me').execute()
                self.logger.info("Successfully accessed Gmail labels")
                self.logger.info(f"Available labels: {[label['name'] for label in labels.get('labels', [])]}")
            except Exception as e:
                self.logger.error(f"Failed to access Gmail labels: {str(e)}")
                self.logger.error("This indicates a possible permissions issue")
                return []

            query = f'from:{email_address} is:unread'
            self.logger.info(f"Using Gmail search query: {query}")

            try:
                results = self.service.users().messages().list(
                    userId='me',
                    q=query
                ).execute()
            except Exception as e:
                self.logger.error(f"Failed to search messages: {str(e)}")
                self.logger.error("This might indicate an issue with the search query or permissions")
                return []

            messages = results.get('messages', [])
            emails = []

            self.logger.info(f"Found {len(messages)} unread messages")
            if len(messages) == 0:
                self.logger.info("No unread messages found. This could mean either:")
                self.logger.info("1. There are no unread emails")
                self.logger.info("2. The service account might need additional permissions")
                self.logger.info(f"Current user being impersonated: {self.config.GMAIL_USER}")
                self.logger.info("Please verify:")
                self.logger.info("1. The service account has domain-wide delegation")
                self.logger.info("2. The necessary scopes are enabled in Google Workspace")
                self.logger.info("3. The Gmail API is enabled in the project")

            for message in messages:
                try:
                    email_data = self.service.users().messages().get(
                        userId='me',
                        id=message['id'],
                        format='full'
                    ).execute()

                    parsed_email = self._parse_email(email_data)
                    self.logger.info(f"Found email - Subject: {parsed_email['subject']}, "
                                   f"From: {parsed_email['sender']}, "
                                   f"Attachments: {len(parsed_email['attachments'])}")
                    emails.append(parsed_email)
                except Exception as e:
                    self.logger.error(f"Error fetching email {message['id']}: {str(e)}")
                    continue

            return emails

        except Exception as e:
            self.logger.error(f"Error fetching emails: {str(e)}")
            return []

    def _parse_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse email data into structured format"""
        headers = email_data['payload']['headers']
        subject = next(h['value'] for h in headers if h['name'].lower() == 'subject')
        sender = next(h['value'] for h in headers if h['name'].lower() == 'from')

        body = ""
        attachments = []

        if 'parts' in email_data['payload']:
            for part in email_data['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    body = base64.urlsafe_b64decode(
                        part['body']['data']
                    ).decode('utf-8')
                elif 'filename' in part:
                    attachments.append({
                        'filename': part['filename'],
                        'attachment_id': part['body'].get('attachmentId'),
                        'mime_type': part['mimeType']
                    })

        return {
            'id': email_data['id'],
            'subject': subject,
            'sender': sender,
            'body': body,
            'attachments': attachments
        }

    def download_attachment(self, email_id: str, attachment_id: str) -> Optional[bytes]:
        """Download email attachment"""
        try:
            attachment = self.service.users().messages().attachments().get(
                userId='me',
                messageId=email_id,
                id=attachment_id
            ).execute()

            if 'data' in attachment:
                return base64.urlsafe_b64decode(attachment['data'])
            return None

        except Exception as e:
            self.logger.error(f"Error downloading attachment: {str(e)}")
            return None

    def forward_email(self, to_address: str, subject: str, body: str, 
                     attachments: List[Dict[str, bytes]] = None) -> bool:
        """Forward email with attachments"""
        try:
            message = MIMEMultipart()
            message['to'] = to_address
            message['subject'] = subject

            message.attach(MIMEText(body, 'plain'))

            if attachments:
                for attachment in attachments:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment['content'])
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {attachment["filename"]}'
                    )
                    message.attach(part)

            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')

            self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()

            return True

        except Exception as e:
            self.logger.error(f"Error forwarding email: {str(e)}")
            return False

    def mark_as_read(self, email_id: str) -> bool:
        """Mark email as read"""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=email_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            return True
        except Exception as e:
            self.logger.error(f"Error marking email as read: {str(e)}")
            return False