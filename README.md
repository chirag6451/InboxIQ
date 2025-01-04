# Gmail Invoice Scanner

A Python application that automatically scans Gmail inboxes for invoices, extracts relevant information, and provides easy management of the extracted data.

## Setup Guide

### 1. Prerequisites
- Python 3.8 or higher
- A Google Cloud Project with Gmail API enabled
- OAuth 2.0 credentials from Google Cloud Console

### 2. Initial Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd invoice-emails
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up Google Cloud Project:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project or select an existing one
   - Enable the Gmail API
   - Create OAuth 2.0 credentials (Web application type)
   - Add `http://localhost:8989/oauth2callback` to authorized redirect URIs
   - Download the credentials and save as `credentials.json` in the project root

### 3. Configuration

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Configure the `.env` file:
```ini
# Gmail Configuration
APP_DOMAIN=localhost:8989  # Your domain (use localhost:8989 for local development)
USE_HTTPS=false  # Set to true in production

# OpenAI Configuration (for invoice processing)
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-4  # or another compatible model

# Flask Configuration
FLASK_SECRET_KEY=your-random-secret-key  # Generate a secure random key
FLASK_ENV=development  # Set to production in production

# Email Configuration
SOURCE_EMAILS=email1@domain.com,email2@domain.com  # Emails to monitor for invoices
TARGET_EMAILS=target1@domain.com,target2@domain.com  # Emails to receive forwarded invoices

# Invoice Scanner Configuration
SCAN_INTERVAL_MINUTES=30
MAX_EMAILS_PER_SCAN=100
ATTACHMENT_TYPES=pdf,PDF
SAVE_ATTACHMENTS_DIR=attachments
```

3. Configure `config.py`:
- Adjust the Gmail API scopes if needed
- Modify invoice processing settings
- Configure logging settings

### 4. Authentication

1. Start the web server:
```bash
python app.py
```

2. Visit `http://localhost:8989`
3. Click "Authenticate with Gmail" and follow the Google OAuth flow
4. Your Gmail account will now be authenticated for invoice scanning

### 5. Running the Invoice Scanner

#### Manual Execution
Run the invoice scanner manually:
```bash
python check_invoice_emails.py
```

#### Automated Scanning (Cron Setup)

1. Create a cron job (Linux/Mac):
```bash
crontab -e
```

2. Add the following line to run every 30 minutes:
```
*/30 * * * * cd /path/to/invoice-emails && /usr/bin/python3 check_invoice_emails.py >> /path/to/invoice-emails/cron.log 2>&1
```

For Windows, use Task Scheduler:
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger to run every 30 minutes
4. Action: Start a program
5. Program: python.exe
6. Arguments: check_invoice_emails.py
7. Start in: C:\path\to\invoice-emails

### 6. Monitoring and Maintenance

#### Logs
- Check `invoice_scanner.log` for detailed operation logs
- For cron jobs, check `cron.log`

#### Common Issues
1. Authentication errors:
   - Ensure credentials.json is properly configured
   - Try re-authenticating through the web interface

2. Email scanning issues:
   - Verify SOURCE_EMAILS and TARGET_EMAILS in .env
   - Check SCAN_INTERVAL_MINUTES and MAX_EMAILS_PER_SCAN settings

3. Invoice processing errors:
   - Verify OPENAI_API_KEY and OPENAI_MODEL settings
   - Check ATTACHMENT_TYPES configuration

### 7. Security Best Practices

1. In production:
   - Set USE_HTTPS=true
   - Use a strong FLASK_SECRET_KEY
   - Set FLASK_ENV=production
   - Store credentials securely
   - Use environment variables for sensitive data

2. File permissions:
   - Restrict access to credentials.json and token.json
   - Secure the attachments directory

## Contributing

Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

unzip gmail_invoice_scanner.zip
cd gmail_invoice_scanner