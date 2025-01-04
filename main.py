import os
import time
import logging
import threading
from typing import List, Dict, Any
from config import Config
from gmail_handler import GmailHandler
from invoice_analyzer import InvoiceAnalyzer
from utils import setup_logging, ensure_directory_exists, extract_pdf_text, is_valid_attachment
from app import app

def run_flask_server():
    """Run the Flask server for OAuth2 callback"""
    try:
        print("\n" + "="*80)
        print("Starting OAuth2 callback server...")
        print("Server will be available at: http://0.0.0.0:8080")
        print("="*80 + "\n")
        app.run(host='0.0.0.0', port=8080, debug=False)
    except Exception as e:
        logging.error(f"Failed to start Flask server: {str(e)}")
        raise

def process_attachments(gmail: GmailHandler, email_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Process email attachments"""
    logger = logging.getLogger(__name__)
    processed_attachments = []

    try:
        for attachment in email_data['attachments']:
            logger.info(f"Processing attachment: {attachment['filename']}")
            content = gmail.download_attachment(
                email_data['id'], 
                attachment['attachment_id']
            )

            if content and is_valid_attachment(
                attachment['filename'],
                len(content)
            ):
                processed_attachments.append({
                    'filename': attachment['filename'],
                    'content': content
                })
                logger.info(f"Successfully processed attachment: {attachment['filename']}")
            else:
                logger.warning(f"Skipped invalid attachment: {attachment['filename']}")
    except Exception as e:
        logger.error(f"Error processing attachments: {str(e)}")

    return processed_attachments

def analyze_email_content(
    analyzer: InvoiceAnalyzer,
    email_body: str,
    attachments: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Analyze email content and attachments"""
    logger = logging.getLogger(__name__)
    logger.info("Starting content analysis")

    try:
        # Analyze email body
        body_analysis = analyzer.analyze_content(email_body)
        if body_analysis:
            logger.info(f"Email body analysis completed - "
                       f"Is Invoice: {body_analysis.get('is_invoice', False)}, "
                       f"Confidence: {body_analysis.get('confidence', 0)}")
            if body_analysis.get('is_invoice'):
                logger.info(f"Invoice details found in body: "
                          f"{body_analysis.get('invoice_data', {})}")

        # Analyze PDF attachments
        pdf_analyses = []
        for attachment in attachments:
            if attachment['filename'].lower().endswith('.pdf'):
                logger.info(f"Analyzing PDF: {attachment['filename']}")
                pdf_text = extract_pdf_text(attachment['content'])
                if pdf_text:
                    pdf_analysis = analyzer.analyze_pdf_content(pdf_text)
                    if pdf_analysis:
                        logger.info(f"PDF analysis completed - "
                                  f"Is Invoice: {pdf_analysis.get('is_invoice', False)}, "
                                  f"Confidence: {pdf_analysis.get('confidence', 0)}")
                        if pdf_analysis.get('is_invoice'):
                            logger.info(f"Invoice details found in PDF: "
                                      f"{pdf_analysis.get('invoice_data', {})}")
                        pdf_analyses.append(pdf_analysis)

        # Combine analyses
        if body_analysis and body_analysis.get('is_invoice'):
            logger.info("Using invoice details from email body")
            return body_analysis

        for pdf_analysis in pdf_analyses:
            if pdf_analysis.get('is_invoice'):
                logger.info("Using invoice details from PDF attachment")
                return pdf_analysis

        logger.info("No invoice detected in content")
        return body_analysis if body_analysis else {'is_invoice': False, 'confidence': 0}

    except Exception as e:
        logger.error(f"Error in content analysis: {str(e)}")
        return {'is_invoice': False, 'confidence': 0}

def process_emails(gmail: GmailHandler, analyzer: InvoiceAnalyzer, config: Config):
    """Process emails from all source addresses"""
    logger = logging.getLogger(__name__)

    for source_email in config.SOURCE_EMAILS:
        logger.info(f"Processing emails from: {source_email}")

        try:
            # Get unread emails
            emails = gmail.get_unread_emails(source_email)
            logger.info(f"Found {len(emails)} unread emails")

            for email in emails:
                logger.info(f"Processing email: {email['subject']}")

                try:
                    # Process attachments
                    attachments = process_attachments(gmail, email)
                    logger.info(f"Processed {len(attachments)} attachments")

                    # Analyze content
                    analysis_result = analyze_email_content(
                        analyzer,
                        email['body'],
                        attachments
                    )

                    # Forward if invoice detected
                    if analyzer.should_forward(analysis_result):
                        logger.info("Invoice detected, forwarding email")

                        for target_email in config.TARGET_EMAILS:
                            success = gmail.forward_email(
                                target_email,
                                f"FWD: {email['subject']} - Invoice Detected",
                                f"""Original email from: {email['sender']}
                                \n\nInvoice Details:
                                {analysis_result['invoice_data']}
                                \n\nOriginal message:
                                {email['body']}""",
                                attachments
                            )

                            if success:
                                logger.info(f"Email forwarded to {target_email}")
                            else:
                                logger.error(f"Failed to forward email to {target_email}")
                    else:
                        logger.info("No invoice detected, skipping forward")

                    # Mark email as read
                    if gmail.mark_as_read(email['id']):
                        logger.info("Email marked as read")
                    else:
                        logger.error("Failed to mark email as read")

                except Exception as e:
                    logger.error(f"Error processing email {email['id']}: {str(e)}")
                    continue

                # Rate limiting pause between emails
                time.sleep(60 / config.GMAIL_RATE_LIMIT)

        except Exception as e:
            logger.error(f"Error processing source email {source_email}: {str(e)}")
            continue

def main():
    # Setup
    setup_logging(Config.LOG_FILE)
    logger = logging.getLogger(__name__)
    ensure_directory_exists(Config.ATTACHMENT_DIR)

    logger.info("Starting email processing")
    config = Config.from_env()
    logger.info(f"Source emails: {config.SOURCE_EMAILS}")
    logger.info(f"Target emails: {config.TARGET_EMAILS}")

    try:
        # Start Flask server in a separate thread
        flask_thread = threading.Thread(target=run_flask_server)
        flask_thread.daemon = True
        flask_thread.start()
        logger.info("Started OAuth2 callback server")

        # Initialize handlers
        logger.info("\n" + "="*80)
        logger.info("Initializing Gmail authentication...")
        logger.info("Please watch for the authentication URL that will be displayed below")
        logger.info("="*80)

        gmail = GmailHandler(config)
        if not gmail.service:
            logger.info("Waiting for authentication to complete...")
            logger.info("Please authenticate using the URL displayed above")
            return 0

        logger.info("Initializing Invoice analyzer")
        analyzer = InvoiceAnalyzer()

        # Main monitoring loop
        logger.info("Starting continuous email monitoring")
        check_interval = 60  # Check every minute

        while True:
            try:
                process_emails(gmail, analyzer, config)
                logger.info(f"Waiting {check_interval} seconds before next check...")
                time.sleep(check_interval)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                logger.info(f"Retrying in {check_interval} seconds...")
                time.sleep(check_interval)

    except KeyboardInterrupt:
        logger.info("Received shutdown signal, stopping gracefully...")
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())