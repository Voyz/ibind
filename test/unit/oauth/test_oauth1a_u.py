import re
import string
import time
import unittest
from unittest.mock import patch, mock_open

from ibind.oauth.oauth1a import (
    generate_request_timestamp,
    generate_oauth_nonce,
    generate_dh_random_bytes,
    generate_authorization_header_string,
    generate_base_string,
    read_private_key
)


class TestUtilityFunctionsU(unittest.TestCase):
    
    def test_generate_request_timestamp_returns_string(self):
        timestamp = generate_request_timestamp()
        self.assertIsInstance(timestamp, str)
        self.assertTrue(timestamp.isdigit())
        
    def test_generate_request_timestamp_current_time(self):
        with patch('time.time', return_value=1234567890):
            timestamp = generate_request_timestamp()
            self.assertEqual(timestamp, '1234567890')

    def test_generate_oauth_nonce_length_and_chars(self):
        nonce = generate_oauth_nonce()
        self.assertIsInstance(nonce, str)
        self.assertEqual(len(nonce), 16)
        
        valid_chars = string.ascii_letters + string.digits
        for char in nonce:
            self.assertIn(char, valid_chars)

    def test_generate_oauth_nonce_uniqueness(self):
        nonces = [generate_oauth_nonce() for _ in range(100)]
        unique_nonces = set(nonces)
        self.assertEqual(len(nonces), len(unique_nonces))

    def test_generate_dh_random_bytes_format(self):
        random_bytes = generate_dh_random_bytes()
        self.assertIsInstance(random_bytes, str)
        
        hex_pattern = re.compile(r'^[0-9a-f]+$')
        self.assertTrue(hex_pattern.match(random_bytes))

    def test_generate_dh_random_bytes_uniqueness(self):
        random_values = [generate_dh_random_bytes() for _ in range(10)]
        unique_values = set(random_values)
        self.assertEqual(len(random_values), len(unique_values))

    def test_generate_authorization_header_string_format(self):
        request_data = {
            'oauth_consumer_key': 'test_consumer_key',
            'oauth_nonce': 'test_nonce',
            'oauth_signature': 'test_signature',
            'oauth_timestamp': '1234567890',
            'oauth_token': 'test_token'
        }
        realm = 'limited_poa'
        
        header_string = generate_authorization_header_string(request_data, realm)
        
        self.assertIsInstance(header_string, str)
        self.assertTrue(header_string.startswith('OAuth realm="limited_poa"'))
        
        for key, value in request_data.items():
            self.assertIn(f'{key}="{value}"', header_string)

    def test_generate_authorization_header_string_sorting(self):
        request_data = {
            'z_last': 'last_value',
            'a_first': 'first_value',
            'm_middle': 'middle_value'
        }
        realm = 'test_realm'
        
        header_string = generate_authorization_header_string(request_data, realm)
        
        expected_order = 'a_first="first_value", m_middle="middle_value", z_last="last_value"'
        self.assertIn(expected_order, header_string)

    def test_generate_authorization_header_string_empty_data(self):
        request_data = {}
        realm = 'test_realm'
        
        header_string = generate_authorization_header_string(request_data, realm)
        
        self.assertEqual(header_string, 'OAuth realm="test_realm", ')


