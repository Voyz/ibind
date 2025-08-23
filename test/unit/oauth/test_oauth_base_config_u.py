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


