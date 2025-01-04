import os
import logging
from typing import List, Dict, Any
from pydantic import BaseModel
from openai import OpenAI
from config import Config
import json

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class EmailClassification(BaseModel):
    """Email classification with priority and routing information"""
    categories: List[str] = []
    priority: str = "normal"
    project_names: List[str] = []
    key_points: List[str] = []
    action_items: List[str] = []
    spam: bool = False
    sales_pitch: bool = False
    alert: bool = False

class EmailClassifier:
    """Classifies emails using OpenAI and handles routing based on configuration"""
    
    def __init__(self, config: Config = None):
        """
        Initialize EmailClassifier with optional config
        
        Args:
            config: Optional Config instance. If not provided, loads from environment.
        """
        self.config = config or Config.from_env()
        self.logger = logging.getLogger(__name__)
        self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

    def _generate_system_prompt(self) -> str:
        """Generate the system prompt based on configuration"""
        # Only include enabled categories
        enabled_categories = {
            cat: conf for cat, conf in self.config.EMAIL_CATEGORIES.items() 
            if conf.get('enabled', True)
        }
        
        categories = list(enabled_categories.keys())
        
        return f"""You are an expert email classifier. Analyze the email and:
1. Identify relevant categories from: {', '.join(categories)}
2. Determine priority (normal/high/urgent/low) based on content urgency
3. Identify if the email appears to be spam or a sales pitch
4. Determine if this is an alert requiring attention or just a notification
5. List key points and required actions

Respond with a JSON object containing:
- categories: List of identified categories
- priority: Priority level (normal/high/urgent/low)
- key_points: List of important points from the email
- action_items: List of actions required
- spam: Whether the email appears to be spam
- alert: Whether the email is an alert requiring attention

For spam detection, look for:
- Unsolicited offers
- Too-good-to-be-true promises
- Urgency to act
- Requests for sensitive information
- Poor grammar or formatting
- Unknown or suspicious senders

For alerts vs notifications:
- Alerts: Require immediate attention or action
- Notifications: Informational updates only
"""

    def _normalize_project_name(self, name: str) -> str:
        """Normalize project name for comparison"""
        # Remove common prefixes and convert to lowercase
        normalized = name.lower()
        prefixes = ['project ', 'proj ', 'prj ']
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
        return normalized

    def classify_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Classify email using OpenAI API"""
        try:
            prompt = f"""
            Subject: {email_data['subject']}
            From: {email_data['sender']}
            Body: {email_data['body']}
            
            Please analyze this email and provide a JSON response with the following structure:
            {{
                "categories": ["work", "meeting", "deadline", "invoice", "report", "follow_up", "support", "project", "sales", "inquiry_lead", "personal"],
                "priority": "urgent/important/normal/low",
                "key_points": ["key point 1", "key point 2"],
                "action_items": ["action 1", "action 2"],
                "spam": true/false,
                "alert": true/false
            }}
            
            Priority Guidelines:
            - urgent: Time-sensitive matters requiring immediate attention (e.g., [URGENT] in subject, deadlines today)
            - important: Significant but not time-critical (e.g., [IMPORTANT] in subject, deadlines this week)
            - normal: Regular communications
            - low: Non-critical, can be handled later
            
            Note: Categories should match one or more from the list above. If [URGENT] or [IMPORTANT] is in the subject, set priority accordingly.
            """
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self._generate_system_prompt()},
                    {"role": "user", "content": prompt}
                ]
            )
            
            result = response.choices[0].message.content
            self.logger.info(f"Classification result: {result}")
            
            # Parse the JSON response
            if isinstance(result, str):
                result = json.loads(result)
            
            # Ensure required fields exist
            result.setdefault('categories', ['notification'])
            result.setdefault('priority', 'normal')
            result.setdefault('key_points', [])
            result.setdefault('action_items', [])
            result.setdefault('spam', False)
            result.setdefault('alert', False)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in email classification: {str(e)}")
            return {
                'categories': ['notification'],
                'priority': 'normal',
                'key_points': [],
                'action_items': [],
                'spam': False,
                'alert': False
            }

    def get_target_emails(self, classification: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get target email addresses based on classification"""
        targets = []
        
        # Get enabled categories
        enabled_categories = {
            cat: conf for cat, conf in self.config.EMAIL_CATEGORIES.items() 
            if conf.get('enabled', True)
        }
        
        # Add targets for each category
        for category in classification.get('categories', []):
            if category in enabled_categories:
                cat_config = enabled_categories[category]
                target_emails = cat_config.get('target_emails', [])
                
                for email in target_emails:
                    targets.append({
                        'email': email,
                        'priority': classification.get('priority', 'normal')
                    })
        
        # Remove duplicates while preserving order
        seen = set()
        unique_targets = []
        for target in targets:
            if target['email'] not in seen:
                seen.add(target['email'])
                unique_targets.append(target)
        
        return unique_targets

    def should_mark_important(self, classification: Dict[str, Any]) -> bool:
        """Determine if email should be marked as important"""
        return (
            classification['priority'] in {'high', 'urgent'} or
            'critical' in classification['categories'] or
            classification['alert']
        )
