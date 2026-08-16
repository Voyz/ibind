import threading
from unittest.mock import MagicMock, patch

import pytest

from ibind.ws.runtime.ws_lifecycle import WsLifecycle
from ibind.ws.runtime.ws_state_manager import WsStateManager, WsState
from ibind.ws.ws_transport import WsTransport
from test.test_utils import capture_logs


@pytest.fixture
def mock_state_manager():
    return WsStateManager(on_state_change=MagicMock())


@pytest.fixture
def mock_runtime_worker():
    worker = MagicMock()
    worker.running = False
    worker.run = MagicMock()
    worker.wait_for_one_cycle = MagicMock()
    return worker


@pytest.fixture
def mock_transport():
    transport = MagicMock(spec=WsTransport)
    transport.connect = MagicMock()
    transport.stop = MagicMock()
    transport.reset_websocket_app = MagicMock()
    transport.set_degraded = MagicMock()
    return transport


@pytest.fixture
def lifecycle(mock_state_manager, mock_runtime_worker, mock_transport):
    return WsLifecycle(
        state_manager=mock_state_manager,
        connection_timeout=1.0,
        runtime_worker=mock_runtime_worker,
        transport=mock_transport,
    )


class TestStopTransportThread:
    @capture_logs(logger_level='DEBUG', expected_errors=['Joining transport thread'], partial_match=True)
    def test_stop_transport_thread_joins_thread(self, lifecycle):
        """WsLifecycle._stop_transport_thread joins the transport thread."""
        ## Arrange
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = False
        lifecycle._transport_thread = mock_thread

        ## Act
        result = lifecycle._stop_transport_thread()

        ## Assert
        lifecycle._transport.stop.assert_called_once()
        mock_thread.join.assert_called_once_with(1.0)
        assert result is True
        assert lifecycle._transport_thread is None

    @capture_logs()
    def test_stop_transport_thread_returns_true_when_thread_none(self, lifecycle):
        """WsLifecycle._stop_transport_thread returns True when thread is None."""
        ## Arrange
        lifecycle._transport_thread = None

        ## Act
        result = lifecycle._stop_transport_thread()

        ## Assert
        lifecycle._transport.stop.assert_called_once()
        assert result is True

    @capture_logs(logger_level='ERROR', expected_errors=['Transport thread failed to stop within timeout'], partial_match=True)
    def test_stop_transport_thread_returns_false_when_thread_alive(self, lifecycle):
        """WsLifecycle._stop_transport_thread returns False and keeps reference when thread is still alive."""
        ## Arrange
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        lifecycle._transport_thread = mock_thread

        ## Act
        result = lifecycle._stop_transport_thread()

        ## Assert
        assert result is False
        assert lifecycle._transport_thread is mock_thread

    @capture_logs(logger_level='ERROR', expected_errors=['Failed to stop transport thread'], partial_match=True)
    def test_stop_transport_thread_logs_exception(self, lifecycle):
        """WsLifecycle._stop_transport_thread logs exceptions and returns False."""
        ## Arrange
        lifecycle._transport.stop = MagicMock(side_effect=RuntimeError('stop error'))

        ## Act
        result = lifecycle._stop_transport_thread()

        ## Assert
        assert result is False


