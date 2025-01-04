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
from google.oauth2.credentials import Credentials

class GmailHandler:
    """Handles Gmail API operations"""
    
    def __init__(self, credentials: Any, config: Any):
        """Initialize Gmail handler with credentials and config"""
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.credentials = credentials  # Store credentials for other services to use
        
        try:
            self.service = build('gmail', 'v1', credentials=credentials)
            self.logger.info("Initializing Gmail handler")
            
            # Test authentication by getting user profile
            user_info = self.service.users().getProfile(userId='me').execute()
            self.email = user_info['emailAddress']
            self.logger.info(f"Successfully authenticated as: {self.email}")
            
            # Get mailbox details
            profile = self.service.users().getProfile(userId='me').execute()
            if 'threadsTotal' in profile:
                self.logger.info(f"Email thread size: {profile['threadsTotal']}")
            
            # Storage info might not be available for all accounts
            if 'storageUsed' in profile:
                storage_used = int(profile.get('storageUsed', 0))
                storage_mb = storage_used / (1024 * 1024)  # Convert to MB
                self.logger.info(f"Storage used: {storage_mb:.2f} MB")
            
            self.logger.info("Gmail handler initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing Gmail handler: {str(e)}")
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
                    body = self._get_message_body(msg)
                    
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

    def get_unread_emails(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """Get unread emails with their details"""
        try:
            messages = self.list_messages(query='is:unread', max_results=max_results)
            emails = []
            
            for message in messages:
                try:
                    msg = self.get_message(message['id'])
                    if msg:
                        # Extract headers
                        headers = msg['payload']['headers']
                        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
                        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
                        to = next((h['value'] for h in headers if h['name'].lower() == 'to'), '')
                        cc = next((h['value'] for h in headers if h['name'].lower() == 'cc'), '')
                        date = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'Unknown')
                        
                        # Extract body
                        body = self._get_message_body(msg)
                        
                        # Check if current user is CC'd
                        user_email = self.get_authenticated_email()
                        is_cced = False
                        if user_email:
                            cc_list = [addr.strip().lower() for addr in cc.split(',') if addr.strip()]
                            to_list = [addr.strip().lower() for addr in to.split(',') if addr.strip()]
                            user_email = user_email.lower()
                            is_cced = user_email in cc_list
                            is_to = user_email in to_list
                        
                        emails.append({
                            'id': message['id'],
                            'thread_id': message['threadId'],
                            'subject': subject,
                            'sender': sender,
                            'to': to,
                            'cc': cc,
                            'date': date,
                            'body': body,
                            'is_cced': is_cced,
                            'is_to': is_to
                        })
                        
                except Exception as e:
                    self.logger.error(f"Error processing message {message['id']}: {str(e)}")
                    continue
            
            return emails
            
        except Exception as e:
            self.logger.error(f"Error getting unread emails: {str(e)}")
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

    def forward_email(self, msg_id: Optional[str], to_email: str) -> bool:
        """Forward an email to specified address"""
        try:
            if not msg_id:
                self.logger.error("Message ID is required for forwarding")
                return False
                
            # Get the original message
            original = self.get_message(msg_id)
            if not original:
                return False
            
            # Extract headers
            headers = original['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            from_email = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
            date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
            
            # Create forwarding message
            message = MIMEMultipart()
            message['to'] = to_email
            message['subject'] = f"Fwd: {subject}"
            
            # Create forwarding header
            forward_msg = [
                "---------- Forwarded message ----------",
                f"From: {from_email}",
                f"Date: {date}",
                f"Subject: {subject}",
                f"To: {to_email}",
                "",
                self._get_message_body(original)
            ]
            
            # Add the forwarded content
            message.attach(MIMEText('\n'.join(forward_msg), 'plain'))
            
            # Encode and send
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            self.service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()
            
            self.logger.info(f"Successfully forwarded message {msg_id} to {to_email}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error forwarding message {msg_id}: {str(e)}")
            return False

    def _get_message_body(self, message_data: Dict[str, Any]) -> str:
        """Extract message body from message data"""
        try:
            # Extract headers for fallback
            headers = message_data['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
            
            # Try to get body from parts
            if 'parts' in message_data['payload']:
                parts = message_data['payload']['parts']
                for part in parts:
                    if part.get('mimeType') == 'text/plain':
                        if 'data' in part.get('body', {}):
                            return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
            
            # Try to get body directly
            if 'body' in message_data['payload'] and 'data' in message_data['payload']['body']:
                return base64.urlsafe_b64decode(message_data['payload']['body']['data']).decode('utf-8')
            
            # Fallback to subject if no body found
            return f"Subject: {subject}"
            
        except Exception as e:
            self.logger.error(f"Error extracting message body: {str(e)}")
            return "Error extracting message body"

    def get_message(self, msg_id: str) -> Optional[Dict[str, Any]]:
        """Get message details by ID"""
        try:
            self.logger.info(f"Fetching message: {msg_id}")
            message = self.service.users().messages().get(
                userId='me',
                id=msg_id,
                format='full'
            ).execute()
            return message
        except Exception as e:
            self.logger.error(f"Error getting message {msg_id}: {str(e)}")
            return None

    def list_messages(self, query: str = None, max_results: int = 10) -> List[Dict[str, Any]]:
        """List messages matching the specified query"""
        try:
            self.logger.info(f"Listing messages with query: {query}")
            
            # Create the list request
            request = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q=query if query else None
            )
            
            # Execute the request
            response = request.execute()
            messages = response.get('messages', [])
            
            self.logger.info(f"Found {len(messages)} messages")
            return messages
            
        except Exception as e:
            self.logger.error(f"Error listing messages: {str(e)}")
            return []

    def get_authenticated_email(self) -> str:
        """Get the email address of the authenticated user"""
        return self.email

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

    def mark_important(self, msg_id: str) -> bool:
        """Mark a message as important"""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'addLabelIds': ['IMPORTANT']}
            ).execute()
            self.logger.info(f"Marked message {msg_id} as important")
            return True
        except Exception as e:
            self.logger.error(f"Error marking message {msg_id} as important: {str(e)}")
            return False

    def _create_label(self, label_name: str) -> Optional[str]:
        """Create a Gmail label if it doesn't exist"""
        try:
            # First check if label already exists
            try:
                results = self.service.users().labels().list(userId='me').execute()
                labels = results.get('labels', [])
                
                # Check for existing label (case insensitive)
                for label in labels:
                    if label['name'].lower() == label_name.lower():
                        return label['id']
            except Exception as e:
                self.logger.error(f"Error checking existing labels: {str(e)}")
                return None

            # Create new label if it doesn't exist
            label = self.service.users().labels().create(
                userId='me',
                body={
                    'name': label_name,
                    'labelListVisibility': 'labelShow',
                    'messageListVisibility': 'show'
                }
            ).execute()
            
            self.logger.info(f"Created new label: {label_name}")
            return label['id']
            
        except Exception as e:
            self.logger.error(f"Error creating label {label_name}: {str(e)}")
            return None

    def add_label(self, msg_id: str, label_name: str) -> bool:
        """Add a label to a message"""
        try:
            # Ensure label exists
            label_id = self._create_label(label_name)
            if not label_id:
                return False
            
            # Add label to message
            self.service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'addLabelIds': [label_id]}
            ).execute()
            
            self.logger.info(f"Added label {label_name} to message {msg_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding label {label_name} to message {msg_id}: {str(e)}")
            return False

    def create_message(self, sender: str, to: str, subject: str, message_html: str) -> Dict[str, Any]:
        """Create an email message with HTML content"""
        try:
            message = MIMEMultipart('alternative')
            message['to'] = to
            message['from'] = sender
            message['subject'] = subject
            
            # Attach HTML content
            message.attach(MIMEText(message_html, 'html'))
            
            # Encode message
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            return {'raw': raw}
            
        except Exception as e:
            self.logger.error(f"Error creating message: {str(e)}")
            return None

    def send_message(self, message: Dict[str, Any]) -> bool:
        """Send an email message"""
        try:
            if not message:
                return False
                
            self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending message: {str(e)}")
            return False