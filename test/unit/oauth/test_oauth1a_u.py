import re
import string
import pytest
from unittest.mock import patch, mock_open, MagicMock

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
def oauth_helpers_mocked():
    """Create commonly used OAuth helper mocks."""
    with patch.multiple(
        'ibind.oauth.oauth1a',
        generate_oauth_nonce=MagicMock(return_value='test_nonce'),
        generate_request_timestamp=MagicMock(return_value='1234567890'),
        generate_base_string=MagicMock(return_value='test_base_string'),
        generate_authorization_header_string=MagicMock(return_value='OAuth realm="limited_poa"'),
    ) as mocks:
        yield mocks


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

def test_generate_authorization_header_string_empty_data():
    # Arrange
    request_data = {}
    realm = 'test_realm'

    # Act
    header_string = generate_authorization_header_string(request_data, realm)

    # Assert
    assert header_string == 'OAuth realm="test_realm", '


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

def test_generate_base_string_parameter_sorting():
    # Arrange
    request_method = 'POST'
    request_url = 'https://api.ibkr.com/v1/test'
    mixed_headers = {
        'z_last': 'last',
        'a_first': 'first',
        'm_middle': 'middle'
    }

    # Act
    base_string = generate_base_string(
        request_method=request_method,
        request_url=request_url,
        request_headers=mixed_headers
    )

    # Assert
    params_section = base_string.split('&')[2]
    decoded_params = params_section.replace('%3D', '=').replace('%26', '&')
    assert decoded_params.index('a_first=first') < decoded_params.index('m_middle=middle')
    assert decoded_params.index('m_middle=middle') < decoded_params.index('z_last=last')

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
@patch('ibind.oauth.oauth1a.RSA.importKey')
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


@patch('builtins.open', new_callable=mock_open)
@patch('ibind.oauth.oauth1a.RSA.importKey')
def test_read_private_key_file_modes(mock_rsa_import, mock_file):
    # Arrange
    mock_rsa_import.return_value = 'mocked_key'

    # Act
    read_private_key('/test/path.pem')

    # Assert
    mock_file.assert_called_once_with('/test/path.pem', 'r')


@patch('ibind.oauth.oauth1a.PKCS1_v1_5_Signature.new')
@patch('ibind.oauth.oauth1a.SHA256.new')
@patch('ibind.oauth.oauth1a.base64.encodebytes')
@patch('ibind.oauth.oauth1a.parse.quote_plus')
def test_generate_rsa_sha_256_signature(mock_quote_plus, mock_b64encode, mock_sha256, mock_signer_new):
    # Arrange
    mock_private_key = 'mock_private_key'
    mock_signer = mock_signer_new.return_value
    mock_hash = mock_sha256.return_value
    mock_signature = b'mock_signature_bytes'
    mock_signer.sign.return_value = mock_signature
    mock_b64encode.return_value = b'bW9ja19zaWduYXR1cmU=\n'
    mock_quote_plus.return_value = 'encoded_signature'
    base_string = 'test_base_string'

    # Act
    result = generate_rsa_sha_256_signature(base_string, mock_private_key)

    # Assert
    mock_sha256.assert_called_once_with(base_string.encode('utf-8'))
    mock_signer_new.assert_called_once_with(mock_private_key)
    mock_signer.sign.assert_called_once_with(mock_hash)
    mock_b64encode.assert_called_once_with(mock_signature)
    mock_quote_plus.assert_called_once_with('bW9ja19zaWduYXR1cmU=')
    assert result == 'encoded_signature'

