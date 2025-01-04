# InboxIQ

An intelligent email management system that automatically processes, categorizes, and manages your emails using AI. The system identifies action items, creates calendar events, and forwards emails based on their content and importance.

## Prerequisites

- Python 3.8 or higher
- A Google Account with Gmail
- OpenAI API key (for AI-powered features)
- Google Cloud Console project with Gmail and Calendar APIs enabled

## Features

### 1. Email Processing and Analysis
- **AI-Powered Classification**: Uses OpenAI's GPT model to categorize emails into predefined categories
- **Action Item Detection**: Automatically identifies and extracts action items from email content
- **Smart Calendar Integration**: Creates calendar events for meetings and deadlines mentioned in emails
- **Intelligent Email Forwarding**: Forwards emails to relevant team members based on content analysis

### 2. Email Summary Reports
- **Comprehensive Summary**: Generates detailed reports of processed emails
- **Category Statistics**: Shows distribution of emails across different categories
- **Action Item Tracking**: Lists all action items extracted from emails with sender and subject information
- **Calendar Event Overview**: Displays all automatically created calendar events
- **Forwarding Details**: Provides information about forwarded emails

### 3. Calendar Management
- **Smart Scheduling**: Automatically schedules events with appropriate time slots
- **Reminder Settings**: Configurable reminder settings for different types of events
- **Event Link Generation**: Creates clickable calendar event links for easy access
- **Time Slot Management**: Ensures events are properly spaced and don't overlap

### 4. Configuration and Customization
- **Flexible Settings**: Customizable configuration for email processing and calendar management
- **Category Definitions**: Configurable email categories and classification rules
- **Calendar Preferences**: Adjustable calendar settings including:
  - Working hours
  - Reminder preferences
  - Time slot duration
  - Buffer between events

### 5. Backup System
- **Automated Backups**: Creates timestamped backups of all important files
- **Sensitive File Handling**: Special handling for sensitive files with restricted permissions
- **Backup Management**: Features include:
  - Creating new backups
  - Restoring from latest backup
  - Restoring from specific backup
  - Listing all backups
  - Deleting all backups

## Installation

1. Clone the repository:
```bash
git clone https://github.com/chirag6451/InboxIQ.git
cd InboxIQ
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install required dependencies:
```bash
pip install -r requirements.txt
```

4. Set up Google Cloud Project:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project or select an existing one
   - Enable Gmail API and Google Calendar API
   - Create OAuth 2.0 credentials (Web application type)
   - Add `http://localhost:8989/oauth2callback` to authorized redirect URIs
   - Download the credentials and save as `credentials.json` in the project root

5. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials and settings
```

## Quick Start

1. Start the application:
```bash
python app.py
```

2. Open your browser and go to:
```
http://localhost:8989/auth
```

3. Follow the Gmail authentication process. This will:
   - Redirect you to Google's consent screen
   - Ask for permissions to access your Gmail and Calendar
   - Redirect back to your application
   - Create a `token.json` file for future authentication

4. The application will start processing your emails based on your configuration

## Configuration Guide

### Email Categories Configuration

The system uses categories to organize and process emails effectively. Here's a real-world example of how to configure categories in `config.py`:

```python
EMAIL_CATEGORIES = {
    'invoice': {
        'enabled': True,
        'keywords': ['invoice', 'payment', 'bill', 'receipt', 'purchase'],
        'target_emails': ['accounting@company.com'],
        'calendar_settings': {
            'create_reminder': True,
            'reminder_advance': 20,  # minutes
            'default_duration': 30,
            'color': 'green'
        }
    },
    'meeting': {
        'enabled': True,
        'keywords': ['meet', 'sync', 'discussion', 'call', 'conference'],
        'target_emails': ['team@company.com'],
        'calendar_settings': {
            'create_reminder': True,
            'reminder_advance': 15,
            'default_duration': 45,
            'color': 'blue'
        }
    },
    'project_update': {
        'enabled': True,
        'keywords': ['project', 'update', 'status', 'progress', 'milestone'],
        'target_emails': ['manager@company.com', 'team@company.com'],
        'calendar_settings': {
            'create_reminder': True,
            'reminder_advance': 30,
            'default_duration': 60,
            'color': 'red'
        }
    }
}
```

### Real-world Examples

1. **Invoice Processing**
   - When an email with "Invoice #123 for Project X" arrives
   - System detects keywords: 'invoice'
   - Automatically forwards to accounting@company.com
   - Creates calendar reminder for payment due date

2. **Meeting Coordination**
   - Email subject: "Team Sync Discussion - Project Y"
   - System detects keywords: 'sync', 'discussion'
   - Creates calendar event with 45-minute duration
   - Sets reminder 15 minutes before
   - Notifies team@company.com

3. **Project Updates**
   - Email contains "Project Z Milestone Update"
   - System detects keywords: 'project', 'update'
   - Forwards to both manager and team
   - Creates 1-hour calendar event for review

### Calendar Integration

Configure calendar settings for different event types:
```python
CALENDAR_REMINDER_SETTINGS = {
    'start_time': '09:00',        # Day start time
    'end_time': '17:00',          # Day end time
    'reminder_advance': 15,        # Minutes before event
    'default_duration': 30,        # Default event duration
    'reminder_slot_duration': 15   # Spacing between events
}
```

## Usage

### Starting the Service
```bash
python app.py
```

### Processing Emails
The system will:
1. Fetch unread emails from your inbox
2. Analyze and categorize each email
3. Extract action items and create calendar events
4. Forward relevant emails
5. Generate and send summary reports

### Viewing Reports
Summary reports are sent to your email and include:
- Processing statistics
- Category distribution
- Action items by email
- Calendar events created
- Forwarding details

## Security

### Data Protection
- Sensitive credentials stored in `.env` file
- OAuth2 authentication for Gmail and Calendar APIs
- Encrypted backup storage for sensitive files
- Restricted permissions for sensitive directories

### Backup Security
- Sensitive files stored with 600 permissions
- Backup directories protected with 700 permissions
- Separate storage for sensitive and regular files

## Troubleshooting

### Common Issues
1. **Authentication Errors**
   - Verify credentials in `.env`
   - Check OAuth token validity
   - Ensure proper API permissions

2. **Processing Errors**
   - Check log files for error messages
   - Verify OpenAI API key and quota
   - Ensure proper email format

3. **Calendar Issues**
   - Verify calendar API access
   - Check time zone settings
   - Confirm calendar permissions

### Logging
- Detailed logs available in application directory
- Different log levels for debugging
- Separate logs for different components

## Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License
MIT License

Copyright (c) 2025 [Chirag Ahmedabadi/Kansara](https://www.linkedin.com/in/indapoint/)

## Acknowledgments
- OpenAI for GPT API
- Google for Gmail and Calendar APIs
- Contributors and maintainers

## Contact
For support or queries, please open an issue or contact the maintainers.