class TestStart:
    @capture_logs()
    def test_start_returns_false_when_state_not_stopped(self, lifecycle):
        """WsLifecycle.start returns False when state is not STOPPED."""
        ## Arrange
        lifecycle._state_manager.set_state(WsState.OPEN)

        ## Act
        result = lifecycle.start()

        ## Assert
        assert result is False

    @capture_logs(logger_level='ERROR', expected_errors=['Runtime thread must be stopped'], partial_match=True)
    def test_start_returns_false_when_runtime_thread_alive(self, lifecycle):
        """WsLifecycle.start returns False when runtime thread is still alive."""
        ## Arrange
        lifecycle._state_manager.set_state(WsState.STOPPED)
        lifecycle._runtime_thread = MagicMock()
        lifecycle._runtime_thread.is_alive.return_value = True

        ## Act
        result = lifecycle.start()

        ## Assert
        assert result is False

    @capture_logs(logger_level='ERROR', expected_errors=['Transport thread must be stopped'], partial_match=True)
    def test_start_returns_false_when_transport_thread_alive(self, lifecycle):
        """WsLifecycle.start returns False when transport thread is still alive."""
        ## Arrange
        lifecycle._state_manager.set_state(WsState.STOPPED)
        lifecycle._transport_thread = MagicMock()
        lifecycle._transport_thread.is_alive.return_value = True

        ## Act
        result = lifecycle.start()

        ## Assert
        assert result is False

    @capture_logs(logger_level='INFO', expected_errors=['Starting WebSocket runtime'], partial_match=True)
    def test_start_sets_state_and_returns_true_on_success(self, lifecycle):
        """WsLifecycle.start sets STARTING and returns True when connection succeeds."""
        ## Arrange
        lifecycle._state_manager.set_state(WsState.STOPPED)
        lifecycle._new_runtime_thread = MagicMock()

        ## Act
        with patch('ibind.ws.runtime.ws_lifecycle.wait_until', return_value=True):
            result = lifecycle.start()

        ## Assert
        assert lifecycle._state_manager.get_state() == WsState.STARTING
        assert lifecycle._runtime_worker.running is True
        lifecycle._new_runtime_thread.assert_called_once()
        assert result is True

    @capture_logs(logger_level='INFO', expected_errors=['Starting WebSocket runtime', 'Starting timeout'], partial_match=True)
    def test_start_returns_false_on_timeout(self, lifecycle):
        """WsLifecycle.start returns False when connection times out."""
        ## Arrange
        lifecycle._state_manager.set_state(WsState.STOPPED)
        lifecycle._new_runtime_thread = MagicMock()

        ## Act
        with patch('ibind.ws.runtime.ws_lifecycle.wait_until', return_value=False):
            result = lifecycle.start()

        ## Assert
        assert result is False


