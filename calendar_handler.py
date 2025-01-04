from datetime import datetime, timedelta, time
import logging
from typing import Dict, Any, Optional, Union
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.credentials import Credentials as BaseCredentials
import base64

class CalendarHandler:
    """Handles Google Calendar operations for email reminders"""
    
    def __init__(self, credentials: Union[Credentials, BaseCredentials], config):
        """Initialize the calendar handler with Google credentials and config"""
        self.service = build('calendar', 'v3', credentials=credentials)
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.current_slot = None
        
    def _parse_time(self, time_str: str) -> time:
        """Parse time string in HH:MM format"""
        hour, minute = map(int, time_str.split(':'))
        return time(hour=hour, minute=minute)
        
    def _get_next_available_slot(self) -> datetime:
        """Get the next available time slot based on configuration"""
        settings = self.config.CALENDER_REMINDER_SETTINGS
        start_time = self._parse_time(settings['start_time'])
        end_time = self._parse_time(settings['end_time'])
        slot_duration = settings['reminder_slot_duration']
        
        now = datetime.now()
        current_time = now.time()
        
        # If slot_duration is 0, all reminders will be set at the same time
        if slot_duration == 0:
            # If current time is before start time, use start time
            if current_time < start_time:
                return datetime.combine(now.date(), start_time)
            # If current time is after end time, use start time of next day
            elif current_time > end_time:
                tomorrow = now.date() + timedelta(days=1)
                return datetime.combine(tomorrow, start_time)
            # Otherwise, use current time
            else:
                return now
        
        # If no current slot or it's a new day, start from the beginning
        if not self.current_slot or self.current_slot.date() != now.date():
            # If current time is before start time, use start time
            if current_time < start_time:
                self.current_slot = datetime.combine(now.date(), start_time)
            # If current time is after end time, use start time of next day
            elif current_time > end_time:
                tomorrow = now.date() + timedelta(days=1)
                self.current_slot = datetime.combine(tomorrow, start_time)
            # Otherwise, find the next available slot from current time
            else:
                minutes_since_start = (current_time.hour - start_time.hour) * 60 + (current_time.minute - start_time.minute)
                slots_to_skip = (minutes_since_start // slot_duration) + 1
                minutes_to_add = slots_to_skip * slot_duration
                self.current_slot = datetime.combine(now.date(), start_time) + timedelta(minutes=minutes_to_add)
        else:
            # Move to next slot
            self.current_slot += timedelta(minutes=slot_duration)
            
            # If next slot is past end time, move to next day
            if self.current_slot.time() > end_time:
                next_day = self.current_slot.date() + timedelta(days=1)
                self.current_slot = datetime.combine(next_day, start_time)
        
        return self.current_slot

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
            
            # Check if we should create an event based on category and priority
            if not self._should_create_event(category, priority, calendar_settings):
                self.logger.info(f"Skipping calendar event for {category} email with {priority} priority")
                return None
            
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
            # Get reminder settings
            settings = self.config.CALENDER_REMINDER_SETTINGS
            
            # Get next available slot
            start_time = self._get_next_available_slot()
            end_time = start_time + timedelta(minutes=settings['default_duration'])

            event = {
                'summary': f"[{category.upper()}] {subject}",
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': calendar_settings.get('timezone', 'Asia/Kolkata'),
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': calendar_settings.get('timezone', 'Asia/Kolkata'),
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': settings['reminder_advance']}
                    ]
                }
            }

            # Set color from global settings
            event['colorId'] = self._get_color_id(settings['reminder_color'])

            # Create the event
            created_event = self.service.events().insert(calendarId='primary', body=event).execute()
            event_id = created_event.get('id')
            
            if event_id:
                self.logger.info(f"Created calendar event for {category} email with {priority} priority at {start_time}: {self.get_event_link(event_id)}")
                return event_id
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error creating calendar reminder: {str(e)}")
            return None

    def get_event_link(self, event_id: str) -> str:
        """Get the Google Calendar link for an event"""
        try:
            # Base64 encode the event ID
            encoded_id = base64.b64encode(event_id.encode()).decode().rstrip('=')
            return f"https://calendar.google.com/calendar/r/event?eid={encoded_id}"
        except Exception as e:
            self.logger.error(f"Error generating calendar link: {str(e)}")
            return ""

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

    def _should_create_event(self, category: str, priority: str, calendar_settings: Dict[str, Any]) -> bool:
        """Check if an event should be created based on category and priority settings"""
        try:
            # First check if calendar creation is enabled
            if not calendar_settings.get('create_reminder', False):
                self.logger.debug(f"Calendar events disabled for category: {category}")
                return False
                
            # Get priority settings for the category
            category_priorities = calendar_settings.get('calendar_priorities', [])
            
            # If no specific priority settings, use default behavior (create for all)
            if not category_priorities:
                self.logger.debug(f"No priority settings for category {category}, using default behavior")
                return True
                
            # Check if the email's priority is in the allowed priorities for this category
            should_create = priority.lower() in [p.lower() for p in category_priorities]
            self.logger.debug(f"Category: {category}, Priority: {priority}, Should create event: {should_create}")
            return should_create
            
        except Exception as e:
            self.logger.error(f"Error checking event creation settings: {str(e)}")
            return False
