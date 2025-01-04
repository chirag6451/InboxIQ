from gmail_handler import GmailHandler
from email_classifier import EmailClassifier
import json
from datetime import datetime, timedelta
import logging
import base64
import re
from config import Config
from typing import Dict, Any, List, Optional
from report_generator import ReportGenerator
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from openai import OpenAI

class EmailProcessor:
    def __init__(self):
        self.config = Config.from_env()
        
        # Load credentials from token file
        if os.path.exists('token.json'):
            with open('token.json', 'r') as token:
                creds_info = eval(token.read())
                from google.oauth2.credentials import Credentials
                creds = Credentials.from_authorized_user_info(creds_info, self.config.GMAIL_SCOPES)
                self.gmail = GmailHandler(credentials=creds, config=self.config)
        else:
            raise ValueError("No token.json found. Please authenticate first.")
            
        self.classifier = EmailClassifier(self.config)
        self.logger = logging.getLogger(__name__)
        self.summary = {
            'total_emails_processed': 0,
            'emails_forwarded': 0,
            'category_stats': {},
            'forwarding_details': [],
            'start_time': datetime.now()
        }

    def process_emails(self, max_emails: int = 10):
        """Process unread emails and generate summary"""
        try:
            # Get authenticated email
            user_email = self.gmail.get_authenticated_email()
            if not user_email:
                self.logger.error("Could not determine authenticated email")
                return

            # Get unread messages
            messages = self.gmail.list_messages(query='is:unread', max_results=max_emails)
            self.summary['total_emails_processed'] = len(messages)
            
            for message in messages:
                try:
                    # Get full message details
                    msg_data = self.gmail.get_message(message['id'])
                    if not msg_data:
                        continue

                    # Extract email details
                    headers = msg_data['payload']['headers']
                    subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
                    sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
                    to = next((h['value'] for h in headers if h['name'].lower() == 'to'), '')
                    cc = next((h['value'] for h in headers if h['name'].lower() == 'cc'), '')
                    date = next((h['value'] for h in headers if h['name'].lower() == 'date'), None)
                    body = self.gmail._get_message_body(msg_data)

                    # Check if user is in CC
                    cc_list = [email.strip() for email in cc.split(',') if email.strip()]
                    is_cc = any(user_email.lower() in cc_email.lower() for cc_email in cc_list)

                    # Parse date if available
                    try:
                        if date:
                            for fmt in [
                                '%a, %d %b %Y %H:%M:%S %z',  # RFC 2822
                                '%a, %d %b %Y %H:%M:%S %Z',  # RFC 2822 with timezone name
                                '%Y-%m-%dT%H:%M:%S%z',       # ISO 8601
                                '%Y-%m-%d %H:%M:%S%z'        # Common format
                            ]:
                                try:
                                    email_date = datetime.strptime(date, fmt)
                                    break
                                except ValueError:
                                    continue
                            else:
                                email_date = datetime.now()
                        else:
                            email_date = datetime.now()
                    except (ValueError, TypeError):
                        email_date = datetime.now()
                    
                    # Classify email
                    classification = self.classifier.classify_email(subject, body)
                    
                    # Skip if classified as spam and spam is disabled
                    if classification.spam and not self.config.EMAIL_CATEGORIES.get('spam', {}).get('enabled', False):
                        self.logger.info(f"Skipping spam email: {subject}")
                        if 'spam' not in self.summary['category_stats']:
                            self.summary['category_stats']['spam'] = 0
                        self.summary['category_stats']['spam'] += 1
                        # Mark spam as read
                        self.gmail.mark_as_read(message['id'])
                        continue
                    
                    # Update category stats
                    for category in classification.categories:
                        if category not in self.summary['category_stats']:
                            self.summary['category_stats'][category] = 0
                        self.summary['category_stats'][category] += 1

                    # Get target emails for enabled categories
                    targets = self.classifier.get_target_emails(classification)
                    
                    if not targets:
                        self.logger.info(f"No target emails found for message {message['id']}")
                        # Mark as read even if no targets found
                        self.gmail.mark_as_read(message['id'])
                        continue

                    # Forward to each target
                    forwarding_success = False
                    for target in targets:
                        if self.gmail.forward_email(message['id'], target['email']):
                            forwarding_success = True
                            self.summary['emails_forwarded'] += 1
                            self.summary['forwarding_details'].append({
                                'subject': subject,
                                'from': sender,
                                'to': to,
                                'cc': cc,
                                'cc_recipient': is_cc,
                                'date': email_date,
                                'categories': classification.categories,
                                'priority': classification.priority,
                                'is_spam': classification.spam,
                                'is_alert': classification.alert,
                                'key_points': classification.key_points,
                                'action_items': classification.action_items,
                                'forwarded_to': target['email']
                            })
                    
                    # Mark as read if forwarding was successful
                    if forwarding_success:
                        self.gmail.mark_as_read(message['id'])
                        self.logger.info(f"Marked email as read: {subject}")
                    
                except Exception as e:
                    self.logger.error(f"Error processing message {message['id']}: {str(e)}")
                    continue
            
            # Generate and send reports
            self.generate_and_send_reports()
            
        except Exception as e:
            self.logger.error(f"Error in process_emails: {str(e)}")

    def generate_and_send_reports(self):
        """Generate and send reports"""
        try:
            # Create report generator
            report_gen = ReportGenerator(self.summary)
            
            # Get report content with personalized intro
            openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            report = report_gen.create_report_email(openai_client)
            
            # Get authenticated email
            to_email = self.gmail.get_authenticated_email()
            if not to_email:
                self.logger.error("Could not determine email address for sending report")
                return
            
            # Create a new HTML email
            message = MIMEMultipart('alternative')
            message['to'] = to_email
            message['subject'] = report['subject']
            
            # Attach HTML content
            message.attach(MIMEText(report['body'], 'html'))
            
            # Encode and send
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            self.gmail.service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()
            
            self.logger.info(f"Report sent to {to_email}")
            
        except Exception as e:
            self.logger.error(f"Error generating reports: {str(e)}")

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    try:
        processor = EmailProcessor()
        processor.process_emails(max_emails=10)
        processor.generate_and_send_reports()
        
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")

if __name__ == "__main__":
    main()
