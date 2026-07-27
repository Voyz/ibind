import time
from unittest.mock import MagicMock, patch

import pytest

from ibind import events
from ibind.subscriptions import OrdersSubscription
from ibind.ws_v2._ws_events import CallbackSink, NoopSink, AsyncSink
from ibind.ws_v2.ws_runtime import WsRuntime
from ibind.ws_v2.runtime.ws_state_manager import WsState
from ibind.ws_v2.ws_subscriptions import BindingStatus
from ibind.ws_v2.ws_transport import TransportOpened, TransportClosed, TransportError, TransportMessage
from test.test_utils import capture_logs


class MockRouter:
    def __init__(self):
        self.route_calls = []

    def route(self, message):
        self.route_calls.append(message)
        return events.WsOpen(previous_state=WsState.STARTING, current_state=WsState.OPEN)


class MockResolver:
    def resolve_binding_key(self, event):
        return (False, None)


@pytest.fixture
def mock_router():
    return MockRouter()


@pytest.fixture
def mock_resolver():
    return MockResolver()


@pytest.fixture
def event_collector():
    """Collects events emitted by the runtime."""
    collected = []
    sink = CallbackSink()

    def collect(event):
        collected.append(event)

    # Register for all event types
    for event_type in [
        events.WsStarting,
        events.WsOpen,
        events.WsAuthenticated,
        events.WsReady,
        events.WsDegraded,
        events.WsClose,
        events.WsError,
        events.WsStopping,
        events.WsStopped,
    ]:
        sink.on(event_type, collect)

    return {'sink': sink, 'events': collected}


@pytest.fixture
def runtime(mock_router, mock_resolver, event_collector):
    """Create a WsRuntime with mocked transport."""
    runtime = WsRuntime(
        url='wss://test.example.com',
        cycle_interval=0.01,
        sink=event_collector['sink'],
        router=mock_router,
        subscription_resolver=mock_resolver,
        connection_timeout=2.0,
        reconnect_timeout=1.0,
        max_ping_interval=20,
    )

    # Register internal callbacks (needed for AsyncSink lifecycle)
    runtime._register_internal_callbacks()

    # Mock transport to prevent actual network calls
    runtime._transport.connect = MagicMock()
    runtime._transport.send = MagicMock(return_value=True)
    runtime._transport.stop = MagicMock()
    runtime._transport.is_ready = MagicMock(return_value=True)
    runtime._transport.check_ping = MagicMock(return_value=True)
    runtime._transport.reset_websocket_app = MagicMock()

    yield runtime

    # Cleanup
    if runtime.is_running():
        runtime.stop()


class TestStateTransitions:
    """Integration tests for state transitions across components."""

    @capture_logs()
    def test_state_transition_emits_events(self, runtime, event_collector):
        """State transitions trigger appropriate events via WsEmitter."""
        ## Act
        runtime.set_state(WsState.STARTING)
        runtime.set_state(WsState.OPEN)
        runtime.set_state(WsState.AUTHENTICATED)

        ## Assert
        open_events = [e for e in event_collector['events'] if isinstance(e, events.WsOpen)]
        ready_events = [e for e in event_collector['events'] if isinstance(e, events.WsReady)]

        assert len(open_events) == 1
        assert len(ready_events) == 1
        assert runtime._state_manager.last_heartbeat is not None

    @capture_logs()
    def test_degraded_state_invalidates_subscriptions(self, runtime):
        """Transitioning to DEGRADED invalidates subscriptions."""
        ## Arrange
        runtime.set_state(WsState.AUTHENTICATED)
        mock_invalidate = MagicMock()
        runtime.subscription_controller.invalidate_subscriptions = mock_invalidate

        ## Act
        runtime.set_state(WsState.DEGRADED)

        ## Assert
        mock_invalidate.assert_called_once()

    @capture_logs()
    def test_unauthentication_triggers_state_change(self, runtime):
        """Transitioning from AUTHENTICATED to OPEN via set_authenticated."""
        ## Arrange
        runtime.set_state(WsState.OPEN)  # Start from OPEN
        runtime.set_state(WsState.AUTHENTICATED)  # Then authenticate
        assert runtime.get_state() == WsState.AUTHENTICATED

        ## Act
        runtime.set_authenticated(False)

        ## Assert
        assert runtime.get_state() == WsState.OPEN
        assert runtime.is_authenticated() is False


