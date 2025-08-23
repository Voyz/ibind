import re
import string
import pytest
import base64
from unittest.mock import patch, mock_open, MagicMock
from Crypto.Cipher import PKCS1_v1_5 as PKCS1_v1_5_Cipher
from Crypto.Hash import HMAC, SHA1
from Crypto.PublicKey import RSA

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
    validate_live_session_token,
    generate_oauth_headers,
    req_live_session_token,
    prepare_oauth,
    OAuth1aConfig
)

@pytest.fixture
def mock_time():
    """Create a mock time value for consistent timestamp testing."""
    return 1234567890

@pytest.fixture
def real_test_keys():
    """Create real RSA key pairs for cross-platform crypto testing.

    Note: Uses 1024-bit keys for test speed. Production should use 2048+ bits.
    """

    test_key_size = 1024
    # Generate a real 1024-bit RSA key for testing (smaller for speed)
    key = RSA.generate(test_key_size)
    private_key = key
    public_key = key.publickey()

    return {
        'private_key': private_key,
        'public_key': public_key,
        'private_pem': private_key.export_key().decode('utf-8'),
        'public_pem': public_key.export_key().decode('utf-8')
    }


@pytest.fixture
def test_crypto_data():
    """Create test data for crypto operations."""
    return {
        'test_string': 'test_base_string_for_signing',
        'test_token': 'dGVzdF90b2tlbg==',  # base64: 'test_token'
        'test_secret': 'ZW5jcnlwdGVkX3NlY3JldA==',  # base64: 'encrypted_secret'
        'dh_prime': 'ff',  # Small prime for testing (255)
        'dh_generator': '2',
        'dh_random': '5',
        'dh_response': '7'
    }

@pytest.fixture
def oauth_config():
    """Create a sample OAuth1aConfig for testing."""
    return OAuth1aConfig(
        oauth_rest_url='https://api.ibkr.com',
        live_session_token_endpoint='/v1/api/oauth/live_session_token',  # noqa: S106
        access_token='test_access_token',  # noqa: S106
        access_token_secret='test_access_token_secret',  # noqa: S106
        consumer_key='test_consumer_key',  # noqa: S106
        dh_prime='ff',  # Small valid hex prime (255) for testing
        encryption_key_fp='/tmp/encryption_key.pem',  # noqa: S108
        signature_key_fp='/tmp/signature_key.pem',  # noqa: S108
        dh_generator='2',
        realm='limited_poa'
    )

@pytest.fixture
def mock_client():
    """Create a mock IbkrClient for testing."""
    client = MagicMock()
    client.base_url = 'https://api.ibkr.com'

    # Mock successful API response with valid hex values
    mock_response = MagicMock()
    mock_response.data = {
        'live_session_token_expiration': 1234567890,
        'diffie_hellman_response': 'abc123',  # Valid hex value
        'live_session_token_signature': 'lst_signature_value'
    }
    client.post.return_value = mock_response

    return client


def test_generate_request_timestamp_returns_string():
    # Arrange

    # Act
    timestamp = generate_request_timestamp()

    # Assert
    assert isinstance(timestamp, str)
    assert timestamp.isdigit()


def test_generate_request_timestamp_current_time(mock_time):
    # Arrange

    # Act
    with patch('time.time', return_value=mock_time):
        timestamp = generate_request_timestamp()

    # Assert
    assert timestamp == '1234567890'

def test_generate_oauth_nonce_length_and_chars():
    # Arrange
    valid_chars = string.ascii_letters + string.digits

    # Act
    nonce = generate_oauth_nonce()

    # Assert
    assert isinstance(nonce, str)
    assert len(nonce) == 16
    for char in nonce:
        assert char in valid_chars


def test_generate_oauth_nonce_uniqueness():
    # Arrange

    # Act
    nonces = [generate_oauth_nonce() for _ in range(100)]
    unique_nonces = set(nonces)

    # Assert
    assert len(nonces) == len(unique_nonces)

def test_generate_dh_random_bytes_format():
    # Arrange
    hex_pattern = re.compile(r'^[0-9a-f]+$')

    # Act
    random_bytes = generate_dh_random_bytes()

    # Assert
    assert isinstance(random_bytes, str)
    assert hex_pattern.match(random_bytes)


def test_generate_dh_random_bytes_uniqueness():
    # Arrange

    # Act
    random_values = [generate_dh_random_bytes() for _ in range(10)]
    unique_values = set(random_values)

    # Assert
    assert len(random_values) == len(unique_values)

