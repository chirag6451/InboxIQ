import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
from tabulate import tabulate
from config import Config
import logging

class ReportGenerator:
    def __init__(self, summary: Dict[str, Any]):
        """Initialize report generator with summary data"""
        self.summary = summary
        self.config = Config()
        self.logger = logging.getLogger(__name__)

    def generate_text_report(self) -> str:
        """Generate a text-based report"""
        report_sections = []
        
        # Header
        report_sections.extend([
            "Email Processing Report",
            "=====================",
            f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ])
        
        # Summary Statistics
        report_sections.extend([
            "Summary Statistics",
            "-----------------",
            f"Total Emails Processed: {self.summary['total_emails_processed']}",
            f"Emails Successfully Forwarded: {self.summary['emails_forwarded']}",
            ""
        ])
        
        # Category Statistics
        if self.summary['category_stats']:
            report_sections.extend([
                "Category Statistics",
                "------------------"
            ])
            for category, count in self.summary['category_stats'].items():
                report_sections.append(f"{category.title()}: {count} emails")
            report_sections.append("")
        
        # Detailed Email Summary
        if self.summary['forwarding_details']:
            report_sections.extend([
                "Email Summary",
                "------------"
            ])
            
            for detail in self.summary['forwarding_details']:
                report_sections.extend([
                    f"\nFrom: {detail['from']}",
                    f"Subject: {detail['subject']}",
                    f"Priority: {detail['priority'].upper()}",
                    f"Categories: {', '.join(detail['categories'])}",
                ])
                
                if detail.get('summary'):
                    report_sections.extend([
                        "Summary:",
                        f"  {detail['summary']}"
                    ])
                
                if detail.get('action_items'):
                    report_sections.extend([
                        "Action Items:",
                        *[f"  - {item}" for item in detail['action_items']]
                    ])
                report_sections.append("-" * 50)
            report_sections.append("")
        
        # Consolidated Action Items Section
        action_items = self.get_action_items_summary()
        if action_items:
            report_sections.extend([
                "Consolidated Action Items",
                "----------------------",
                "All action items across emails that require attention:",
                ""
            ])
            
            # Group action items by priority
            priority_order = {'urgent': 0, 'high': 1, 'normal': 2, 'low': 3}
            action_items.sort(key=lambda x: priority_order.get(x['priority'].lower(), 99))
            
            for item in action_items:
                report_sections.extend([
                    f"Priority: {item['priority'].upper()}",
                    f"From: {item['from']}",
                    f"Subject: {item['subject']}",
                    "Action Items:"
                ])
                for action in item['items']:
                    report_sections.append(f"  - {action}")
                report_sections.extend(["", "-" * 50, ""])
        
        return "\n".join(report_sections)

    def generate_html_report(self) -> str:
        """Generate an elegant HTML report"""
        # CSS styles for the report
        styles = """
            <style>
                body {
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 1000px;
                    margin: 0 auto;
                    padding: 20px;
                }
                .header {
                    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                }
                .section {
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .stats-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin-bottom: 20px;
                }
                .stat-card {
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 6px;
                    text-align: center;
                }
                .stat-number {
                    font-size: 24px;
                    font-weight: bold;
                    color: #1e3c72;
                }
                .stat-label {
                    color: #666;
                    font-size: 14px;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 20px;
                }
                th {
                    background: #f8f9fa;
                    padding: 12px;
                    text-align: left;
                    border-bottom: 2px solid #dee2e6;
                }
                td {
                    padding: 12px;
                    border-bottom: 1px solid #dee2e6;
                }
                .priority {
                    font-weight: bold;
                    padding: 4px 8px;
                    border-radius: 4px;
                }
                .priority-urgent { color: #dc3545; background: #ffe6e6; }
                .priority-high { color: #fd7e14; background: #fff3e6; }
                .priority-normal { color: #28a745; background: #e6ffe6; }
                .priority-low { color: #6c757d; background: #f8f9fa; }
                .email-card {
                    background: white;
                    padding: 15px;
                    border-radius: 6px;
                    margin-bottom: 15px;
                    border-left: 4px solid #1e3c72;
                }
                .action-item {
                    background: #fff3cd;
                    padding: 10px;
                    margin: 5px 0;
                    border-radius: 4px;
                }
                .badge {
                    display: inline-block;
                    padding: 4px 8px;
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: bold;
                    margin-right: 5px;
                }
                .badge-category {
                    background: #e7f5ff;
                    color: #1e3c72;
                }
                .badge-alert {
                    background: #ffe6e6;
                    color: #dc3545;
                }
                .badge-spam {
                    background: #f8f9fa;
                    color: #6c757d;
                }
                .badge-cc {
                    background: #e7f5ff;
                    color: #1e3c72;
                }
                .intro-message {
                    font-size: 16px;
                    line-height: 1.6;
                    margin-bottom: 30px;
                    padding: 20px;
                    background: #f8f9fa;
                    border-radius: 8px;
                    border-left: 4px solid #1e3c72;
                }
                .intro-message p {
                    margin: 0 0 15px 0;
                }
                .intro-message ul {
                    margin: 10px 0;
                    padding-left: 20px;
                }
                .intro-message li {
                    margin: 5px 0;
                }
                .intro-message strong {
                    color: #1e3c72;
                }
                .forwarded-to {
                    color: #666;
                    font-size: 14px;
                    margin-top: 10px;
                    padding-top: 10px;
                    border-top: 1px solid #dee2e6;
                }
            </style>
        """

        # Start building HTML content
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            styles,
            "</head>",
            "<body>",
            
            # Header
            '<div class="header">',
            f'<h1>Email Processing Report</h1>',
            f'<p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>',
            '</div>',
            
            # Summary Statistics
            '<div class="section">',
            '<h2>Summary Statistics</h2>',
            '<div class="stats-grid">',
            self._generate_stat_card("Total Emails", self.summary['total_emails_processed']),
            self._generate_stat_card("Emails Forwarded", self.summary['emails_forwarded']),
        ]

        # Add category statistics
        if self.summary['category_stats']:
            for category, count in self.summary['category_stats'].items():
                html_parts.append(self._generate_stat_card(category.title(), count))
        
        html_parts.extend([
            '</div>',  # Close stats-grid
            '</div>',  # Close section
            
            # Processed Emails Section
            '<div class="section">',
            '<h2>Processed Emails</h2>'
        ])

        # Add processed emails
        if self.summary['forwarding_details']:
            for detail in self.summary['forwarding_details']:
                html_parts.append(self._generate_email_card(detail))
        else:
            html_parts.append('<p>No emails processed in this session.</p>')

        # Add Action Items Section
        action_items = self.get_action_items_summary()
        if action_items:
            html_parts.extend([
                '<div class="section">',
                '<h2>Action Items</h2>'
            ])
            
            # Group action items by priority
            priority_order = {'urgent': 0, 'high': 1, 'normal': 2, 'low': 3}
            action_items.sort(key=lambda x: priority_order.get(x['priority'].lower(), 99))
            
            for item in action_items:
                html_parts.append(self._generate_action_card(item))
            
            html_parts.append('</div>')  # Close action items section

        # Add Forwarded Emails Summary Section
        html_parts.extend([
            '<div class="section">',
            '<h2>Forwarded Emails Summary</h2>',
            self._generate_forwarded_summary_table(),
            '</div>'
        ])

        # Close HTML
        html_parts.extend([
            '</div>',  # Close last section
            '</body>',
            '</html>'
        ])

        return '\n'.join(html_parts)

    def _generate_stat_card(self, label: str, value: int) -> str:
        """Generate HTML for a statistics card"""
        return f'''
            <div class="stat-card">
                <div class="stat-number">{value}</div>
                <div class="stat-label">{label}</div>
            </div>
        '''

    def _generate_email_card(self, detail: Dict[str, Any]) -> str:
        """Generate HTML for an email card"""
        priority_class = f"priority-{detail['priority'].lower()}"
        categories = ' '.join([
            f'<span class="badge badge-category">{cat}</span>'
            for cat in detail['categories']
        ])
        
        badges = []
        if detail.get('is_alert'):
            badges.append('<span class="badge badge-alert">Alert</span>')
        if detail.get('is_spam'):
            badges.append('<span class="badge badge-spam">Spam</span>')
        if detail.get('cc_recipient'):
            badges.append('<span class="badge badge-cc">CC\'d</span>')
        
        badges_html = ' '.join(badges)

        return f'''
            <div class="email-card">
                <h3>{detail['subject']}</h3>
                <p>From: {detail['from']}</p>
                <p>To: {detail.get('to', 'N/A')}</p>
                {f'<p>CC: {detail.get("cc", "N/A")}</p>' if detail.get('cc') else ''}
                <p>
                    <span class="priority {priority_class}">{detail['priority'].upper()}</span>
                    {categories}
                    {badges_html}
                </p>
                {self._generate_key_points(detail.get('key_points', []))}
                {self._generate_action_items(detail.get('action_items', []))}
                <p class="forwarded-to">Forwarded to: {detail['forwarded_to']}</p>
            </div>
        '''

    def _generate_key_points(self, points: List[str]) -> str:
        """Generate HTML for key points"""
        if not points:
            return ''
        return f'''
            <div class="key-points">
                <h4>Key Points</h4>
                <ul>
                    {''.join(f'<li>{point}</li>' for point in points)}
                </ul>
            </div>
        '''

    def _generate_action_items(self, items: List[str]) -> str:
        """Generate HTML for action items"""
        if not items:
            return ''
        return f'''
            <div class="action-items">
                <h4>Action Items</h4>
                {''.join(f'<div class="action-item">{item}</div>' for item in items)}
            </div>
        '''

    def _generate_action_card(self, item: Dict[str, Any]) -> str:
        """Generate HTML for an action item card"""
        priority_class = f"priority-{item['priority'].lower()}"
        return f'''
            <div class="email-card">
                <h3>{item['subject']}</h3>
                <p>From: {item['from']}</p>
                <p><span class="priority {priority_class}">{item['priority'].upper()}</span></p>
                <div class="action-items">
                    {''.join(f'<div class="action-item">{action}</div>' for action in item['items'])}
                </div>
            </div>
        '''

    def _generate_forwarded_summary_table(self) -> str:
        """Generate HTML table for forwarded emails summary"""
        if not self.summary['forwarding_details']:
            return '<p>No emails were forwarded in this session.</p>'
            
        rows = []
        for detail in self.summary['forwarding_details']:
            rows.append(f'''
                <tr>
                    <td>{detail['from']}</td>
                    <td>{detail['subject']}</td>
                    <td>{detail['forwarded_to']}</td>
                    <td><span class="priority {detail['priority'].lower()}">{detail['priority'].upper()}</span></td>
                </tr>
            ''')
            
        return f'''
            <table class="forwarded-table">
                <thead>
                    <tr>
                        <th>From</th>
                        <th>Subject</th>
                        <th>Forwarded To</th>
                        <th>Priority</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        '''

    def get_personalized_intro(self, openai_client) -> str:
        """Get personalized introduction from OpenAI"""
        # Prepare summary data
        total_emails = self.summary['total_emails_processed']
        forwarded = self.summary['emails_forwarded']
        categories = self.summary['category_stats']
        
        # Get urgent and high priority items
        urgent_items = []
        high_priority = []
        cc_emails = 0
        
        for detail in self.summary['forwarding_details']:
            if detail.get('cc_recipient'):
                cc_emails += 1
            if detail.get('action_items'):
                if detail['priority'].lower() == 'urgent':
                    urgent_items.extend(detail['action_items'])
                elif detail['priority'].lower() == 'high':
                    high_priority.extend(detail['action_items'])

        # Create summary for OpenAI
        summary = {
            'total_emails': total_emails,
            'forwarded_emails': forwarded,
            'cc_emails': cc_emails,
            'categories': categories,
            'urgent_items': urgent_items[:3],  # Top 3 urgent items
            'high_priority': high_priority[:3],  # Top 3 high priority items
            'time': datetime.now().strftime('%I:%M %p')
        }

        # Create prompt for OpenAI
        prompt = f"""
        Write a personalized HTML-formatted email introduction for {self.config.USER_DETAILS['name']}.
        
        User Details:
        - Name: {self.config.USER_DETAILS['name']}
        - Company: {self.config.USER_DETAILS['company']}
        - Position: {self.config.USER_DETAILS['position']}
        
        Email Summary:
        - Processed {summary['total_emails']} emails
        - Forwarded {summary['forwarded_emails']} emails
        - You were CC'd in {summary['cc_emails']} emails
        - Categories: {', '.join(f'{k}: {v}' for k, v in summary['categories'].items())}
        
        {'Urgent Items:' if urgent_items else ''}
        {chr(10).join(f'- {item}' for item in urgent_items)}
        
        {'High Priority Items:' if high_priority else ''}
        {chr(10).join(f'- {item}' for item in high_priority)}
        
        Instructions:
        1. Write in HTML format using paragraphs (<p>), line breaks (<br>), etc.
        2. Address the user by first name
        3. Mention the current time ({summary['time']})
        4. Highlight if they were CC'd in any emails
        5. Provide a brief overview of processed emails
        6. Emphasize urgent or important items if any
        7. Use a friendly, helpful tone
        8. Keep it concise (2-3 paragraphs)
        9. Use appropriate formatting for emphasis (<strong>, <em>, etc.)
        10. End with a professional sign-off
        """

        try:
            response = openai_client.chat.completions.create(
                model=os.getenv('OPENAI_MODEL', 'gpt-4'),
                messages=[{
                    'role': 'system',
                    'content': 'You are a professional AI email assistant writing a personalized HTML-formatted email summary. Use appropriate HTML tags for formatting.'
                }, {
                    'role': 'user',
                    'content': prompt
                }],
                temperature=0.7,
                max_tokens=400
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Error getting personalized intro: {str(e)}")
            return self._generate_fallback_intro()

    def create_report_email(self, openai_client) -> Dict[str, str]:
        """Create email content for the report"""
        html_content = self.generate_html_report()
        intro_message = self.get_personalized_intro(openai_client)
        
        # Combine intro and report
        full_html = f"""
        <div class="intro-message">
            {intro_message}
        </div>
        {html_content}
        """
        
        return {
            'subject': f"Email Processing Report - {datetime.now().strftime('%Y-%m-%d')}",
            'body': full_html
        }

    def get_action_items_summary(self) -> List[Dict[str, Any]]:
        """Get summary of action items"""
        action_items = []
        for detail in self.summary['forwarding_details']:
            if detail.get('action_items'):
                action_items.append({
                    'subject': detail['subject'],
                    'from': detail['from'],
                    'priority': detail['priority'],
                    'items': detail['action_items']
                })
        return action_items

    def _generate_fallback_intro(self) -> str:
        """Generate a fallback introduction if OpenAI fails"""
        name = self.config.USER_DETAILS['name']
        time = datetime.now().strftime('%I:%M %p')
        cc_count = sum(1 for detail in self.summary['forwarding_details'] if detail.get('cc_recipient'))
        
        cc_text = f"<strong>You were CC'd in {cc_count} emails.</strong>" if cc_count > 0 else ""
        
        return f"""
        <p>Dear {name},</p>

        <p>It's {time}, and I've completed scanning your emails. I've processed {self.summary['total_emails_processed']} emails 
        and forwarded {self.summary['emails_forwarded']} to relevant team members. {cc_text}</p>

        <p>Please find the detailed report below.</p>

        <p>Best regards,<br>
        Your AI Email Assistant</p>
        """
