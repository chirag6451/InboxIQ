import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
from tabulate import tabulate

class ReportGenerator:
    def __init__(self, summary: Dict[str, Any]):
        """Initialize report generator with summary data"""
        self.summary = summary

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

    def create_report_email(self) -> Dict[str, str]:
        """Create email content for the report"""
        report_text = self.generate_text_report()
        
        return {
            'subject': f"Email Processing Report - {datetime.now().strftime('%Y-%m-%d')}",
            'body': report_text
        }