@patch('ibind.oauth.oauth1a.HMAC.new')
@patch('ibind.oauth.oauth1a.base64.b64decode')
@patch('ibind.oauth.oauth1a.base64.b64encode')
@patch('ibind.oauth.oauth1a.parse.quote_plus')
def test_generate_hmac_sha_256_signature(mock_quote_plus, mock_b64encode, mock_b64decode, mock_hmac_new):
    # Arrange
    mock_token_bytes = b'decoded_token_bytes'
    mock_b64decode.return_value = mock_token_bytes
    mock_hmac = mock_hmac_new.return_value
    mock_digest = b'hmac_digest_bytes'
    mock_hmac.digest.return_value = mock_digest
    mock_b64encode.return_value = b'encoded_digest'
    mock_quote_plus.return_value = 'final_signature'
    base_string = 'test_base_string'
    live_session_token = 'dGVzdF90b2tlbg=='  # base64 encoded  # noqa: S105

    # Act
    result = generate_hmac_sha_256_signature(base_string, live_session_token)

    # Assert
    mock_b64decode.assert_called_once_with(live_session_token)
    mock_hmac_new.assert_called_once()
    mock_hmac.update.assert_called_once_with(base_string.encode('utf-8'))
    mock_b64encode.assert_called_once_with(mock_digest)
    mock_quote_plus.assert_called_once_with('encoded_digest')
    assert result == 'final_signature'

@patch('ibind.oauth.oauth1a.base64.b64decode')
@patch('ibind.oauth.oauth1a.PKCS1_v1_5_Cipher.new')
def test_calculate_live_session_token_prepend(mock_cipher_new, mock_b64decode):
    # Arrange
    mock_encrypted_bytes = b'encrypted_secret_bytes'
    mock_b64decode.return_value = mock_encrypted_bytes
    mock_cipher = mock_cipher_new.return_value
    mock_decrypted = b'decrypted_secret'
    mock_cipher.decrypt.return_value = mock_decrypted
    mock_private_key = 'mock_private_key'
    access_token_secret = 'ZW5jcnlwdGVkX3NlY3JldA=='  # base64 encoded  # noqa: S105

    # Act
    result = calculate_live_session_token_prepend(access_token_secret, mock_private_key)

    # Assert
    mock_b64decode.assert_called_once_with(access_token_secret)
    mock_cipher_new.assert_called_once_with(mock_private_key)
    mock_cipher.decrypt.assert_called_once_with(mock_encrypted_bytes, None)
    expected_hex = mock_decrypted.hex()
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

def test_generate_dh_challenge_default_generator():
    # Arrange
    dh_prime = 'ff'
    dh_random = 'a'

    # Act
    result = generate_dh_challenge(dh_prime, dh_random)

    # Assert
    # With generator=2, random=a(10), prime=ff(255): 2^10 mod 255 = 1024 mod 255 = 4
    expected = hex(pow(2, 10, 255))[2:]
    assert result == expected

def test_generate_dh_challenge_custom_generator():
    # Arrange
    dh_prime = 'ff'
    dh_random = '2'
    dh_generator = 3

    # Act
    result = generate_dh_challenge(dh_prime, dh_random, dh_generator)

    # Assert
    # With generator=3, random=2, prime=ff(255): 3^2 mod 255 = 9
    expected = hex(pow(3, 2, 255))[2:]
    assert result == expected


def test_get_access_token_secret_bytes():
    # Arrange
    hex_string = 'deadbeef'

    # Act
    result = get_access_token_secret_bytes(hex_string)

    # Assert
    expected = [222, 173, 190, 239]
    assert result == expected
    assert isinstance(result, list)
    assert all(isinstance(b, int) for b in result)

def test_get_access_token_secret_bytes_empty():

    # Act
    result = get_access_token_secret_bytes('')

    # Assert
    assert result == []

def test_to_byte_array_simple():
    # Arrange
    # Test with 255 (0xff) - binary is 11111111 (8 bits), so gets leading zero

    # Act
    result = to_byte_array(255)

    # Assert
    expected = [0, 255]  # Leading zero for 8-bit alignment
    assert result == expected

def test_to_byte_array_with_padding():

    # Act
    result = to_byte_array(15)

    # Assert
    expected = [15]
    assert result == expected

