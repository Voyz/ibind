"""
Unit tests for OAuthConfig base class.

The OAuthConfig class provides the abstract base class for OAuth configuration management
across different OAuth protocol versions. This base class defines common attributes
and methods for handling OAuth authentication lifecycle, including initialization,
maintenance, and shutdown behaviors.

Core Functionality Tested:
==========================

1. **Abstract Method Implementation**:
   - Version method abstract enforcement
   - Proper NotImplementedError raising for abstract methods

2. **Configuration Management**:
   - Default parameter initialization from environment variables
   - Configuration copying with modifications
   - Attribute validation during copy operations

3. **Lifecycle Control**:
   - OAuth initialization behavior configuration
   - Brokerage session management settings
   - OAuth maintenance and shutdown control

Key Components:
===============

- **OAuthConfig**: Abstract base class for OAuth configuration
- **Configuration Copying**: Deep configuration modification capabilities
- **Environment Integration**: Default values from environment variables
- **Abstract Method Pattern**: Enforced implementation in subclasses

Test Coverage:
==============

This test suite focuses on the base class functionality that provides the foundation
for OAuth protocol implementations:

- **Abstract Method Validation**: Ensures subclass implementation requirements
- **Configuration Copying**: Validates safe configuration modification patterns
- **Attribute Management**: Tests proper attribute validation and assignment
- **Default Behavior**: Verifies correct environment variable integration

The tests ensure that the base class provides a solid foundation for OAuth protocol
implementations while maintaining proper abstraction boundaries and validation.

Security Considerations:
========================

The base class handles OAuth configuration parameters that form the foundation
for secure authentication flows. Tests ensure proper validation without exposing
sensitive configuration details or creating security vulnerabilities through
improper configuration handling.
"""

import pytest

from ibind.oauth import OAuthConfig


class ConcreteOAuthConfig(OAuthConfig):
    """Concrete implementation of OAuthConfig for testing purposes."""

    def version(self):
        return "test_version"


@pytest.fixture
def concrete_config():
    """Create a concrete OAuthConfig implementation for testing."""
    return ConcreteOAuthConfig(
        init_oauth=True,
        init_brokerage_session=False,
        maintain_oauth=True,
        shutdown_oauth=False
    )


def test_oauth_config_abstract_version_method():
    # Arrange

    # Act & Assert
    with pytest.raises(TypeError, match="Can't instantiate abstract class OAuthConfig"):
        OAuthConfig()


def test_concrete_config_version_method(concrete_config):
    # Arrange

    # Act
    result = concrete_config.version()

    # Assert
    assert result == "test_version"


def test_verify_config_base_implementation(concrete_config):
    # Arrange

    # Act
    result = concrete_config.verify_config()

    # Assert
    # Base implementation returns None
    assert result is None


def test_oauth_config_default_attributes():
    # Arrange & Act
    config = ConcreteOAuthConfig()

    # Assert
    # Test that default values are set (these come from var module)
    assert hasattr(config, 'init_oauth')
    assert hasattr(config, 'init_brokerage_session')
    assert hasattr(config, 'maintain_oauth')
    assert hasattr(config, 'shutdown_oauth')


def test_copy_method_creates_shallow_copy(concrete_config):
    # Arrange
    original_id = id(concrete_config)

    # Act
    copied_config = concrete_config.copy()

    # Assert
    assert id(copied_config) != original_id
    assert copied_config.init_oauth == concrete_config.init_oauth
    assert copied_config.init_brokerage_session == concrete_config.init_brokerage_session
    assert copied_config.maintain_oauth == concrete_config.maintain_oauth
    assert copied_config.shutdown_oauth == concrete_config.shutdown_oauth


def test_copy_method_with_modifications(concrete_config):
    # Arrange
    original_init_oauth = concrete_config.init_oauth
    original_maintain_oauth = concrete_config.maintain_oauth

    # Act
    copied_config = concrete_config.copy(
        init_oauth=not original_init_oauth,
        maintain_oauth=not original_maintain_oauth
    )

    # Assert
    assert copied_config.init_oauth == (not original_init_oauth)
    assert copied_config.maintain_oauth == (not original_maintain_oauth)
    # Unchanged attributes should remain the same
    assert copied_config.init_brokerage_session == concrete_config.init_brokerage_session
    assert copied_config.shutdown_oauth == concrete_config.shutdown_oauth


def test_copy_method_with_invalid_attribute(concrete_config):
    # Arrange
    invalid_attribute = 'nonexistent_attribute'

    # Act & Assert
    with pytest.raises(AttributeError, match=f'OAuthConfig does not have attribute "{invalid_attribute}"'):
        concrete_config.copy(nonexistent_attribute='some_value')


def test_copy_method_with_multiple_modifications(concrete_config):
    # Arrange
    modifications = {
        'init_oauth': False,
        'init_brokerage_session': True,
        'maintain_oauth': False,
        'shutdown_oauth': True
    }

    # Act
    copied_config = concrete_config.copy(**modifications)

    # Assert
    for attr, expected_value in modifications.items():
        assert getattr(copied_config, attr) == expected_value


def test_copy_preserves_type(concrete_config):
    # Arrange

    # Act
    copied_config = concrete_config.copy()

    # Assert
    assert type(copied_config) is type(concrete_config)
    assert isinstance(copied_config, ConcreteOAuthConfig)
    assert isinstance(copied_config, OAuthConfig)


def test_copy_method_with_no_modifications(concrete_config):
    # Arrange

    # Act
    copied_config = concrete_config.copy()

    # Assert
    # All attributes should be identical
    assert copied_config.init_oauth == concrete_config.init_oauth
    assert copied_config.init_brokerage_session == concrete_config.init_brokerage_session
    assert copied_config.maintain_oauth == concrete_config.maintain_oauth
    assert copied_config.shutdown_oauth == concrete_config.shutdown_oauth
    # But should be a different object
    assert copied_config is not concrete_config


def test_default_values_are_set():
    # Arrange & Act
    config = ConcreteOAuthConfig()

    # Assert
    # Test that all required attributes exist with boolean values
    assert isinstance(config.init_oauth, bool)
    assert isinstance(config.init_brokerage_session, bool)
    assert isinstance(config.maintain_oauth, bool)
    assert isinstance(config.shutdown_oauth, bool)


def test_copy_method_edge_case_empty_kwargs(concrete_config):
    # Arrange
    empty_kwargs = {}

    # Act
    copied_config = concrete_config.copy(**empty_kwargs)

    # Assert
    assert copied_config is not concrete_config
    assert copied_config.init_oauth == concrete_config.init_oauth
