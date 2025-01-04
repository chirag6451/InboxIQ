from gmail_handler import GmailHandler
from invoice_analyzer import InvoiceAnalyzer
import json
from datetime import datetime, timedelta
import logging
import base64
import re
from config import Config

def setup_invoice_logging():
    """Configure logging specifically for invoice detection"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('invoice_detection.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def get_date_filter():
    """Get Gmail query filter for last 2 days"""
    today = datetime.now()
    two_days_ago = today - timedelta(days=2)
    date_str = two_days_ago.strftime('%Y/%m/%d')
    return f'after:{date_str}'

def decode_base64(data):
    """Decode base64 data, handling padding if necessary"""
    pad = len(data) % 4
    if pad:
        data += '=' * (4 - pad)
    return base64.urlsafe_b64decode(data).decode()

def extract_email_content(msg):
    """Extract content from email message"""
    headers = msg['payload']['headers']
    subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
    sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
    date = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'Unknown')

    # Extract body and attachments
    body = 'No body'
    attachments = []

    def process_parts(parts):
        """Recursively process message parts"""
        nonlocal body, attachments
        for part in parts:
            # Handle nested parts
            if 'parts' in part:
                process_parts(part['parts'])
                continue

            # Get mime type
            mime_type = part.get('mimeType', '')

            # Handle text content
            if mime_type == 'text/plain' and 'data' in part.get('body', {}):
                body = decode_base64(part['body']['data'])
            
            # Handle attachments
            elif 'filename' in part and part['filename']:
                attachments.append({
                    'filename': part['filename'],
                    'attachmentId': part['body'].get('attachmentId'),
                    'mimeType': mime_type
                })

    # Process message parts
    if 'parts' in msg['payload']:
        process_parts(msg['payload']['parts'])
    elif 'body' in msg['payload'] and 'data' in msg['payload']['body']:
        body = decode_base64(msg['payload']['body']['data'])

    return {
        'subject': subject,
        'sender': sender,
        'date': date,
        'body': body,
        'attachments': attachments
    }

def is_likely_invoice(email_content):
    """Quick check if email might contain invoice without using OpenAI"""
    # Common invoice-related keywords
    invoice_keywords = [
        'invoice', 'bill', 'receipt', 'payment', 'statement', 'order', 
        'transaction', 'purchase', 'subscription', 'charge'
    ]
    
    # Amount patterns (various currencies)
    amount_pattern = r'(?:[\$₹€£]\s*\d+(?:[,.]\d+)*)|(?:\d+(?:[,.]\d+)*\s*(?:usd|eur|gbp|inr))'
    
    # Convert text to lowercase for case-insensitive matching
    subject_lower = email_content['subject'].lower()
    body_lower = email_content['body'].lower()

    # Check subject for invoice keywords
    if any(keyword in subject_lower for keyword in invoice_keywords):
        return True

    # Check for currency amounts in body
    if re.search(amount_pattern, body_lower):
        return True

    # Check for invoice keywords in body with context
    body_keyword_count = sum(1 for keyword in invoice_keywords if keyword in body_lower)
    if body_keyword_count >= 2:  # At least 2 invoice-related keywords
        return True

    # Check attachments for invoice-like filenames
    for attachment in email_content['attachments']:
        filename_lower = attachment['filename'].lower()
        if any(keyword in filename_lower for keyword in invoice_keywords):
            return True
        # Check for common invoice file patterns
        if re.search(r'inv[-_]?\d+|invoice[-_]?\d+', filename_lower):
            return True

    return False

def check_for_invoice(analyzer, email_content):
    """Check if email contains invoice data"""
    # First do a quick check without OpenAI
    if not is_likely_invoice(email_content):
        logger = logging.getLogger(__name__)
        logger.info(f"Quick check: Not likely an invoice - {email_content['subject']}")
        return False, 0, None

    # If it looks like an invoice, use OpenAI for detailed analysis
    logger = logging.getLogger(__name__)
    logger.info(f"Quick check passed, analyzing with OpenAI: {email_content['subject']}")
    analysis_result = analyzer.analyze_content(email_content['body'])

    if analysis_result and analyzer.should_forward(analysis_result):
        invoice_data = analysis_result.get('invoice_data', {})
        confidence = analysis_result.get('confidence', 0)
        return True, confidence, invoice_data
    return False, 0, None

def main():
    # Initialize logger first
    logger = setup_invoice_logging()
    
    try:
        logger.info("Starting invoice detection in emails")

        # Initialize handlers with config
        config = Config.from_env()
        handler = GmailHandler(config)
        analyzer = InvoiceAnalyzer()

        # Check if Gmail service is properly initialized
        if not handler.service:
            logger.error("Gmail service not initialized. Please authenticate first.")
            return

        logger.info("Fetching unread emails")

        # Get UNREAD label ID
        try:
            labels = handler.service.users().labels().list(userId='me').execute()
            unread_label = next((label for label in labels['labels'] if label['name'] == 'UNREAD'), None)
            if not unread_label:
                logger.error("Could not find UNREAD label")
                return
            unread_label_id = unread_label['id']
            logger.info("Found UNREAD label ID")
        except Exception as e:
            logger.error(f"Failed to get labels: {str(e)}")
            return

        # List messages with UNREAD label
        try:
            # Build query for unread emails from last 2 days
            date_filter = get_date_filter()
            query = f'NOT label:sent {date_filter}'
            logger.info(f"Using Gmail query: {query}")
            
            results = handler.service.users().messages().list(
                userId='me',
                maxResults=50,  # Increased to account for date filter
                labelIds=[unread_label_id],
                q=query
            ).execute()
        except Exception as e:
            logger.error(f"Failed to fetch emails: {str(e)}")
            return

        messages = results.get('messages', [])
        invoice_count = 0
        processed_count = 0

        if not messages:
            print("\nNo unread emails found from the last 2 days.")
            return

        logger.info(f"Found {len(messages)} unread emails from the last 2 days to process")
        print("\n" + "="*80)
        print("📧 Processing Unread Emails for Invoices")
        print(f"Date Range: {datetime.now().strftime('%Y-%m-%d')} to {(datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')}")
        print("="*80 + "\n")

        for message in messages:
            processed_count += 1
            try:
                # Get full message details
                msg = handler.service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'
                ).execute()

                # Extract email content
                email_content = extract_email_content(msg)
                print(f"\n[{processed_count}/{len(messages)}] Processing: {email_content['subject']}")

                # Check for invoice
                has_invoice, confidence, invoice_data = check_for_invoice(analyzer, email_content)

                if has_invoice:
                    invoice_count += 1
                    print("\n" + "="*80)
                    print("📑 INVOICE DETECTED")
                    print("="*80)
                    print(f"From: {email_content['sender']}")
                    print(f"Subject: {email_content['subject']}")
                    print(f"Date: {email_content['date']}")
                    print(f"Confidence: {confidence:.2%}")
                    print(f"\nInvoice Details:")
                    print("-"*40)
                    print(f"Invoice Number: {invoice_data.get('invoice_number', 'N/A')}")
                    print(f"Issue Date: {invoice_data.get('date', 'N/A')}")
                    print(f"Due Date: {invoice_data.get('due_date', 'N/A')}")
                    if invoice_data.get('total_amount'):
                        print(f"Total Amount: {invoice_data['total_amount'].get('amount')} {invoice_data['total_amount'].get('currency')}")
                    
                    if email_content['attachments']:
                        print("\nAttachments:")
                        print("-"*40)
                        for attachment in email_content['attachments']:
                            print(f"📎 {attachment['filename']} ({attachment['mimeType']})")
                    
                    print("\nEmail Body Preview:")
                    print("-"*40)
                    preview = email_content['body'][:500] + "..." if len(email_content['body']) > 500 else email_content['body']
                    print(preview)
                    print("\nForwarding Status:")
                    print("-"*40)
                    
                    # Forward to each target email
                    forward_subject = f"[INVOICE] {email_content['subject']}"
                    forward_body = f"""