class TestEventHandling:
    """Integration tests for event handling pipeline."""

    @capture_logs(logger_level='INFO', expected_errors=['Connection open'], partial_match=True)
    def test_transport_opened_triggers_state_change(self, runtime, event_collector):
        """TransportOpened event triggers state change to OPEN."""
        ## Act
        runtime._event_handler.put(TransportOpened())
        runtime._event_handler.process_transport_queue()

        ## Assert
        assert runtime.get_state() == WsState.OPEN
        open_events = [e for e in event_collector['events'] if isinstance(e, events.WsOpen)]
        assert len(open_events) == 1

    @capture_logs(logger_level='INFO', expected_errors=['Connection closed'], partial_match=True)
    def test_transport_closed_triggers_state_change(self, runtime, event_collector):
        """TransportClosed event triggers state change to CLOSED."""
        ## Arrange
        runtime.set_state(WsState.OPEN)

        ## Act
        runtime._event_handler.put(TransportClosed(close_status_code=None, close_msg=None))
        runtime._event_handler.process_transport_queue()

        ## Assert
        assert runtime.get_state() == WsState.CLOSED
        close_events = [e for e in event_collector['events'] if isinstance(e, events.WsClose)]
        assert len(close_events) == 1

    @capture_logs(logger_level='ERROR', expected_errors=['Connection error'], partial_match=True)
    def test_transport_error_emits_error_event(self, runtime, event_collector):
        """TransportError event emits WsError."""
        ## Arrange
        error = RuntimeError('test error')

        ## Act
        runtime._event_handler.put(TransportError(exception=error))
        runtime._event_handler.process_transport_queue()

        ## Assert
        error_events = [e for e in event_collector['events'] if isinstance(e, events.WsError)]
        assert len(error_events) == 1
        assert error_events[0].error is error

    @capture_logs()
    def test_transport_message_routes_through_router(self, runtime, mock_router):
        """TransportMessage is routed through the router."""
        ## Arrange
        message = '{"test": "data"}'

        ## Act
        runtime._event_handler.put(TransportMessage(message=message))
        runtime._event_handler.process_transport_queue()

        ## Assert
        assert message in mock_router.route_calls


class TestHealthMonitoring:
    """Integration tests for health monitoring."""

    @capture_logs(logger_level='WARNING', expected_errors=['Last heartbeat happened'], partial_match=True)
    def test_stale_heartbeat_triggers_degraded_state(self, runtime):
        """Stale heartbeat triggers health check failure and DEGRADED state."""
        ## Arrange
        runtime.set_state(WsState.AUTHENTICATED)
        runtime._state_manager.last_heartbeat = time.time() - 100  # 100 seconds ago
        # Force health check interval to have passed
        runtime._health_monitor._last_health_check = time.monotonic() - 20

        ## Act
        health_ok = runtime._health_monitor.health_ok()

        ## Assert
        assert health_ok is False
        assert runtime.get_state() == WsState.DEGRADED

    @capture_logs()
    def test_healthy_connection_passes_health_check(self, runtime):
        """Healthy connection passes health check."""
        ## Arrange
        runtime.set_state(WsState.AUTHENTICATED)
        runtime._state_manager.last_heartbeat = time.time()

        ## Act
        health_ok = runtime._health_monitor.health_ok()

        ## Assert
        assert health_ok is True
        assert runtime.get_state() == WsState.AUTHENTICATED

    @capture_logs(logger_level='WARNING', expected_errors=['State is not ready while reporting authenticated'], partial_match=True)
    def test_authentication_mismatch_corrects_state(self, runtime):
        """Health monitor corrects state when authentication status mismatches."""
        ## Arrange
        runtime.set_state(WsState.OPEN)
        runtime._health_monitor._get_authenticated = MagicMock(return_value=True)

        ## Act
        should_reset = runtime._health_monitor.check_should_reset()

        ## Assert
        assert should_reset is False
        assert runtime.get_state() == WsState.AUTHENTICATED


class TestAsyncSinkIntegration:
    """Integration tests for AsyncSink lifecycle management."""

    @capture_logs()
    def test_async_sink_starts_on_ws_starting_event(self, runtime):
        """AsyncSink starts when WsStarting event is emitted."""
        ## Arrange
        async_sink = AsyncSink(sink=NoopSink())
        runtime._sink = async_sink
        runtime._register_internal_callbacks()

        ## Act 1
        runtime.set_state(WsState.STARTING)

        ## Assert 1
        assert async_sink._running is True

        ## Act 2
        runtime.set_state(WsState.STOPPED)

        ## Assert 2
        assert async_sink._running is False


