import tempfile
import unittest
from pathlib import Path

from ibind.oauth.oauth1a import OAuth1aConfig


class TestOAuth1aConfigU(unittest.TestCase):
    def setUp(self):
        self.valid_config = OAuth1aConfig(
            oauth_rest_url='https://api.ibkr.com',
            live_session_token_endpoint='/v1/api/oauth/live_session_token',  # noqa: S106
            access_token='test_access_token',  # noqa: S106
            access_token_secret='test_access_token_secret',  # noqa: S106
            consumer_key='test_consumer_key',
            dh_prime='test_dh_prime',
            encryption_key_fp='/tmp/encryption_key.pem',  # noqa: S108
            signature_key_fp='/tmp/signature_key.pem',  # noqa: S108
        )

    def test_version_returns_1_0a(self):
        config = OAuth1aConfig()
        self.assertEqual(config.version(), '1.0a')

    def test_verify_config_success_with_valid_params(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as enc_file, tempfile.NamedTemporaryFile(mode='w', delete=False) as sig_file:
            enc_file.write('dummy key content')
            sig_file.write('dummy key content')
            enc_file.flush()
            sig_file.flush()

            config = OAuth1aConfig(
                oauth_rest_url='https://api.ibkr.com',
                live_session_token_endpoint='/v1/api/oauth/live_session_token',  # noqa: S106
                access_token='test_access_token',  # noqa: S106
                access_token_secret='test_access_token_secret',  # noqa: S106
                consumer_key='test_consumer_key',
                dh_prime='test_dh_prime',
                encryption_key_fp=enc_file.name,
                signature_key_fp=sig_file.name,
            )

            config.verify_config()

            Path(enc_file.name).unlink()
            Path(sig_file.name).unlink()

    def test_verify_config_missing_required_params(self):
        config = OAuth1aConfig()

        with self.assertRaises(ValueError) as context:
            config.verify_config()

        error_message = str(context.exception)
        self.assertIn('OAuth1aConfig is missing required parameters:', error_message)
        # Check that some expected None parameters are mentioned
        expected_missing = ['access_token', 'access_token_secret', 'consumer_key', 'dh_prime']
        for param in expected_missing:
            self.assertIn(param, error_message)

    def test_verify_config_partial_missing_params(self):
        config = OAuth1aConfig(
            access_token='test_access_token',  # noqa: S106
            consumer_key='test_consumer_key',
        )

        with self.assertRaises(ValueError) as context:
            config.verify_config()

        error_message = str(context.exception)
        self.assertIn('OAuth1aConfig is missing required parameters:', error_message)
        # Should not contain the provided parameters (using word boundaries)
        import re

        self.assertIsNone(re.search(r'\baccess_token\b', error_message))
        self.assertNotIn('consumer_key', error_message)
        # Should contain missing parameters
        self.assertIn('access_token_secret', error_message)
        self.assertIn('dh_prime', error_message)

    def test_verify_config_missing_filepaths(self):
        config = OAuth1aConfig(
            oauth_rest_url='https://api.ibkr.com',
            live_session_token_endpoint='/v1/api/oauth/live_session_token',  # noqa: S106
            access_token='test_access_token',  # noqa: S106
            access_token_secret='test_access_token_secret',  # noqa: S106
            consumer_key='test_consumer_key',
            dh_prime='test_dh_prime',
            encryption_key_fp='/nonexistent/encryption_key.pem',
            signature_key_fp='/nonexistent/signature_key.pem',
        )

        with self.assertRaises(ValueError) as context:
            config.verify_config()

        error_message = str(context.exception)
        self.assertIn("OAuth1aConfig's filepaths don't exist:", error_message)
        self.assertIn('encryption_key_fp', error_message)
        self.assertIn('signature_key_fp', error_message)

    def test_verify_config_partial_missing_filepaths(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as enc_file:
            enc_file.write('dummy key content')
            enc_file.flush()

            config = OAuth1aConfig(
                oauth_rest_url='https://api.ibkr.com',
                live_session_token_endpoint='/v1/api/oauth/live_session_token',  # noqa: S106
                access_token='test_access_token',  # noqa: S106
                access_token_secret='test_access_token_secret',  # noqa: S106
                consumer_key='test_consumer_key',
                dh_prime='test_dh_prime',
                encryption_key_fp=enc_file.name,
                signature_key_fp='/nonexistent/signature_key.pem',
            )

            with self.assertRaises(ValueError) as context:
                config.verify_config()

            error_message = str(context.exception)
            self.assertIn("OAuth1aConfig's filepaths don't exist:", error_message)
            self.assertNotIn('encryption_key_fp', error_message)
            self.assertIn('signature_key_fp', error_message)

            Path(enc_file.name).unlink()