def test_generate_authorization_header_string_format():
    # Arrange
    request_data = {
        'oauth_consumer_key': 'test_consumer_key',  # noqa: S106
        'oauth_nonce': 'test_nonce',
        'oauth_signature': 'test_signature',
        'oauth_timestamp': '1234567890',
        'oauth_token': 'test_token'
    }
    realm = 'limited_poa'

    # Act
    header_string = generate_authorization_header_string(request_data, realm)

    # Assert
    assert isinstance(header_string, str)
    assert header_string.startswith('OAuth realm="limited_poa"')
    for key, value in request_data.items():
        assert f'{key}="{value}"' in header_string

def test_generate_authorization_header_string_sorting():
    # Arrange
    request_data = {
        'z_last': 'last_value',
        'a_first': 'first_value',
        'm_middle': 'middle_value'
    }
    realm = 'test_realm'

    # Act
    header_string = generate_authorization_header_string(request_data, realm)

    # Assert
    expected_order = 'a_first="first_value", m_middle="middle_value", z_last="last_value"'
    assert expected_order in header_string

@pytest.fixture
def base_request_headers():
    """Create standard OAuth request headers for testing."""
    return {
        'oauth_consumer_key': 'test_consumer_key',  # noqa: S106
        'oauth_nonce': 'test_nonce',
        'oauth_timestamp': '1234567890',
        'oauth_token': 'test_token'
    }

def test_generate_base_string_basic(base_request_headers):
    # Arrange
    request_method = 'POST'
    request_url = 'https://api.ibkr.com/v1/test'

    # Act
    base_string = generate_base_string(
        request_method=request_method,
        request_url=request_url,
        request_headers=base_request_headers
    )

    # Assert
    assert isinstance(base_string, str)
    assert base_string.startswith('POST&')
    assert 'https%3A%2F%2Fapi.ibkr.com%2Fv1%2Ftest' in base_string


@pytest.mark.parametrize("data_type,data_value,expected_encoded", [
    ("request_params", {'param1': 'value1', 'param2': 'value2'}, ['param1%3Dvalue1', 'param2%3Dvalue2']),
    ("request_form_data", {'form_field': 'form_value'}, ['form_field%3Dform_value']),
    ("request_body", {'body_field': 'body_value'}, ['body_field%3Dbody_value']),
    ("extra_headers", {'extra_header': 'extra_value'}, ['extra_header%3Dextra_value']),
])
def test_generate_base_string_with_data(base_request_headers, data_type, data_value, expected_encoded):
    # Arrange
    request_method = 'POST'
    request_url = 'https://api.ibkr.com/v1/test'
    kwargs = {data_type: data_value}

    # Act
    base_string = generate_base_string(
        request_method=request_method,
        request_url=request_url,
        request_headers=base_request_headers,
        **kwargs
    )

    # Assert
    for expected in expected_encoded:
        assert expected in base_string


def test_generate_base_string_with_prepend(base_request_headers):
    # Arrange
    request_method = 'POST'
    request_url = 'https://api.ibkr.com/v1/test'
    prepend = 'prepend_value'

    # Act
    base_string = generate_base_string(
        request_method=request_method,
        request_url=request_url,
        request_headers=base_request_headers,
        prepend=prepend
    )

    # Assert
    assert base_string.startswith('prepend_value')

def test_generate_base_string_combined_parameters(base_request_headers):
    # Arrange
    request_method = 'POST'
    request_url = 'https://api.ibkr.com/v1/test'
    request_params = {'url_param': 'url_value'}
    request_form_data = {'form_param': 'form_value'}
    extra_headers = {'header_param': 'header_value'}

    # Act
    base_string = generate_base_string(
        request_method=request_method,
        request_url=request_url,
        request_headers=base_request_headers,
        request_params=request_params,
        request_form_data=request_form_data,
        extra_headers=extra_headers
    )

    # Assert
    assert 'url_param%3Durl_value' in base_string
    assert 'form_param%3Dform_value' in base_string
    assert 'header_param%3Dheader_value' in base_string


