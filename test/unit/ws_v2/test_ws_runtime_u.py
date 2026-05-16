import threading
from unittest.mock import MagicMock, patch

import pytest

from ibind.events import WsOpen, WsAuthenticated, WsDegraded, WsReady, WsClose, WsError
from test.test_utils import capture_logs, mock_module_time
from ibind.ws_v2._ws_events import AsyncSink, CallbackSink, NoopSink
from ibind.ws_v2.ws_runtime import WsRuntime, WsState, make_sslopt
from ibind.ws_v2.ws_transport import TransportOpened, TransportClosed, TransportError, TransportMessage, TransportReconnect


class MockRouter:
    def route(self, message):
        return WsOpen()


class MockResolver:
    def resolve_binding_key(self, event):
        return (False, None)


@pytest.fixture
def mock_sink():
    return NoopSink()


@pytest.fixture
def mock_internal_sink():
    sink = CallbackSink()
    sink._callbacks = {}
    return sink


@pytest.fixture
def mock_router():
    return MockRouter()


@pytest.fixture
def mock_resolver():
    return MockResolver()


@pytest.fixture
def runtime(mock_sink, mock_internal_sink, mock_router, mock_resolver):
    return WsRuntime(
        url='wss://test.example.com',
        cycle_interval=0.01,
        sink=mock_sink,
        internal_sink=mock_internal_sink,
        router=mock_router,
        subscription_resolver=mock_resolver,
        ready_state=WsState.OPEN,
        connection_timeout=1.0,
        reconnect_timeout=1.0,
        max_ping_interval=20,
    )


class TestMakeSslopt:
    @capture_logs()
    def test_make_sslopt_with_false_returns_cert_none(self):
        """make_sslopt returns CERT_NONE when cacert is False."""
        ## Act
        result = make_sslopt(False)

        ## Assert
        assert result == {'cert_reqs': 0}

    @capture_logs()
    def test_make_sslopt_with_none_returns_cert_none(self):
        """make_sslopt returns CERT_NONE when cacert is None."""
        ## Act
        result = make_sslopt('')

        ## Assert
        assert result == {'cert_reqs': 0}

    @capture_logs()
    def test_make_sslopt_with_valid_path_returns_ca_certs(self):
        """make_sslopt returns ca_certs when cacert is a valid path."""
        ## Arrange
        with patch('ibind.ws_v2.ws_runtime.Path') as mock_path:
            mock_path.return_value.exists.return_value = True

            ## Act
            result = make_sslopt('/path/to/cert.pem')

        ## Assert
        assert result == {'ca_certs': '/path/to/cert.pem'}

    @capture_logs()
    def test_make_sslopt_raises_when_path_invalid(self):
        """make_sslopt raises ValueError when cacert path does not exist."""
        ## Arrange
        with patch('ibind.ws_v2.ws_runtime.Path') as mock_path:
            mock_path.return_value.exists.return_value = False

            ## Act / Assert
            with pytest.raises(ValueError, match='Cacert must be a valid Path or False'):
                make_sslopt('/invalid/path.pem')


class TestInit:
    @capture_logs()
    def test_init_sets_attributes(self, mock_sink, mock_internal_sink, mock_router, mock_resolver):
        """WsRuntime.__init__ initializes all attributes correctly."""
        ## Act
        runtime = WsRuntime(
            url='wss://test.example.com',
            cycle_interval=0.5,
            sink=mock_sink,
            internal_sink=mock_internal_sink,
            router=mock_router,
            subscription_resolver=mock_resolver,
            ready_state=WsState.AUTHENTICATED,
            connection_timeout=10.0,
        )

        ## Assert
        assert runtime._url == 'wss://test.example.com'
        assert runtime._cycle_interval == 0.5
        assert runtime._sink is mock_sink
        assert runtime._internal_sink is mock_internal_sink
        assert runtime._router is mock_router
        assert runtime._ready_state == WsState.AUTHENTICATED
        assert runtime._connection_timeout == 10.0
        assert runtime._state == WsState.STOPPED
        assert runtime._running is False

    @capture_logs()
    def test_init_raises_when_invalid_ready_state(self, mock_sink, mock_internal_sink, mock_router, mock_resolver):
        """WsRuntime.__init__ raises ValueError when ready_state is invalid."""
        ## Act / Assert
        with pytest.raises(ValueError, match='Invalid ready_state'):
            WsRuntime(
                url='wss://test.example.com',
                cycle_interval=0.5,
                sink=mock_sink,
                internal_sink=mock_internal_sink,
                router=mock_router,
                subscription_resolver=mock_resolver,
                ready_state=WsState.STOPPED,
            )


class TestStateManagement:
    @capture_logs(logger_level='DEBUG', expected_errors=['STOPPED -> CONNECTING'], partial_match=True)
    def test_set_state_updates_state(self, runtime):
        """WsRuntime._set_state updates the state and logs transition."""
        ## Act
        runtime._set_state(WsState.CONNECTING)

        ## Assert
        assert runtime._state == WsState.CONNECTING

    @capture_logs(logger_level='INFO', expected_errors=['Websocket ready'], partial_match=True)
    def test_set_state_emits_ready_when_ready_state_reached(self, runtime, mock_internal_sink):
        """WsRuntime._set_state emits WsReady when ready_state is reached."""
        ## Arrange
        ready_events = []
        mock_internal_sink.on(WsReady, lambda e: ready_events.append(e))

        ## Act
        runtime._set_state(WsState.OPEN)

        ## Assert
        assert len(ready_events) == 1
        assert runtime._last_heartbeat is not None


