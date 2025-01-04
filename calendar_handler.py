from datetime import datetime, timedelta
import logging
from typing import Dict, Any, Optional, Union
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.credentials import Credentials as BaseCredentials

class CalendarHandler:
    """Handles Google Calendar operations for email reminders"""
    
    def __init__(self, credentials: Union[Credentials, BaseCredentials]):
        """Initialize the calendar handler with Google credentials"""
        self.service = build('calendar', 'v3', credentials=credentials)
        self.logger = logging.getLogger(__name__)

    def create_reminder(self, email_data: Dict[str, Any], category: str, calendar_settings: Dict[str, Any]) -> Optional[str]:
        """Create a calendar reminder for an email"""
        try:
            # Extract email details
            subject = email_data.get('subject', 'No Subject')
            sender = email_data.get('sender', 'Unknown')
            body = email_data.get('body', '')
            
            # Get AI analysis
            ai_analysis = email_data.get('ai_analysis', {})
            action_items = ai_analysis.get('action_items', [])
            key_points = ai_analysis.get('key_points', [])
            priority = ai_analysis.get('priority', 'normal')
            
            # Only create reminder if there are action items
            if not action_items:
                return None

            # Format event description
            description = f"""
Email Details:
From: {sender}
Subject: {subject}

Priority: {priority.upper()}

Action Items Required:
{chr(10).join(f'• {item}' for item in action_items)}

Key Points:
{chr(10).join(f'• {point}' for point in key_points)}

Original Email Preview:
{body[:500]}{'...' if len(body) > 500 else ''}
"""

            # Set event time (default to now + advance time)
            start_time = datetime.now() + timedelta(minutes=calendar_settings.get('reminder_advance', 30))
            end_time = start_time + timedelta(minutes=calendar_settings.get('default_duration', 30))

            event = {
                'summary': f"[{category.upper()}] {subject} - Action Required",
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'Asia/Kolkata',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'Asia/Kolkata',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': calendar_settings.get('reminder_advance', 30)}
                    ]
                }
            }

            # Set color if specified
            if 'color' in calendar_settings:
                event['colorId'] = self._get_color_id(calendar_settings['color'])

            # Create the event
            created_event = self.service.events().insert(calendarId='primary', body=event).execute()
            event_id = created_event.get('id')
            
            if event_id:
                self.logger.info(f"Created calendar event: {self.get_event_link(event_id)}")
                return event_id
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error creating calendar reminder: {str(e)}")
            return None

    def get_event_link(self, event_id: str) -> str:
        """Get the Google Calendar link for an event"""
        return f"https://www.google.com/calendar/event?eid={event_id}"

    def _format_action_items(self, action_items: list) -> str:
        """Format action items for calendar event description"""
        if not action_items:
            return "No specific action items identified."
        
        return "\n".join(f"- {item}" for item in action_items)

    def _get_color_id(self, color: str) -> str:
        """Convert color name to Google Calendar color ID"""
        color_map = {
            'red': '11',      # Tomato red
            'orange': '6',    # Tangerine
            'yellow': '5',    # Banana yellow
            'green': '10',    # Sage green
            'blue': '1',      # Lavender
            'purple': '3',    # Grape purple
        }
        return color_map.get(color.lower(), '1')  # Default to blue