@patch('builtins.open', new_callable=mock_open, read_data='dummy_key_content')
@patch('ibind.oauth.oauth1a.RSA.importKey', autospec=True)
def test_read_private_key_success(mock_rsa_import, mock_file):
    # Arrange
    mock_key = 'mocked_rsa_key'
    mock_rsa_import.return_value = mock_key

    # Act
    result = read_private_key('/path/to/key.pem')

    # Assert
    mock_file.assert_called_once_with('/path/to/key.pem', 'r')
    mock_rsa_import.assert_called_once_with('dummy_key_content')
    assert result == mock_key

def test_generate_rsa_sha_256_signature(real_test_keys, test_crypto_data):
    # Arrange
    private_key = real_test_keys['private_key']
    base_string = test_crypto_data['test_string']

    # Act
    result = generate_rsa_sha_256_signature(base_string, private_key)

    # Assert
    assert isinstance(result, str)
    # Should be URL-encoded base64 string
    assert '%' in result or result.replace('-', '+').replace('_', '/').isalnum()

    # Verify signature is deterministic for same input
    result2 = generate_rsa_sha_256_signature(base_string, private_key)
    assert result == result2

def test_generate_hmac_sha_256_signature_real_crypto(test_crypto_data):
    # Arrange
    base_string = test_crypto_data['test_string']
    live_session_token = test_crypto_data['test_token']

    # Act
    result = generate_hmac_sha_256_signature(base_string, live_session_token)

    # Assert
    assert isinstance(result, str)
    # Should be URL-encoded base64 string
    assert '%' in result or result.replace('-', '+').replace('_', '/').isalnum()

    # Verify signature is deterministic for same input
    result2 = generate_hmac_sha_256_signature(base_string, live_session_token)
    assert result == result2

def test_calculate_live_session_token_prepend(real_test_keys):
    # Arrange
    private_key = real_test_keys['private_key']
    public_key = real_test_keys['public_key']

    # Create real encrypted token secret
    test_secret = b'test_secret_data_for_decryption'
    cipher = PKCS1_v1_5_Cipher.new(public_key)
    encrypted_secret = cipher.encrypt(test_secret)
    access_token_secret = base64.b64encode(encrypted_secret).decode('utf-8')

    # Act
    result = calculate_live_session_token_prepend(access_token_secret, private_key)

    # Assert
    assert isinstance(result, str)
    # Should be hex representation of decrypted secret
    assert all(c in '0123456789abcdef' for c in result.lower())
    expected_hex = test_secret.hex()
    assert result == expected_hex


def test_generate_dh_challenge_basic():
    # Arrange
    dh_prime = 'ffffffffffffffffc90fdaa22168c234c4c6628b80dc1cd129024e088a67cc74020bbea63b139b22514a08798e3404ddef9519b3cd3a431b302b0a6df25f14374fe1356d6d51c245e485b576625e7ec6f44c42e9a637ed6b0bff5cb6f406b7edee386bfb5a899fa5ae9f24117c4b1fe649286651ece45b3dc2007cb8a163bf0598da48361c55d39a69163fa8fd24cf5f83655d23dca3ad961c62f356208552bb9ed529077096966d670c354e4abc9804f1746c08ca237327ffffffffffffffff'
    dh_random = 'abcdef123456789'
    dh_generator = 2

    # Act
    result = generate_dh_challenge(dh_prime, dh_random, dh_generator)

    # Assert
    assert isinstance(result, str)
    int(result, 16)  # Should not raise ValueError

@pytest.mark.parametrize("dh_prime,dh_random,dh_generator,description", [
    ('ff', 'a', 2, "default generator=2, random=a(10), prime=ff(255): 2^10 mod 255 = 4"),
    ('ff', '2', 3, "custom generator=3, random=2, prime=ff(255): 3^2 mod 255 = 9"),
])
def test_generate_dh_challenge_calculations(dh_prime, dh_random, dh_generator, description):
    # Act
    result = generate_dh_challenge(dh_prime, dh_random, dh_generator)

    # Assert - Calculate expected value based on the DH formula
    dh_random_int = int(dh_random, 16)
    dh_prime_int = int(dh_prime, 16)
    expected = hex(pow(dh_generator, dh_random_int, dh_prime_int))[2:]
    assert result == expected


@pytest.mark.parametrize("hex_string,expected,description", [
    ('deadbeef', [222, 173, 190, 239], "standard hex conversion"),
    ('', [], "empty string returns empty list"),
    ('ff', [255], "single byte"),
    ('0000', [0, 0], "zeros"),
])
def test_get_access_token_secret_bytes(hex_string, expected, description):
    # Act
    result = get_access_token_secret_bytes(hex_string)

    # Assert
    assert result == expected
    assert isinstance(result, list)
    assert all(isinstance(b, int) for b in result)