def test_to_byte_array_multiple_bytes():
    # Arrange
    # Test with 65535 (0xffff) - binary is 16 bits, so gets leading zero

    # Act
    result = to_byte_array(65535)

    # Assert
    expected = [0, 255, 255]  # Leading zero for 16-bit alignment
    assert result == expected

def test_to_byte_array_byte_alignment():
    # Arrange
    # Test with 256 (0x100) - binary is 100000000 (9 bits), no leading zero needed

    # Act
    result = to_byte_array(256)

    # Assert
    expected = [1, 0]  # No leading zero for 9-bit number
    assert result == expected


@pytest.mark.parametrize("calculated_signature,provided_signature,expected_result", [
    ('expected_signature', 'expected_signature', True),
    ('calculated_signature', 'different_signature', False),
])
@patch('ibind.oauth.oauth1a.HMAC.new')
@patch('ibind.oauth.oauth1a.base64.b64decode')
def test_validate_live_session_token(mock_b64decode, mock_hmac_new, calculated_signature, provided_signature, expected_result):
    # Arrange
    mock_token_bytes = b'decoded_token'
    mock_b64decode.return_value = mock_token_bytes
    mock_hmac = mock_hmac_new.return_value
    mock_hmac.hexdigest.return_value = calculated_signature
    live_session_token = 'dGVzdF90b2tlbg=='  # noqa: S105
    consumer_key = 'test_consumer_key'  # noqa: S106

    # Act
    result = validate_live_session_token(live_session_token, provided_signature, consumer_key)

    # Assert
    mock_b64decode.assert_called_once_with(live_session_token)
    mock_hmac_new.assert_called_once()
    mock_hmac.update.assert_called_once_with(consumer_key.encode('utf-8'))
    mock_hmac.hexdigest.assert_called_once()
    assert result is expected_result


@patch('ibind.oauth.oauth1a.get_access_token_secret_bytes')
@patch('ibind.oauth.oauth1a.to_byte_array')
@patch('ibind.oauth.oauth1a.HMAC.new')
@patch('ibind.oauth.oauth1a.base64.b64encode')
def test_calculate_live_session_token(mock_b64encode, mock_hmac_new, mock_to_byte_array, mock_get_bytes):
    # Arrange
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

    # Act
    result = calculate_live_session_token(dh_prime, dh_random_value, dh_response, prepend)

    # Assert
    mock_get_bytes.assert_called_once_with(prepend)
    # Verify DH shared secret calculation: 3^2 mod 255 = 9
    expected_shared_secret = pow(3, 2, 255)
    mock_to_byte_array.assert_called_once_with(expected_shared_secret)
    mock_hmac_new.assert_called_once()
    mock_hmac.update.assert_called_once_with(bytes([1, 2, 3, 4]))
    mock_b64encode.assert_called_once_with(mock_digest)
    assert result == 'encoded_token'



@pytest.fixture
def oauth_config():
    """Create a sample OAuth1aConfig for testing."""
    return OAuth1aConfig(
        oauth_rest_url='https://api.ibkr.com',
        live_session_token_endpoint='/v1/api/oauth/live_session_token',  # noqa: S106
        access_token='test_access_token',  # noqa: S106
        access_token_secret='test_access_token_secret',  # noqa: S106
        consumer_key='test_consumer_key',  # noqa: S106
        dh_prime='test_dh_prime',  # noqa: S106
        encryption_key_fp='/tmp/encryption_key.pem',  # noqa: S108
        signature_key_fp='/tmp/signature_key.pem',  # noqa: S108
        dh_generator='2',
        realm='limited_poa'
    )


