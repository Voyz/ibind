import pytest
from unittest.mock import MagicMock
from ibind.client.ibkr_client import IbkrClient

@pytest.fixture
def client():
    # Minimal config for IbkrClient, mock dependencies
    c = IbkrClient(use_oauth=False)
    c.check_auth_status = MagicMock()
    c.stop_tickler = MagicMock()
    c.oauth_init = MagicMock()
    c.oauth_config = MagicMock()
    c.oauth_config.maintain_oauth = True
    c.oauth_config.init_brokerage_session = True
    c.oauth_config.shutdown_oauth = False
    return c


def test_handle_auth_status_healthy(client, caplog):
    ## Arrange
    client.check_auth_status.return_value = True

    ## Act
    with caplog.at_level("WARNING", logger="ibind.client.ibkr_client"):
        assert client.handle_auth_status() is True

    ## Assert
    # No warning should be logged
    assert not any("IBKR connection is not healthy" in r.message for r in caplog.records)
    client.check_auth_status.assert_called_once()
    client.stop_tickler.assert_not_called()
    client.oauth_init.assert_not_called()


def test_handle_auth_status_not_healthy_no_oauth(client, caplog):
    ## Arrange
    client.check_auth_status.return_value = False
    client._use_oauth = False

    ## Act
    with caplog.at_level("WARNING", logger="ibind.client.ibkr_client"):
        assert client.handle_auth_status() is False

    ## Assert
    assert any("IBKR connection is not healthy. Ensure authentication with the Gateway is re-established." in r.message for r in caplog.records)
    client.stop_tickler.assert_not_called()
    client.oauth_init.assert_not_called()


def test_handle_auth_status_not_healthy_oauth_success(client, caplog):
    ## Arrange
    client.check_auth_status.return_value = False
    client._use_oauth = True
    client.stop_tickler.side_effect = None
    client.oauth_init.side_effect = None

    ## Act
    with caplog.at_level("WARNING", logger="ibind.client.ibkr_client"):
        assert client.handle_auth_status() is False

    ## Assert
    assert any("IBKR connection is not healthy. Attempting to re-establish OAuth authentication." in r.message for r in caplog.records)
    client.stop_tickler.assert_called_once_with(15)
    client.oauth_init.assert_called_once_with(maintain_oauth=True, init_brokerage_session=True)