class TestAuthentication:
    @capture_logs(logger_level='INFO', expected_errors=['Connection authenticated'], partial_match=True)
    def test_set_authenticated_true_when_open(self, runtime, mock_internal_sink):
        """WsRuntime.set_authenticated emits WsAuthenticated and transitions to AUTHENTICATED when state is OPEN."""
        ## Arrange
        runtime._state = WsState.OPEN
        auth_events = []
        mock_internal_sink.on(WsAuthenticated, lambda e: auth_events.append(e))

        ## Act
        runtime.set_authenticated(True)

        ## Assert
        assert runtime._authenticated is True
        assert len(auth_events) == 1
        assert runtime._state == WsState.AUTHENTICATED

    @capture_logs(logger_level='INFO', expected_errors=['Connection unauthenticated'], partial_match=True)
    def test_set_authenticated_false_when_ready_degrades(self, runtime):
        """WsRuntime.set_authenticated degrades state when set to False from ready state."""
        ## Arrange
        runtime._state = WsState.OPEN
        runtime._authenticated = True

        ## Act
        runtime.set_authenticated(False)

        ## Assert
        assert runtime._authenticated is False
        assert runtime._state == WsState.DEGRADED


class TestStateDegraded:
    @capture_logs()
    def test_state_degraded_emits_event_first_time(self, runtime, mock_internal_sink):
        """WsRuntime.state_degraded emits WsDegraded event on first call."""
        ## Arrange
        runtime._state = WsState.OPEN
        degraded_events = []
        mock_internal_sink.on(WsDegraded, lambda e: degraded_events.append(e))

        ## Act
        runtime.state_degraded()

        ## Assert
        assert runtime._state == WsState.DEGRADED
        assert len(degraded_events) == 1

    @capture_logs()
    def test_state_degraded_does_not_emit_when_already_degraded(self, runtime, mock_internal_sink):
        """WsRuntime.state_degraded does not emit WsDegraded when already degraded."""
        ## Arrange
        runtime._state = WsState.DEGRADED
        degraded_events = []
        mock_internal_sink.on(WsDegraded, lambda e: degraded_events.append(e))

        ## Act
        runtime.state_degraded()

        ## Assert
        assert len(degraded_events) == 0

    @capture_logs()
    def test_state_degraded_invalidates_subscriptions(self, runtime):
        """WsRuntime.state_degraded invalidates all subscriptions."""
        ## Arrange
        runtime._state = WsState.OPEN
        runtime.subscription_controller.invalidate_subscriptions = MagicMock()

        ## Act
        runtime.state_degraded()

        ## Assert
        runtime.subscription_controller.invalidate_subscriptions.assert_called_once()


class TestSend:
    @capture_logs(logger_level='ERROR', expected_errors=['State must be OPEN before sending'], partial_match=True)
    def test_send_returns_false_when_not_ready(self, runtime):
        """WsRuntime.send returns False when state is not ready."""
        ## Arrange
        runtime._state = WsState.CONNECTING

        ## Act
        result = runtime.send('test_payload')

        ## Assert
        assert result is False

    @capture_logs(logger_level='INFO', expected_errors=['Sending payload: test_payload'], partial_match=True)
    def test_send_calls_transport_when_ready(self, runtime):
        """WsRuntime.send calls transport.send when state is ready."""
        ## Arrange
        runtime._state = WsState.OPEN
        runtime._transport.send = MagicMock(return_value=True)

        ## Act
        result = runtime.send('test_payload')

        ## Assert
        runtime._transport.send.assert_called_once_with('test_payload')
        assert result is True