class TestStop:
    @capture_logs()
    def test_stop_returns_early_when_already_stopped(self, lifecycle):
        """WsLifecycle.stop returns early when state is already STOPPED."""
        ## Arrange
        lifecycle._state_manager.set_state(WsState.STOPPED)

        ## Act
        lifecycle.stop()

        ## Assert
        lifecycle._runtime_worker.wait_for_one_cycle.assert_not_called()

    @capture_logs()
    def test_stop_raises_when_called_from_runtime_thread(self, lifecycle):
        """WsLifecycle.stop raises RuntimeError when called from runtime thread."""
        ## Arrange
        lifecycle._state_manager.set_state(WsState.OPEN)
        lifecycle._runtime_thread = threading.current_thread()

        ## Act & Assert
        with pytest.raises(RuntimeError, match='Stopping runtime called from within runtime thread'):
            lifecycle.stop()

    @capture_logs(logger_level='INFO', expected_errors=['Stopping WebSocket runtime'], partial_match=True)
    def test_stop_returns_true_and_transitions_to_stopped_on_success(self, lifecycle):
        """WsLifecycle.stop returns True and transitions to STOPPED when all threads stop cleanly."""
        ## Arrange
        lifecycle._state_manager.set_state(WsState.OPEN)
        lifecycle._runtime_worker.running = True
        lifecycle._runtime_thread = MagicMock()
        lifecycle._runtime_thread.is_alive.return_value = False

        ## Act
        with patch.object(lifecycle, '_stop_transport_thread', return_value=True):
            result = lifecycle.stop()

        ## Assert
        assert result is True
        assert lifecycle._runtime_worker.running is False
        assert lifecycle._state_manager.get_state() == WsState.STOPPED
        assert lifecycle._runtime_thread is None

    @capture_logs(logger_level='ERROR', expected_errors=['Failed to stop transport thread', 'Stop incomplete'], partial_match=True)
    def test_stop_returns_false_when_transport_thread_fails(self, lifecycle):
        """WsLifecycle.stop returns False when transport thread fails to stop."""
        ## Arrange
        lifecycle._state_manager.set_state(WsState.OPEN)
        lifecycle._runtime_worker.running = True
        lifecycle._runtime_thread = MagicMock()
        lifecycle._runtime_thread.is_alive.return_value = False

        ## Act
        with patch.object(lifecycle, '_stop_transport_thread', return_value=False):
            result = lifecycle.stop()

        ## Assert
        assert result is False
        assert lifecycle._state_manager.get_state() == WsState.STOPPING
        lifecycle._transport.set_degraded.assert_called_once_with(True)

    @capture_logs(logger_level='ERROR', expected_errors=['Runtime thread failed to stop within timeout', 'Stop incomplete'], partial_match=True)
    def test_stop_returns_false_when_runtime_thread_fails(self, lifecycle):
        """WsLifecycle.stop returns False and keeps reference when runtime thread fails to stop."""
        ## Arrange
        lifecycle._state_manager.set_state(WsState.OPEN)
        lifecycle._runtime_worker.running = True
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        lifecycle._runtime_thread = mock_thread

        ## Act
        with patch.object(lifecycle, '_stop_transport_thread', return_value=True):
            result = lifecycle.stop()

        ## Assert
        assert result is False
        assert lifecycle._runtime_thread is mock_thread
        assert lifecycle._state_manager.get_state() == WsState.STOPPING

    @capture_logs(logger_level='INFO', expected_errors=['Stopping WebSocket runtime'], partial_match=True)
    def test_stop_waits_for_one_cycle(self, lifecycle):
        """WsLifecycle.stop waits for one runtime cycle before stopping."""
        ## Arrange
        lifecycle._state_manager.set_state(WsState.OPEN)
        lifecycle._runtime_thread = MagicMock()
        lifecycle._runtime_thread.is_alive.return_value = False

        ## Act
        with patch.object(lifecycle, '_stop_transport_thread', return_value=True):
            lifecycle.stop()

        ## Assert
        lifecycle._runtime_worker.wait_for_one_cycle.assert_called_once()

    @capture_logs(logger_level='INFO', expected_errors=['Stopping WebSocket runtime'], partial_match=True)
    def test_stop_sets_transport_degraded(self, lifecycle):
        """WsLifecycle.stop sets transport to degraded state."""
        ## Arrange
        lifecycle._state_manager.set_state(WsState.OPEN)
        lifecycle._runtime_thread = MagicMock()
        lifecycle._runtime_thread.is_alive.return_value = False

        ## Act
        with patch.object(lifecycle, '_stop_transport_thread', return_value=True):
            lifecycle.stop()

        ## Assert
        lifecycle._transport.set_degraded.assert_called_once_with(True)

    @capture_logs(
        logger_level='ERROR',
        expected_errors=['Failed to stop transport thread', 'Runtime thread failed to stop', 'Stop incomplete'],
        partial_match=True,
    )
    def test_stop_returns_false_when_both_threads_fail(self, lifecycle):
        """WsLifecycle.stop returns False when both threads fail to stop."""
        ## Arrange
        lifecycle._state_manager.set_state(WsState.OPEN)
        lifecycle._runtime_worker.running = True
        mock_runtime_thread = MagicMock()
        mock_runtime_thread.is_alive.return_value = True
        lifecycle._runtime_thread = mock_runtime_thread

        ## Act
        with patch.object(lifecycle, '_stop_transport_thread', return_value=False):
            result = lifecycle.stop()

        ## Assert
        assert result is False
        assert lifecycle._runtime_thread is mock_runtime_thread
        assert lifecycle._state_manager.get_state() == WsState.STOPPING


