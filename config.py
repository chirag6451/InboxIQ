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
    
    # Gmail API scopes required
    GMAIL_SCOPES: List[str] = field(
        default_factory=lambda: [
            'https://www.googleapis.com/auth/gmail.modify',
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/calendar.events'
        ]
    )
    
    # User Configuration
    USER_DETAILS: Dict[str, str] = field(
        default_factory=lambda: {
            'name': 'Chirag',  # User's first name
            'full_name': 'Chirag Ahmed Abadi',  # User's full name
            'company': 'IndaPoint',  # Company name
            'position': 'CEO',  # Job position
            'timezone': 'Asia/Kolkata',  # User's timezone
            'preferred_language': 'English',  # Preferred language for communications
            'email_signature': 'Best regards,\nChirag Ahmed Abadi\nCEO | IndaPoint'  # Email signature
        }
    )
    
    # Email categories and their configurations
    EMAIL_CATEGORIES: Dict[str, dict] = field(
        default_factory=lambda: {
            'urgent': {
                'enabled': True,
                'target_emails': ['ahmedabadi@gmail.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 30,  # minutes
                    'default_duration': 60,  # minutes
                    'color': '1',  # Red
                    'notification': True
                }
            },
            'important': {
                'enabled': True,
                'target_emails': ['ahmedabadi@gmail.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 60,
                    'default_duration': 45,
                    'color': '5',  # Yellow
                    'notification': True
                }
            },
            'notification': {
                'enabled': True,
                'target_emails': ['ahmedabadi@gmail.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 120,
                    'default_duration': 30,
                    'color': '9',  # Blue
                    'notification': False
                }
            },
            'support': {
                'enabled': True,
                'target_emails': ['ahmedabadi@gmail.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 45,
                    'default_duration': 30,
                    'color': '2',  # Green
                    'notification': True
                }
            },
            'alert': {
                'enabled': True,
                'target_emails': ['ahmedabadi@gmail.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 15,
                    'default_duration': 30,
                    'color': '4',  # Orange
                    'notification': True
                }
            },
            'spam': {
                'enabled': False,
                'target_emails': [],
                'calendar_settings': {
                    'create_reminder': False
                }
            }
        }
    )
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        self._validate_categories()
        
    def _validate_categories(self):
        """Validate email category configurations"""
        for category, config in self.EMAIL_CATEGORIES.items():
            if not isinstance(config, dict):
                raise ValueError(f"Category {category} configuration must be a dictionary")
            
            required_keys = {'enabled', 'target_emails', 'calendar_settings'}
            if not all(key in config for key in required_keys):
                raise ValueError(f"Category {category} missing required configuration keys")
            
            if not isinstance(config['target_emails'], list):
                raise ValueError(f"Target emails for category {category} must be a list")
            
            if not isinstance(config['calendar_settings'], dict):
                raise ValueError(f"Calendar settings for category {category} must be a dictionary")
            
            if config['calendar_settings'].get('create_reminder'):
                calendar_required_keys = {'reminder_advance', 'default_duration', 'color', 'notification'}
                if not all(key in config['calendar_settings'] for key in calendar_required_keys):
                    raise ValueError(f"Calendar settings for category {category} missing required keys")
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Create configuration from environment variables"""
        return cls()
    
    @classmethod
    def get_gmail_scopes(cls) -> List[str]:
        """Get required Gmail API scopes"""
        return cls.GMAIL_SCOPES