class TestStartStop:
    @capture_logs()
    def test_start_returns_early_when_state_not_stopped(self, runtime):
        """WsRuntime.start returns early when state is not STOPPED."""
        ## Arrange
        runtime._state = WsState.OPEN
        runtime._set_state = MagicMock()

        ## Act
        result = runtime.start()

        ## Assert
        assert result is None
        runtime._set_state.assert_not_called()

    @capture_logs(logger_level='ERROR', expected_errors=['Runtime thread must be stopped'], partial_match=True)
    def test_start_returns_when_runtime_thread_alive(self, runtime):
        """WsRuntime.start returns early when runtime thread is still alive."""
        ## Arrange
        runtime._state = WsState.STOPPED
        runtime._runtime_thread = MagicMock()
        runtime._runtime_thread.is_alive.return_value = True

        ## Act
        runtime.start()

        ## Assert
        assert runtime._state == WsState.STOPPED

    @capture_logs(logger_level='INFO', expected_errors=['Starting WebSocket runtime'], partial_match=True)
    def test_start_sets_state_and_returns_true_on_success(self, runtime):
        """WsRuntime.start sets STARTING and returns True when connection succeeds."""
        ## Arrange
        runtime._state = WsState.STOPPED
        runtime._new_runtime_thread = MagicMock()

        ## Act
        with patch('ibind.ws_v2.ws_runtime.wait_until', return_value=True):
            result = runtime.start()

        ## Assert
        assert runtime._state == WsState.STARTING
        assert runtime._running is True
        runtime._new_runtime_thread.assert_called_once()
        assert result is True

    @capture_logs(logger_level='INFO', expected_errors=['Starting WebSocket runtime', 'Starting timeout'], partial_match=True)
    def test_start_returns_false_on_timeout(self, runtime):
        """WsRuntime.start returns False when connection times out."""
        ## Arrange
        runtime._state = WsState.STOPPED
        runtime._new_runtime_thread = MagicMock()

        ## Act
        with patch('ibind.ws_v2.ws_runtime.wait_until', return_value=False):
            result = runtime.start()

        ## Assert
        assert result is False

    @capture_logs(logger_level='INFO', expected_errors=['Starting WebSocket runtime'], partial_match=True)
    def test_start_starts_async_sink(self, runtime):
        """WsRuntime.start starts the sink when it is an AsyncSink."""
        ## Arrange
        async_sink = AsyncSink(sink=NoopSink())
        async_sink.start = MagicMock()
        runtime._sink = async_sink
        runtime._state = WsState.STOPPED
        runtime._new_runtime_thread = MagicMock()

        ## Act
        with patch('ibind.ws_v2.ws_runtime.wait_until', return_value=True):
            runtime.start()

        ## Assert
        async_sink.start.assert_called_once()

    @capture_logs()
    def test_stop_returns_early_when_already_stopped(self, runtime):
        """WsRuntime.stop returns early when state is already STOPPED."""
        ## Arrange
        runtime._state = WsState.STOPPED
        runtime._stop_transport_thread = MagicMock()

        ## Act
        runtime.stop()

        ## Assert
        runtime._stop_transport_thread.assert_not_called()

    @capture_logs(logger_level='INFO', expected_errors=['Stopping WebSocket runtime'], partial_match=True)
    def test_stop_sets_running_false_and_stops_threads(self, runtime):
        """WsRuntime.stop sets running to False and stops all threads."""
        ## Arrange
        runtime._state = WsState.OPEN
        runtime._running = True
        runtime._runtime_thread = MagicMock()
        runtime._runtime_thread.is_alive.return_value = False
        runtime._transport_thread = MagicMock()

        ## Act
        with patch.object(runtime, '_stop_transport_thread', return_value=True):
            with patch('ibind.ws_v2.ws_runtime.wait_until', return_value=True):
                runtime.stop()

        ## Assert
        assert runtime._running is False
        assert runtime._state == WsState.STOPPED

    @capture_logs()
    def test_stop_raises_when_called_from_runtime_thread(self, runtime):
        """WsRuntime.stop raises RuntimeError when called from runtime thread."""
        ## Arrange
        runtime._state = WsState.OPEN
        runtime._runtime_thread = threading.current_thread()

        ## Act / Assert
        with pytest.raises(RuntimeError, match='Stopping runtime called from within runtime thread'):
            runtime.stop()

    @capture_logs(logger_level='ERROR', expected_errors=['Failed to stop transport thread'], partial_match=True)
    def test_stop_abandons_transport_thread_when_stop_fails(self, runtime):
        """WsRuntime.stop abandons transport thread when stop fails."""
        ## Arrange
        runtime._state = WsState.OPEN
        runtime._running = True
        runtime._runtime_thread = MagicMock()
        runtime._runtime_thread.is_alive.return_value = False
        runtime._transport_thread = MagicMock()

        ## Act
        with patch.object(runtime, '_stop_transport_thread', return_value=False):
            with patch('ibind.ws_v2.ws_runtime.wait_until', return_value=True):
                runtime.stop()

        ## Assert
        assert runtime._transport_thread is None

    @capture_logs(logger_level='ERROR', expected_errors=['Runtime thread failed to stop'], partial_match=True)
    def test_stop_abandons_runtime_thread_when_join_fails(self, runtime):
        """WsRuntime.stop abandons runtime thread when join times out."""
        ## Arrange
        runtime._state = WsState.OPEN
        runtime._running = True
        runtime._runtime_thread = MagicMock()
        runtime._runtime_thread.is_alive.return_value = True

        ## Act
        with patch.object(runtime, '_stop_transport_thread', return_value=True):
            with patch('ibind.ws_v2.ws_runtime.wait_until', return_value=True):
                runtime.stop()

        ## Assert
        assert runtime._runtime_thread is None

    @capture_logs(logger_level='INFO', expected_errors=['Stopping WebSocket runtime'], partial_match=True)
    def test_stop_stops_async_sink(self, runtime):
        """WsRuntime.stop calls stop on the sink when it is an AsyncSink."""
        ## Arrange
        async_sink = AsyncSink(sink=NoopSink())
        async_sink.stop = MagicMock(return_value=True)
        runtime._sink = async_sink
        runtime._state = WsState.OPEN
        runtime._running = True
        runtime._runtime_thread = MagicMock()
        runtime._runtime_thread.is_alive.return_value = False
        runtime._transport_thread = MagicMock()

        ## Act
        with patch.object(runtime, '_stop_transport_thread', return_value=True):
            with patch('ibind.ws_v2.ws_runtime.wait_until', return_value=True):
                runtime.stop()

        ## Assert
        async_sink.stop.assert_called_once()
        assert runtime._state == WsState.STOPPED


