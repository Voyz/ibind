from unittest.mock import MagicMock, patch

import pytest

from ibind.ws_v2.runtime.ws_health_monitor import WsHealthMonitor
from ibind.ws_v2.runtime.ws_state_manager import WsStateManager, WsState
from ibind.ws_v2.ws_transport import WsTransport
from test.test_utils import capture_logs, mock_module_time


@pytest.fixture
def mock_transport():
    transport = MagicMock(spec=WsTransport)
    transport.is_ready.return_value = True
    transport.check_ping.return_value = True
    transport.get_time_since_last_ping.return_value = 5.0
    return transport


@pytest.fixture
def mock_state_manager():
    state_manager = MagicMock(spec=WsStateManager)
    state_manager.get_state.return_value = WsState.AUTHENTICATED
    state_manager.is_authenticated.return_value = True
    state_manager.last_heartbeat = None
    return state_manager


@pytest.fixture
def mock_get_authenticated():
    return MagicMock(return_value=True)


@pytest.fixture
def health_monitor(mock_transport, mock_state_manager, mock_get_authenticated):
    return WsHealthMonitor(
        transport=mock_transport,
        state_manager=mock_state_manager,
        max_ping_interval=20.0,
        get_authenticated=mock_get_authenticated,
        reconnect_timeout=5.0,
        health_check_interval=10.0,
    )


class TestCheckShouldReset:
    @capture_logs()
    def test_returns_false_when_transport_not_ready(self, health_monitor, mock_transport):
        """check_should_reset returns False when transport is not ready."""
        ## Arrange
        mock_transport.is_ready.return_value = False

        ## Act
        result = health_monitor.check_should_reset()

        ## Assert
        assert result is False
        mock_transport.is_ready.assert_called_once()

    @capture_logs()
    def test_returns_false_when_state_not_open_or_authenticated(self, health_monitor, mock_state_manager):
        """check_should_reset returns False when state is neither OPEN nor AUTHENTICATED."""
        ## Arrange
        mock_state_manager.get_state.return_value = WsState.STARTING

        ## Act
        result = health_monitor.check_should_reset()

        ## Assert
        assert result is False

    @capture_logs(expected_errors=['Last WebSocket ping happened'], partial_match=True)
    def test_returns_false_when_ping_fails_with_reconnect_timeout(self, health_monitor, mock_transport):
        """check_should_reset returns False when ping fails but reconnect_timeout is set."""
        ## Arrange
        mock_transport.check_ping.return_value = False
        mock_transport.get_time_since_last_ping.return_value = 25.0
        health_monitor._reconnect_timeout = 5.0

        ## Act
        result = health_monitor.check_should_reset()

        ## Assert
        assert result is False
        mock_transport.check_ping.assert_called_once_with(20.0)

    @capture_logs(expected_errors=['Last WebSocket ping happened'], partial_match=True)
    def test_returns_true_when_ping_fails_without_reconnect_timeout(self, health_monitor, mock_transport):
        """check_should_reset returns True when ping fails and reconnect_timeout is None."""
        ## Arrange
        mock_transport.check_ping.return_value = False
        mock_transport.get_time_since_last_ping.return_value = 30.0
        health_monitor._reconnect_timeout = None

        ## Act
        result = health_monitor.check_should_reset()

        ## Assert
        assert result is True

    @capture_logs(expected_errors=['Last heartbeat happened'], partial_match=True)
    def test_returns_true_when_heartbeat_exceeds_max_interval(self, health_monitor, mock_state_manager):
        """check_should_reset returns True when heartbeat exceeds max_ping_interval."""
        ## Arrange
        with mock_module_time('ibind.ws_v2.runtime.ws_health_monitor', time_sequence=[1000.0]):
            mock_state_manager.last_heartbeat = 950.0

            ## Act
            result = health_monitor.check_should_reset()

        ## Assert
        assert result is True

    @capture_logs()
    def test_returns_false_when_heartbeat_within_interval(self, health_monitor, mock_state_manager):
        """check_should_reset returns False when heartbeat is within max_ping_interval."""
        ## Arrange
        with mock_module_time('ibind.ws_v2.runtime.ws_health_monitor', time_sequence=[1000.0]):
            mock_state_manager.last_heartbeat = 995.0

            ## Act
            result = health_monitor.check_should_reset()

        ## Assert
        assert result is False

    @capture_logs()
    def test_returns_false_when_heartbeat_is_none(self, health_monitor, mock_state_manager):
        """check_should_reset returns False when last_heartbeat is None."""
        ## Arrange
        mock_state_manager.last_heartbeat = None

        ## Act
        result = health_monitor.check_should_reset()

        ## Assert
        assert result is False

    @capture_logs(expected_errors=['State is not ready while reporting authenticated=True'], partial_match=True)
    def test_updates_state_when_authenticated_but_state_not_ready(self, health_monitor, mock_state_manager, mock_get_authenticated):
        """check_should_reset updates state to AUTHENTICATED when get_authenticated returns True but state is not authenticated."""
        ## Arrange
        mock_state_manager.is_authenticated.return_value = False
        mock_get_authenticated.return_value = True

        ## Act
        result = health_monitor.check_should_reset()

        ## Assert
        assert result is False
        mock_state_manager.set_state.assert_called_once_with(WsState.AUTHENTICATED)

    @capture_logs()
    def test_returns_false_when_not_authenticated_and_get_authenticated_false(self, health_monitor, mock_state_manager, mock_get_authenticated):
        """check_should_reset returns False when not authenticated and get_authenticated returns False."""
        ## Arrange
        mock_state_manager.is_authenticated.return_value = False
        mock_get_authenticated.return_value = False

        ## Act
        result = health_monitor.check_should_reset()

        ## Assert
        assert result is False
        mock_state_manager.set_state.assert_not_called()

    @capture_logs()
    def test_returns_false_when_all_checks_pass(self, health_monitor):
        """check_should_reset returns False when all health checks pass."""
        ## Act
        result = health_monitor.check_should_reset()

        ## Assert
        assert result is False


