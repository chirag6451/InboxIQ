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
from calendar_handler import CalendarHandler
from collections import defaultdict

class EmailProcessor:
    def __init__(self, gmail_handler, config):
        """Initialize the email processor with handlers and config"""
        self.gmail = gmail_handler
        self.config = config
        self.calendar = CalendarHandler(gmail_handler.credentials)
        self.classifier = EmailClassifier(config)
        self.logger = logging.getLogger(__name__)
        self.summary = {
            'total_emails_processed': 0,
            'emails_forwarded': 0,
            'category_stats': defaultdict(int),
            'forwarding_details': [],
            'calendar_events': [],
            'start_time': datetime.now()
        }
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

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
                    classification = self.classifier.classify_email({
                        'subject': subject,
                        'sender': sender,
                        'body': body
                    })
                    
                    # Update category stats
                    for category in classification.get('categories', []):
                        if category not in self.summary['category_stats']:
                            self.summary['category_stats'][category] = 0
                        self.summary['category_stats'][category] += 1
                    
                    # Skip if spam
                    if classification.get('spam', False):
                        self.logger.info(f"Skipping spam email: {subject}")
                        self.gmail.mark_as_read(message['id'])
                        continue

                    # Get target emails for forwarding
                    targets = self.classifier.get_target_emails(classification)
                    forwarding_success = False

                    # Forward to each target
                    forwarded_to = []
                    if targets:
                        for target in targets:
                            if self.gmail.forward_email(message['id'], target['email']):
                                forwarded_to.append(target['email'])
                                forwarding_success = True
                                self.summary['emails_forwarded'] += 1

                    # Add to forwarding details
                    self.summary['forwarding_details'].append({
                        'subject': subject,
                        'from': sender,
                        'to': to,
                        'cc': cc,
                        'cc_recipient': is_cc,
                        'date': email_date,
                        'categories': classification.get('categories', []),
                        'priority': classification.get('priority', 'normal'),
                        'action_items': classification.get('action_items', []),
                        'forwarded_to': forwarded_to
                    })

                    # Create calendar reminder if needed
                    if classification.get('categories'):
                        primary_category = classification['categories'][0]
                        category_config = self.config.EMAIL_CATEGORIES.get(primary_category, {})
                        calendar_settings = category_config.get('calendar_settings', {})
                        
                        if calendar_settings.get('create_reminder', False):
                            # Add AI analysis to email data
                            email_data = {
                                'subject': subject,
                                'sender': sender,
                                'body': body,
                                'ai_analysis': {
                                    'action_items': classification.get('action_items', []),
                                    'key_points': classification.get('key_points', []),
                                    'priority': classification.get('priority', 'normal')
                                }
                            }

                            event_id = self.calendar.create_reminder(
                                email_data=email_data,
                                category=primary_category,
                                calendar_settings=calendar_settings
                            )

                            if event_id:
                                event_link = self.calendar.get_event_link(event_id)
                                self.summary['calendar_events'].append({
                                    'subject': subject,
                                    'category': primary_category,
                                    'event_link': event_link,
                                    'priority': classification.get('priority', 'normal')
                                })
                                self.logger.info(f"Created calendar event for: {subject}")

                    # Mark as read if forwarding was successful or no targets
                    if forwarding_success or not targets:
                        self.gmail.mark_as_read(message['id'])

                except Exception as e:
                    self.logger.error(f"Error processing message {message['id']}: {str(e)}")
                    continue

            # Generate and send reports
            self.generate_and_send_reports()
            
        except Exception as e:
            self.logger.error(f"Error in process_emails: {str(e)}")

    def process_email_with_ai(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process email content using AI"""
        try:
            # Prepare email content for AI
            prompt = f"""
            Subject: {email_data['subject']}
            From: {email_data['sender']}
            Body: {email_data['body']}
            
            Please analyze this email and provide:
            1. Category (urgent, important, notification, spam, support, alert)
            2. Summary
            3. Suggested actions
            4. Should this be forwarded? If yes, to whom?
            
            Note: Please provide your response without any markdown formatting or code block indicators.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            
            ai_response = response.choices[0].message.content
            # Clean up AI response
            ai_response = self._clean_ai_response(ai_response)
            
            # Parse AI response and update email data
            email_data['ai_analysis'] = ai_response
            
            return email_data
            
        except Exception as e:
            self.logger.error(f"Error in AI processing: {str(e)}")
            email_data['ai_analysis'] = "Error in AI processing"
            return email_data

    def generate_and_send_reports(self):
        """Generate and send email reports"""
        try:
            # Generate report HTML
            report_html = self._generate_report_html()
            
            # Send email report
            subject = f"Email Processing Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            # Get authenticated email
            user_email = self.gmail.get_authenticated_email()
            if not user_email:
                self.logger.error("Could not determine authenticated email")
                return
                
            # Create message
            message = self.gmail.create_message(
                sender=user_email,
                to=user_email,
                subject=subject,
                message_html=report_html
            )
            
            # Send message
            if message:
                self.gmail.send_message(message)
                self.logger.info(f"Sent report email to {user_email}")
            
        except Exception as e:
            self.logger.error(f"Error generating reports: {str(e)}")

    def _generate_introduction(self) -> str:
        """Generate personalized introduction using OpenAI"""
        try:
            # Prepare the context for OpenAI
            stats = {
                'total_emails': self.summary['total_emails_processed'],
                'forwarded': self.summary['emails_forwarded'],
                'calendar_events': len(self.summary.get('calendar_events', [])),
                'categories': self.summary.get('category_stats', {}),
                'time': datetime.now().strftime("%I:%M %p")
            }
            
            prompt = f"""
            Generate a friendly and professional email introduction for an email processing report.
            
            Context:
            - User's name: {self.config.USER_DETAILS['name']}
            - Time: {stats['time']}
            - Total emails processed: {stats['total_emails']}
            - Emails forwarded: {stats['forwarded']}
            - Calendar events created: {stats['calendar_events']}
            - Categories processed: {', '.join(stats['categories'].keys())}
            
            The introduction should:
            1. Be personal and engaging
            2. Highlight key statistics
            3. Be concise (2-3 paragraphs)
            4. Use a professional but friendly tone
            5. Include any notable patterns or important observations
            
            Format the response in HTML with appropriate styling.
            """
            
            response = self.openai_client.chat.completions.create(
                model=self.config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a professional email assistant generating a report introduction."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            introduction = response.choices[0].message.content
            
            # Wrap in a styled div if not already wrapped
            if not introduction.strip().startswith('<div'):
                introduction = f"""
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #3498db;">
                    {introduction}
                </div>
                """
            
            return introduction
            
        except Exception as e:
            self.logger.error(f"Error generating introduction: {str(e)}")
            # Fallback to basic introduction
            return f"""
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #3498db;">
                <p>Hi {self.config.USER_DETAILS['name']},</p>
                
                <p>Here's your email processing report as of {datetime.now().strftime("%I:%M %p")}. 
                I've processed {self.summary['total_emails_processed']} emails, 
                with {self.summary['emails_forwarded']} being forwarded to appropriate contacts.</p>
            </div>
            """

    def _generate_report_html(self) -> str:
        """Generate HTML report"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 20px auto; line-height: 1.6;">
            <h2 style="color: #2c3e50;">Email Processing Report</h2>
            
            {self._generate_introduction()}
            
            <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="color: #2c3e50; margin-top: 0;">Summary Statistics:</h3>
                <ul style="list-style-type: none; padding-left: 0;">
                    <li><strong>Total Emails Processed:</strong> {self.summary['total_emails_processed']}</li>
                    <li><strong>Emails Forwarded:</strong> {self.summary['emails_forwarded']}</li>
                    <li><strong>Calendar Events Created:</strong> {len(self.summary.get('calendar_events', []))}</li>
                </ul>
            </div>
            
            {self._format_action_items()}
            {self._format_category_stats()}
            {self._format_forwarding_details()}
            {self._format_calendar_events()}
            
            <p style="margin-top: 20px;">If any of these items require immediate attention, please let me know.</p>
            
            <p>Best regards,<br>Your Email Assistant</p>
            
            <p style="color: #7f8c8d; font-size: 0.9em; margin-top: 30px; border-top: 1px solid #eee; padding-top: 20px;">
                This is an automated report generated by the Email Processing System.
            </p>
        </body>
        </html>
        """

    def _format_category_stats(self) -> str:
        """Format category statistics section of the report"""
        if not self.summary['category_stats']:
            return ""
            
        stats = [
            '<div style="background-color: #f5f6fa; padding: 15px; border-radius: 5px; margin: 20px 0;">',
            '<h3 style="color: #2c3e50; margin-top: 0;">Category Statistics:</h3>',
            '<table style="width: 100%; border-collapse: collapse;">',
            '<tr style="background-color: #34495e; color: white;">',
            '<th style="padding: 10px; text-align: left;">Category</th>',
            '<th style="padding: 10px; text-align: center;">Count</th>',
            '</tr>'
        ]
        
        for category, count in self.summary['category_stats'].items():
            stats.append(f"""
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 10px; text-transform: capitalize;">{category}</td>
                    <td style="padding: 10px; text-align: center;">{count}</td>
                </tr>
            """)
        
        stats.extend(['</table>', '</div>'])
        return '\n'.join(stats)

    def _format_forwarding_details(self) -> str:
        """Format forwarding details section of the report"""
        if not self.summary['forwarding_details']:
            return ""
            
        details = [
            '<div style="background-color: #fff5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">',
            '<h3 style="color: #2c3e50; margin-top: 0;">Forwarding Details:</h3>',
            '<table style="width: 100%; border-collapse: collapse;">',
            '<tr style="background-color: #c0392b; color: white;">',
            '<th style="padding: 10px; text-align: left;">Subject</th>',
            '<th style="padding: 10px; text-align: left;">From</th>',
            '<th style="padding: 10px; text-align: left;">Category</th>',
            '<th style="padding: 10px; text-align: left;">Forwarded To</th>',
            '</tr>'
        ]
        
        for detail in self.summary['forwarding_details']:
            cc_badge = ' <span style="color: #e74c3c; font-weight: bold;">[CC]</span>' if detail.get('cc_recipient', False) else ''
            categories = ', '.join(detail.get('categories', []))
            forwarded_to = ', '.join(detail.get('forwarded_to', []))
            
            details.append(f"""
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 10px;">{detail['subject']}{cc_badge}</td>
                    <td style="padding: 10px;">{detail['from']}</td>
                    <td style="padding: 10px; text-transform: capitalize;">{categories}</td>
                    <td style="padding: 10px;">{forwarded_to}</td>
                </tr>
            """)
        
        details.extend(['</table>', '</div>'])
        return '\n'.join(details)

    def _format_calendar_events(self) -> str:
        """Format calendar events section of the report"""
        if not self.summary.get('calendar_events'):
            return ""
            
        events = [
            '<div style="background-color: #f0f7ff; padding: 15px; border-radius: 5px; margin: 20px 0;">',
            '<h3 style="color: #2c3e50; margin-top: 0;">Calendar Reminders Created:</h3>',
            '<table style="width: 100%; border-collapse: collapse;">',
            '<tr style="background-color: #2980b9; color: white;">',
            '<th style="padding: 10px; text-align: left;">Subject</th>',
            '<th style="padding: 10px; text-align: left;">Category</th>',
            '<th style="padding: 10px; text-align: center;">Priority</th>',
            '<th style="padding: 10px; text-align: center;">Action</th>',
            '</tr>'
        ]
        
        for event in self.summary['calendar_events']:
            priority_color = {
                'high': '#e74c3c',
                'urgent': '#c0392b',
                'normal': '#3498db',
                'low': '#7f8c8d'
            }.get(event.get('priority', 'normal'), '#3498db')
            
            events.append(f"""
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 10px;">{event['subject']}</td>
                    <td style="padding: 10px; text-transform: uppercase;">{event['category']}</td>
                    <td style="padding: 10px; text-align: center;">
                        <span style="color: {priority_color}; font-weight: bold;">{event['priority'].upper()}</span>
                    </td>
                    <td style="padding: 10px; text-align: center;">
                        <a href="{event['event_link']}" style="color: #3498db; text-decoration: none;">View in Calendar →</a>
                    </td>
                </tr>
            """)
        
        events.extend(['</table>', '</div>'])
        return '\n'.join(events)

    def _format_action_items(self) -> str:
        """Format action items section of the report"""
        action_items = []
        for detail in self.summary['forwarding_details']:
            if detail.get('action_items'):
                action_items.extend(detail['action_items'])
        
        if not action_items:
            return ""
            
        items = [
            '<div style="background-color: #fdf6e3; padding: 15px; border-radius: 5px; margin: 20px 0;">',
            '<h3 style="color: #2c3e50; margin-top: 0;">Action Items Required:</h3>',
            '<ul style="list-style-type: none; padding-left: 0;">'
        ]
        
        for item in action_items:
            items.append(f"""
                <li style="margin-bottom: 10px; padding-left: 20px; position: relative;">
                    <span style="position: absolute; left: 0; color: #d35400;">•</span>
                    {item}
                </li>
            """)
        
        items.extend(['</ul>', '</div>'])
        return '\n'.join(items)

    def _get_cc_summary(self, cc_count: int) -> str:
        """Get summary text for CC'd emails"""
        if cc_count == 0:
            return "None of the processed emails had you in CC."
        elif cc_count == 1:
            return "One email had you in CC."
        else:
            return f"{cc_count} emails had you in CC."

    def _clean_ai_response(self, text: str) -> str:
        """Clean up AI response by removing markdown and code block indicators"""
        # Remove markdown code block indicators
        text = re.sub(r'```\w*\n?', '', text)
        # Remove trailing backticks
        text = re.sub(r'```$', '', text)
        # Remove html comments
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        # Remove any remaining backticks
        text = text.replace('`', '')
        # Clean up multiple newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    try:
        # Load credentials from token file
        if os.path.exists('token.json'):
            with open('token.json', 'r') as token:
                creds_info = eval(token.read())
                from google.oauth2.credentials import Credentials
                creds = Credentials.from_authorized_user_info(creds_info, Config.from_env().GMAIL_SCOPES)
                gmail_handler = GmailHandler(credentials=creds, config=Config.from_env())
                processor = EmailProcessor(gmail_handler, Config.from_env())
                processor.process_emails(max_emails=10)
                processor.generate_and_send_reports()
                
        else:
            raise ValueError("No token.json found. Please authenticate first.")
            
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")

if __name__ == "__main__":
    main()