class TestThreadManagement:
    @capture_logs(logger_level='DEBUG', expected_errors=['Joining transport thread'], partial_match=True)
    def test_stop_transport_thread_joins_thread(self, runtime):
        """WsRuntime._stop_transport_thread joins the transport thread."""
        ## Arrange
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = False
        runtime._transport_thread = mock_thread
        runtime._transport.stop = MagicMock()

        ## Act
        result = runtime._stop_transport_thread()

        ## Assert
        runtime._transport.stop.assert_called_once()
        mock_thread.join.assert_called_once()
        assert result is True
        assert runtime._transport_thread is None

    @capture_logs()
    def test_stop_transport_thread_returns_true_when_thread_none(self, runtime):
        """WsRuntime._stop_transport_thread returns True when thread is None."""
        ## Arrange
        runtime._transport_thread = None
        runtime._transport.stop = MagicMock()

        ## Act
        result = runtime._stop_transport_thread()

        ## Assert
        assert result is True

    @capture_logs(logger_level='ERROR', expected_errors=['Failed to stop transport thread'], partial_match=True)
    def test_stop_transport_thread_logs_exception(self, runtime):
        """WsRuntime._stop_transport_thread logs exceptions and returns False."""
        ## Arrange
        runtime._transport.stop = MagicMock(side_effect=RuntimeError('stop error'))

        ## Act
        result = runtime._stop_transport_thread()

        ## Assert
        assert result is False


class TestHardReset:
    @capture_logs(logger_level='INFO', expected_errors=['Hard reset'], partial_match=True)
    def test_hard_reset_stops_and_starts(self, runtime):
        """WsRuntime.hard_reset stops and restarts the runtime."""
        ## Arrange
        runtime.stop = MagicMock()
        runtime.start = MagicMock()

        ## Act
        runtime.hard_reset()

        ## Assert
        runtime.stop.assert_called_once()
        runtime.start.assert_called_once()

    @capture_logs()
    def test_hard_reset_raises_when_called_from_runtime_thread(self, runtime):
        """WsRuntime.hard_reset raises RuntimeError when called from runtime thread."""
        ## Arrange
        runtime._runtime_thread = threading.current_thread()

        ## Act / Assert
        with pytest.raises(RuntimeError, match='Hard reset called from Runtime or Transport thread'):
            runtime.hard_reset()

    @capture_logs()
    def test_hard_reset_raises_when_called_from_transport_thread(self, runtime):
        """WsRuntime.hard_reset raises RuntimeError when called from transport thread."""
        ## Arrange
        runtime._transport_thread = threading.current_thread()

        ## Act / Assert
        with pytest.raises(RuntimeError, match='Hard reset called from Runtime or Transport thread'):
            runtime.hard_reset()


class TestRestartTransport:
    @capture_logs()
    def test_restart_transport_stops_and_recreates_transport(self, runtime):
        """WsRuntime.restart_transport stops transport thread and creates new transport."""
        ## Arrange
        old_transport = runtime._transport

        ## Act
        with patch.object(runtime, '_stop_transport_thread', return_value=True):
            with patch.object(runtime, '_new_transport_thread'):
                runtime.restart_transport()

        ## Assert
        assert runtime._transport is not old_transport

    @capture_logs()
    def test_restart_transport_raises_when_called_from_transport_thread(self, runtime):
        """WsRuntime.restart_transport raises RuntimeError when called from transport thread."""
        ## Arrange
        runtime._transport_thread = threading.current_thread()

        ## Act / Assert
        with pytest.raises(RuntimeError, match='Resetting transport thread called from within transport thread'):
            runtime.restart_transport()

    @capture_logs(logger_level='ERROR', expected_errors=['Failed to stop transport thread'], partial_match=True)
    def test_restart_transport_abandons_thread_when_stop_fails(self, runtime):
        """WsRuntime.restart_transport abandons thread when stop fails."""
        ## Arrange
        runtime._transport_thread = MagicMock()

        ## Act
        with patch.object(runtime, '_stop_transport_thread', return_value=False):
            with patch.object(runtime, '_new_transport_thread'):
                runtime.restart_transport()

        ## Assert
        assert runtime._transport_thread is None


class TestMaintainTransport:
    @capture_logs()
    def test_maintain_transport_creates_thread_when_none(self, runtime):
        """WsRuntime._maintain_transport creates transport thread when None."""
        ## Arrange
        runtime._transport_thread = None

        ## Act
        with patch.object(runtime, '_new_transport_thread'):
            runtime._maintain_transport()

        ## Assert
        assert runtime._state == WsState.CONNECTING

    @capture_logs()
    def test_maintain_transport_creates_thread_when_not_alive(self, runtime):
        """WsRuntime._maintain_transport creates transport thread when not alive."""
        ## Arrange
        runtime._transport_thread = MagicMock()
        runtime._transport_thread.is_alive.return_value = False

        ## Act
        with patch.object(runtime, '_new_transport_thread'):
            runtime._maintain_transport()

        ## Assert
        assert runtime._state == WsState.CONNECTING

    @capture_logs()
    def test_maintain_transport_does_nothing_when_stopping(self, runtime):
        """WsRuntime._maintain_transport does nothing when state is STOPPING."""
        ## Arrange
        runtime._state = WsState.STOPPING
        runtime._transport_thread = None

        ## Act
        runtime._maintain_transport()

        ## Assert
        assert runtime._transport_thread is None