@pytest.mark.parametrize("input_value,expected,description", [
    (15, [15], "simple single byte"),
    (255, [0, 255], "8-bit boundary - gets leading zero"),
    (256, [1, 0], "9-bit value - no leading zero needed"),
    (65535, [0, 255, 255], "16-bit boundary - gets leading zero"),
])
def test_to_byte_array(input_value, expected, description):
    # Act
    result = to_byte_array(input_value)

    # Assert
    assert result == expected


def test_validate_live_session_token():
    # Arrange - Create real live session token and signature for testing
    # Create a test live session token (base64 encoded)
    test_token_data = b'test_session_token_data'
    live_session_token = base64.b64encode(test_token_data).decode('utf-8')
    consumer_key = 'test_consumer_key'

    # Generate the real signature that the function should produce
    hmac_obj = HMAC.new(test_token_data, digestmod=SHA1)
    hmac_obj.update(consumer_key.encode('utf-8'))
    expected_signature = hmac_obj.hexdigest()

    # Test with matching signature (should pass)
    result = validate_live_session_token(live_session_token, expected_signature, consumer_key)
    assert result is True

    # Test with non-matching signature (should fail validation)
    wrong_signature = 'definitely_wrong_signature'
    result = validate_live_session_token(live_session_token, wrong_signature, consumer_key)
    assert result is False

    # Test deterministic behavior
    result2 = validate_live_session_token(live_session_token, expected_signature, consumer_key)
    assert result2 is True

    # Additional validation: Test with different consumer key should fail
    different_consumer_key = 'different_consumer_key'
    result3 = validate_live_session_token(live_session_token, expected_signature, different_consumer_key)
    assert result3 is False  # Should fail because consumer key is different


def test_calculate_live_session_token_integration(test_crypto_data):
    # Arrange
    dh_prime = test_crypto_data['dh_prime']  # 'ff' = 255
    dh_random_value = test_crypto_data['dh_random']  # '5'
    dh_response = test_crypto_data['dh_response']  # '7'
    prepend = 'deadbeef'

    # Act - Test real function composition and crypto
    result = calculate_live_session_token(dh_prime, dh_random_value, dh_response, prepend)

    # Assert
    assert isinstance(result, str)
    # Should be base64 encoded
    try:
        decoded = base64.b64decode(result)
        assert len(decoded) > 0  # Should decode to non-empty bytes
    except Exception:
        pytest.fail(f"Result '{result}' is not valid base64")

    # Verify deterministic behavior
    result2 = calculate_live_session_token(dh_prime, dh_random_value, dh_response, prepend)
    assert result == result2

@patch('time.time', return_value=1234567890, autospec=True)
@patch('secrets.choice', side_effect=lambda x: 'a', autospec=True)  # Predictable nonce
@patch('builtins.open', new_callable=mock_open, read_data='dummy_key_content')
def test_generate_oauth_headers_rsa_integration(mock_file, mock_choice_func, mock_time_func, oauth_config, real_test_keys):
    # Arrange
    oauth_config.signature_key_fp = '/tmp/test_signature_key.pem' # noqa: S108

    # Mock only the file read to return our real test key
    with patch('ibind.oauth.oauth1a.RSA.importKey', autospec=True) as mock_rsa_import:
        mock_rsa_import.return_value = real_test_keys['private_key']

        request_method = 'POST'
        request_url = 'https://api.ibkr.com/v1/test'

        # Act - Let internal functions run naturally, use real crypto
        result = generate_oauth_headers(
            oauth_config=oauth_config,
            request_method=request_method,
            request_url=request_url,
            signature_method='RSA-SHA256'
        )

        # Assert
        assert isinstance(result, dict)
        assert 'Authorization' in result
        assert 'User-Agent' in result
        assert result['User-Agent'] == 'ibind'
        assert result['Host'] == 'api.ibkr.com'

        # Verify authorization header contains expected elements
        auth_header = result['Authorization']
        assert 'OAuth realm="limited_poa"' in auth_header
        assert 'oauth_consumer_key="test_consumer_key"' in auth_header
        assert 'oauth_token="test_access_token"' in auth_header
        assert 'oauth_timestamp="1234567890"' in auth_header
        assert 'oauth_nonce="aaaaaaaaaaaaaaaa"' in auth_header  # 16 'a's from mocked choice
        assert 'oauth_signature=' in auth_header


