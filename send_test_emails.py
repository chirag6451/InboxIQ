#!/usr/bin/env python3
import os
import time
import base64
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from gmail_handler import GmailHandler
from gmail_auth import GmailAuthenticator
from config import Config
import json
from google.oauth2.credentials import Credentials

def create_test_email(subject, body, to_email):
    """Create a test email message"""
    message = MIMEMultipart()
    message['to'] = to_email
    message['subject'] = subject
    
    # Create email body with calendar block
    full_body = f"""
{body}

=== Calendar Event ===
When: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Duration: 30 minutes
Reminder: 15 minutes before

=== Action Items ===
1. Review the information provided
2. Schedule follow-up meeting
3. Prepare necessary documents

=== Key Points ===
• Important deadline approaching
• Requires immediate attention
• Follow-up actions needed
"""
    
    message.attach(MIMEText(full_body, 'plain'))
    
    # Convert the message to base64url encoding
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    return {'raw': raw}

def send_test_emails():
    """Send test emails for each category with different priorities"""
    # Initialize configuration
    config = Config()
    
    # Initialize Gmail authentication
    auth = GmailAuthenticator(config.GMAIL_SCOPES)
    
    # Load credentials from token file
    with open('token.json', 'r') as token:
        creds_info = token.read()
        credentials = Credentials.from_authorized_user_info(eval(creds_info), config.GMAIL_SCOPES)
    
    # Initialize Gmail handler
    gmail_handler = GmailHandler(credentials, config)
    service = gmail_handler.service
    
    # Test cases for each category
    test_cases = [
        # Work category tests
        {
            'category': 'work',
            'emails': [
                {
                    'subject': '[URGENT] Project Deadline Update',
                    'body': '''This is an urgent task that needs immediate attention. Please update the project status by EOD.

Action Items:
1. Update project timeline
2. Schedule team meeting
3. Prepare status report

Key Points:
• Critical deadline approaching
• Team coordination required
• Documentation needs update''',
                    'expected_priority': 'urgent'
                },
                {
                    'subject': '[IMPORTANT] Project Status Review',
                    'body': '''Important project status update meeting scheduled for tomorrow. Please prepare your updates.

Action Items:
1. Gather project metrics
2. Prepare presentation
3. Review deliverables

Key Points:
• Regular status review
• Performance evaluation
• Resource allocation discussion''',
                    'expected_priority': 'important'
                }
            ]
        },
        # Meeting category tests
        {
            'category': 'meeting',
            'emails': [
                {
                    'subject': '[URGENT] Emergency Team Sync',
                    'body': '''Emergency team sync required to discuss critical issues.

Action Items:
1. Prepare agenda
2. Gather incident reports
3. Document action plan

Key Points:
• Critical system issue
• Immediate response needed
• Customer impact assessment''',
                    'expected_priority': 'urgent'
                }
            ]
        }
    ]

    # Send test emails
    for case in test_cases:
        print(f"\nSending test emails for {case['category']} category:")
        for email in case['emails']:
            try:
                # Get target email from config
                category_config = config.EMAIL_CATEGORIES[case['category']]
                to_email = category_config['target_emails'][0] if category_config['target_emails'] else 'chirag@indapoint.com'
                
                # Create and send email
                message = create_test_email(
                    subject=email['subject'],
                    body=email['body'],
                    to_email=to_email
                )
                
                result = service.users().messages().send(
                    userId='me',
                    body=message
                ).execute()
                
                print(f"✓ Sent: {email['subject']} (Expected Priority: {email['expected_priority']})")
                
                # Wait a bit between emails to avoid rate limits
                time.sleep(2)
                
            except Exception as e:
                print(f"✗ Error sending {email['subject']}: {str(e)}")

if __name__ == '__main__':
    print("Starting to send test emails...")
    print("This will send multiple test emails to test the classification and calendar event creation.")
    print("Make sure your email processing script is running to handle these test emails.")
    
    # Ask for confirmation
    response = input("Do you want to proceed? (yes/no): ")
    if response.lower() == 'yes':
        send_test_emails()
        print("\nAll test emails have been sent!")
        print("Please check your email and calendar to verify:")
        print("1. Email classification")
        print("2. Calendar event creation based on priority")
        print("3. Notification settings")
    else:
        print("Test cancelled.")