class TestHardReset:
    @capture_logs(logger_level='INFO', expected_errors=['Hard reset'], partial_match=True)
    def test_hard_reset_stops_and_starts_on_success(self, lifecycle):
        """WsLifecycle.hard_reset stops and restarts the lifecycle when stop succeeds."""
        ## Arrange
        lifecycle.stop = MagicMock(return_value=True)
        lifecycle.start = MagicMock(return_value=True)

        ## Act
        result = lifecycle.hard_reset()

        ## Assert
        assert result is True
        lifecycle.stop.assert_called_once()
        lifecycle.start.assert_called_once()

    @capture_logs()
    def test_hard_reset_raises_when_called_from_runtime_thread(self, lifecycle):
        """WsLifecycle.hard_reset raises RuntimeError when called from runtime thread."""
        ## Arrange
        lifecycle._runtime_thread = threading.current_thread()

        ## Act & Assert
        with pytest.raises(RuntimeError, match='Hard reset called from Runtime or Transport thread'):
            lifecycle.hard_reset()

    @capture_logs()
    def test_hard_reset_raises_when_called_from_transport_thread(self, lifecycle):
        """WsLifecycle.hard_reset raises RuntimeError when called from transport thread."""
        ## Arrange
        lifecycle._transport_thread = threading.current_thread()

        ## Act & Assert
        with pytest.raises(RuntimeError, match='Hard reset called from Runtime or Transport thread'):
            lifecycle.hard_reset()

    @capture_logs(logger_level='ERROR', expected_errors=['Hard reset', 'Hard reset aborted'], partial_match=True)
    def test_hard_reset_aborts_when_stop_fails(self, lifecycle):
        """WsLifecycle.hard_reset aborts and returns False when stop fails."""
        ## Arrange
        lifecycle.stop = MagicMock(return_value=False)
        lifecycle.start = MagicMock()

        ## Act
        result = lifecycle.hard_reset()

        ## Assert
        assert result is False
        lifecycle.stop.assert_called_once()
        lifecycle.start.assert_not_called()


class TestMaintainTransport:
    @capture_logs()
    def test_maintain_transport_creates_thread_when_none(self, lifecycle):
        """WsLifecycle.maintain_transport creates transport thread when None."""
        ## Arrange
        lifecycle._transport_thread = None
        lifecycle.new_transport_thread = MagicMock()

        ## Act
        lifecycle.maintain_transport()

        ## Assert
        lifecycle.new_transport_thread.assert_called_once()

    @capture_logs()
    def test_maintain_transport_creates_thread_when_not_alive(self, lifecycle):
        """WsLifecycle.maintain_transport creates transport thread when not alive."""
        ## Arrange
        lifecycle._transport_thread = MagicMock()
        lifecycle._transport_thread.is_alive.return_value = False
        lifecycle.new_transport_thread = MagicMock()

        ## Act
        lifecycle.maintain_transport()

        ## Assert
        lifecycle.new_transport_thread.assert_called_once()

    @capture_logs()
    def test_maintain_transport_does_nothing_when_stopping(self, lifecycle):
        """WsLifecycle.maintain_transport does nothing when state is STOPPING."""
        ## Arrange
        lifecycle._state_manager.set_state(WsState.STOPPING)
        lifecycle._transport_thread = None
        lifecycle.new_transport_thread = MagicMock()

        ## Act
        lifecycle.maintain_transport()

        ## Assert
        lifecycle.new_transport_thread.assert_not_called()

    @capture_logs()
    def test_maintain_transport_does_nothing_when_thread_alive(self, lifecycle):
        """WsLifecycle.maintain_transport does nothing when thread is alive."""
        ## Arrange
        lifecycle._transport_thread = MagicMock()
        lifecycle._transport_thread.is_alive.return_value = True
        lifecycle.new_transport_thread = MagicMock()

        ## Act
        lifecycle.maintain_transport()

        ## Assert
        lifecycle.new_transport_thread.assert_not_called()