@patch('time.time', return_value=1234567890, autospec=True)
@patch('secrets.choice', side_effect=lambda x: 'a', autospec=True)  # Predictable nonce
def test_generate_oauth_headers_hmac_integration(mock_choice_func, mock_time_func, oauth_config, test_crypto_data):
    # Arrange
    request_method = 'GET'
    request_url = 'https://api.ibkr.com/v1/test'
    live_session_token = test_crypto_data['test_token']

    # Act - Let internal functions run naturally, use real crypto
    result = generate_oauth_headers(
        oauth_config=oauth_config,
        request_method=request_method,
        request_url=request_url,
        live_session_token=live_session_token,
        signature_method='HMAC-SHA256'
    )

    # Assert
    assert isinstance(result, dict)
    assert 'Authorization' in result
    assert result['User-Agent'] == 'ibind'

    # Verify authorization header structure
    auth_header = result['Authorization']
    assert 'OAuth realm="limited_poa"' in auth_header
    assert 'oauth_signature=' in auth_header


@pytest.mark.parametrize("extra_data_type,extra_data_value", [
    ("extra_headers", {'custom_header': 'custom_value'}),
    ("request_params", {'param1': 'value1', 'param2': 'value2'}),
])
@patch('time.time', return_value=1234567890, autospec=True)
@patch('secrets.choice', side_effect=lambda x: 'a', autospec=True)  # Predictable nonce
def test_generate_oauth_headers_with_extra_data_integration(mock_choice, mock_time, oauth_config, extra_data_type, extra_data_value, test_crypto_data):
    # Arrange - Use real functions, only mock deterministic inputs
    request_method = 'GET'
    request_url = 'https://api.ibkr.com/v1/test'
    kwargs = {extra_data_type: extra_data_value}
    live_session_token = test_crypto_data['test_token']

    # Act - Let all internal functions run naturally with real crypto
    result = generate_oauth_headers(
        oauth_config=oauth_config,
        request_method=request_method,
        request_url=request_url,
        live_session_token=live_session_token,
        signature_method='HMAC-SHA256',
        **kwargs
    )

    # Assert - Test the actual behavior, not implementation details
    assert isinstance(result, dict)
    assert 'Authorization' in result
    assert result['User-Agent'] == 'ibind'

    # Verify the authorization header is properly formed
    auth_header = result['Authorization']
    assert 'OAuth realm="limited_poa"' in auth_header
    assert 'oauth_signature=' in auth_header
    assert 'oauth_timestamp="1234567890"' in auth_header
    assert 'oauth_nonce="aaaaaaaaaaaaaaaa"' in auth_header  # 16 'a's from mocked choice

    # Most importantly: verify extra data affects the signature (different signatures for different data)
    # Generate another header without extra data
    result_without_extra = generate_oauth_headers(
        oauth_config=oauth_config,
        request_method=request_method,
        request_url=request_url,
        live_session_token=live_session_token,
        signature_method='HMAC-SHA256'
    )

    # The signatures should be different because the base string includes extra data
    auth_header_without_extra = result_without_extra['Authorization']
    signature_with_extra = auth_header.split('oauth_signature="')[1].split('"')[0]
    signature_without_extra = auth_header_without_extra.split('oauth_signature="')[1].split('"')[0]
    assert signature_with_extra != signature_without_extra, "Extra data should affect OAuth signature"