Invoice detected in email:

From: {email_content['sender']}
Original Subject: {email_content['subject']}
Date: {email_content['date']}

Invoice Details:
---------------
Invoice Number: {invoice_data.get('invoice_number', 'N/A')}
Issue Date: {invoice_data.get('date', 'N/A')}
Due Date: {invoice_data.get('due_date', 'N/A')}
Total Amount: {invoice_data.get('total_amount', {}).get('amount')} {invoice_data.get('total_amount', {}).get('currency')}

Original Email Body:
------------------
{email_content['body'][:1000] + '...' if len(email_content['body']) > 1000 else email_content['body']}
"""
                    # Get attachments
                    attachments = []
                    for attachment in email_content['attachments']:
                        attachment_data = handler.download_attachment(
                            message['id'],
                            attachment['attachmentId']
                        )
                        if attachment_data:
                            attachments.append({
                                'filename': attachment['filename'],
                                'content': attachment_data
                            })
                            print(f"✓ Downloaded attachment: {attachment['filename']}")
                        else:
                            print(f"✗ Failed to download attachment: {attachment['filename']}")

                    # Forward to each target email
                    forward_success = True  # Track if all forwards were successful
                    forwarded_count = 0
                    
                    for target_email in config.TARGET_EMAILS:
                        try:
                            if handler.forward_email(target_email, forward_subject, forward_body, attachments):
                                print(f"✓ Forwarded to {target_email} with {len(attachments)} attachment(s)")
                                forwarded_count += 1
                            else:
                                print(f"✗ Failed to forward to {target_email}")
                                forward_success = False
                        except Exception as e:
                            logger.error(f"Error forwarding to {target_email}: {str(e)}")
                            forward_success = False
                            continue

                    # Only mark as read if all forwards were successful
                    if forward_success and forwarded_count == len(config.TARGET_EMAILS):
                        try:
                            if handler.mark_as_read(message['id']):
                                print("✓ Marked email as read")
                                logger.info(f"Successfully processed and marked email as read: {email_content['subject']}")
                            else:
                                print("✗ Failed to mark email as read")
                                logger.error(f"Failed to mark email as read: {email_content['subject']}")
                        except Exception as e:
                            print("✗ Error marking email as read")
                            logger.error(f"Error marking email as read: {str(e)}")
                    else:
                        print(f"⚠️ Email not marked as read ({forwarded_count}/{len(config.TARGET_EMAILS)} forwards successful)")

                    print("="*80 + "\n")
                else:
                    print(f"✗ [{processed_count}/{len(messages)}] {email_content['subject']}")

            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                continue

        print("\nSummary:")
        print("="*40)
        print(f"Date Range: {(datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")
        print(f"Total unread emails: {processed_count}")
        print(f"Invoices found and forwarded: {invoice_count}")
        print(f"Non-invoice emails: {processed_count - invoice_count}")
        print("="*40)

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")

if __name__ == "__main__":
    main()
