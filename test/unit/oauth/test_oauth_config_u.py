import tempfile
import pytest
from pathlib import Path

from ibind.oauth.oauth1a import OAuth1aConfig


@pytest.fixture
def valid_config():
    """Create a valid OAuth1aConfig for testing."""
    return OAuth1aConfig(
        oauth_rest_url='https://api.ibkr.com',
        live_session_token_endpoint='/v1/api/oauth/live_session_token',  # noqa: S106
        access_token='test_access_token',  # noqa: S106
        access_token_secret='test_access_token_secret',  # noqa: S106
        consumer_key='test_consumer_key',  # noqa: S106
        dh_prime='test_dh_prime',  # noqa: S106
        encryption_key_fp='/tmp/encryption_key.pem',  # noqa: S108
        signature_key_fp='/tmp/signature_key.pem',  # noqa: S108
    )

def test_version_returns_1_0a():
    # Arrange
    config = OAuth1aConfig()

    # Act
    result = config.version()

    # Assert
    assert result == '1.0a'

# TODO Check this test
def test_verify_config_success_with_valid_params():
    # Arrange
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
            consumer_key='test_consumer_key',  # noqa: S106
            dh_prime='test_dh_prime',  # noqa: S106
            encryption_key_fp=enc_file.name,
            signature_key_fp=sig_file.name,
        )

        # Act
        config.verify_config()

        # Assert
        # No exception should be raised

        # Cleanup
        Path(enc_file.name).unlink()
        Path(sig_file.name).unlink()

def test_verify_config_missing_required_params():
    # Arrange
    config = OAuth1aConfig()

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        config.verify_config()

    error_message = str(exc_info.value)
    assert 'OAuth1aConfig is missing required parameters:' in error_message
    # Check that some expected None parameters are mentioned
    expected_missing = ['access_token', 'access_token_secret', 'consumer_key', 'dh_prime']
    for param in expected_missing:
        assert param in error_message

def test_verify_config_partial_missing_params():
    # Arrange
    config = OAuth1aConfig(
        access_token='test_access_token',  # noqa: S106
        consumer_key='test_consumer_key',  # noqa: S106
    )

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        config.verify_config()

    error_message = str(exc_info.value)
    assert 'OAuth1aConfig is missing required parameters:' in error_message
    # Should not contain the provided parameters (using word boundaries)
    import re
    assert re.search(r'\baccess_token\b', error_message) is None
    assert 'consumer_key' not in error_message
    # Should contain missing parameters
    assert 'access_token_secret' in error_message
    assert 'dh_prime' in error_message

def test_verify_config_missing_filepaths():
    # Arrange
    config = OAuth1aConfig(
        oauth_rest_url='https://api.ibkr.com',
        live_session_token_endpoint='/v1/api/oauth/live_session_token',  # noqa: S106
        access_token='test_access_token',  # noqa: S106
        access_token_secret='test_access_token_secret',  # noqa: S106
        consumer_key='test_consumer_key',  # noqa: S106
        dh_prime='test_dh_prime',  # noqa: S106
        encryption_key_fp='/nonexistent/encryption_key.pem',
        signature_key_fp='/nonexistent/signature_key.pem',
    )

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        config.verify_config()

    error_message = str(exc_info.value)
    assert "OAuth1aConfig's filepaths don't exist:" in error_message
    assert 'encryption_key_fp' in error_message
    assert 'signature_key_fp' in error_message

def test_verify_config_partial_missing_filepaths():
    # Arrange
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as enc_file:
        enc_file.write('dummy key content')
        enc_file.flush()

        config = OAuth1aConfig(
            oauth_rest_url='https://api.ibkr.com',
            live_session_token_endpoint='/v1/api/oauth/live_session_token',  # noqa: S106
            access_token='test_access_token',  # noqa: S106
            access_token_secret='test_access_token_secret',  # noqa: S106
            consumer_key='test_consumer_key',  # noqa: S106
            dh_prime='test_dh_prime',  # noqa: S106
            encryption_key_fp=enc_file.name,
            signature_key_fp='/nonexistent/signature_key.pem',
        )

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            config.verify_config()

        error_message = str(exc_info.value)
        assert "OAuth1aConfig's filepaths don't exist:" in error_message
        assert 'encryption_key_fp' not in error_message
        assert 'signature_key_fp' in error_message

        # Cleanup
        Path(enc_file.name).unlink()