@patch('secrets.randbits', return_value=0x123, autospec=True)  # Deterministic randomness
@patch('builtins.open', new_callable=mock_open, read_data='dummy_key_content')
def test_prepare_oauth_integration(mock_file, mock_randbits, oauth_config, real_test_keys):
    # Arrange
    oauth_config.encryption_key_fp = '/tmp/encryption_key.pem'  # noqa: S108

    # Create real encrypted access token secret for testing
    test_secret = b'test_decrypted_secret_for_prepend'
    cipher = PKCS1_v1_5_Cipher.new(real_test_keys['public_key'])
    encrypted_secret = cipher.encrypt(test_secret)
    oauth_config.access_token_secret = base64.b64encode(encrypted_secret).decode('utf-8')

    # Mock RSA key import to return our real test key
    with patch('ibind.oauth.oauth1a.RSA.importKey', autospec=True) as mock_rsa_import:
        mock_rsa_import.return_value = real_test_keys['private_key']

        # Act - Test real behavior with actual crypto operations
        prepend, extra_headers, dh_random = prepare_oauth(oauth_config)

        # Assert
        assert isinstance(prepend, str)
        assert isinstance(dh_random, str)
        assert isinstance(extra_headers, dict)
        assert 'diffie_hellman_challenge' in extra_headers

        # Verify prepend is the hex representation of decrypted secret
        assert prepend == test_secret.hex()

        # Verify dh_random is hex format
        assert all(c in '0123456789abcdef' for c in dh_random.lower())

        # Verify DH challenge is valid hex
        dh_challenge = extra_headers['diffie_hellman_challenge']
        int(dh_challenge, 16)  # Should not raise ValueError

        # Verify deterministic behavior
        prepend2, extra_headers2, dh_random2 = prepare_oauth(oauth_config)
        assert prepend == prepend2  # Same encrypted secret should give same prepend
        assert dh_random == dh_random2  # Same mocked random should give same result

@patch('secrets.randbits', return_value=0x123, autospec=True)
@patch('secrets.choice', side_effect=lambda x: 'a', autospec=True)
@patch('time.time', return_value=1234567890, autospec=True)
@patch('builtins.open', new_callable=mock_open, read_data='dummy_key_content')
def test_req_live_session_token_integration(mock_file, mock_time_func, mock_choice_func, mock_randbits_func, oauth_config, mock_client, real_test_keys):
    # Arrange
    oauth_config.encryption_key_fp = '/tmp/encryption_key.pem' # noqa: S108
    oauth_config.signature_key_fp = '/tmp/signature_key.pem' # noqa: S108

    # Create real encrypted access token secret for testing
    test_secret = b'test_decrypted_secret'
    cipher = PKCS1_v1_5_Cipher.new(real_test_keys['public_key'])
    encrypted_secret = cipher.encrypt(test_secret)
    oauth_config.access_token_secret = base64.b64encode(encrypted_secret).decode('utf-8')

    with patch('ibind.oauth.oauth1a.RSA.importKey', autospec=True) as mock_rsa_import:
        mock_rsa_import.return_value = real_test_keys['private_key']

        # Act
        live_session_token, lst_expires, lst_signature = req_live_session_token(mock_client, oauth_config)

        # Assert
        assert isinstance(live_session_token, str)
        assert lst_expires == 1234567890
        assert lst_signature == 'lst_signature_value'

        # Verify HTTP call was made
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args

        # Verify endpoint was called correctly
        assert call_args.args[0] == oauth_config.live_session_token_endpoint

        # Verify authorization header structure (real OAuth header generated)
        auth_header = call_args.kwargs['extra_headers']['Authorization']
        assert isinstance(auth_header, str)
        assert 'OAuth realm=' in auth_header
        assert 'oauth_signature=' in auth_header

@patch('ibind.oauth.oauth1a.prepare_oauth')
@patch('ibind.oauth.oauth1a.generate_oauth_headers')
def test_req_live_session_token_api_failure(mock_gen_headers, mock_prepare, oauth_config, mock_client):
    # Arrange
    mock_prepare.return_value = ('prepend_value', {'diffie_hellman_challenge': 'challenge'}, 'dh_random_value')
    mock_gen_headers.return_value = {'Authorization': 'OAuth realm="limited_poa"'}

    # Mock API failure
    mock_client.post.side_effect = Exception('API request failed')

    # Act & Assert
    with pytest.raises(Exception, match='API request failed'):
        req_live_session_token(mock_client, oauth_config)


@patch('ibind.oauth.oauth1a.prepare_oauth')
@patch('ibind.oauth.oauth1a.generate_oauth_headers')
@patch('ibind.oauth.oauth1a.calculate_live_session_token')
def test_req_live_session_token_missing_response_data(mock_calculate_lst, mock_gen_headers, mock_prepare, oauth_config, mock_client):
    # Arrange
    mock_prepare.return_value = ('prepend_value', {'diffie_hellman_challenge': 'challenge'}, 'dh_random_value')
    mock_gen_headers.return_value = {'Authorization': 'OAuth realm="limited_poa"'}

    # Mock response with missing data
    mock_response = MagicMock()
    mock_response.data = {}  # Missing required fields
    mock_client.post.return_value = mock_response

    # Act & Assert
    with pytest.raises(KeyError):
        req_live_session_token(mock_client, oauth_config)