class TestMaintainSubscriptions:
    @capture_logs()
    def test_maintain_subscriptions_reconciles_only_when_ready(self, runtime):
        """WsRuntime._maintain_subscriptions reconciles bindings when state is ready."""
        ## Arrange
        runtime.subscription_controller.reconcile_bindings = MagicMock()

        ## Act & Assert 1 - not OPEN, not ready
        runtime._state = WsState.CONNECTING
        runtime._maintain_subscriptions()
        runtime.subscription_controller.reconcile_bindings.assert_not_called()

        ## Act & Assert 2 - OPEN, ready
        runtime._state = WsState.OPEN
        runtime._maintain_subscriptions()
        runtime.subscription_controller.reconcile_bindings.assert_called_once()

        ## Act & Assert 3 - not AUTHENTICATED, not ready
        runtime.subscription_controller.reconcile_bindings = MagicMock()
        runtime._ready_state = WsState.AUTHENTICATED
        runtime._state = WsState.OPEN
        runtime._maintain_subscriptions()
        runtime.subscription_controller.reconcile_bindings.assert_not_called()

        ## Act & Assert 4 - AUTHENTICATED, ready
        runtime.subscription_controller.reconcile_bindings = MagicMock()
        runtime._state = WsState.AUTHENTICATED
        runtime._maintain_subscriptions()
        runtime.subscription_controller.reconcile_bindings.assert_called_once()


class TestCheckShouldReset:
    @capture_logs()
    def test_check_should_reset_returns_false_when_transport_not_ready(self, runtime):
        """WsRuntime.check_should_reset returns False when transport is not ready."""
        ## Arrange
        runtime._transport.is_ready = MagicMock(return_value=False)

        ## Act & Assert
        assert runtime.check_should_reset() is False

    @capture_logs()
    def test_check_should_reset_returns_false_when_state_not_open_or_authenticated(self, runtime):
        """WsRuntime.check_should_reset returns False when state is not OPEN or AUTHENTICATED."""
        ## Arrange
        runtime._state = WsState.CONNECTING
        runtime._transport.is_ready = MagicMock(return_value=True)

        ## Act & Assert
        assert runtime.check_should_reset() is False

    @capture_logs(logger_level='WARNING', expected_errors=['Last WebSocket ping happened'], partial_match=True)
    def test_check_should_reset_returns_true_when_ping_fails_and_no_reconnect_timeout(self, runtime):
        """WsRuntime.check_should_reset returns True when ping fails and reconnect_timeout is None."""
        ## Arrange
        runtime._state = WsState.OPEN
        runtime._reconnect_timeout = None
        runtime._transport.is_ready = MagicMock(return_value=True)
        runtime._transport.check_ping = MagicMock(return_value=False)
        runtime._transport.get_time_since_last_ping = MagicMock(return_value=30.0)

        ## Act & Assert
        assert runtime.check_should_reset() is True

    @capture_logs(logger_level='WARNING', expected_errors=['Last WebSocket ping happened'], partial_match=True)
    def test_check_should_reset_returns_false_when_ping_fails_with_reconnect_timeout(self, runtime):
        """WsRuntime.check_should_reset returns False when ping fails but reconnect_timeout is set."""
        ## Arrange
        runtime._state = WsState.OPEN
        runtime._reconnect_timeout = 5.0
        runtime._transport.is_ready = MagicMock(return_value=True)
        runtime._transport.check_ping = MagicMock(return_value=False)
        runtime._transport.get_time_since_last_ping = MagicMock(return_value=30.0)

        ## Act & Assert
        assert runtime.check_should_reset() is False

    @capture_logs(logger_level='WARNING', expected_errors=['Last heartbeat happened'], partial_match=True)
    def test_check_should_reset_returns_true_when_heartbeat_exceeds_interval(self, runtime):
        """WsRuntime.check_should_reset returns True when heartbeat exceeds max_ping_interval."""
        ## Arrange
        runtime._state = WsState.OPEN
        runtime._transport.is_ready = MagicMock(return_value=True)
        runtime._transport.check_ping = MagicMock(return_value=True)
        runtime._last_heartbeat = 1000.0

        ## Act
        with mock_module_time('ibind.ws_v2.ws_runtime', time_sequence=[1030.0]):
            result = runtime.check_should_reset()

        ## Assert
        assert result is True

    @capture_logs()
    def test_check_should_reset_returns_false_when_heartbeat_within_interval(self, runtime):
        """WsRuntime.check_should_reset returns False when heartbeat is within max_ping_interval."""
        ## Arrange
        runtime._state = WsState.OPEN
        runtime._transport.is_ready = MagicMock(return_value=True)
        runtime._transport.check_ping = MagicMock(return_value=True)

        ## Act
        with mock_module_time('ibind.ws_v2.ws_runtime', time_sequence=[1000.0, 1010.0]):
            runtime._last_heartbeat = 1000.0
            result = runtime.check_should_reset()

        ## Assert
        assert result is False


