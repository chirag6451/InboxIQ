import unittest
from unittest.mock import patch, MagicMock
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gmail_auth import GmailAuthenticator

class TestGmailAuthenticator(unittest.TestCase):
    def setUp(self):
        self.scopes = ['https://www.googleapis.com/auth/gmail.readonly']
        self.authenticator = GmailAuthenticator(self.scopes)

    @patch('gmail_auth.Flow')
    def test_get_authorization_url(self, mock_flow):
        # Setup mock
        mock_flow_instance = MagicMock()
        mock_flow_instance.authorization_url.return_value = ('http://test-auth-url', 'test-state')
        mock_flow.from_client_config.return_value = mock_flow_instance

        # Test
        with patch.dict('os.environ', {'FLASK_SECRET_KEY': 'test-key'}):
            auth_url = self.authenticator.get_authorization_url()

        # Assert
        self.assertEqual(auth_url, 'http://test-auth-url')
        mock_flow.from_client_config.assert_called_once()

if __name__ == '__main__':
    unittest.main()
