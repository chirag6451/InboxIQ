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
            'work': {
                'enabled': True,
                'keywords': ['project', 'task', 'deadline', 'update', 'status'],
                'target_emails': ['chirag@indapoint.com'],
                'cc_to': ['manager@company.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 30,  # minutes
                    'default_duration': 60,  # minutes
                    'color': 'red',
                    'notification': True,
                    'calendar_priorities': ['urgent', 'important'],
                    'timezone': 'Asia/Kolkata'
                }
            },
            'meeting': {
                'enabled': True,
                'keywords': ['meet', 'sync', 'discussion', 'call', 'conference'],
                'target_emails': ['chirag@indapoint.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 60,
                    'default_duration': 45,
                    'color': 'yellow',
                    'notification': True,
                    'calendar_priorities': ['urgent', 'important', 'normal'],
                    'timezone': 'Asia/Kolkata'
                }
            },
            'deadline': {
                'enabled': True,
                'keywords': ['due', 'deadline', 'by', 'until', 'complete'],
                'target_emails': ['chirag@indapoint.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 120,
                    'default_duration': 30,
                    'color': 'blue',
                    'notification': True,
                    'calendar_priorities': ['urgent'],
                    'timezone': 'Asia/Kolkata'
                }
            },
            'invoice': {
                'enabled': True,
                'keywords': ['invoice', 'payment', 'bill', 'receipt', 'purchase'],
                'target_emails': ['chirag@indapoint.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 45,
                    'default_duration': 30,
                    'color': 'green',
                    'notification': True,
                    'calendar_priorities': ['urgent', 'important'],
                    'timezone': 'Asia/Kolkata'
                }
            },
            'report': {
                'enabled': True,
                'keywords': ['report', 'analysis', 'metrics', 'performance', 'results'],
                'target_emails': ['chirag@indapoint.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 15,
                    'default_duration': 30,
                    'color': 'orange',
                    'notification': True,
                    'calendar_priorities': ['urgent'],
                    'timezone': 'Asia/Kolkata'
                }
            },
            'follow_up': {
                'enabled': True,
                'keywords': ['follow up', 'following up', 'checking in', 'status', 'update'],
                'target_emails': ['chirag@indapoint.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 30,
                    'default_duration': 30,
                    'color': 'purple',
                    'notification': True,
                    'calendar_priorities': ['urgent', 'important'],
                    'timezone': 'Asia/Kolkata'
                }
            },
            'support': {
                'enabled': True,
                'keywords': ['help', 'support', 'issue', 'bug', 'ticket'],
                'target_emails': ['chirag@indapoint.com'],
                'cc_to': ['manager@company.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 30,
                    'default_duration': 30,
                    'color': 'brown',
                    'notification': True,
                    'calendar_priorities': ['urgent', 'important'],
                    'timezone': 'Asia/Kolkata'
                }
            },
            'project': {
                'enabled': True,
                'keywords': ['project', 'scope', 'planning', 'phase', 'milestone'],
                'target_emails': ['chirag@indapoint.com'],
                'cc_to': ['pm@company.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 45,
                    'default_duration': 60,
                    'color': 'gray',
                    'notification': True,
                    'calendar_priorities': ['urgent', 'important', 'normal'],
                    'timezone': 'Asia/Kolkata'
                }
            },
            'sales': {
                'enabled': True,
                'keywords': ['sale', 'deal', 'offer', 'discount', 'contract'],
                'target_emails': ['chirag@indapoint.com'],
                'cc_to': ['manager@company.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 30,
                    'default_duration': 45,
                    'color': 'pink',
                    'notification': True,
                    'calendar_priorities': ['urgent', 'important'],
                    'timezone': 'Asia/Kolkata'
                }
            },
            'inquiry_lead': {
                'enabled': True,
                'keywords': ['lead', 'prospect', 'inquiry', 'request', 'information'],
                'target_emails': ['chirag@indapoint.com'],
                'cc_to': ['manager@company.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 20,
                    'default_duration': 30,
                    'color': 'pink',
                    'notification': True,
                    'calendar_priorities': ['urgent', 'important', 'normal'],
                    'timezone': 'Asia/Kolkata'
                }
            },
            'personal': {
                'enabled': True,
                'keywords': ['family', 'friends', 'birthday', 'anniversary', 'personal'],
                'target_emails': ['chirag@indapoint.com'],
                'calendar_settings': {
                    'create_reminder': True,
                    'reminder_advance': 60,
                    'default_duration': 60,
                    'color': 'yellow',
                    'notification': True,
                    'calendar_priorities': ['urgent', 'important', 'normal'],
                    'timezone': 'Asia/Kolkata'
                }
            },
            'spam': {
                'enabled': False,
                'keywords': ['spam', 'junk', 'unsubscribe', 'promotional'],
                'target_emails': [],
                'calendar_settings': {
                    'create_reminder': False,
                    'calendar_priorities': [],
                    'timezone': 'Asia/Kolkata'
                }
            },
            
            # New Categories
        }
    )
    
    # Calendar settings
    CALENDAR_SETTINGS = {
        'default_reminder_minutes': 30,
        'timezone': 'Asia/Kolkata'
    }
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        self._validate_categories()
        
    def _validate_categories(self):
        """Validate email category configurations"""
        for category, config in self.EMAIL_CATEGORIES.items():
            if not isinstance(config, dict):
                raise ValueError(f"Category {category} configuration must be a dictionary")
            
            required_keys = {'enabled', 'keywords', 'target_emails', 'calendar_settings'}
            if not all(key in config for key in required_keys):
                raise ValueError(f"Category {category} missing required configuration keys")
            
            if not isinstance(config['keywords'], list):
                raise ValueError(f"Keywords for category {category} must be a list")
                
            if not isinstance(config['target_emails'], list):
                raise ValueError(f"Target emails for category {category} must be a list")
                
            if not isinstance(config['calendar_settings'], dict):
                raise ValueError(f"Calendar settings for category {category} must be a dictionary")
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Create configuration from environment variables"""
        return cls()
    
    @classmethod
    def get_gmail_scopes(cls) -> List[str]:
        """Get required Gmail API scopes"""
        return cls.GMAIL_SCOPES

# ----------------------------------------------------------------------------------------
# Additional Category Suggestions (not added above, but you might consider for future use):
# 1. 'marketing': for emails containing campaign, SEO, ads, branding, social media
# 2. 'finance': for emails containing budget, expense, reimbursement, accounts, investment
# 3. 'legal': for emails containing contract, agreement, NDA, compliance, policy
# 4. 'hr': for emails containing recruitment, hiring, interview, employee relations
# 5. 'travel': for emails containing flights, booking, itinerary, hotel, trip
# 6. 'vacation': for personal or out-of-office reminders
# 7. 'health': for emails related to medical appointments, insurance, wellness
# ----------------------------------------------------------------------------------------