class TestHealthCheck:
    @capture_logs()
    def test_health_check_returns_true_when_no_reset_needed(self, runtime):
        """WsRuntime.health_check returns True when check_should_reset returns False."""
        ## Arrange
        runtime.check_should_reset = MagicMock(return_value=False)

        ## Act & Assert
        assert runtime.health_check() is True

    @capture_logs(logger_level='WARNING', expected_errors=['Health check failed'], partial_match=True)
    def test_health_check_resets_websocket_when_check_fails(self, runtime):
        """WsRuntime.health_check resets websocket when check_should_reset returns True."""
        ## Arrange
        runtime._running = True
        runtime.check_should_reset = MagicMock(return_value=True)
        runtime.reset_websocket_app = MagicMock()

        ## Act
        result = runtime.health_check()

        ## Assert
        runtime.reset_websocket_app.assert_called_once()
        assert result is False
        assert runtime._state == WsState.DEGRADED

    @capture_logs()
    def test_health_check_returns_false_when_not_running(self, runtime):
        """WsRuntime.health_check returns False when runtime is not running."""
        ## Arrange
        runtime._running = False
        runtime.check_should_reset = MagicMock(return_value=True)

        ## Act & Assert
        assert runtime.health_check() is False


class TestProcessTransportQueue:
    @capture_logs()
    def test_process_transport_queue_handles_events(self, runtime):
        """WsRuntime._process_transport_queue processes all events in queue."""
        ## Arrange
        event1 = TransportOpened()
        event2 = TransportClosed(close_status_code=1000, close_msg='')
        runtime._transport_queue.put(event1)
        runtime._transport_queue.put(event2)
        runtime._handle_transport_event = MagicMock()

        ## Act
        runtime._process_transport_queue()

        ## Assert
        assert runtime._handle_transport_event.call_count == 2

    @capture_logs(logger_level='ERROR', expected_errors=['Exception processing transport event'], partial_match=True)
    def test_process_transport_queue_retries_failed_events(self, runtime):
        """WsRuntime._process_transport_queue retries events that raise exceptions."""
        ## Arrange
        event = TransportOpened()
        runtime._transport_queue.put(event)
        runtime._handle_transport_event = MagicMock(side_effect=RuntimeError('processing error'))

        ## Act
        runtime._process_transport_queue()

        ## Assert
        assert event.get_attempt() == 1
        assert runtime._transport_queue.get() is event

    @capture_logs(logger_level='ERROR', expected_errors=['Exception processing transport event', 'Max retries', 'dropping event'], partial_match=True)
    def test_process_transport_queue_drops_event_after_max_retries(self, runtime):
        """WsRuntime._process_transport_queue drops events after max retries."""
        ## Arrange
        event = TransportOpened()
        for _ in range(6):
            event.add_attempt()
        runtime._transport_queue.put(event)
        runtime._handle_transport_event = MagicMock(side_effect=RuntimeError('processing error'))

        ## Act
        runtime._process_transport_queue()

        ## Assert
        assert runtime._transport_queue.empty()


class TestHandleTransportEvent:
    @capture_logs()
    def test_handle_transport_event_routes_opened(self, runtime):
        """WsRuntime._handle_transport_event routes TransportOpened to _handle_on_open."""
        ## Arrange
        event = TransportOpened()
        runtime._handle_on_open = MagicMock()

        ## Act
        runtime._handle_transport_event(event)

        ## Assert
        runtime._handle_on_open.assert_called_once()

    @capture_logs()
    def test_handle_transport_event_routes_reconnect(self, runtime):
        """WsRuntime._handle_transport_event routes TransportReconnect to _handle_on_reconnect."""
        ## Arrange
        event = TransportReconnect()
        runtime._handle_on_reconnect = MagicMock()

        ## Act
        runtime._handle_transport_event(event)

        ## Assert
        runtime._handle_on_reconnect.assert_called_once()

    @capture_logs()
    def test_handle_transport_event_routes_closed(self, runtime):
        """WsRuntime._handle_transport_event routes TransportClosed to _handle_on_close."""
        ## Arrange
        event = TransportClosed(close_status_code=1000, close_msg='normal')
        runtime._handle_on_close = MagicMock()

        ## Act
        runtime._handle_transport_event(event)

        ## Assert
        runtime._handle_on_close.assert_called_once_with(1000, 'normal')

    @capture_logs()
    def test_handle_transport_event_routes_error(self, runtime):
        """WsRuntime._handle_transport_event routes TransportError to _handle_on_error."""
        ## Arrange
        exc = RuntimeError('error')
        event = TransportError(exception=exc)
        runtime._handle_on_error = MagicMock()

        ## Act
        runtime._handle_transport_event(event)

        ## Assert
        runtime._handle_on_error.assert_called_once_with(exc)

    @capture_logs()
    def test_handle_transport_event_routes_message(self, runtime):
        """WsRuntime._handle_transport_event routes TransportMessage to _handle_on_message."""
        ## Arrange
        event = TransportMessage(message='{"test": "data"}')
        runtime._handle_on_message = MagicMock()

        ## Act
        runtime._handle_transport_event(event)

        ## Assert
        runtime._handle_on_message.assert_called_once_with('{"test": "data"}')

    @capture_logs(logger_level='ERROR', expected_errors=['Unknown event type'], partial_match=True)
    def test_handle_transport_event_logs_unknown_event(self, runtime):
        """WsRuntime._handle_transport_event logs error for unknown event types."""
        ## Arrange
        event = MagicMock()

        ## Act
        runtime._handle_transport_event(event)