class TestRuntimeWorkerIntegration:
    """Integration tests for RuntimeWorker coordination."""

    @capture_logs()
    def test_worker_maintains_transport_thread(self, runtime):
        """RuntimeWorker maintains transport thread via WsLifecycle."""
        ## Arrange
        runtime._lifecycle._transport_thread = None
        runtime.set_state(WsState.STARTING)
        runtime._runtime_worker._lifecycle = runtime._lifecycle  # Set lifecycle reference

        ## Act
        with patch.object(runtime._lifecycle, 'new_transport_thread') as mock_new_thread:
            runtime._runtime_worker._cycle()

        ## Assert
        mock_new_thread.assert_called_once()

    @capture_logs()
    def test_worker_maintains_subscriptions_when_authenticated(self, runtime):
        """RuntimeWorker reconciles subscriptions when authenticated."""
        ## Arrange
        runtime.set_state(WsState.AUTHENTICATED)
        mock_reconcile = MagicMock()
        runtime.subscription_controller.reconcile_bindings = mock_reconcile

        ## Act
        runtime._runtime_worker._maintain_subscriptions()

        ## Assert
        mock_reconcile.assert_called_once()

    @capture_logs()
    def test_worker_skips_subscriptions_when_not_authenticated(self, runtime):
        """RuntimeWorker skips subscription reconciliation when not authenticated."""
        ## Arrange
        runtime.set_state(WsState.OPEN)
        mock_reconcile = MagicMock()
        runtime.subscription_controller.reconcile_bindings = mock_reconcile

        ## Act
        runtime._runtime_worker._maintain_subscriptions()

        ## Assert
        mock_reconcile.assert_not_called()


class TestEndToEndScenarios:
    """End-to-end integration tests simulating real usage."""

    @capture_logs()
    def test_successful_connection_flow(self, runtime, event_collector):
        """Simulate successful connection: STOPPED → STARTING → CONNECTING → OPEN → AUTHENTICATED."""
        ## Act
        runtime.set_state(WsState.STARTING)
        runtime._event_handler.put(TransportOpened())
        runtime._event_handler.process_transport_queue()
        runtime.set_state(WsState.AUTHENTICATED)

        ## Assert
        assert runtime.get_state() == WsState.AUTHENTICATED
        assert runtime.is_authenticated() is True

        # Verify event sequence
        event_types = [type(e) for e in event_collector['events']]
        assert events.WsStarting in event_types
        assert events.WsOpen in event_types
        assert events.WsAuthenticated in event_types
        assert events.WsReady in event_types

    @capture_logs(logger_level='ERROR', expected_errors=['Connection error'], partial_match=True)
    def test_connection_failure_and_recovery(self, runtime, event_collector):
        """Simulate connection failure and recovery."""
        ## Arrange
        runtime.set_state(WsState.AUTHENTICATED)

        ## Act - Connection fails
        runtime._event_handler.put(TransportError(exception=Exception('Connection to remote host was lost.')))
        runtime._event_handler.process_transport_queue()

        ## Assert - Error event emitted (state remains AUTHENTICATED unless health check triggers DEGRADED)
        error_events = [e for e in event_collector['events'] if isinstance(e, events.WsError)]
        assert len(error_events) == 1

        ## Act - Reconnect
        runtime._event_handler.put(TransportOpened())
        runtime._event_handler.process_transport_queue()
        runtime.set_state(WsState.AUTHENTICATED)

        ## Assert - Recovered
        assert runtime.get_state() == WsState.AUTHENTICATED

    @capture_logs()
    def test_graceful_shutdown(self, runtime, event_collector):
        """Simulate graceful shutdown."""
        ## Arrange
        runtime.set_state(WsState.AUTHENTICATED)

        ## Act
        runtime.set_state(WsState.STOPPING)
        runtime._event_handler.put(TransportClosed(close_status_code=None, close_msg=None))
        runtime._event_handler.process_transport_queue()
        runtime.set_state(WsState.STOPPED)

        ## Assert
        assert runtime.get_state() == WsState.STOPPED
        stopped_events = [e for e in event_collector['events'] if isinstance(e, events.WsStopped)]
        assert len(stopped_events) == 1


