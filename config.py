import os
import re
from dataclasses import dataclass, field
from typing import List, Set, Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables at module level
load_dotenv(override=True)

@dataclass
class Config:
    """Configuration class for email processing"""
    
    # OpenAI settings
    OPENAI_MODEL: str = field(default="gpt-3.5-turbo")
    
    # Logging configuration
    LOG_FILE = "app.log"
    
    # Attachment handling configuration
    ATTACHMENT_DIR = "attachments"
    ALLOWED_EXTENSIONS = {'pdf', 'txt', 'doc', 'docx', 'xls', 'xlsx', 'csv'}
    MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024  # 10MB in bytes
    
    # Gmail API scopes required
    GMAIL_SCOPES = [
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/gmail.compose',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/calendar.events'
    ]
    
    # Calendar settings for reminders
    CALENDER_REMINDER_SETTINGS: Dict[str, Any] = field(
        default_factory=lambda: {
            'start_time': '09:00',
            'end_time': '17:00',
            'reminder_advance': 45,  # minutes
            'default_duration': 60,  # minutes
            'reminder_slot_duration': 30,
            'reminder_color': 'red',
            'notification': True
        }
    )
    # User Configuration
    USER_DETAILS: Dict[str, str] = field(
        default_factory=lambda: {
            'name': 'User',  # User's first name
            'full_name': 'User Name',  # User's full name
            'company': 'Company Name',  # Company name
            'position': 'Position',  # Job position
            'timezone': 'UTC',  # User's timezone
            'preferred_language': 'English',  # Preferred language for communications
            'email_signature': 'Best regards,\nUser Name\nPosition | Company Name'  # Email signature
        }
    )
    
    # Email categories and their configurations
    EMAIL_CATEGORIES: Dict[str, dict] = field(
        default_factory=lambda: {
            'bank_notification': {
                'enabled': True,
                'keywords': ['account', 'transaction', 'deposit', 'withdrawal', 'balance', 'statement', 'bank', 'transfer', 'NEFT', 'RTGS', 'IMPS'],
                'direct_forward': True,
                'from_emails': ['alerts@bank.com', 'notifications@bank.com'],
                'target_emails': ['user.email@example.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 30,  # minutes
                    'default_duration': 15,  # minutes
                    'color': 'green',
                    'notification': True,
                    'calendar_priorities': ['important'],
                    'timezone': 'UTC'
                }
            },
            'invoice_alerts': {
                'enabled': True,
                'keywords': ['invoice', 'payment', 'due', 'bill', 'amount', 'payable', 'outstanding', 'reminder'],
                'direct_forward': False,
                'from_emails': [],
                'target_emails': ['user.email@example.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 1440,  # 24 hours in minutes
                    'default_duration': 15,  # minutes
                    'color': 'red',
                    'notification': True,
                    'calendar_priorities': ['urgent'],
                    'timezone': 'UTC'
                }
            }
        }
    )

    @classmethod
    def get_gmail_scopes(cls) -> List[str]:
        """Get the Gmail API scopes required for the application."""
        return cls.GMAIL_SCOPES

    @classmethod
    def from_env(cls):
        """Create a Config instance from environment variables"""
        config = cls()
        
        # Load source and target emails from environment
        source_emails_str = os.getenv('SOURCE_EMAILS', '')
        target_emails_str = os.getenv('TARGET_EMAILS', '')
        
        config.SOURCE_EMAILS = [email.strip() for email in source_emails_str.split(',') if email.strip()]
        config.TARGET_EMAILS = [email.strip() for email in target_emails_str.split(',') if email.strip()]
        
        # Load OpenAI settings
        if os.getenv('OPENAI_MODEL'):
            config.OPENAI_MODEL = os.getenv('OPENAI_MODEL')
            
        return config