class TestHandleOnOpen:
    @capture_logs(logger_level='INFO', expected_errors=['Connection open', 'Websocket ready'], partial_match=True)
    def test_handle_on_open_sets_state_and_emits_event(self, runtime, mock_internal_sink):
        """WsRuntime._handle_on_open sets state to OPEN and emits WsOpen."""
        ## Arrange
        open_events = []
        mock_internal_sink.on(WsOpen, lambda e: open_events.append(e))

        ## Act
        runtime._handle_on_open()

        ## Assert
        assert runtime._state == WsState.OPEN
        assert len(open_events) == 1

    @capture_logs()
    def test_handle_on_open_sets_authenticated_false_when_not_ready_state(self, runtime):
        """WsRuntime._handle_on_open sets authenticated to False when ready_state is AUTHENTICATED."""
        ## Arrange
        runtime._ready_state = WsState.AUTHENTICATED
        runtime._authenticated = True

        ## Act
        runtime._handle_on_open()

        ## Assert
        assert runtime._authenticated is False


class TestHandleOnReconnect:
    @capture_logs(logger_level='INFO', expected_errors=['Connection reopened', 'Websocket ready'], partial_match=True)
    def test_handle_on_reconnect_sets_state_and_emits_event(self, runtime, mock_internal_sink):
        """WsRuntime._handle_on_reconnect sets state to OPEN and emits WsOpen."""
        ## Arrange
        open_events = []
        mock_internal_sink.on(WsOpen, lambda e: open_events.append(e))

        ## Act
        runtime._handle_on_reconnect()

        ## Assert
        assert runtime._state == WsState.OPEN
        assert len(open_events) == 1

    @capture_logs(logger_level='INFO', expected_errors=['Connection reopened', 'Connection unauthenticated'], partial_match=True)
    def test_handle_on_reconnect_sets_authenticated_false_when_not_ready(self, runtime):
        """WsRuntime._handle_on_reconnect unauthenticates when ready_state is AUTHENTICATED."""
        ## Arrange
        runtime._ready_state = WsState.AUTHENTICATED
        runtime._authenticated = True

        ## Act
        runtime._handle_on_reconnect()

        ## Assert
        assert runtime._state == WsState.OPEN
        assert runtime._authenticated is False


class TestHandleOnError:
    @capture_logs(logger_level='ERROR', expected_errors=['Connection error: test error'], partial_match=True)
    def test_handle_on_error_emits_event(self, runtime, mock_internal_sink):
        """WsRuntime._handle_on_error emits WsError event."""
        ## Arrange
        error = RuntimeError('test error')
        error_events = []
        mock_internal_sink.on(WsError, lambda e: error_events.append(e))

        ## Act
        runtime._handle_on_error(error)

        ## Assert
        assert len(error_events) == 1
        assert error_events[0].error is error

    @capture_logs(logger_level='ERROR', expected_errors=['Connection error: Connection to remote host was lost'], partial_match=True)
    def test_handle_on_error_degrades_on_connection_lost(self, runtime):
        """WsRuntime._handle_on_error degrades state on connection lost error."""
        ## Arrange
        runtime._state = WsState.OPEN

        ## Act
        runtime._handle_on_error(Exception('Connection to remote host was lost.'))

        ## Assert
        assert runtime._state == WsState.DEGRADED
        assert runtime._authenticated is False


class TestHandleOnClose:
    @capture_logs(logger_level='ERROR', expected_errors=['on_close error: 1000'], partial_match=True)
    def test_handle_on_close_sets_state_and_emits_event(self, runtime, mock_internal_sink):
        """WsRuntime._handle_on_close sets state to CLOSED and emits WsClose."""
        ## Arrange
        runtime._state = WsState.OPEN
        close_events = []
        mock_internal_sink.on(WsClose, lambda e: close_events.append(e))

        ## Act
        runtime._handle_on_close(1000, 'normal')

        ## Assert
        assert runtime._state == WsState.CLOSED
        assert runtime._last_heartbeat is None
        assert len(close_events) == 1

    @capture_logs(logger_level='INFO', expected_errors=['Connection gracefully closed'], partial_match=True)
    def test_handle_on_close_graceful_when_stopping(self, runtime):
        """WsRuntime._handle_on_close logs graceful close when state is STOPPING."""
        ## Arrange
        runtime._state = WsState.STOPPING

        ## Act
        runtime._handle_on_close(None, None)

        ## Assert
        assert runtime._state == WsState.CLOSED

    @capture_logs(logger_level='ERROR', expected_errors=['WsRuntime(CLOSED): on_close error: 1001 | going away'])
    def test_handle_on_close_logs_error_when_status_code_present(self, runtime):
        """WsRuntime._handle_on_close logs error when close_status_code is not None."""
        ## Arrange
        runtime._state = WsState.OPEN

        ## Act
        runtime._handle_on_close(1001, 'going away')

    @capture_logs(logger_level='INFO', expected_errors=['Connection closed'], partial_match=True)
    def test_handle_on_close_invalidates_subscriptions_when_not_stopping(self, runtime):
        """WsRuntime._handle_on_close invalidates subscriptions when not STOPPING."""
        ## Arrange
        runtime._state = WsState.OPEN
        runtime.subscription_controller.invalidate_subscriptions = MagicMock()

        ## Act
        runtime._handle_on_close(None, None)

        ## Assert
        assert runtime.subscription_controller.invalidate_subscriptions.call_count >= 1


