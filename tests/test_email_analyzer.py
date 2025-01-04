import unittest
from email_analyzer import EmailAnalyzer
from config import Config
import os
import json
from unittest.mock import patch, MagicMock

class TestEmailAnalyzer(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        # Ensure OPENAI_API_KEY is set for testing
        if not os.getenv('OPENAI_API_KEY'):
            os.environ['OPENAI_API_KEY'] = 'test_key'
        
        self.analyzer = EmailAnalyzer()
        
        # Test email samples
        self.sales_email = {
            'subject': 'Product Inquiry: Enterprise Package Pricing',
            'body': '''
            Hello,
            
            I'm interested in your enterprise software package. Could you please send me 
            pricing information and available features? We are a company of 500 employees 
            looking to implement this in Q2.
            
            Best regards,
            John Smith
            '''
        }
        
        self.urgent_support_email = {
            'subject': 'URGENT: System Down - Production Issue',
            'body': '''
            Critical Alert!
            
            The production system is down and affecting all users. This is causing 
            significant business impact. Immediate assistance required.
            
            Error details:
            - Service: Main API
            - Time: 10:30 AM EST
            - Impact: All users affected
            
            Please escalate and resolve ASAP.
            
            Thanks,
            Operations Team
            '''
        }
        
        self.project_email = {
            'subject': 'Project Phoenix: Sprint Review Updates',
            'body': '''
            Hi Team,
            
            Here are the updates from Project Phoenix sprint review:
            
            1. Milestone 1 completed
            2. New requirements added for payment integration
            3. Next sprint planning scheduled for Friday
            
            Please review and provide feedback.
            
            Regards,
            Project Manager
            '''
        }
        
        self.multi_category_email = {
            'subject': 'Urgent: Invoice Payment Issue for Project Atlas',
            'body': '''
            Hello Accounts Team,
            
            We have an urgent issue with the payment processing for Project Atlas.
            The client is reporting that their last invoice payment failed, and this
            is blocking their access to critical features.
            
            This needs immediate attention as it's affecting project deliverables.
            
            Invoice Details:
            - Invoice #: INV-2025-001
            - Amount: $50,000
            - Due Date: Overdue by 5 days
            
            Please help resolve this ASAP.
            
            Best regards,
            Account Manager
            '''
        }

    def test_prompt_generation(self):
        """Test if the system prompt is generated correctly based on config"""
        prompt = self.analyzer._generate_system_prompt()
        
        # Check if prompt contains all configured categories in lowercase
        for category in self.analyzer.config.EMAIL_CATEGORIES:
            self.assertIn(category.lower(), prompt)
            
        # Check if prompt contains priority levels
        self.assertIn("normal:", prompt)
        self.assertIn("high:", prompt)
        self.assertIn("urgent:", prompt)
        
        # Check if prompt includes the lowercase instruction
        self.assertIn("Always return category names in lowercase", prompt)

    @patch('openai.OpenAI')
    def test_sales_email_analysis(self, mock_openai):
        """Test analysis of a sales inquiry email"""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps({
            "categories": [{
                "name": "sales",
                "confidence": 0.95,
                "priority": "normal",
                "extracted_data": {
                    "key_points": ["Enterprise package inquiry", "500 employees", "Q2 implementation"],
                    "action_items": ["Send pricing information", "Provide feature list"],
                    "entities": {"company_size": "500", "timeline": "Q2"},
                    "project_names": [],
                    "deadlines": [],
                    "category_specific": {"product": "enterprise software package"}
                }
            }],
            "summary": "Enterprise software package pricing inquiry for 500-employee company",
            "overall_priority": "normal"
        })
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        result = self.analyzer.analyze_email(
            self.sales_email['subject'],
            self.sales_email['body']
        )
        
        self.assertEqual(len(result['categories']), 1)
        self.assertEqual(result['categories'][0]['name'], 'sales')
        self.assertEqual(result['overall_priority'], 'normal')

    @patch('openai.OpenAI')
    def test_urgent_support_email_analysis(self, mock_openai):
        """Test analysis of an urgent support email"""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps({
            "categories": [{
                "name": "critical",
                "confidence": 0.98,
                "priority": "urgent",
                "extracted_data": {
                    "key_points": ["Production system down", "All users affected"],
                    "action_items": ["Immediate resolution required", "Escalate issue"],
                    "entities": {"service": "Main API"},
                    "project_names": [],
                    "deadlines": [],
                    "category_specific": {"impact": "all users", "system": "production"}
                }
            }],
            "summary": "Critical production system outage affecting all users",
            "overall_priority": "urgent"
        })
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        result = self.analyzer.analyze_email(
            self.urgent_support_email['subject'],
            self.urgent_support_email['body']
        )
        
        self.assertTrue(any(c['name'] == 'critical' for c in result['categories']))
        self.assertEqual(result['overall_priority'], 'urgent')

    @patch('openai.OpenAI')
    def test_multi_category_email_analysis(self, mock_openai):
        """Test analysis of an email that fits multiple categories"""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps({
            "categories": [
                {
                    "name": "accounts",
                    "confidence": 0.9,
                    "priority": "high",
                    "extracted_data": {
                        "key_points": ["Invoice payment failed", "Overdue payment"],
                        "action_items": ["Process payment", "Restore access"],
                        "entities": {"invoice": "INV-2025-001", "amount": "$50,000"},
                        "project_names": ["Atlas"],
                        "deadlines": ["Overdue by 5 days"],
                        "category_specific": {"invoice_number": "INV-2025-001"}
                    }
                },
                {
                    "name": "critical",
                    "confidence": 0.85,
                    "priority": "urgent",
                    "extracted_data": {
                        "key_points": ["Blocking access to features", "Affecting deliverables"],
                        "action_items": ["Immediate resolution needed"],
                        "entities": {},
                        "project_names": ["Atlas"],
                        "deadlines": [],
                        "category_specific": {}
                    }
                }
            ],
            "summary": "Urgent invoice payment issue blocking Project Atlas access",
            "overall_priority": "urgent"
        })
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        result = self.analyzer.analyze_email(
            self.multi_category_email['subject'],
            self.multi_category_email['body']
        )
        
        self.assertGreaterEqual(len(result['categories']), 2)
        categories = {c['name'] for c in result['categories']}
        self.assertTrue('accounts' in categories)
        self.assertTrue('critical' in categories)
        self.assertEqual(result['overall_priority'], 'urgent')

if __name__ == '__main__':
    unittest.main()