class TestRestartAndHardResetScenarios:
    """Integration tests for restarting a runtime instance and handling failed shutdowns."""

    @staticmethod
    def _install_stopped_runtime_thread(runtime):
        runtime_thread = MagicMock()
        runtime_thread.is_alive.return_value = False
        runtime._lifecycle._runtime_thread = runtime_thread
        return runtime_thread

    @staticmethod
    def _install_unstoppable_threads(runtime):
        transport_thread = MagicMock()
        transport_thread.is_alive.return_value = True
        runtime_thread = MagicMock()
        runtime_thread.is_alive.return_value = True

        runtime._lifecycle._transport_thread = transport_thread
        runtime._lifecycle._runtime_thread = runtime_thread
        return transport_thread, runtime_thread

    @capture_logs()
    def test_hard_reset_reenables_transport_callbacks(self, runtime):
        """A hard reset must leave the recreated transport able to emit callbacks."""
        ## Arrange
        runtime.set_state(WsState.AUTHENTICATED)
        self._install_stopped_runtime_thread(runtime)

        with (
            patch.object(runtime._runtime_worker, 'wait_for_one_cycle'),
            patch.object(runtime._lifecycle, '_new_runtime_thread'),
            patch('ibind.ws_v2.runtime.ws_lifecycle.wait_until', return_value=True),
        ):
            ## Act
            runtime.hard_reset()

        event_callback = MagicMock()
        runtime._transport._event_callback = event_callback
        with patch.object(runtime._transport, 'check_cookie', return_value=True):
            runtime._transport._on_open(MagicMock())

        # The mocked startup does not create a worker, so restore a stopped fixture state.
        runtime._runtime_worker.running = False
        runtime.set_state(WsState.STOPPED)
        runtime._lifecycle._runtime_thread = None

        ## Assert
        event_callback.assert_called_once()
        assert isinstance(event_callback.call_args.args[0], TransportOpened)

    @capture_logs()
    def test_shutdown_then_start_resubscribes_previously_active_bindings(self, runtime):
        """Restarting the same runtime must re-send subscriptions active before shutdown."""
        ## Arrange
        runtime.set_state(WsState.AUTHENTICATED)
        subscription = OrdersSubscription()
        runtime.subscription_controller.subscribe(subscription)
        runtime.subscription_controller.reconcile_bindings()
        assert runtime.subscription_controller.get_status(subscription.binding_key()) == BindingStatus.ACTIVE

        runtime._transport.send.reset_mock()
        self._install_stopped_runtime_thread(runtime)

        with (
            patch.object(runtime._runtime_worker, 'wait_for_one_cycle'),
            patch.object(runtime._lifecycle, '_new_runtime_thread'),
            patch('ibind.ws_v2.runtime.ws_lifecycle.wait_until', return_value=True),
        ):
            ## Act
            assert runtime.stop() is True
            assert runtime.start() is True

        # Simulate the open/authenticated events that would follow a successful reconnect.
        runtime.set_state(WsState.OPEN)
        runtime.set_state(WsState.AUTHENTICATED)
        runtime.subscription_controller.reconcile_bindings()

        # The mocked startup does not create a worker, so restore a stopped fixture state.
        runtime._runtime_worker.running = False
        runtime.set_state(WsState.STOPPED)
        runtime._lifecycle._runtime_thread = None

        ## Assert
        runtime._transport.send.assert_called_once_with(subscription.subscribe_payload())

    @capture_logs(
        logger_level='ERROR',
        expected_errors=['Failed to stop transport thread', 'Runtime thread failed to stop'],
        partial_match=True,
    )
    def test_restart_replaces_threads_that_failed_to_stop(self, runtime):
        """A restart must create replacement workers after old threads time out."""
        ## Arrange
        runtime.set_state(WsState.AUTHENTICATED)
        old_transport_thread, old_runtime_thread = self._install_unstoppable_threads(runtime)

        with (
            patch.object(runtime._runtime_worker, 'wait_for_one_cycle'),
            patch.object(runtime._lifecycle, '_new_runtime_thread') as new_runtime_thread,
            patch.object(runtime._lifecycle, 'new_transport_thread') as new_transport_thread,
            patch('ibind.ws_v2.runtime.ws_lifecycle.wait_until', return_value=True),
        ):
            ## Act
            assert runtime.stop() is True
            assert runtime.start() is True
            runtime._lifecycle.maintain_transport()

        # The mocked startup does not create workers, so restore a stopped fixture state.
        runtime._runtime_worker.running = False
        runtime.set_state(WsState.STOPPED)
        runtime._lifecycle._runtime_thread = None

        ## Assert
        old_transport_thread.join.assert_called_once()
        old_runtime_thread.join.assert_called_once()
        new_runtime_thread.assert_called_once_with()
        new_transport_thread.assert_called_once_with()
