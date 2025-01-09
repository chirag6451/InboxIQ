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
import argparse

class EmailProcessor:
    def __init__(self, gmail_handler, config):
        """Initialize the email processor with handlers and config"""
        self.gmail = gmail_handler
        self.config = config
        self.calendar = CalendarHandler(gmail_handler.credentials, config)
        self.classifier = EmailClassifier(config)
        self.logger = logging.getLogger(__name__)
        self.summary = {
            'total_emails_processed': 0,
            'actionable_emails': 0,  # New counter for emails that had actions taken
            'emails_forwarded': 0,
            'category_stats': defaultdict(int),
            'forwarding_details': [],
            'calendar_events': [],
            'action_items': [],
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

            # Reset calendar handler's last event time and slot at the start of processing
            self.calendar.last_event_time = None
            self.calendar.current_slot = None
            
            # Get unread messages
            messages = self.gmail.list_messages(query='is:unread', max_results=max_emails)
            self.summary['total_emails_processed'] = len(messages)
            
            for message in messages:
                try:
                    # Track if any action was taken for this email
                    email_had_action = False
                    
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
                    primary_category = classification.get('categories', [])[0] if classification.get('categories', []) else None
                    if primary_category:
                        self.summary['category_stats'][primary_category] += 1
                    
                    # Skip if spam
                    if classification.get('spam', False):
                        self.logger.info(f"Skipping spam email: {subject}")
                        self.gmail.mark_as_read(message['id'])
                        continue

                    # Extract sender's email address from the From field
                    sender_email = None
                    if '<' in sender and '>' in sender:
                        sender_email = sender[sender.find('<')+1:sender.find('>')]
                    else:
                        sender_email = sender.strip()

                    # Get target emails for forwarding
                    targets = self.classifier.get_target_emails(classification, sender_email)
                    forwarding_success = False

                    # Forward to each target
                    forwarded_to = []
                    if targets:
                        for target in targets:
                            disclaimer = f"""
                            
                            ----------------------------------------
                            This email was automatically forwarded by InboxIQ on behalf of:
                            {self.config.USER_DETAILS['full_name']}
                            {self.config.USER_DETAILS['position']}
                            {self.config.USER_DETAILS['company']}
                            
                            Email processed and forwarded using InboxIQ - Intelligent Email Management System
                            ----------------------------------------"""
                            
                            if self.gmail.forward_email(
                                to_email=target['email'],
                                subject=f"FWD: {subject}",
                                body=f"""Original email from: {sender}
                                \n\nCategories: {', '.join(classification.get('categories', []))}
                                Priority: {classification.get('priority', 'normal')}
                                \n\nAction Items:
                                {chr(10).join(['- ' + item for item in classification.get('action_items', [])])}
                                \n\nOriginal message:
                                {body}
                                {disclaimer}""",
                                attachments=[]  # Add attachments if needed
                            ):
                                forwarded_to.append(target['email'])
                                forwarding_success = True
                                self.summary['emails_forwarded'] += 1

                    # Add to forwarding details
                    if forwarding_success:
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

                    # Update action tracking based on forwarding
                    if forwarding_success:
                        email_had_action = True
                        self.summary['actionable_emails'] += 1

                    # Store action items in summary if present
                    if classification.get('action_items'):
                        if 'action_items' not in self.summary:
                            self.summary['action_items'] = []
                        self.summary['action_items'].append({
                            'sender': sender,
                            'subject': subject,
                            'items': classification['action_items']
                        })

                    # Create calendar reminder if needed
                    if classification.get('categories'):
                        primary_category = classification['categories'][0]
                        category_config = self.config.EMAIL_CATEGORIES.get(primary_category, {})
                        calendar_settings = category_config.get('calendar_settings', {})
                        
                        if calendar_settings.get('create_reminder', False):
                            # Process email with AI first
                            email_data = {
                                'subject': subject,
                                'sender': sender,
                                'body': body,
                                'priority': classification.get('priority', 'normal'),
                                'ai_analysis': {
                                    'action_items': classification.get('action_items', []),
                                    'key_points': classification.get('key_points', []),
                                    'priority': classification.get('priority', 'normal')
                                }
                            }
                            
                            # Process with AI to get additional insights
                            ai_result = self.process_email_with_ai(email_data)
                            
                            # Ensure ai_analysis is a dictionary
                            if isinstance(ai_result.get('ai_analysis'), str):
                                try:
                                    ai_result['ai_analysis'] = json.loads(ai_result['ai_analysis'])
                                except:
                                    ai_result['ai_analysis'] = {
                                        'action_items': classification.get('action_items', []),
                                        'key_points': classification.get('key_points', []),
                                        'priority': classification.get('priority', 'normal')
                                    }

                            event_id = self.calendar.create_reminder(
                                email_data=ai_result,
                                category=primary_category,
                                calendar_settings=calendar_settings
                            )

                            if event_id:
                                email_had_action = True
                                event_link = self.calendar.get_event_link(event_id)
                                self.summary['calendar_events'].append({
                                    'subject': subject,
                                    'category': primary_category,
                                    'event_link': event_link,
                                    'priority': classification.get('priority', 'normal')
                                })
                                self.logger.info(f"Created calendar event for: {subject}")

                    # Update category stats only for actionable emails
                    if email_had_action:
                        self.summary['category_stats'][primary_category] += 1

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
                'actionable_emails': self.summary['actionable_emails'],
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
            - Emails requiring action: {stats['actionable_emails']}
            - Emails forwarded: {stats['forwarded']}
            - Calendar events created: {stats['calendar_events']}
            - Categories with actions: {', '.join(stats['categories'].keys())}
            
            The introduction should:
            1. Be personal and engaging
            2. Focus on emails that required actions (forwarding, calendar events, etc.)
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
                with {self.summary['actionable_emails']} requiring actions.</p>
            </div>
            """

    def _generate_action_items_summary(self) -> str:
        """Generate an intuitive summary of all action items using OpenAI"""
        if not self.summary.get('action_items'):
            return ""

        try:
            # Prepare context for OpenAI
            action_items_context = []
            for item in self.summary['action_items']:
                action_items_context.append({
                    'subject': item.get('subject', 'No Subject'),
                    'action_items': item.get('action_items', []),
                    'priority': item.get('priority', 'normal'),
                    'category': item.get('category', 'general')
                })

            prompt = f"""
            Please create an intuitive and organized summary of the following action items from emails:

            Action Items:
            {json.dumps(action_items_context, indent=2)}

            Please create a summary that:
            1. Groups related actions together
            2. Prioritizes urgent/important items
            3. Provides a clear, bulleted structure
            4. Adds context where helpful
            5. Suggests any obvious next steps
            6. Uses a professional but clear tone

            Format the response in HTML with appropriate styling for a email report.
            """

            response = self.openai_client.chat.completions.create(
                model=self.config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a professional email assistant creating an action items summary."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )

            summary = response.choices[0].message.content

            # Wrap in styled div if not already wrapped
            if not summary.strip().startswith('<div'):
                summary = f"""
                <div class="action-summary" style="background-color: #fff3e0; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ff9800;">
                    <h2 style="color: #e65100; margin-top: 0;">Action Items Summary</h2>
                    {summary}
                </div>
                """

            return summary

        except Exception as e:
            self.logger.error(f"Error generating action items summary: {str(e)}")
            return self._format_action_items()  # Fallback to basic format

    def _generate_report_html(self) -> str:
        """Generate HTML report"""
        try:
            introduction = self._generate_introduction()
            action_summary = self._generate_action_items_summary()  # New action items summary
            category_stats = self._format_category_stats()
            forwarding_details = self._format_forwarding_details()
            calendar_events = self._format_calendar_events()
            action_items = self._format_action_items()
            
            # Only include detailed action items if there's no summary
            if action_summary:
                action_items = ""  # Skip detailed list if we have a summary
            
            disclaimer = f"""
            <div style="margin-top: 30px; padding: 20px; background-color: #f8f9fa; border-radius: 5px; font-size: 12px; color: #666;">
                <p>This report was automatically generated by InboxIQ on behalf of:</p>
                <p><strong>{self.config.USER_DETAILS['full_name']}</strong><br>
                {self.config.USER_DETAILS['position']}<br>
                {self.config.USER_DETAILS['company']}</p>
                <p>Generated using InboxIQ - Intelligent Email Management System</p>
            </div>"""
            
            return f"""
            <html>
            <head>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 800px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .section {{
                        margin: 20px 0;
                        padding: 15px;
                        background-color: #fff;
                        border-radius: 5px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    h2 {{
                        color: #2c3e50;
                        margin-top: 0;
                    }}
                    .stats-table {{
                        width: 100%;
                        border-collapse: collapse;
                    }}
                    .stats-table th, .stats-table td {{
                        padding: 12px;
                        text-align: left;
                        border-bottom: 1px solid #ddd;
                    }}
                    .stats-table th {{
                        background-color: #f8f9fa;
                        font-weight: bold;
                    }}
                    .priority-high {{
                        color: #e74c3c;
                    }}
                    .priority-medium {{
                        color: #f39c12;
                    }}
                    .priority-low {{
                        color: #27ae60;
                    }}
                </style>
            </head>
            <body>
                {introduction}
                {action_summary}
                {category_stats}
                {forwarding_details}
                {calendar_events}
                {action_items}
                {disclaimer}
            </body>
            </html>
            """
        except Exception as e:
            self.logger.error(f"Error generating HTML report: {str(e)}")
            return f"""
            <html>
            <body>
                <h1>Error Generating Report</h1>
                <p>An error occurred while generating the email processing report.</p>
            </body>
            </html>
            """

    def _format_category_stats(self) -> str:
        """Format category statistics section of the report"""
        if not self.summary['category_stats']:
            return ""
            
        stats_html = """
        <div class="section">
            <h2>Category Statistics (Actionable Emails)</h2>
            <table class="stats-table">
                <tr>
                    <th>Category</th>
                    <th>Count</th>
                </tr>
        """
        
        for category, count in self.summary['category_stats'].items():
            stats_html += f"""
                <tr>
                    <td>{category}</td>
                    <td>{count}</td>
                </tr>
            """
            
        stats_html += """
            </table>
        </div>
        """
        
        return stats_html

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
        
        if not self.summary.get('action_items'):
            return ""
            
        items = [
            '<div style="background-color: #fdf6e3; padding: 15px; border-radius: 5px; margin: 20px 0;">',
            '<h3 style="color: #2c3e50; margin-top: 0;">Action Items Required:</h3>',
            '<ul style="list-style-type: none; padding-left: 0;">'
        ]
        
        for email_actions in self.summary['action_items']:
            items.extend([
                f"<li style='margin-bottom: 10px; padding-left: 20px; position: relative;'>",
                f"<span style='position: absolute; left: 0; color: #d35400;'>•</span>",
                f"<strong>From:</strong> {email_actions['sender']}",
                f"<br><strong>Subject:</strong> {email_actions['subject']}",
                "<br>Action Items:"
            ])
            for item in email_actions['items']:
                items.append(f"<li style='margin-left: 20px;'>{item}</li>")
            items.append("</li>")
        
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
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Process unread emails with InboxIQ')
    parser.add_argument('--max-emails', type=int, default=10,
                      help='Maximum number of emails to process (default: 10)')
    args = parser.parse_args()

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
                processor.process_emails(max_emails=args.max_emails)  # Use the command line argument
                processor.generate_and_send_reports()
                
        else:
            raise ValueError("No token.json found. Please authenticate first.")
            
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")

if __name__ == "__main__":
    main()
