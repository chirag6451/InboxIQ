from gmail_handler import GmailHandler
import json
from datetime import datetime
from dotenv import load_dotenv
import os
import base64

# Load environment variables from .env file
load_dotenv()

def decode_base64(data):
    """Decode base64 data, handling padding if necessary"""
    # Add padding if needed
    pad = len(data) % 4
    if pad:
        data += '=' * (4 - pad)
    return base64.urlsafe_b64decode(data).decode()

def main():
    try:
        # Initialize Gmail handler
        handler = GmailHandler()
        
        print("\nFetching recent emails...")
        
        # List messages
        results = handler.service.users().messages().list(
            userId='me',
            maxResults=10  # Fetch last 10 emails
        ).execute()
        
        messages = results.get('messages', [])
        emails = []
        
        for message in messages:
            try:
                # Get full message details
                msg = handler.service.users().messages().get(
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
                body = 'No body'
                if 'parts' in msg['payload']:
                    # Multipart message
                    for part in msg['payload']['parts']:
                        if part['mimeType'] == 'text/plain' and 'data' in part.get('body', {}):
                            body = decode_base64(part['body']['data'])
                            break
                elif 'body' in msg['payload'] and 'data' in msg['payload']['body']:
                    # Single part message
                    body = decode_base64(msg['payload']['body']['data'])
                
                email_data = {
                    'id': message['id'],
                    'subject': subject,
                    'from': sender,
                    'date': date,
                    'body': body[:500] + '...' if len(body) > 500 else body  # Truncate long bodies
                }
                
                emails.append(email_data)
                
                # Print email details
                print("\n" + "="*80)
                print(f"From: {sender}")
                print(f"Subject: {subject}")
                print(f"Date: {date}")
                print("-"*80)
                print(f"Body: {body[:200]}..." if len(body) > 200 else f"Body: {body}")
                print("="*80)
                
            except Exception as e:
                print(f"Error processing message {message['id']}: {str(e)}")
                continue
        
        # Save emails to a JSON file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"emails_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(emails, f, indent=2)
        
        print(f"\nEmails have been saved to {output_file}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
