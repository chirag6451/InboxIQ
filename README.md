# InboxIQ

Your AI-Powered Email Intelligence Assistant

## The Problem

In today's fast-paced business environment, executives, project managers, and busy professionals face a common challenge: email overload. They spend hours daily sorting through hundreds of emails, trying to:
- Identify critical messages requiring immediate attention
- Forward relevant information to appropriate team members
- Set reminders for important deadlines and meetings
- Extract and track action items
- Maintain organized communication across departments

This manual email management can consume 2-3 hours daily, reducing productivity and increasing stress levels.

## The Solution

InboxIQ is an intelligent email management system that acts as your personal AI assistant, transforming how busy professionals handle their email workflow. It automatically processes, categorizes, and manages your emails using advanced AI, turning hours of email management into a few minutes of reviewing smart summaries.

### Perfect For:
- **C-Level Executives** who need to stay on top of company communications
- **Project Managers** handling multiple project communications and deadlines
- **Team Leaders** coordinating with various departments and stakeholders
- **Business Owners** managing client communications and internal operations
- **Department Heads** overseeing team communications and deliverables

### Key Features

#### 1. Smart Email Classification
- Automatically categorizes emails using AI (meetings, action items, reports, etc.)
- Learns from your email patterns and preferences
- Prioritizes emails based on urgency and importance

#### 2. Intelligent Forwarding System
- Automatically routes emails to relevant team members or departments
- Smart CC and BCC management based on content context
- Maintains communication chain while reducing email clutter

#### 3. Automated Calendar Management
- Creates calendar events from email content
- Sets smart reminders for deadlines and follow-ups
- Manages meeting schedules with conflict detection
- Sends calendar invites to relevant participants

#### 4. Action Item Extraction
- Identifies and extracts action items from email content
- Creates task lists with deadlines
- Tracks action item status and sends reminders
- Links related emails to specific action items

#### 5. Priority Filtering
- Identifies high-priority emails requiring immediate attention
- Filters out non-essential communications
- Creates focused work queues based on importance
- Reduces noise while ensuring critical items aren't missed

#### 6. Daily Intelligence Reports
- Generates comprehensive daily email summaries
- Provides quick overview of key actions and decisions
- Highlights pending items and upcoming deadlines
- Takes just minutes to review instead of hours of email processing

#### 7. Customization and Control
- Fully customizable classification rules
- Adjustable forwarding and notification preferences
- Flexible calendar and reminder settings
- Department-specific workflow configurations
- Custom keywords and priority settings

### Real-World Impact

A typical executive receiving 100+ emails daily can:
- Reduce email management time from 2-3 hours to 15-20 minutes
- Never miss critical communications or deadlines
- Ensure proper team coordination without manual forwarding
- Stay informed with minimal time investment
- Focus on strategic tasks instead of email organization

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

## Automated Email Processing Setup

### Understanding process_emails.py

The `process_emails.py` script is the core component of InboxIQ that:
- Fetches unread emails from your Gmail
- Classifies them using AI
- Creates calendar events
- Forwards emails to appropriate team members
- Generates comprehensive daily reports

### Running the Email Processor

#### Manual Execution
```bash
# Process default number of emails (10)
python process_emails.py

# Process specific number of emails
python process_emails.py --max-emails 50
```

#### Automated Daily Processing

For optimal results, set up `process_emails.py` to run automatically at midnight:

1. Open your crontab configuration:
```bash
crontab -e
```

2. Add the following line to run at midnight (00:00):
```bash
0 0 * * * cd /path/to/InboxIQ && /path/to/venv/bin/python process_emails.py --max-emails 100 >> /path/to/InboxIQ/logs/cron.log 2>&1
```

Replace `/path/to/InboxIQ` with your actual installation path.

For different timezones, adjust the cron schedule accordingly. For example, for IST (UTC+5:30):
```bash
30 18 * * * cd /path/to/InboxIQ && /path/to/venv/bin/python process_emails.py --max-emails 100 >> /path/to/InboxIQ/logs/cron.log 2>&1
```

#### Processing Options

The script supports several command-line arguments:

```bash
python process_emails.py [options]

Options:
  --max-emails N        Maximum number of emails to process (default: 10)
  --report-format       Report format: 'html' or 'text' (default: 'html')
  --days-back N         Process emails from N days back (default: 1)
  --categories          Specific categories to process (comma-separated)
```

