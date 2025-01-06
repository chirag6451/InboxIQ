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
            'name': 'John',  # User's first name
            'full_name': 'John Smith',  # User's full name
            'company': 'Example Corp',  # Company name
            'position': 'Manager',  # Job position
            'timezone': 'UTC',  # User's timezone
            'preferred_language': 'English',  # Preferred language for communications
            'email_signature': 'Best regards,\nJohn Smith\nManager | Example Corp'  # Email signature
        }
    )
    
    # Email categories and their configurations
    EMAIL_CATEGORIES: Dict[str, dict] = field(
        default_factory=lambda: {
            'work': {
                'enabled': True,
                'keywords': ['project', 'task', 'deadline', 'update', 'status'],
                'target_emails': ['manager@example.com'],
                'cc_to': ['team@example.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 45,  # minutes
                    'default_duration': 60,  # minutes
                    'color': 'red',
                    'notification': True,
                    'calendar_priorities': ['urgent', 'important'],
                    'timezone': 'UTC'
                }
            },
            'meeting': {
                'enabled': True,
                'keywords': ['meet', 'sync', 'discussion', 'call', 'conference'],
                'target_emails': ['team@example.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 30,
                    'default_duration': 45,
                    'color': 'yellow',
                    'notification': True,
                    'calendar_priorities': ['urgent', 'important', 'normal'],
                    'timezone': 'UTC'
                }
            },
            'deadline': {
                'enabled': True,
                'keywords': ['due', 'deadline', 'by', 'until', 'complete'],
                'target_emails': ['manager@example.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 60,
                    'default_duration': 30,
                    'color': 'blue',
                    'notification': True,
                    'calendar_priorities': ['urgent', 'important'],
                    'timezone': 'UTC'
                }
            },
            'invoice': {
                'enabled': True,
                'keywords': ['invoice', 'payment', 'bill', 'receipt', 'purchase'],
                'target_emails': ['finance@example.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 20,
                    'default_duration': 30,
                    'color': 'green',
                    'notification': True,
                    'calendar_priorities': ['urgent', 'important'],
                    'timezone': 'UTC'
                }
            },
            'report': {
                'enabled': True,
                'keywords': ['report', 'analysis', 'metrics', 'performance', 'results'],
                'target_emails': ['reports@example.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 15,
                    'default_duration': 30,
                    'color': 'orange',
                    'notification': True,
                    'calendar_priorities': ['urgent'],
                    'timezone': 'UTC'
                }
            },
            'follow_up': {
                'enabled': True,
                'keywords': ['follow up', 'following up', 'checking in', 'status', 'update'],
                'target_emails': ['team@example.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 30,
                    'default_duration': 30,
                    'color': 'purple',
                    'notification': True,
                    'calendar_priorities': ['urgent', 'important'],
                    'timezone': 'UTC'
                }
            },
            'support': {
                'enabled': True,
                'keywords': ['help', 'support', 'issue', 'bug', 'ticket'],
                'target_emails': ['support@example.com'],
                'cc_to': ['manager@example.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 30,
                    'default_duration': 30,
                    'color': 'brown',
                    'notification': True,
                    'calendar_priorities': ['urgent', 'important'],
                    'timezone': 'UTC'
                }
            },
            'project': {
                'enabled': True,
                'keywords': ['project', 'scope', 'planning', 'phase', 'milestone'],
                'target_emails': ['project@example.com'],
                'cc_to': ['manager@example.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 45,
                    'default_duration': 60,
                    'color': 'gray',
                    'notification': True,
                    'calendar_priorities': ['urgent', 'important', 'normal'],
                    'timezone': 'UTC'
                }
            },
            'sales': {
                'enabled': True,
                'keywords': ['sale', 'deal', 'offer', 'discount', 'contract'],
                'target_emails': ['sales@example.com'],
                'cc_to': ['manager@example.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 30,
                    'default_duration': 45,
                    'color': 'pink',
                    'notification': True,
                    'calendar_priorities': ['urgent', 'important'],
                    'timezone': 'UTC'
                }
            },
            'inquiry_lead': {
                'enabled': True,
                'keywords': ['lead', 'prospect', 'inquiry', 'request', 'information'],
                'target_emails': ['sales@example.com'],
                'cc_to': ['manager@example.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 20,
                    'default_duration': 30,
                    'color': 'pink',
                    'notification': True,
                    'calendar_priorities': ['urgent', 'important', 'normal'],
                    'timezone': 'UTC'
                }
            }
        }
    )

    @classmethod
    def get_gmail_scopes(cls) -> List[str]:
        """Get the Gmail API scopes required for the application."""
        return cls.GMAIL_SCOPES