class TestHealthOk:
    @capture_logs()
    def test_returns_true_when_within_health_check_interval(self, health_monitor):
        """health_ok returns True when called within health_check_interval."""
        ## Arrange
        health_monitor._last_health_check = 0
        with mock_module_time('ibind.ws_v2.runtime.ws_health_monitor', time_sequence=[5.0]):
            ## Act
            result = health_monitor.health_ok()

        ## Assert
        assert result is True
        assert health_monitor._last_health_check == 0.0

    @capture_logs()
    def test_returns_true_when_check_should_reset_returns_false(self, health_monitor):
        """health_ok returns True when check_should_reset returns False."""
        ## Arrange
        health_monitor._last_health_check = 0
        with mock_module_time('ibind.ws_v2.runtime.ws_health_monitor', time_sequence=[115.0]):
            with patch.object(health_monitor, 'check_should_reset', return_value=False):
                ## Act
                result = health_monitor.health_ok()

        ## Assert
        assert result is True
        assert health_monitor._last_health_check == 115.0

    @capture_logs()
    def test_returns_false_and_sets_degraded_when_check_should_reset_returns_true(self, health_monitor, mock_state_manager):
        """health_ok returns False and sets state to DEGRADED when check_should_reset returns True."""
        ## Arrange
        health_monitor._last_health_check = 0
        with mock_module_time('ibind.ws_v2.runtime.ws_health_monitor', time_sequence=[115.0]):
            with patch.object(health_monitor, 'check_should_reset', return_value=True):
                ## Act
                result = health_monitor.health_ok()

        ## Assert
        assert result is False
        assert health_monitor._last_health_check == 115.0
        mock_state_manager.set_state.assert_called_once_with(WsState.DEGRADED)

    @capture_logs()
    def test_updates_last_health_check_on_each_interval_check(self, health_monitor):
        """health_ok updates _last_health_check when health_check_interval has passed."""
        ## Arrange
        health_monitor._last_health_check = 0
        with mock_module_time('ibind.ws_v2.runtime.ws_health_monitor', time_sequence=[111.0]):
            # health_monitor = health_monitor_factory()
            with patch.object(health_monitor, 'check_should_reset', return_value=False):
                ## Act
                result = health_monitor.health_ok()

        ## Assert
        assert result is True
        assert health_monitor._last_health_check == 111.0
