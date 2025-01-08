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
    
    # User Configuration - Replace with your details
    USER_DETAILS: Dict[str, str] = field(
        default_factory=lambda: {
            'name': 'John',  # Your first name
            'full_name': 'John Smith',  # Your full name
            'company': 'Example Corp',  # Your company name
            'position': 'Manager',  # Your job position
            'timezone': 'UTC',  # Your timezone
            'preferred_language': 'English',  # Your preferred language
            'email_signature': 'Best regards,\nJohn Smith\nManager | Example Corp'  # Your email signature
        }
    )
    
    # Email categories and their configurations
    EMAIL_CATEGORIES: Dict[str, dict] = field(
        default_factory=lambda: {
            'bank_notification': {
                'enabled': True,
                'keywords': ['account', 'transaction', 'deposit', 'withdrawal', 'balance', 'statement', 'bank', 'transfer', 'NEFT', 'RTGS', 'IMPS'],
                'direct_forward': True,
                'from_emails': ['alerts@yourbank.com', 'notifications@bankexample.com'],
                'target_emails': ['your.email@example.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 30,
                    'default_duration': 15,
                    'color': 'green',
                    'notification': True,
                    'calendar_priorities': ['important'],
                    'timezone': 'UTC'
                }
            },
            'credit_card': {
                'enabled': True,
                'keywords': ['credit card', 'transaction', 'payment due', 'statement', 'card', 'spent', 'purchase', 'bill'],
                'direct_forward': True,
                'from_emails': ['alerts@creditcard.com', 'statements@cardexample.com'],
                'target_emails': ['your.email@example.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 1440,
                    'default_duration': 15,
                    'color': 'red',
                    'notification': True,
                    'calendar_priorities': ['urgent'],
                    'timezone': 'UTC'
                }
            },
            'invoices_payments': {
                'enabled': True,
                'keywords': ['invoice', 'payment', 'due', 'overdue', 'bill', 'subscription', 'receipt', 'amount', 'vendor'],
                'direct_forward': True,
                'from_emails': ['accounts@company.com', 'billing@vendor.com'],
                'target_emails': ['finance@yourcompany.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 2880,  # 48 hours
                    'default_duration': 30,
                    'color': 'orange',
                    'priority': 'urgent'
                }
            },
            'job_applications': {
                'enabled': True,
                'keywords': ['resume', 'job application', 'interview', 'candidate', 'hiring', 'CV', 'offer letter'],
                'direct_forward': False,
                'from_emails': ['hr@company.com', 'jobs@jobportal.com'],
                'target_emails': ['recruitment@company.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 1440,
                    'default_duration': 60,
                    'color': 'blue',
                    'priority': 'normal'
                }
            },
            'travel_bookings': {
                'enabled': True,
                'keywords': ['ticket', 'flight', 'hotel', 'reservation', 'boarding pass', 'trip', 'travel'],
                'direct_forward': False,
                'from_emails': ['travel@airline.com', 'hotel@booking.com'],
                'target_emails': ['personal.email@example.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 720,  # 12 hours
                    'default_duration': 60,
                    'color': 'cyan',
                    'priority': 'high'
                }
            },
            'shopping_deliveries': {
                'enabled': True,
                'keywords': ['order', 'shipment', 'tracking', 'delivery', 'cart', 'purchase', 'return', 'refund'],
                'direct_forward': False,
                'from_emails': ['store@onlineshop.com', 'delivery@courier.com'],
                'target_emails': ['personal.email@example.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 60,  # 1 hour
                    'default_duration': 30,
                    'color': 'purple',
                    'priority': 'normal'
                }
            }
        }
    )
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Create Config instance from environment variables"""
        return cls()
