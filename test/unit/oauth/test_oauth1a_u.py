import base64
import re
import string
import unittest
from unittest.mock import patch, mock_open

from ibind.oauth.oauth1a import (
    generate_request_timestamp,
    generate_oauth_nonce,
    generate_dh_random_bytes,
    generate_authorization_header_string,
    generate_base_string,
    read_private_key,
    generate_rsa_sha_256_signature,
    generate_hmac_sha_256_signature,
    calculate_live_session_token_prepend,
    generate_dh_challenge,
    to_byte_array,
    get_access_token_secret_bytes,
    calculate_live_session_token,
    validate_live_session_token
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


class TestCryptoFunctionsU(unittest.TestCase):

    @patch('ibind.oauth.oauth1a.PKCS1_v1_5_Signature.new')
    @patch('ibind.oauth.oauth1a.SHA256.new')
    @patch('ibind.oauth.oauth1a.base64.encodebytes')
    @patch('ibind.oauth.oauth1a.parse.quote_plus')
    def test_generate_rsa_sha_256_signature(self, mock_quote_plus, mock_b64encode, mock_sha256, mock_signer_new):
        # Setup mocks
        mock_private_key = 'mock_private_key'
        mock_signer = mock_signer_new.return_value
        mock_hash = mock_sha256.return_value
        mock_signature = b'mock_signature_bytes'
        mock_signer.sign.return_value = mock_signature
        mock_b64encode.return_value = b'bW9ja19zaWduYXR1cmU=\n'
        mock_quote_plus.return_value = 'encoded_signature'

        base_string = 'test_base_string'

        result = generate_rsa_sha_256_signature(base_string, mock_private_key)

        # Verify the crypto operations were called correctly
        mock_sha256.assert_called_once_with(base_string.encode('utf-8'))
        mock_signer_new.assert_called_once_with(mock_private_key)
        mock_signer.sign.assert_called_once_with(mock_hash)
        mock_b64encode.assert_called_once_with(mock_signature)
        mock_quote_plus.assert_called_once_with('bW9ja19zaWduYXR1cmU=')

        self.assertEqual(result, 'encoded_signature')

    @patch('ibind.oauth.oauth1a.HMAC.new')
    @patch('ibind.oauth.oauth1a.base64.b64decode')
    @patch('ibind.oauth.oauth1a.base64.b64encode')
    @patch('ibind.oauth.oauth1a.parse.quote_plus')
    def test_generate_hmac_sha_256_signature(self, mock_quote_plus, mock_b64encode, mock_b64decode, mock_hmac_new):
        # Setup mocks
        mock_token_bytes = b'decoded_token_bytes'
        mock_b64decode.return_value = mock_token_bytes
        mock_hmac = mock_hmac_new.return_value
        mock_digest = b'hmac_digest_bytes'
        mock_hmac.digest.return_value = mock_digest
        mock_b64encode.return_value = b'encoded_digest'
        mock_quote_plus.return_value = 'final_signature'

        base_string = 'test_base_string'
        live_session_token = 'dGVzdF90b2tlbg=='  # base64 encoded  # noqa: S105

        result = generate_hmac_sha_256_signature(base_string, live_session_token)

        # Verify HMAC operations
        mock_b64decode.assert_called_once_with(live_session_token)
        mock_hmac_new.assert_called_once()
        mock_hmac.update.assert_called_once_with(base_string.encode('utf-8'))
        mock_b64encode.assert_called_once_with(mock_digest)
        mock_quote_plus.assert_called_once_with('encoded_digest')

        self.assertEqual(result, 'final_signature')

    @patch('ibind.oauth.oauth1a.base64.b64decode')
    @patch('ibind.oauth.oauth1a.PKCS1_v1_5_Cipher.new')
    def test_calculate_live_session_token_prepend(self, mock_cipher_new, mock_b64decode):
        # Setup mocks
        mock_encrypted_bytes = b'encrypted_secret_bytes'
        mock_b64decode.return_value = mock_encrypted_bytes
        mock_cipher = mock_cipher_new.return_value
        mock_decrypted = b'decrypted_secret'
        mock_cipher.decrypt.return_value = mock_decrypted
        mock_private_key = 'mock_private_key'

        access_token_secret = 'ZW5jcnlwdGVkX3NlY3JldA=='  # base64 encoded  # noqa: S105

        result = calculate_live_session_token_prepend(access_token_secret, mock_private_key)

        # Verify decryption process
        mock_b64decode.assert_called_once_with(access_token_secret)
        mock_cipher_new.assert_called_once_with(mock_private_key)
        mock_cipher.decrypt.assert_called_once_with(mock_encrypted_bytes, None)

        # Verify hex conversion
        expected_hex = mock_decrypted.hex()
        self.assertEqual(result, expected_hex)


class TestDiffieHellmanU(unittest.TestCase):

    def test_generate_dh_challenge_basic(self):
        dh_prime = 'ffffffffffffffffc90fdaa22168c234c4c6628b80dc1cd129024e088a67cc74020bbea63b139b22514a08798e3404ddef9519b3cd3a431b302b0a6df25f14374fe1356d6d51c245e485b576625e7ec6f44c42e9a637ed6b0bff5cb6f406b7edee386bfb5a899fa5ae9f24117c4b1fe649286651ece45b3dc2007cb8a163bf0598da48361c55d39a69163fa8fd24cf5f83655d23dca3ad961c62f356208552bb9ed529077096966d670c354e4abc9804f1746c08ca237327ffffffffffffffff'
        dh_random = 'abcdef123456789'
        dh_generator = 2

        result = generate_dh_challenge(dh_prime, dh_random, dh_generator)

        # Verify it returns a hex string
        self.assertIsInstance(result, str)
        # Verify it's valid hex (no 0x prefix)
        int(result, 16)  # Should not raise ValueError

    def test_generate_dh_challenge_default_generator(self):
        dh_prime = 'ff'
        dh_random = 'a'

        result = generate_dh_challenge(dh_prime, dh_random)

        # With generator=2, random=a(10), prime=ff(255): 2^10 mod 255 = 1024 mod 255 = 4
        expected = hex(pow(2, 10, 255))[2:]
        self.assertEqual(result, expected)

    def test_generate_dh_challenge_custom_generator(self):
        dh_prime = 'ff'
        dh_random = '2'
        dh_generator = 3

        result = generate_dh_challenge(dh_prime, dh_random, dh_generator)

        # With generator=3, random=2, prime=ff(255): 3^2 mod 255 = 9
        expected = hex(pow(3, 2, 255))[2:]
        self.assertEqual(result, expected)


class TestByteConversionU(unittest.TestCase):
    """
    Tests for byte array conversion functions used in OAuth 1.0a cryptographic operations.

    The to_byte_array() function implements RFC 2631 compliance for Diffie-Hellman shared secrets
    and two's complement big-endian byte representation. When a number's binary representation
    has a bit count that is exactly divisible by 8 (e.g., 8, 16, 24 bits), a leading zero byte
    is added to prevent misinterpretation as a negative value in two's complement form.

    This ensures proper cryptographic byte array format and compatibility with standard
    cryptographic libraries used in HMAC-SHA1 and Diffie-Hellman operations.

    References:
    - RFC 2631: Diffie-Hellman Key Agreement Method (leading zeros preservation)
    - RFC 2104: HMAC specification (byte array handling)
    - RFC 5849: OAuth 1.0a protocol specification

    For detailed analysis: https://www.rfc-editor.org/rfc/rfc2631.txt
    """

    def test_get_access_token_secret_bytes(self):
        hex_string = 'deadbeef'

        result = get_access_token_secret_bytes(hex_string)

        # deadbeef = [222, 173, 190, 239]
        expected = [222, 173, 190, 239]
        self.assertEqual(result, expected)
        self.assertIsInstance(result, list)
        self.assertTrue(all(isinstance(b, int) for b in result))

    def test_get_access_token_secret_bytes_empty(self):
        result = get_access_token_secret_bytes('')
        self.assertEqual(result, [])

    def test_to_byte_array_simple(self):
        # Test with 255 (0xff) - binary is 11111111 (8 bits), so gets leading zero
        result = to_byte_array(255)
        expected = [0, 255]  # Leading zero for 8-bit alignment
        self.assertEqual(result, expected)

    def test_to_byte_array_with_padding(self):
        # Test with 15 (0xf) - should get padded to 0x0f
        result = to_byte_array(15)
        expected = [15]
        self.assertEqual(result, expected)

    def test_to_byte_array_multiple_bytes(self):
        # Test with 65535 (0xffff) - binary is 16 bits, so gets leading zero
        result = to_byte_array(65535)
        expected = [0, 255, 255]  # Leading zero for 16-bit alignment
        self.assertEqual(result, expected)

    def test_to_byte_array_byte_alignment(self):
        # Test with 256 (0x100) - binary is 100000000 (9 bits), no leading zero needed
        result = to_byte_array(256)
        expected = [1, 0]  # No leading zero for 9-bit number
        self.assertEqual(result, expected)


class TestTokenValidationU(unittest.TestCase):

    @patch('ibind.oauth.oauth1a.HMAC.new')
    @patch('ibind.oauth.oauth1a.base64.b64decode')
    def test_validate_live_session_token_valid(self, mock_b64decode, mock_hmac_new):
        # Setup mocks
        mock_token_bytes = b'decoded_token'
        mock_b64decode.return_value = mock_token_bytes
        mock_hmac = mock_hmac_new.return_value
        mock_hmac.hexdigest.return_value = 'expected_signature'

        live_session_token = 'dGVzdF90b2tlbg=='  # noqa: S105
        live_session_token_signature = 'expected_signature'  # noqa: S105
        consumer_key = 'test_consumer_key'

        result = validate_live_session_token(live_session_token, live_session_token_signature, consumer_key)

        # Verify HMAC validation process
        mock_b64decode.assert_called_once_with(live_session_token)
        mock_hmac_new.assert_called_once()
        mock_hmac.update.assert_called_once_with(consumer_key.encode('utf-8'))
        mock_hmac.hexdigest.assert_called_once()

        self.assertTrue(result)

    @patch('ibind.oauth.oauth1a.HMAC.new')
    @patch('ibind.oauth.oauth1a.base64.b64decode')
    def test_validate_live_session_token_invalid(self, mock_b64decode, mock_hmac_new):
        # Setup mocks for invalid signature
        mock_token_bytes = b'decoded_token'
        mock_b64decode.return_value = mock_token_bytes
        mock_hmac = mock_hmac_new.return_value
        mock_hmac.hexdigest.return_value = 'calculated_signature'

        live_session_token = 'dGVzdF90b2tlbg=='  # noqa: S105
        live_session_token_signature = 'different_signature'  # Different from calculated  # noqa: S105
        consumer_key = 'test_consumer_key'

        result = validate_live_session_token(live_session_token, live_session_token_signature, consumer_key)

        self.assertFalse(result)


class TestLiveSessionTokenCalculationU(unittest.TestCase):

    @patch('ibind.oauth.oauth1a.get_access_token_secret_bytes')
    @patch('ibind.oauth.oauth1a.to_byte_array')
    @patch('ibind.oauth.oauth1a.HMAC.new')
    @patch('ibind.oauth.oauth1a.base64.b64encode')
    def test_calculate_live_session_token(self, mock_b64encode, mock_hmac_new, mock_to_byte_array, mock_get_bytes):
        # Setup mocks
        mock_get_bytes.return_value = [1, 2, 3, 4]  # Mock access token secret bytes
        mock_to_byte_array.return_value = [5, 6, 7, 8]  # Mock shared secret bytes
        mock_hmac = mock_hmac_new.return_value
        mock_digest = b'hmac_digest'
        mock_hmac.digest.return_value = mock_digest
        mock_b64encode.return_value = b'encoded_token'

        dh_prime = 'ff'  # 255
        dh_random_value = '2'  # 2
        dh_response = '3'  # 3
        prepend = 'deadbeef'

        result = calculate_live_session_token(dh_prime, dh_random_value, dh_response, prepend)

        # Verify the calculation steps
        mock_get_bytes.assert_called_once_with(prepend)

        # Verify DH shared secret calculation: 3^2 mod 255 = 9
        expected_shared_secret = pow(3, 2, 255)
        mock_to_byte_array.assert_called_once_with(expected_shared_secret)

        # Verify HMAC operations
        mock_hmac_new.assert_called_once()
        mock_hmac.update.assert_called_once_with(bytes([1, 2, 3, 4]))
        mock_b64encode.assert_called_once_with(mock_digest)

        self.assertEqual(result, 'encoded_token')

    def test_calculate_live_session_token_integration(self):
        # Integration test with real crypto (no mocks)
        dh_prime = 'ff'  # Small prime for testing
        dh_random_value = '2'
        dh_response = '3'
        prepend = 'deadbeef'  # Will be converted to [222, 173, 190, 239]

        result = calculate_live_session_token(dh_prime, dh_random_value, dh_response, prepend)

        # Verify result is a valid base64 string
        self.assertIsInstance(result, str)
        # Should be able to decode without error
        decoded = base64.b64decode(result.encode())
        self.assertIsInstance(decoded, bytes)