class TestEmit:
    @capture_logs()
    def test_emit_sends_to_both_sinks(self, runtime):
        """WsRuntime._emit sends event to both internal and external sinks."""
        ## Arrange
        event = WsOpen()
        runtime._internal_sink.emit = MagicMock()
        runtime._sink.emit = MagicMock()

        ## Act
        runtime._emit(event)

        ## Assert
        runtime._internal_sink.emit.assert_called_once_with(event)
        runtime._sink.emit.assert_called_once_with(event)

    @capture_logs(logger_level='ERROR', expected_errors=['Internal sink exception'], partial_match=True)
    def test_emit_logs_internal_sink_exception(self, runtime):
        """WsRuntime._emit logs exceptions from internal sink."""
        ## Arrange
        event = WsOpen()
        runtime._internal_sink.emit = MagicMock(side_effect=RuntimeError('internal error'))
        runtime._sink.emit = MagicMock()

        ## Act
        runtime._emit(event)

        ## Assert
        runtime._sink.emit.assert_called_once_with(event)

    @capture_logs(logger_level='ERROR', expected_errors=['External sink exception'], partial_match=True)
    def test_emit_logs_external_sink_exception(self, runtime):
        """WsRuntime._emit logs exceptions from external sink."""
        ## Arrange
        event = WsOpen()
        runtime._internal_sink.emit = MagicMock()
        runtime._sink.emit = MagicMock(side_effect=RuntimeError('external error'))

        ## Act
        runtime._emit(event)


class TestCycle:
    @capture_logs(logger_level='DEBUG', expected_errors=['Runtime thread started', 'Runtime thread stopped'], partial_match=True)
    def test_cycle_runs_one_iteration(self, runtime):
        """WsRuntime._cycle runs one iteration then exits when _running becomes False."""
        ## Arrange
        runtime._running = True
        runtime._wait_event.wait = MagicMock(side_effect=lambda t: setattr(runtime, '_running', False))
        runtime._maintain_transport = MagicMock()
        runtime._maintain_subscriptions = MagicMock()
        runtime._process_transport_queue = MagicMock()
        runtime.health_check = MagicMock()

        ## Act
        runtime._cycle()

        ## Assert
        runtime._maintain_transport.assert_called_once()
        runtime._maintain_subscriptions.assert_called_once()
        runtime._process_transport_queue.assert_called_once()
        runtime.health_check.assert_not_called()

    @capture_logs(logger_level='DEBUG', expected_errors=['Runtime thread started', 'Runtime thread stopped'], partial_match=True)
    def test_cycle_triggers_health_check(self, runtime):
        """WsRuntime._cycle triggers health_check when interval has passed."""
        ## Arrange
        runtime._running = True
        runtime._wait_event.wait = MagicMock(side_effect=lambda t: setattr(runtime, '_running', False))
        runtime._maintain_transport = MagicMock()
        runtime._maintain_subscriptions = MagicMock()
        runtime._process_transport_queue = MagicMock()
        runtime.health_check = MagicMock()
        runtime._last_health_check = 0

        ## Act
        with mock_module_time('ibind.ws_v2.ws_runtime', time_sequence=[15.0]):
            runtime._cycle()

        ## Assert
        runtime.health_check.assert_called_once()
        assert runtime._last_health_check == 15.0

    @capture_logs(logger_level='DEBUG', expected_errors=['Runtime thread started', 'Runtime thread stopped'], partial_match=True)
    def test_cycle_final_pass_when_not_stopped_or_closed(self, runtime):
        """WsRuntime._cycle performs final pass when state is not STOPPED or CLOSED."""
        ## Arrange
        runtime._running = False
        runtime._state = WsState.OPEN
        runtime._process_transport_queue = MagicMock()
        runtime.subscription_controller.reconcile_bindings = MagicMock()

        ## Act
        runtime._cycle()

        ## Assert
        runtime._process_transport_queue.assert_called_once()
        runtime.subscription_controller.reconcile_bindings.assert_called_once()

    @capture_logs(logger_level='DEBUG', expected_errors=['Runtime thread started', 'Runtime thread stopped'], partial_match=True)
    def test_cycle_skips_final_pass_when_stopped(self, runtime):
        """WsRuntime._cycle skips final pass when state is STOPPED."""
        ## Arrange
        runtime._running = False
        runtime._state = WsState.STOPPED
        runtime._process_transport_queue = MagicMock()
        runtime.subscription_controller.reconcile_bindings = MagicMock()

        ## Act
        runtime._cycle()

        ## Assert
        runtime._process_transport_queue.assert_not_called()
        runtime.subscription_controller.reconcile_bindings.assert_not_called()
