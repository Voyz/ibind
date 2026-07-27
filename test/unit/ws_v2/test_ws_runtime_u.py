import ssl
from unittest.mock import MagicMock, patch

import pytest

from ibind import events
from ibind.ws_v2._ws_events import NoopSink, AsyncSink, QueueSink
from ibind.ws_v2.ws_runtime import WsRuntime, make_sslopt
from ibind.ws_v2.runtime.ws_state_manager import WsState
from test.test_utils import capture_logs, mock_module_time


class MockRouter:
    def route(self, message):
        return events.WsOpen()


class MockResolver:
    def resolve_binding_key(self, event):
        return (False, None)


@pytest.fixture
def mock_sink():
    return NoopSink()


@pytest.fixture
def mock_router():
    return MockRouter()


@pytest.fixture
def mock_resolver():
    return MockResolver()


@pytest.fixture
def runtime(mock_sink, mock_router, mock_resolver):
    return WsRuntime(
        url='wss://test.example.com',
        cycle_interval=0.01,
        sink=mock_sink,
        router=mock_router,
        subscription_resolver=mock_resolver,
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
        assert result == {'cert_reqs': ssl.CERT_NONE}

    @capture_logs()
    def test_make_sslopt_with_none_returns_cert_none(self):
        """make_sslopt returns CERT_NONE when cacert is None."""
        ## Act
        result = make_sslopt('')

        ## Assert
        assert result == {'cert_reqs': ssl.CERT_NONE}

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

            ## Act & Assert
            with pytest.raises(ValueError, match='Cacert must be a valid Path or False'):
                make_sslopt('/invalid/path.pem')


class TestOnStateChange:
    @capture_logs(logger_level='DEBUG', expected_errors=['STOPPED -> STARTING'], partial_match=True)
    def test_on_state_change_emits_starting_event(self, runtime):
        """_on_state_change emits WsStarting when state becomes STARTING."""
        ## Arrange
        starting_events = []
        runtime._internal_sink.on(events.WsStarting, starting_events.append)

        ## Act
        runtime._state_manager.set_state(WsState.STARTING)

        ## Assert
        assert len(starting_events) == 1

    @capture_logs(logger_level='DEBUG', expected_errors=['STOPPED -> OPEN'], partial_match=True)
    def test_on_state_change_emits_open_event(self, runtime):
        """_on_state_change emits WsOpen when state becomes OPEN."""
        ## Arrange
        open_events = []
        runtime._internal_sink.on(events.WsOpen, open_events.append)

        ## Act
        runtime._state_manager.set_state(WsState.OPEN)

        ## Assert
        assert len(open_events) == 1
        assert runtime._state_manager.last_heartbeat is None

    @capture_logs(logger_level='DEBUG', expected_errors=['OPEN -> AUTHENTICATED'], partial_match=True)
    def test_on_state_change_emits_authenticated_and_ready_events(self, runtime):
        """_on_state_change emits WsAuthenticated and WsReady when state becomes AUTHENTICATED."""
        ## Arrange
        runtime._state_manager.set_state(WsState.OPEN)
        auth_events = []
        ready_events = []
        runtime._internal_sink.on(events.WsAuthenticated, auth_events.append)
        runtime._internal_sink.on(events.WsReady, ready_events.append)

        ## Act
        with mock_module_time('ibind.ws_v2.ws_runtime', time_sequence=[1000.0]):
            runtime._state_manager.set_state(WsState.AUTHENTICATED)

        ## Assert
        assert len(auth_events) == 1
        assert len(ready_events) == 1
        assert runtime._state_manager.last_heartbeat == 1000.0

    @capture_logs(logger_level='DEBUG', expected_errors=['STOPPED -> DEGRADED'], partial_match=True)
    def test_on_state_change_emits_degraded_event_and_invalidates_subscriptions(self, runtime):
        """_on_state_change emits WsDegraded and invalidates subscriptions when state becomes DEGRADED."""
        ## Arrange
        degraded_events = []
        runtime._internal_sink.on(events.WsDegraded, degraded_events.append)
        runtime.subscription_controller.invalidate_subscriptions = MagicMock()

        ## Act
        runtime._state_manager.set_state(WsState.DEGRADED)

        ## Assert
        assert len(degraded_events) == 1
        runtime.subscription_controller.invalidate_subscriptions.assert_called_once()

    @capture_logs(logger_level='DEBUG', expected_errors=['OPEN -> AUTHENTICATED', 'AUTHENTICATED -> DEGRADED'], partial_match=True)
    def test_on_state_change_emits_degraded_event_when_leaving_authenticated(self, runtime):
        """_on_state_change emits WsDegraded and invalidates subscriptions when an authenticated connection degrades."""
        ## Arrange
        degraded_events = []
        runtime._internal_sink.on(events.WsDegraded, degraded_events.append)
        runtime.subscription_controller.invalidate_subscriptions = MagicMock()
        runtime._state_manager.set_state(WsState.OPEN)
        with mock_module_time('ibind.ws_v2.ws_runtime', time_sequence=[1000.0]):
            runtime._state_manager.set_state(WsState.AUTHENTICATED)

        ## Act
        runtime._state_manager.set_state(WsState.DEGRADED)

        ## Assert
        assert len(degraded_events) == 1
        assert degraded_events[0].previous_state == WsState.AUTHENTICATED
        assert degraded_events[0].current_state == WsState.DEGRADED
        runtime.subscription_controller.invalidate_subscriptions.assert_called_once()

    @capture_logs()
    def test_on_state_change_does_not_emit_degraded_when_already_degraded(self, runtime):
        """_on_state_change does not emit WsDegraded when already in DEGRADED state."""
        ## Arrange
        runtime._state_manager._state = WsState.DEGRADED
        degraded_events = []
        runtime._internal_sink.on(events.WsDegraded, degraded_events.append)

        ## Act
        runtime._state_manager.set_state(WsState.DEGRADED)

        ## Assert
        assert len(degraded_events) == 0

    @capture_logs(logger_level='DEBUG', expected_errors=['OPEN -> AUTHENTICATED', 'AUTHENTICATED -> DEGRADED'], partial_match=True)
    def test_on_state_change_invalidates_subscriptions_when_leaving_authenticated(self, runtime):
        """_on_state_change invalidates subscriptions when leaving AUTHENTICATED state (not to STOPPING)."""
        ## Arrange
        mock_invalidate = MagicMock()
        runtime.subscription_controller.invalidate_subscriptions = mock_invalidate
        runtime._state_manager.set_state(WsState.OPEN)
        with mock_module_time('ibind.ws_v2.ws_runtime', time_sequence=[1000.0]):
            runtime._state_manager.set_state(WsState.AUTHENTICATED)

        ## Act
        runtime._state_manager.set_state(WsState.DEGRADED)

        ## Assert
        mock_invalidate.assert_called_once()

    @capture_logs(logger_level='DEBUG', expected_errors=['OPEN -> AUTHENTICATED', 'AUTHENTICATED -> OPEN'], partial_match=True)
    def test_on_state_change_invalidates_subscriptions_when_authentication_is_lost(self, runtime):
        """_on_state_change invalidates subscriptions when an authenticated connection returns to OPEN."""
        ## Arrange
        mock_invalidate = MagicMock()
        runtime.subscription_controller.invalidate_subscriptions = mock_invalidate
        runtime._state_manager.set_state(WsState.OPEN)
        with mock_module_time('ibind.ws_v2.ws_runtime', time_sequence=[1000.0]):
            runtime._state_manager.set_state(WsState.AUTHENTICATED)

        ## Act
        runtime._state_manager.set_state(WsState.OPEN)

        ## Assert
        mock_invalidate.assert_called_once()

    @capture_logs(logger_level='DEBUG', expected_errors=['OPEN -> CLOSED'], partial_match=True)
    def test_on_state_change_invalidates_subscriptions_on_close_when_not_stopping(self, runtime):
        """_on_state_change invalidates subscriptions when state becomes CLOSED (not from STOPPING)."""
        ## Arrange
        runtime._state_manager.set_state(WsState.OPEN)
        runtime.subscription_controller.invalidate_subscriptions = MagicMock()

        ## Act
        runtime._state_manager.set_state(WsState.CLOSED)

        ## Assert
        runtime.subscription_controller.invalidate_subscriptions.assert_called_once()

    @capture_logs(logger_level='DEBUG', expected_errors=['STOPPING -> CLOSED'], partial_match=True)
    def test_on_state_change_does_not_invalidate_subscriptions_when_stopping(self, runtime):
        """_on_state_change does not invalidate subscriptions when transitioning from STOPPING to CLOSED."""
        ## Arrange
        runtime._state_manager._state = WsState.STOPPING
        runtime.subscription_controller.invalidate_subscriptions = MagicMock()

        ## Act
        runtime._state_manager.set_state(WsState.CLOSED)

        ## Assert
        runtime.subscription_controller.invalidate_subscriptions.assert_not_called()

    @capture_logs(logger_level='DEBUG', expected_errors=['OPEN -> STOPPING'], partial_match=True)
    def test_on_state_change_emits_stopping_event(self, runtime):
        """_on_state_change emits WsStopping when state becomes STOPPING."""
        ## Arrange
        runtime._state_manager.set_state(WsState.OPEN)
        stopping_events = []
        runtime._internal_sink.on(events.WsStopping, stopping_events.append)

        ## Act
        runtime._state_manager.set_state(WsState.STOPPING)

        ## Assert
        assert len(stopping_events) == 1
        assert stopping_events[0].previous_state == WsState.OPEN
        assert stopping_events[0].current_state == WsState.STOPPING

    @capture_logs(logger_level='DEBUG', expected_errors=['OPEN -> STOPPED'], partial_match=True)
    def test_on_state_change_emits_stopped_event(self, runtime):
        """_on_state_change emits WsStopped when state becomes STOPPED."""
        ## Arrange
        runtime._state_manager.set_state(WsState.OPEN)
        stopped_events = []
        runtime._internal_sink.on(events.WsStopped, stopped_events.append)

        ## Act
        runtime._state_manager.set_state(WsState.STOPPED)

        ## Assert
        assert len(stopped_events) == 1


class TestSetAuthenticated:
    @capture_logs(logger_level='DEBUG', expected_errors=['AUTHENTICATED -> OPEN'], partial_match=True)
    def test_set_authenticated_false_when_authenticated(self, runtime):
        """set_authenticated(False) transitions from AUTHENTICATED to OPEN."""
        ## Arrange
        runtime._state_manager.set_state(WsState.AUTHENTICATED)

        ## Act
        runtime.set_authenticated(False)

        ## Assert
        assert runtime._state_manager.get_state() == WsState.OPEN

    @capture_logs(logger_level='DEBUG', expected_errors=['OPEN -> AUTHENTICATED'], partial_match=True)
    def test_set_authenticated_true_when_open(self, runtime):
        """set_authenticated(True) transitions from OPEN to AUTHENTICATED."""
        ## Arrange
        runtime._state_manager.set_state(WsState.OPEN)

        ## Act
        with mock_module_time('ibind.ws_v2.ws_runtime', time_sequence=[1000.0]):
            runtime.set_authenticated(True)

        ## Assert
        assert runtime._state_manager.get_state() == WsState.AUTHENTICATED

    @capture_logs()
    def test_set_authenticated_false_when_not_authenticated_does_nothing(self, runtime):
        """set_authenticated(False) does nothing when not AUTHENTICATED."""
        ## Arrange
        runtime._state_manager.set_state(WsState.OPEN)

        ## Act
        runtime.set_authenticated(False)

        ## Assert
        assert runtime._state_manager.get_state() == WsState.OPEN


class TestSend:
    @capture_logs(logger_level='ERROR', expected_errors=['State must be AUTHENTICATED before sending'], partial_match=True)
    def test_send_returns_false_when_not_authenticated(self, runtime):
        """send returns False when state is not AUTHENTICATED."""
        ## Arrange
        runtime._state_manager.set_state(WsState.OPEN)

        ## Act
        result = runtime.send('test_payload')

        ## Assert
        assert result is False

    @capture_logs(logger_level='INFO', expected_errors=['Sending payload: test_payload'], partial_match=True)
    def test_send_calls_transport_when_authenticated(self, runtime):
        """send calls transport.send when state is AUTHENTICATED."""
        ## Arrange
        runtime._state_manager.set_state(WsState.AUTHENTICATED)
        runtime._transport.send = MagicMock(return_value=True)

        ## Act
        result = runtime.send('test_payload')

        ## Assert
        runtime._transport.send.assert_called_once_with('test_payload')
        assert result is True


class TestAsyncSinkHandling:
    @capture_logs(logger_level='DEBUG', expected_errors=['STOPPED -> STARTING'], partial_match=True)
    def test_on_starting_starts_async_sink(self, mock_router, mock_resolver):
        """_on_starting starts AsyncSink when WsStarting event is emitted."""
        ## Arrange
        async_sink = AsyncSink(sink=NoopSink())
        async_sink.start = MagicMock()
        runtime = WsRuntime(
            url='wss://test.example.com',
            cycle_interval=0.01,
            sink=async_sink,
            router=mock_router,
            subscription_resolver=mock_resolver,
        )
        runtime._register_internal_callbacks()

        ## Act
        runtime._state_manager.set_state(WsState.STARTING)

        ## Assert
        async_sink.start.assert_called_once()

    @capture_logs(logger_level='DEBUG', expected_errors=['OPEN -> STOPPED'], partial_match=True)
    def test_on_stopped_stops_async_sink(self, mock_router, mock_resolver):
        """_on_stopped stops AsyncSink when WsStopped event is emitted."""
        ## Arrange
        async_sink = AsyncSink(sink=NoopSink())
        async_sink.stop = MagicMock(return_value=True)
        runtime = WsRuntime(
            url='wss://test.example.com',
            cycle_interval=0.01,
            sink=async_sink,
            router=mock_router,
            subscription_resolver=mock_resolver,
        )
        runtime._register_internal_callbacks()
        runtime._state_manager.set_state(WsState.OPEN)

        ## Act
        runtime._state_manager.set_state(WsState.STOPPED)

        ## Assert
        async_sink.stop.assert_called_once()

    @capture_logs(
        logger_level='DEBUG',
        expected_errors=['STOPPED -> STARTING', 'STARTING -> OPEN', 'OPEN -> STOPPED'],
        partial_match=True,
    )
    def test_on_stopped_delivers_event_before_stopping_async_sink(self, mock_router, mock_resolver):
        """WsStopped reaches the wrapped sink during AsyncSink's final queue drain."""
        ## Arrange
        queue_sink = QueueSink()
        async_sink = AsyncSink(sink=queue_sink, stop_timeout=1, cycle_interval=0.01)
        runtime = WsRuntime(
            url='wss://test.example.com',
            cycle_interval=0.01,
            sink=async_sink,
            router=mock_router,
            subscription_resolver=mock_resolver,
        )
        runtime._state_manager.set_state(WsState.STARTING)
        runtime._state_manager.set_state(WsState.OPEN)

        ## Act
        runtime._state_manager.set_state(WsState.STOPPED)

        ## Assert
        stopped_event = queue_sink.get(events.WsStopped)
        assert stopped_event is not None
        assert stopped_event.previous_state == WsState.OPEN
        assert stopped_event.current_state == WsState.STOPPED
        assert async_sink._running is False
