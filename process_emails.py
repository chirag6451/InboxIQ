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

class EmailProcessor:
    def __init__(self):
        self.config = Config.from_env()
        self.gmail = GmailHandler(self.config)
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
                    date = next((h['value'] for h in headers if h['name'].lower() == 'date'), None)
                    body = self.gmail._get_message_body(msg_data)

                    # Parse date if available
                    try:
                        if date:
                            # Try multiple date formats
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
                        continue

                    # Forward to each target
                    for target in targets:
                        if self.gmail.forward_email(message['id'], target['email']):
                            self.summary['emails_forwarded'] += 1
                            self.summary['forwarding_details'].append({
                                'subject': subject,
                                'from': sender,
                                'date': email_date,
                                'categories': classification.categories,
                                'forwarded_to': target['email'],
                                'priority': target['priority'],
                                'is_spam': classification.spam,
                                'is_sales_pitch': classification.sales_pitch,
                                'is_alert': classification.alert,
                                'key_points': classification.key_points,
                                'action_items': classification.action_items
                            })

                    # Mark as read
                    self.gmail.mark_as_read(message['id'])

                    # Add appropriate labels
                    for category in classification.categories:
                        if self.config.EMAIL_CATEGORIES.get(category, {}).get('enabled', True):
                            self.gmail.add_label(message['id'], category)
                    
                    # Add special labels
                    if classification.spam:
                        self.gmail.add_label(message['id'], 'Spam')
                    if classification.sales_pitch:
                        self.gmail.add_label(message['id'], 'Sales Pitch')
                    if classification.alert:
                        self.gmail.add_label(message['id'], 'Alert')
                    
                    if self.classifier.should_mark_important(classification):
                        self.gmail.mark_important(message['id'])

                except Exception as e:
                    self.logger.error(f"Error processing message {message['id']}: {str(e)}")
                    continue

        except Exception as e:
            self.logger.error(f"Error in email processing: {str(e)}")

    def generate_and_send_reports(self):
        """Generate and send reports"""
        try:
            # Create report generator
            report_gen = ReportGenerator(self.summary)
            
            # Get report content
            report = report_gen.create_report_email()
            
            # Get authenticated email
            to_email = self.gmail.get_authenticated_email()
            if not to_email:
                self.logger.error("Could not determine email address for sending report")
                return
            
            # Create a new email with the report
            message = MIMEMultipart()
            message['to'] = to_email
            message['subject'] = report['subject']
            message.attach(MIMEText(report['body'], 'plain'))
            
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
