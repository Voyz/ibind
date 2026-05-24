from unittest.mock import MagicMock

import pytest

from ibind.ws_v2.runtime.ws_state_manager import WsStateManager, WsState
from test.test_utils import capture_logs


@pytest.fixture
def on_state_change():
    return MagicMock()


@pytest.fixture
def state_manager(on_state_change):
    return WsStateManager(on_state_change=on_state_change)


class TestWsStateManagerInit:
    @capture_logs()
    def test_init_sets_attributes(self, on_state_change):
        """WsStateManager.__init__ initializes all attributes correctly."""
        ## Act
        manager = WsStateManager(on_state_change=on_state_change, lock_timeout=30.0)

        ## Assert
        assert manager._on_state_change is on_state_change
        assert manager._state == WsState.STOPPED
        assert manager.last_heartbeat is None


class TestWsStateManagerGetState:
    @capture_logs()
    def test_get_state_returns_current_state(self, state_manager):
        """get_state returns current state."""
        ## Arrange
        state_manager._state = WsState.OPEN

        ## Act
        result = state_manager.get_state()

        ## Assert
        assert result == WsState.OPEN


class TestWsStateManagerIsAuthenticated:
    @capture_logs()
    def test_is_authenticated_returns_true_when_authenticated(self, state_manager):
        """is_authenticated returns True when state is AUTHENTICATED."""
        ## Arrange
        state_manager._state = WsState.AUTHENTICATED

        ## Act
        result = state_manager.is_authenticated()

        ## Assert
        assert result is True

    @capture_logs()
    def test_is_authenticated_returns_false_when_not_authenticated(self, state_manager):
        """is_authenticated returns False when state is not AUTHENTICATED."""
        ## Arrange
        state_manager._state = WsState.OPEN

        ## Act
        result = state_manager.is_authenticated()

        ## Assert
        assert result is False


class TestWsStateManagerSetState:
    @capture_logs()
    def test_set_state_updates_state(self, state_manager, on_state_change):
        """set_state updates the state and calls on_state_change callback."""
        ## Act
        state_manager.set_state(WsState.OPEN)

        ## Assert
        assert state_manager._state == WsState.OPEN
        on_state_change.assert_called_once_with(WsState.STOPPED, WsState.OPEN)

    @capture_logs()
    def test_set_state_calls_callback_with_previous_and_new_state(self, state_manager, on_state_change):
        """set_state passes previous and new state to callback."""
        ## Arrange
        state_manager._state = WsState.OPEN

        ## Act
        state_manager.set_state(WsState.AUTHENTICATED)

        ## Assert
        on_state_change.assert_called_once_with(WsState.OPEN, WsState.AUTHENTICATED)