### Daily Reports

After processing, the script generates comprehensive reports:

1. **Email Statistics**
   - Total emails processed
   - Category distribution
   - Processing time

2. **Action Items**
   - Extracted tasks and deadlines
   - Priority levels
   - Assigned team members

3. **Calendar Events**
   - Created/Updated events
   - Meeting schedules
   - Reminders set

4. **Forwarding Summary**
   - Emails forwarded
   - Target recipients
   - Forwarding rules applied

### Monitoring and Logs

Monitor the email processor's operation through:

1. **Log Files**
   ```bash
   tail -f logs/email_processing.log
   ```

2. **Cron Job Logs**
   ```bash
   tail -f logs/cron.log
   ```

3. **Report History**
   - Located in: `reports/`
   - Named format: `email_report_YYYYMMDD_HHMMSS.html`

### Troubleshooting

If the automated processing isn't working:

1. Check permissions:
   ```bash
   chmod +x process_emails.py
   ```

2. Verify Python path in cron:
   ```bash
   which python  # Use this path in cron job
   ```

3. Ensure all environment variables are available to cron:
   ```bash
   # Add to crontab
   PYTHONPATH=/path/to/InboxIQ
   PATH=/usr/local/bin:/usr/bin:/bin
   ```

4. Test the command manually with cron user:
   ```bash
   sudo -u your-user /path/to/venv/bin/python process_emails.py
   ```

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

## Frequently Asked Questions (FAQ)

### General Questions

#### Q: How secure is InboxIQ with my emails?
A: Security is our top priority. InboxIQ:
- Uses OAuth2 for secure Gmail authentication
- Never stores email contents, only metadata
- Processes emails in memory
- Follows Google's security best practices
- Requires explicit permission for each access level

#### Q: Can I customize which emails are processed?
A: Yes! You can:
- Set specific email domains to process/ignore
- Define custom keywords for each category
- Configure working hours for processing
- Set priority levels for different senders
- Exclude specific folders or labels

#### Q: Will this work with my existing email workflow?
A: InboxIQ is designed to enhance, not replace, your workflow:
- Integrates seamlessly with Gmail
- Preserves your existing folders and labels
- Works alongside other email tools
- Allows manual override of any automated action
- Can be configured to match your work style

#### Q: How accurate is the AI classification?
A: Our AI system achieves high accuracy through:
- Advanced natural language processing
- Learning from your corrections and preferences
- Regular model updates and improvements
- Category-specific training
- Confidence scoring for classifications

### Technical Questions

#### Q: Can I run this on my own server?
A: Yes, InboxIQ can be deployed on:
- Local machines
- Cloud servers (AWS, GCP, Azure)
- Docker containers
- Corporate networks
Just ensure Python 3.8+ and required dependencies are available.

#### Q: What happens if the system goes offline?
A: InboxIQ is designed for reliability:
- No emails are lost or missed
- Processes missed emails when back online
- Maintains local backup of configurations
- Logs all activities for audit
- Auto-recovers from interruptions

#### Q: How resource-intensive is InboxIQ?
A: The system is optimized for efficiency:
- Minimal CPU usage during idle
- Configurable processing intervals
- Efficient memory management
- Scalable based on email volume
- Optional batch processing for large volumes

### Usage Questions

#### Q: How long does it take to set up?
A: Basic setup takes about 15 minutes:
- 5 minutes for installation
- 5 minutes for Gmail authentication
- 5 minutes for initial configuration
Additional customization can be done gradually.

#### Q: Can multiple team members use the same instance?
A: Yes, InboxIQ supports:
- Multiple user accounts
- Shared configurations
- Team-specific rules
- Department-level settings
- Role-based access control

#### Q: What kind of maintenance is required?
A: InboxIQ is designed for minimal maintenance:
- Automatic updates for AI models
- Self-cleaning log management
- Regular configuration backups
- Health monitoring alerts
- Automated error recovery

### Support Questions

#### Q: What if I need help with configuration?
A: Support is available through:
- Detailed documentation
- Configuration examples
- GitHub issues
- Community forums
- Direct support (for enterprise users)

#### Q: Can I contribute to the project?
A: Yes! We welcome:
- Code contributions
- Feature suggestions
- Bug reports
- Documentation improvements
- Use case examples

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