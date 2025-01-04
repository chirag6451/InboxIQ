import os
import re
from dataclasses import dataclass, field
from typing import List, Set, Optional
from dotenv import load_dotenv

# Load environment variables at module level
load_dotenv(override=True)

@dataclass
class Config:
    """Configuration class for email processing application"""

    # Gmail API configuration
    GMAIL_SCOPES: List[str] = field(
        default_factory=lambda: [
            'https://www.googleapis.com/auth/gmail.modify',
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.labels',
            'https://www.googleapis.com/auth/gmail.send'
        ],
        metadata={'help': 'Gmail API scopes required for the application'}
    )

    # OpenAI configuration
    OPENAI_API_KEY: str = field(
        default=None,
        metadata={'help': 'OpenAI API key for invoice analysis'}
    )

    # Rate limiting (requests per minute)
    GMAIL_RATE_LIMIT: int = field(
        default=250,
        metadata={'help': 'Maximum Gmail API requests per minute'}
    )
    
    OPENAI_RATE_LIMIT: int = field(
        default=60,
        metadata={'help': 'Maximum OpenAI API requests per minute'}
    )

    # Email processing configuration
    SOURCE_EMAILS: List[str] = field(
        default_factory=list,
        metadata={'help': 'List of email addresses to monitor for invoices'}
    )
    TARGET_EMAILS: List[str] = field(
        default_factory=list,
        metadata={'help': 'List of email addresses to forward invoices to'}
    )

    # Invoice detection configuration
    MIN_CONFIDENCE_THRESHOLD: float = field(
        default=0.8,
        metadata={'help': 'Minimum confidence score for invoice detection'}
    )

    # Logging configuration
    LOG_FILE: str = field(
        default='email_processor.log',
        metadata={'help': 'Path to the log file'}
    )
    LOG_LEVEL: str = field(
        default='INFO',
        metadata={'help': 'Logging level'}
    )

    # Attachment handling
    ATTACHMENT_DIR: str = field(
        default='attachments',
        metadata={'help': 'Directory to store email attachments'}
    )
    ALLOWED_EXTENSIONS: Set[str] = field(
        default_factory=lambda: {'.pdf', '.png', '.jpg', '.jpeg', '.tiff'},
        metadata={'help': 'Allowed file extensions for attachments'}
    )
    MAX_ATTACHMENT_SIZE: int = field(
        default=10 * 1024 * 1024,  # 10MB
        metadata={'help': 'Maximum allowed attachment size in bytes'}
    )

    def __post_init__(self):
        """Post initialization validation and setup"""
        self._load_environment_variables()
        self._validate_api_keys()
        self._validate_email_lists()
        self._validate_emails()
        self._validate_paths()
        self._validate_rate_limits()
        self._validate_confidence_threshold()
        self._setup_directories()

    def _load_environment_variables(self):
        """Load configuration from environment variables"""
        # Load OpenAI API key
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
        
        # Load email lists
        source_emails = os.getenv('SOURCE_EMAILS', '')
        target_emails = os.getenv('TARGET_EMAILS', '')
        
        self.SOURCE_EMAILS = [email.strip() for email in source_emails.split(',') if email.strip()]
        self.TARGET_EMAILS = [email.strip() for email in target_emails.split(',') if email.strip()]

    def _validate_api_keys(self):
        """Validate required API keys"""
        if not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")

    def _validate_email_lists(self):
        """Validate email lists"""
        if not self.SOURCE_EMAILS:
            raise ValueError("SOURCE_EMAILS environment variable is required")
        if not self.TARGET_EMAILS:
            raise ValueError("TARGET_EMAILS environment variable is required")

    def _validate_emails(self):
        """Validate email address format"""
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

        def validate_email_list(emails: List[str], list_name: str) -> None:
            for email in emails:
                if not email_pattern.match(email):
                    raise ValueError(f"Invalid email format in {list_name}: {email}")

        if self.SOURCE_EMAILS:
            validate_email_list(self.SOURCE_EMAILS, "SOURCE_EMAILS")
        if self.TARGET_EMAILS:
            validate_email_list(self.TARGET_EMAILS, "TARGET_EMAILS")

    def _validate_paths(self):
        """Validate file paths"""
        pass

    def _validate_rate_limits(self):
        """Validate rate limits"""
        if self.GMAIL_RATE_LIMIT <= 0:
            raise ValueError("GMAIL_RATE_LIMIT must be positive")
        if self.OPENAI_RATE_LIMIT <= 0:
            raise ValueError("OPENAI_RATE_LIMIT must be positive")

    def _validate_confidence_threshold(self):
        """Validate confidence threshold"""
        if not 0 <= self.MIN_CONFIDENCE_THRESHOLD <= 1:
            raise ValueError("MIN_CONFIDENCE_THRESHOLD must be between 0 and 1")

    def _setup_directories(self):
        """Create necessary directories"""
        if not os.path.exists(self.ATTACHMENT_DIR):
            os.makedirs(self.ATTACHMENT_DIR)

    @classmethod
    def from_env(cls) -> 'Config':
        """Create configuration from environment variables"""
        config = cls()
        return config