class TestBaseStringGenerationU(unittest.TestCase):
    
    def setUp(self):
        self.base_request_headers = {
            'oauth_consumer_key': 'test_consumer_key',
            'oauth_nonce': 'test_nonce',
            'oauth_timestamp': '1234567890',
            'oauth_token': 'test_token'
        }

    def test_generate_base_string_basic(self):
        request_method = 'POST'
        request_url = 'https://api.ibkr.com/v1/test'
        
        base_string = generate_base_string(
            request_method=request_method,
            request_url=request_url,
            request_headers=self.base_request_headers
        )
        
        self.assertIsInstance(base_string, str)
        self.assertTrue(base_string.startswith('POST&'))
        self.assertIn('https%3A%2F%2Fapi.ibkr.com%2Fv1%2Ftest', base_string)

    def test_generate_base_string_with_params(self):
        request_method = 'GET'
        request_url = 'https://api.ibkr.com/v1/test'
        request_params = {'param1': 'value1', 'param2': 'value2'}
        
        base_string = generate_base_string(
            request_method=request_method,
            request_url=request_url,
            request_headers=self.base_request_headers,
            request_params=request_params
        )
        
        self.assertIn('param1%3Dvalue1', base_string)
        self.assertIn('param2%3Dvalue2', base_string)

    def test_generate_base_string_with_form_data(self):
        request_method = 'POST'
        request_url = 'https://api.ibkr.com/v1/test'
        request_form_data = {'form_field': 'form_value'}
        
        base_string = generate_base_string(
            request_method=request_method,
            request_url=request_url,
            request_headers=self.base_request_headers,
            request_form_data=request_form_data
        )
        
        self.assertIn('form_field%3Dform_value', base_string)

    def test_generate_base_string_with_body(self):
        request_method = 'POST'
        request_url = 'https://api.ibkr.com/v1/test'
        request_body = {'body_field': 'body_value'}
        
        base_string = generate_base_string(
            request_method=request_method,
            request_url=request_url,
            request_headers=self.base_request_headers,
            request_body=request_body
        )
        
        self.assertIn('body_field%3Dbody_value', base_string)

    def test_generate_base_string_with_extra_headers(self):
        request_method = 'POST'
        request_url = 'https://api.ibkr.com/v1/test'
        extra_headers = {'extra_header': 'extra_value'}
        
        base_string = generate_base_string(
            request_method=request_method,
            request_url=request_url,
            request_headers=self.base_request_headers,
            extra_headers=extra_headers
        )
        
        self.assertIn('extra_header%3Dextra_value', base_string)

    def test_generate_base_string_with_prepend(self):
        request_method = 'POST'
        request_url = 'https://api.ibkr.com/v1/test'
        prepend = 'prepend_value'
        
        base_string = generate_base_string(
            request_method=request_method,
            request_url=request_url,
            request_headers=self.base_request_headers,
            prepend=prepend
        )
        
        self.assertTrue(base_string.startswith('prepend_value'))

    def test_generate_base_string_parameter_sorting(self):
        request_method = 'POST'
        request_url = 'https://api.ibkr.com/v1/test'
        mixed_headers = {
            'z_last': 'last',
            'a_first': 'first',
            'm_middle': 'middle'
        }
        
        base_string = generate_base_string(
            request_method=request_method,
            request_url=request_url,
            request_headers=mixed_headers
        )
        
        params_section = base_string.split('&')[2]
        decoded_params = params_section.replace('%3D', '=').replace('%26', '&')
        
        self.assertTrue(decoded_params.index('a_first=first') < decoded_params.index('m_middle=middle'))
        self.assertTrue(decoded_params.index('m_middle=middle') < decoded_params.index('z_last=last'))

    def test_generate_base_string_combined_parameters(self):
        request_method = 'POST'
        request_url = 'https://api.ibkr.com/v1/test'
        request_params = {'url_param': 'url_value'}
        request_form_data = {'form_param': 'form_value'}
        extra_headers = {'header_param': 'header_value'}
        
        base_string = generate_base_string(
            request_method=request_method,
            request_url=request_url,
            request_headers=self.base_request_headers,
            request_params=request_params,
            request_form_data=request_form_data,
            extra_headers=extra_headers
        )
        
        self.assertIn('url_param%3Durl_value', base_string)
        self.assertIn('form_param%3Dform_value', base_string)
        self.assertIn('header_param%3Dheader_value', base_string)


class TestReadPrivateKeyU(unittest.TestCase):
    
    @patch('builtins.open', new_callable=mock_open, read_data='dummy_key_content')
    @patch('ibind.oauth.oauth1a.RSA.importKey')
    def test_read_private_key_success(self, mock_rsa_import, mock_file):
        mock_key = 'mocked_rsa_key'
        mock_rsa_import.return_value = mock_key
        
        result = read_private_key('/path/to/key.pem')
        
        mock_file.assert_called_once_with('/path/to/key.pem', 'r')
        mock_rsa_import.assert_called_once_with('dummy_key_content')
        self.assertEqual(result, mock_key)

    @patch('builtins.open', new_callable=mock_open)
    @patch('ibind.oauth.oauth1a.RSA.importKey')
    def test_read_private_key_file_modes(self, mock_rsa_import, mock_file):
        mock_rsa_import.return_value = 'mocked_key'
        
        read_private_key('/test/path.pem')
        
        mock_file.assert_called_once_with('/test/path.pem', 'r')