@pytest.mark.parametrize("signature_method,live_session_token,expected_sig_calls", [
    ("HMAC-SHA256", "test_session_token", ["mock_hmac_sig"]),
    ("RSA-SHA256", None, ["mock_read_key", "mock_rsa_sig"]),
])
@patch('ibind.oauth.oauth1a.generate_oauth_nonce')
@patch('ibind.oauth.oauth1a.generate_request_timestamp')
@patch('ibind.oauth.oauth1a.generate_base_string')
@patch('ibind.oauth.oauth1a.read_private_key')
@patch('ibind.oauth.oauth1a.generate_hmac_sha_256_signature')
@patch('ibind.oauth.oauth1a.generate_rsa_sha_256_signature')
@patch('ibind.oauth.oauth1a.generate_authorization_header_string')
def test_generate_oauth_headers_signature_methods(
    mock_header_string, mock_rsa_sig, mock_hmac_sig, mock_read_key, mock_base_string,
    mock_timestamp, mock_nonce, oauth_config, signature_method, live_session_token, expected_sig_calls
):
    # Arrange
    mock_nonce.return_value = 'test_nonce'
    mock_timestamp.return_value = '1234567890'
    mock_base_string.return_value = 'test_base_string'
    mock_hmac_sig.return_value = 'test_hmac_signature'
    mock_rsa_sig.return_value = 'test_rsa_signature'
    mock_header_string.return_value = 'OAuth realm="limited_poa", oauth_consumer_key="test_consumer_key"'
    mock_private_key = MagicMock()
    mock_read_key.return_value = mock_private_key

    request_method = 'POST'
    request_url = 'https://api.ibkr.com/v1/test'

    # Act
    result = generate_oauth_headers(
        oauth_config=oauth_config,
        request_method=request_method,
        request_url=request_url,
        live_session_token=live_session_token,
        signature_method=signature_method
    )

    # Assert
    assert isinstance(result, dict)
    assert 'Authorization' in result
    assert 'Accept' in result
    assert 'User-Agent' in result
    assert result['User-Agent'] == 'ibind'
    assert result['Host'] == 'api.ibkr.com'

    if signature_method == 'HMAC-SHA256':
        mock_hmac_sig.assert_called_once_with(base_string='test_base_string', live_session_token=live_session_token)
        mock_read_key.assert_not_called()
        mock_rsa_sig.assert_not_called()
    else:  # RSA-SHA256
        mock_read_key.assert_called_once_with(oauth_config.signature_key_fp)
        mock_rsa_sig.assert_called_once_with(base_string='test_base_string', private_signature_key=mock_private_key)
        mock_hmac_sig.assert_not_called()


@pytest.mark.parametrize("extra_data_type,extra_data_value,expected_key,expected_location", [
    ("extra_headers", {'custom_header': 'custom_value'}, 'custom_header', 'request_headers'),
    ("request_params", {'param1': 'value1', 'param2': 'value2'}, 'request_params', 'kwargs'),
])
def test_generate_oauth_headers_with_extra_data(oauth_config, extra_data_type, extra_data_value, expected_key, expected_location):
    # Arrange
    request_method = 'GET'
    request_url = 'https://api.ibkr.com/v1/test'
    kwargs = {extra_data_type: extra_data_value}

    with patch('ibind.oauth.oauth1a.generate_oauth_nonce') as mock_nonce, \
         patch('ibind.oauth.oauth1a.generate_request_timestamp') as mock_timestamp, \
         patch('ibind.oauth.oauth1a.generate_base_string') as mock_base_string, \
         patch('ibind.oauth.oauth1a.generate_hmac_sha_256_signature') as mock_hmac_sig, \
         patch('ibind.oauth.oauth1a.generate_authorization_header_string') as mock_header_string:

        mock_nonce.return_value = 'test_nonce'
        mock_timestamp.return_value = '1234567890'
        mock_base_string.return_value = 'test_base_string'
        mock_hmac_sig.return_value = 'test_signature'
        mock_header_string.return_value = 'OAuth realm="limited_poa"'

        # Act
        result = generate_oauth_headers(
            oauth_config=oauth_config,
            request_method=request_method,
            request_url=request_url,
            signature_method='HMAC-SHA256',
            **kwargs
        )

        # Assert
        assert isinstance(result, dict)
        mock_base_string.assert_called_once()
        call_args = mock_base_string.call_args

        if expected_location == 'request_headers':
            request_headers = call_args.kwargs.get('request_headers', {})
            assert expected_key in request_headers
            assert request_headers[expected_key] == extra_data_value[expected_key]
        else:  # kwargs
            assert expected_key in call_args.kwargs
            assert call_args.kwargs[expected_key] == extra_data_value


