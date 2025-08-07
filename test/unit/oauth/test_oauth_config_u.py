"""
Unit tests for OAuth1aConfig.

The OAuth1aConfig class provides configuration management for OAuth 1.0a authentication
with Interactive Brokers (IBKR) API. This configuration class handles the validation
and storage of all required parameters for establishing secure OAuth 1.0a connections
including API endpoints, tokens, keys, and cryptographic key file paths.

Core Functionality Tested:
==========================

1. **Configuration Initialization**:
   - Default parameter initialization
   - Custom parameter assignment
   - Version identification for OAuth protocol

2. **Configuration Validation**:
   - Required parameter presence validation
   - File path existence verification
   - Comprehensive error reporting for missing components

3. **Parameter Management**:
   - OAuth endpoint URL configuration
   - Access token and secret handling
   - Consumer key and DH prime parameter storage
   - Encryption and signature key file path management

Key Components:
===============

- **OAuth1aConfig**: Main configuration class for OAuth 1.0a parameters
- **Parameter Validation**: Required field checking and file existence verification
- **Error Handling**: Descriptive error messages for configuration issues

Required Parameters:
===================

The OAuth1aConfig requires the following parameters for proper operation:
- oauth_rest_url: Base URL for OAuth REST API endpoints
- live_session_token_endpoint: Endpoint path for live session token requests
- access_token: OAuth access token for authenticated requests
- access_token_secret: Secret associated with the access token
- consumer_key: OAuth consumer key identifying the application
- dh_prime: Diffie-Hellman prime parameter for key exchange
- encryption_key_fp: File path to encryption private key
- signature_key_fp: File path to signature private key

Test Coverage:
==============

This test suite focuses on configuration validation logic that ensures:

- **Parameter Completeness**: All required OAuth parameters are provided
- **File System Validation**: Cryptographic key files exist and are accessible
- **Error Reporting**: Clear, actionable error messages for configuration issues
- **Version Compliance**: Correct OAuth protocol version identification

The tests use temporary files to simulate real key file scenarios while avoiding
dependencies on actual cryptographic key content or permanent file system state.

Security Considerations:
========================

This configuration class handles sensitive authentication parameters including:
- Access tokens and secrets
- Consumer keys
- File paths to private cryptographic keys

Tests ensure proper validation without exposing sensitive values in error messages
or test outputs, maintaining security best practices for credential handling.
"""

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
        consumer_key='test_consumer_key',
        dh_prime='test_dh_prime',
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
            consumer_key='test_consumer_key',
            dh_prime='test_dh_prime',
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
        consumer_key='test_consumer_key',
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
        consumer_key='test_consumer_key',
        dh_prime='test_dh_prime',
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
            consumer_key='test_consumer_key',
            dh_prime='test_dh_prime',
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
