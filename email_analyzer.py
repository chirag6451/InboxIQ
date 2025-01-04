import json
from typing import Dict, Any, Optional, List, Tuple
from openai import OpenAI
import logging
from config import Config
from utils import rate_limit
import os
from dotenv import load_dotenv

# Load environment variables at module level
load_dotenv(override=True)

class EmailAnalyzer:
    """Analyzes email content to categorize and route to appropriate teams."""

    def __init__(self):
        """Initialize the EmailAnalyzer with OpenAI client and logging."""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
            
        self.client = OpenAI(api_key=api_key)
        self.logger = logging.getLogger(__name__)
        self.model = "gpt-4o"
        self.config = Config()

    def _generate_system_prompt(self) -> str:
        """Generate system prompt based on configured categories"""
        # Build category descriptions from config
        category_descriptions = []
        for cat_name, cat_config in self.config.EMAIL_CATEGORIES.items():
            keywords = ', '.join(cat_config['keywords'])
            priority = cat_config['priority']
            # Use lowercase for category names in prompt
            desc = f"- {cat_name.lower()}: Emails containing keywords [{keywords}]. Default priority: {priority}"
            category_descriptions.append(desc)
            
        categories_text = '\n'.join(category_descriptions)
        
        return f"""You are an expert email analyzer. Your task is to:
1. Analyze the email content and determine the most appropriate category(s) based on configured keywords and context
2. Extract key information relevant to those categories
3. Determine the priority level based on content urgency and importance
4. Identify any project names or codes mentioned

Configured Categories:
{categories_text}

Priority Levels:
- normal: Regular business communication, no immediate action needed
- high: Important matters requiring attention within 24 hours
- urgent: Critical issues requiring immediate attention

IMPORTANT: Always return category names in lowercase.

Respond with a JSON object in this exact format:
{{
    "categories": [
        {{
            "name": string,  # Category name from configured categories (in lowercase)
            "confidence": float,  # Scale of 0-1
            "priority": string,  # normal/high/urgent (consider default category priority)
            "extracted_data": {{
                "key_points": array,  # List of important points
                "action_items": array,  # List of required actions
                "entities": object,  # Named entities (people, companies, products)
                "project_names": array,  # Any project names/codes mentioned
                "deadlines": array,  # Any mentioned deadlines or important dates
                "category_specific": object  # Category-specific extracted data
            }}
        }}
    ],
    "summary": string,  # Brief summary of the email
    "overall_priority": string  # normal/high/urgent (highest priority among categories)
}}"""

    def analyze_email(self, subject: str, body: str) -> Dict[str, Any]:
        """
        Analyze email content to determine category and extract relevant information.
        
        Args:
            subject: Email subject line
            body: Email body text
            
        Returns:
            Dict containing analysis results including categories, priority, and extracted data
        """
        try:
            self.logger.info(f"Analyzing email with subject: {subject[:100]}...")

            # Generate prompt based on current configuration
            system_prompt = self._generate_system_prompt()

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": f"Subject: {subject}\n\nBody: {body}"
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )

            result = json.loads(response.choices[0].message.content)
            
            # Validate categories against configuration and ensure lowercase names
            valid_categories = []
            for category in result['categories']:
                # Convert category name to lowercase
                category['name'] = category['name'].lower()
                if category['name'] in self.config.EMAIL_CATEGORIES:
                    valid_categories.append(category)
            
            result['categories'] = valid_categories
            self.logger.info(f"Analysis complete. Categories: {[c['name'] for c in result['categories']]}")
            return result

        except Exception as e:
            self.logger.error(f"Error analyzing email: {str(e)}")
            return {
                "categories": [],
                "summary": "Error analyzing email",
                "overall_priority": "normal"
            }

    def get_target_emails(self, analysis_result: Dict[str, Any]) -> List[Tuple[str, str]]:
        """
        Get target email addresses for forwarding based on analysis results.
        
        Returns:
            List of tuples containing (email, priority)
        """
        target_emails = []
        
        for category in analysis_result['categories']:
            cat_name = category['name']
            priority = category['priority']
            
            if cat_name == 'projects':
                # Handle project-specific routing
                for project_name in category['extracted_data'].get('project_names', []):
                    if project_name in self.config.EMAIL_CATEGORIES['projects']['target_emails']:
                        project_emails = self.config.EMAIL_CATEGORIES['projects']['target_emails'][project_name]
                        target_emails.extend([(email, priority) for email in project_emails])
            else:
                # Handle other categories
                if cat_name in self.config.EMAIL_CATEGORIES:
                    cat_emails = self.config.EMAIL_CATEGORIES[cat_name]['target_emails']
                    target_emails.extend([(email, priority) for email in cat_emails])

        return list(set(target_emails))  # Remove duplicates while preserving priority

    def should_mark_important(self, analysis_result: Dict[str, Any]) -> bool:
        """Determine if the email should be marked as important."""
        return (
            analysis_result['overall_priority'] in ['high', 'urgent'] or
            any(cat['name'] == 'critical' for cat in analysis_result['categories'])
        )