@patch('ibind.oauth.oauth1a.generate_dh_random_bytes')
@patch('ibind.oauth.oauth1a.generate_dh_challenge')
@patch('ibind.oauth.oauth1a.calculate_live_session_token_prepend')
@patch('ibind.oauth.oauth1a.read_private_key')
def test_prepare_oauth(mock_read_key, mock_prepend, mock_dh_challenge, mock_dh_random, oauth_config):
    # Arrange
    mock_dh_random.return_value = 'random_value'
    mock_dh_challenge.return_value = 'challenge_value'
    mock_prepend.return_value = 'prepend_value'
    mock_private_key = MagicMock()
    mock_read_key.return_value = mock_private_key

    # Act
    prepend, extra_headers, dh_random = prepare_oauth(oauth_config)

    # Assert
    assert prepend == 'prepend_value'
    assert extra_headers == {'diffie_hellman_challenge': 'challenge_value'}
    assert dh_random == 'random_value'

    mock_dh_random.assert_called_once()
    mock_dh_challenge.assert_called_once_with(
        dh_prime=oauth_config.dh_prime,
        dh_random='random_value',
        dh_generator=int(oauth_config.dh_generator)
    )
    mock_read_key.assert_called_once_with(private_key_fp=oauth_config.encryption_key_fp)
    mock_prepend.assert_called_once_with(
        access_token_secret=oauth_config.access_token_secret,
        private_encryption_key=mock_private_key
    )


@pytest.fixture
def mock_client():
    """Create a mock IbkrClient for testing."""
    client = MagicMock()
    client.base_url = 'https://api.ibkr.com'

    # Mock successful API response
    mock_response = MagicMock()
    mock_response.data = {
        'live_session_token_expiration': 1234567890,
        'diffie_hellman_response': 'dh_response_value',
        'live_session_token_signature': 'lst_signature_value'
    }
    client.post.return_value = mock_response

    return client


@patch('ibind.oauth.oauth1a.prepare_oauth')
@patch('ibind.oauth.oauth1a.generate_oauth_headers')
@patch('ibind.oauth.oauth1a.calculate_live_session_token')
def test_req_live_session_token_success(mock_calculate_lst, mock_gen_headers, mock_prepare, oauth_config, mock_client):
    # Arrange
    mock_prepare.return_value = ('prepend_value', {'diffie_hellman_challenge': 'challenge'}, 'dh_random_value')
    mock_gen_headers.return_value = {'Authorization': 'OAuth realm="limited_poa"'}
    mock_calculate_lst.return_value = 'calculated_live_session_token'

    # Act
    live_session_token, lst_expires, lst_signature = req_live_session_token(mock_client, oauth_config)

    # Assert
    assert live_session_token == 'calculated_live_session_token'  # noqa: S105
    assert lst_expires == 1234567890
    assert lst_signature == 'lst_signature_value'

    mock_prepare.assert_called_once_with(oauth_config)
    mock_gen_headers.assert_called_once_with(
        oauth_config=oauth_config,
        request_method='POST',
        request_url=f'{mock_client.base_url}{oauth_config.live_session_token_endpoint}',
        extra_headers={'diffie_hellman_challenge': 'challenge'},
        signature_method='RSA-SHA256',
        prepend='prepend_value'
    )
    mock_client.post.assert_called_once_with(
        oauth_config.live_session_token_endpoint,
        extra_headers={'Authorization': 'OAuth realm="limited_poa"'}
    )
    mock_calculate_lst.assert_called_once_with(
        dh_prime=oauth_config.dh_prime,
        dh_random_value='dh_random_value',
        dh_response='dh_response_value',
        prepend='prepend_value'
    )


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
