import os
import logging
from typing import List, Dict, Any
from pydantic import BaseModel
from openai import OpenAI
from config import Config

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
        self.model = os.getenv("OPENAI_MODEL", "gpt-4")
        
        # Create category mapping for classification
        self.category_mapping = {}
        for category, config in self.config.EMAIL_CATEGORIES.items():
            for keyword in config['keywords']:
                self.category_mapping[keyword] = category

    def _generate_system_prompt(self) -> str:
        """Generate the system prompt based on configuration"""
        # Only include enabled categories
        enabled_categories = {
            cat: conf for cat, conf in self.config.EMAIL_CATEGORIES.items() 
            if conf.get('enabled', True)
        }
        
        categories = list(enabled_categories.keys())
        keywords = [kw for cat in enabled_categories.values() for kw in cat['keywords']]
        
        return f"""You are an expert email classifier. Analyze the email and:
1. Identify relevant categories from: {', '.join(categories)}
2. Look for keywords: {', '.join(keywords)}
3. Determine priority (normal/high/urgent/low) based on content urgency
4. Extract any project names mentioned
5. Identify if the email appears to be spam or a sales pitch
6. Determine if this is an alert requiring attention or just a notification
7. List key points and required actions

Respond with a JSON object containing:
- categories: List of identified categories
- priority: Priority level (normal/high/urgent/low)
- project_names: List of project names found
- key_points: List of important points from the email
- action_items: List of actions required
- spam: Whether the email appears to be spam
- sales_pitch: Whether the email appears to be a sales pitch
- alert: Whether the email is an alert requiring attention

For spam detection, look for:
- Unsolicited offers
- Too-good-to-be-true promises
- Urgency to act
- Requests for sensitive information
- Poor grammar or formatting
- Unknown or suspicious senders

For sales pitches, identify:
- Product or service offerings
- Promotional language
- Special deals or discounts
- Marketing content

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

    def classify_email(self, subject: str, body: str) -> EmailClassification:
        """
        Classify email content and determine routing.
        
        Args:
            subject: Email subject
            body: Email body
            
        Returns:
            EmailClassification object with categories and priority
        """
        try:
            # Combine subject and body for analysis
            email_content = f"Subject: {subject}\n\nBody: {body}"
            
            # Get classification from OpenAI
            completion = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._generate_system_prompt()},
                    {"role": "user", "content": email_content}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )

            # Parse response
            result = completion.choices[0].message.content
            self.logger.info(f"Classification result: {result}")
            
            # Create classification object
            classification = EmailClassification.model_validate_json(result)
            
            # Validate categories against configuration
            enabled_categories = {
                cat: conf for cat, conf in self.config.EMAIL_CATEGORIES.items() 
                if conf.get('enabled', True)
            }
            valid_categories = [
                cat for cat in classification.categories 
                if cat in enabled_categories
            ]
            classification.categories = valid_categories
            
            # Ensure valid priority
            if classification.priority not in {'normal', 'high', 'urgent', 'low'}:
                classification.priority = 'normal'
            
            return classification

        except Exception as e:
            self.logger.error(f"Error classifying email: {str(e)}")
            return EmailClassification()

    def get_target_emails(self, classification: EmailClassification) -> List[Dict[str, Any]]:
        """
        Get target email addresses based on classification.
        
        Args:
            classification: EmailClassification object
            
        Returns:
            List of dicts with email and priority
        """
        targets = []
        
        # Only process enabled categories
        enabled_categories = {
            cat: conf for cat, conf in self.config.EMAIL_CATEGORIES.items() 
            if conf.get('enabled', True)
        }
        
        # Add category-specific targets for enabled categories
        for category in classification.categories:
            if category in enabled_categories:
                cat_config = enabled_categories[category]
                
                # Handle project-specific routing
                if category == 'projects':
                    normalized_config_projects = {
                        self._normalize_project_name(p): emails 
                        for p, emails in cat_config['target_emails'].items()
                    }
                    
                    # First try project-specific routing
                    project_matched = False
                    for project in classification.project_names:
                        normalized_project = self._normalize_project_name(project)
                        if normalized_project in normalized_config_projects:
                            project_matched = True
                            for email in normalized_config_projects[normalized_project]:
                                targets.append({
                                    'email': email,
                                    'priority': classification.priority
                                })
                    
                    # If no project matches, use default routing
                    if not project_matched and 'default' in cat_config['target_emails']:
                        for email in cat_config['target_emails']['default']:
                            targets.append({
                                'email': email,
                                'priority': classification.priority
                            })
                else:
                    # Handle non-project categories
                    target_emails = cat_config.get('target_emails', [])
                    if isinstance(target_emails, list):
                        for email in target_emails:
                            targets.append({
                                'email': email,
                                'priority': classification.priority
                            })
                    elif isinstance(target_emails, str):
                        targets.append({
                            'email': target_emails,
                            'priority': classification.priority
                        })
                    elif isinstance(target_emails, dict):
                        # Handle dictionary of target emails (e.g., for subcategories)
                        for emails in target_emails.values():
                            if isinstance(emails, list):
                                for email in emails:
                                    targets.append({
                                        'email': email,
                                        'priority': classification.priority
                                    })
                            elif isinstance(emails, str):
                                targets.append({
                                    'email': emails,
                                    'priority': classification.priority
                                })
        
        # Remove duplicates while preserving order
        seen = set()
        unique_targets = []
        for target in targets:
            if target['email'] not in seen:
                seen.add(target['email'])
                unique_targets.append(target)
        
        return unique_targets

    def should_mark_important(self, classification: EmailClassification) -> bool:
        """Determine if email should be marked as important"""
        return (
            classification.priority in {'high', 'urgent'} or
            'critical' in classification.categories or
            classification.alert
        )
