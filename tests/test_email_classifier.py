import unittest
from email_classifier import EmailClassifier, EmailClassification
from config import Config
import os
from unittest.mock import patch, MagicMock

class TestEmailClassifier(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        if not os.getenv('OPENAI_API_KEY'):
            os.environ['OPENAI_API_KEY'] = 'test_key'
        
        # Setup test configuration
        os.environ['EMAIL_CATEGORIES__CRITICAL__TARGET_EMAILS'] = 'urgent@test.com'
        os.environ['EMAIL_CATEGORIES__PROJECTS__TARGET_EMAILS__ATLAS'] = 'atlas-team@test.com'
        
        self.classifier = EmailClassifier()
        
        # Test email samples
        self.test_emails = {
            'sales': {
                'subject': 'Product Inquiry',
                'body': 'I would like to get pricing information for your enterprise package.'
            },
            'urgent': {
                'subject': 'URGENT: System Down',
                'body': 'The production system is down. Immediate assistance required.'
            },
            'project': {
                'subject': 'Project Phoenix Update',
                'body': 'Here are the latest updates for Project Phoenix sprint.'
            },
            'multi_category': {
                'subject': 'Urgent Invoice Issue - Project Atlas',
                'body': 'We have an urgent payment processing issue for Project Atlas.'
            }
        }

    def test_system_prompt_generation(self):
        """Test system prompt generation"""
        prompt = self.classifier._generate_system_prompt()
        
        # Check for key components
        self.assertIn("expert email classifier", prompt.lower())
        self.assertIn("priority", prompt.lower())
        self.assertIn("project names", prompt.lower())
        
        # Check for configured categories
        for category in self.classifier.config.EMAIL_CATEGORIES:
            self.assertIn(category, prompt.lower())

    @patch('openai.OpenAI')
    def test_sales_email_classification(self, mock_openai):
        """Test classification of sales email"""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '''
        {
            "categories": ["sales"],
            "priority": "normal",
            "project_names": [],
            "key_points": ["Enterprise package inquiry", "Pricing information needed"],
            "action_items": ["Send pricing details"]
        }
        '''
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        result = self.classifier.classify_email(
            self.test_emails['sales']['subject'],
            self.test_emails['sales']['body']
        )
        
        self.assertIn('sales', result.categories)
        self.assertEqual(result.priority, 'normal')
        self.assertEqual(len(result.project_names), 0)

    @patch('openai.OpenAI')
    def test_urgent_email_classification(self, mock_openai):
        """Test classification of urgent email"""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '''
        {
            "categories": ["critical"],
            "priority": "urgent",
            "project_names": [],
            "key_points": ["Production system down", "Immediate assistance needed"],
            "action_items": ["Restore system", "Investigate cause"]
        }
        '''
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        result = self.classifier.classify_email(
            self.test_emails['urgent']['subject'],
            self.test_emails['urgent']['body']
        )
        
        self.assertIn('critical', result.categories)
        self.assertEqual(result.priority, 'urgent')

    @patch('openai.OpenAI')
    def test_multi_category_classification(self, mock_openai):
        """Test classification of email with multiple categories"""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '''
        {
            "categories": ["accounts", "critical", "projects"],
            "priority": "urgent",
            "project_names": ["Project Atlas", "Atlas"],
            "key_points": ["Payment processing issue", "Project Atlas affected"],
            "action_items": ["Resolve payment issue", "Update project team"]
        }
        '''
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        result = self.classifier.classify_email(
            self.test_emails['multi_category']['subject'],
            self.test_emails['multi_category']['body']
        )
        
        self.assertTrue(len(result.categories) > 1)
        self.assertEqual(result.priority, 'urgent')
        self.assertTrue(
            any('atlas' in name.lower() for name in result.project_names),
            "Expected 'Atlas' in project names"
        )

    def test_target_email_resolution(self):
        """Test getting target emails based on classification"""
        # Create a classification with known configured categories
        classification = EmailClassification(
            categories=['critical', 'projects'],
            priority='urgent',
            project_names=['Atlas', 'Project Atlas'],  # Include both formats
            key_points=['Urgent issue'],
            action_items=['Resolve immediately']
        )
        
        targets = self.classifier.get_target_emails(classification)
        
        # Verify we get targets for both categories
        self.assertTrue(len(targets) > 0, "No target emails found")
        
        # Check if we got the expected target emails
        target_emails = {t['email'] for t in targets}
        self.assertIn('urgent@test.com', target_emails, "Critical team email not found")
        self.assertIn('atlas-team@test.com', target_emails, "Project team email not found")
        
        # Check priority is preserved
        for target in targets:
            self.assertEqual(target['priority'], 'urgent')

    def test_important_marking(self):
        """Test conditions for marking email as important"""
        # Test urgent priority
        classification = EmailClassification(
            categories=['sales'],
            priority='urgent'
        )
        self.assertTrue(self.classifier.should_mark_important(classification))
        
        # Test critical category
        classification = EmailClassification(
            categories=['critical'],
            priority='normal'
        )
        self.assertTrue(self.classifier.should_mark_important(classification))
        
        # Test normal case
        classification = EmailClassification(
            categories=['sales'],
            priority='normal'
        )
        self.assertFalse(self.classifier.should_mark_important(classification))

if __name__ == '__main__':
    unittest.main()
