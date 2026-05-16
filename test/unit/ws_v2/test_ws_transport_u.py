from unittest.mock import MagicMock, patch
from websocket import STATUS_NORMAL, STATUS_UNEXPECTED_CONDITION

import pytest

from ibind import ExternalBrokerError
from ibind.support.py_utils import UNDEFINED
from test.test_utils import capture_logs, mock_module_time
from ibind.ws_v2.ws_transport import (
    TransportOpened,
    TransportClosed,
    TransportError,
    TransportMessage,
    TransportReconnect,
    WsTransport,
)

TEST_PING_INTERVAL = 10
TEST_PING_TIMEOUT = 10
TEST_MAX_PING_INTERVAL = 20
TEST_CONNECTION_TIMEOUT = 5
TEST_RECONNECT_TIMEOUT = 5
TEST_TIME_WITHIN_INTERVAL = 10
TEST_TIME_EXCEEDS_INTERVAL = 30
TEST_TIME_CUSTOM_CHECK = 15
TEST_TIME_SINCE_LAST_PING = 5
TEST_CUSTOM_MAX_INTERVAL = 10


@pytest.fixture
def mock_event_callback():
    return MagicMock()


@pytest.fixture
def mock_get_cookie():
    return MagicMock(return_value='test_cookie')


@pytest.fixture
def mock_get_header():
    return MagicMock(return_value={'User-Agent': 'test'})


@pytest.fixture
def transport(mock_event_callback, mock_get_cookie, mock_get_header):
    return WsTransport(
        url='wss://test.example.com',
        event_callback=mock_event_callback,
        sslopt={'cert_reqs': 0},
        get_cookie=mock_get_cookie,
        get_header=mock_get_header,
        ping_interval=TEST_PING_INTERVAL,
        ping_timeout=TEST_PING_TIMEOUT,
        max_ping_interval=TEST_MAX_PING_INTERVAL,
        connection_timeout=TEST_CONNECTION_TIMEOUT,
        reconnect_timeout=TEST_RECONNECT_TIMEOUT,
    )


@pytest.fixture
def ready_wsa():
    """Returns a ready WebSocketApp mock with nested socket mocks."""
    wsa = MagicMock()
    wsa.ready = True
    wsa.sock = MagicMock()
    wsa.sock.sock = MagicMock()
    return wsa


class TestTransportEvent:
    @capture_logs()
    def test_add_attempt_increments_counter(self):
        """TransportEvent.add_attempt increments the attempt counter."""
        ## Arrange
        event = TransportOpened()

        ## Act
        event.add_attempt()
        event.add_attempt()

        ## Assert
        assert event.get_attempt() == 2

    @capture_logs()
    def test_get_attempt_returns_current_count(self):
        """TransportEvent.get_attempt returns the current attempt count."""
        ## Arrange
        event = TransportOpened()

        ## Act
        result = event.get_attempt()

        ## Assert
        assert result == 0


class TestTransportEvents:
    @capture_logs()
    def test_transport_event_creation(self):
        """All transport event types can be created with their respective fields."""
        ## Arrange
        exc = RuntimeError('connection failed')
        opened = TransportOpened()
        closed = TransportClosed(close_status_code=1000, close_msg='normal')
        error = TransportError(exception=exc)
        message = TransportMessage(message='{"test": "data"}')
        reconnect = TransportReconnect()

        ## Assert
        assert opened.received_at is not None
        assert closed.close_status_code == 1000
        assert closed.close_msg == 'normal'
        assert error.exception is exc
        assert message.message == '{"test": "data"}'
        assert reconnect.received_at is not None


class TestDisconnect:
    @capture_logs(logger_level='INFO', expected_errors=['WebSocketApp is None, skipping disconnect'], partial_match=True)
    def test_disconnect_when_wsa_is_none(self, transport):
        """WsTransport.disconnect logs and returns early when WebSocketApp is None."""
        ## Arrange
        transport._wsa = None

        ## Act
        transport.disconnect()

    @capture_logs()
    def test_disconnect_calls_close(self, transport):
        """WsTransport.disconnect calls WebSocketApp.close with STATUS_NORMAL."""
        ## Arrange
        transport._wsa = MagicMock()

        ## Act
        transport.disconnect()

        ## Assert
        transport._wsa.close.assert_called_once_with(status=STATUS_NORMAL, timeout=TEST_CONNECTION_TIMEOUT)


class TestStop:
    @capture_logs(logger_level='DEBUG', expected_errors=['Stopping transport'], partial_match=True)
    def test_stop_sets_running_false_and_disconnects(self, transport):
        """WsTransport.stop sets running to False and calls disconnect."""
        ## Arrange
        transport._running = True
        transport._wsa = MagicMock()

        ## Act
        transport.stop()

        ## Assert
        assert transport._running is False
        transport._wsa.close.assert_called_once()


class TestResetWebsocketApp:
    @capture_logs()
    def test_reset_raises_when_called_from_transport_thread(self, transport):
        """WsTransport.reset_websocket_app raises RuntimeError when called from transport thread."""
        ## Arrange
        transport._tname = 'test_thread'

        ## Act / Assert
        with patch('ibind.ws_v2.ws_transport.tname', return_value='test_thread'):
            with pytest.raises(RuntimeError, match='Resetting websocket app called from within transport thread'):
                transport.reset_websocket_app()

    @capture_logs(logger_level='INFO', expected_errors=['WebSocketApp is None, skipping reset'], partial_match=True)
    def test_reset_returns_false_when_wsa_is_none(self, transport):
        """WsTransport.reset_websocket_app returns False when WebSocketApp is None."""
        ## Arrange
        transport._wsa = None

        ## Act
        result = transport.reset_websocket_app()

        ## Assert
        assert result is False

    @capture_logs(logger_level='INFO', expected_errors=['Reset'], partial_match=True)
    def test_reset_closes_and_recreates_wsa(self, transport):
        """WsTransport.reset_websocket_app closes current WebSocketApp and waits for recreation."""
        ## Arrange
        mock_wsa = MagicMock()
        transport._wsa = mock_wsa

        ## Act
        with patch('ibind.ws_v2.ws_transport.wait_until', side_effect=[True, True]):
            result = transport.reset_websocket_app()

        ## Assert
        mock_wsa.close.assert_called_once_with(status=STATUS_UNEXPECTED_CONDITION, timeout=TEST_CONNECTION_TIMEOUT)

    @capture_logs(logger_level='WARNING', expected_errors=['Abandoning current WebSocketApp'], partial_match=True)
    def test_reset_abandons_wsa_when_close_times_out(self, transport):
        """WsTransport.reset_websocket_app abandons WebSocketApp when close times out."""
        ## Arrange
        mock_wsa = MagicMock()
        transport._wsa = mock_wsa

        ## Act
        with patch('ibind.ws_v2.ws_transport.wait_until', side_effect=[False, True]):
            result = transport.reset_websocket_app()

        ## Assert
        assert transport._wsa is None


class TestCheckPing:
    @capture_logs()
    def test_check_ping_returns_true_when_wsa_is_none(self, transport):
        """WsTransport.check_ping returns True when WebSocketApp is None."""
        ## Arrange
        transport._wsa = None

        ## Act
        result = transport.check_ping()

        ## Assert
        assert result is True

    @capture_logs()
    def test_check_ping_returns_true_when_last_pong_is_zero(self, transport):
        """WsTransport.check_ping returns True when last_pong_tm is 0."""
        ## Arrange
        transport._wsa = MagicMock()
        transport._wsa.last_pong_tm = 0

        ## Act
        result = transport.check_ping()

        ## Assert
        assert result is True

    @capture_logs()
    def test_check_ping_returns_true_when_within_interval(self, transport):
        """WsTransport.check_ping returns True when last pong is within max_ping_interval."""
        ## Arrange
        transport._wsa = MagicMock()
        current_time = 100.0
        transport._wsa.last_pong_tm = current_time - TEST_TIME_WITHIN_INTERVAL

        ## Act
        with mock_module_time('ibind.ws_v2.ws_transport', time_sequence=[current_time]):
            result = transport.check_ping()

        ## Assert
        assert result is True

    @capture_logs()
    def test_check_ping_returns_false_when_exceeds_interval(self, transport):
        """WsTransport.check_ping returns False when last pong exceeds max_ping_interval."""
        ## Arrange
        transport._wsa = MagicMock()
        current_time = 100.0
        transport._wsa.last_pong_tm = current_time - TEST_TIME_EXCEEDS_INTERVAL

        ## Act
        with mock_module_time('ibind.ws_v2.ws_transport', time_sequence=[current_time]):
            result = transport.check_ping()

        ## Assert
        assert result is False

    @capture_logs()
    def test_check_ping_uses_custom_max_interval(self, transport):
        """WsTransport.check_ping uses custom max_interval when provided."""
        ## Arrange
        transport._wsa = MagicMock()
        current_time = 100.0
        transport._wsa.last_pong_tm = current_time - TEST_TIME_CUSTOM_CHECK

        ## Act
        with mock_module_time('ibind.ws_v2.ws_transport', time_sequence=[current_time]):
            result = transport.check_ping(max_interval=TEST_CUSTOM_MAX_INTERVAL)

        ## Assert
        assert result is False

    @capture_logs()
    def test_get_time_since_last_ping_returns_elapsed_time(self, transport):
        """WsTransport.get_time_since_last_ping returns seconds since last pong."""
        ## Arrange
        transport._wsa = MagicMock()
        current_time = 100.0
        transport._wsa.last_pong_tm = current_time - TEST_TIME_SINCE_LAST_PING

        ## Act
        with mock_module_time('ibind.ws_v2.ws_transport', time_sequence=[current_time]):
            result = transport.get_time_since_last_ping()

        ## Assert
        assert result == TEST_TIME_SINCE_LAST_PING


class TestFetchCookie:
    @capture_logs()
    def test_fetch_cookie_returns_cookie(self, transport, mock_get_cookie):
        """WsTransport.fetch_cookie returns cookie from get_cookie callback."""
        ## Arrange
        mock_get_cookie.return_value = 'session_cookie'

        ## Act
        result = transport.fetch_cookie()

        ## Assert
        assert result == 'session_cookie'
        mock_get_cookie.assert_called_once()

    @capture_logs()
    def test_fetch_cookie_clears_authentication_flag_on_success(self, transport, mock_get_cookie):
        """WsTransport.fetch_cookie clears session_lacks_authentication flag on success."""
        ## Arrange
        transport._session_lacks_authentication = True
        mock_get_cookie.return_value = 'session_cookie'

        ## Act
        result = transport.fetch_cookie()

        ## Assert
        assert transport._session_lacks_authentication is False

    @capture_logs(logger_level='INFO', expected_errors=['Timeout retrieving cookie'], partial_match=True)
    def test_fetch_cookie_returns_undefined_on_timeout(self, transport, mock_get_cookie):
        """WsTransport.fetch_cookie returns UNDEFINED on TimeoutError."""
        ## Arrange
        mock_get_cookie.side_effect = TimeoutError('timeout')

        ## Act
        result = transport.fetch_cookie()

        ## Assert
        assert result is UNDEFINED

    @capture_logs(logger_level='INFO', expected_errors=['Failed to retrieve cookie due to lack of authentication'], partial_match=True)
    def test_fetch_cookie_handles_401_error_first_time(self, transport, mock_get_cookie):
        """WsTransport.fetch_cookie logs and sets flag on first 401 error."""
        ## Arrange
        mock_get_cookie.side_effect = ExternalBrokerError('Unauthorized', status_code=401)

        ## Act
        result = transport.fetch_cookie()

        ## Assert
        assert result is UNDEFINED
        assert transport._session_lacks_authentication is True

    @capture_logs()
    def test_fetch_cookie_silently_handles_401_error_when_flag_set(self, transport, mock_get_cookie):
        """WsTransport.fetch_cookie silently returns UNDEFINED on subsequent 401 errors."""
        ## Arrange
        transport._session_lacks_authentication = True
        mock_get_cookie.side_effect = ExternalBrokerError('Unauthorized', status_code=401)

        ## Act
        result = transport.fetch_cookie()

        ## Assert
        assert result is UNDEFINED

    @capture_logs(logger_level='ERROR', expected_errors=['Failed to retrieve cookie'], partial_match=True)
    def test_fetch_cookie_logs_other_exceptions(self, transport, mock_get_cookie):
        """WsTransport.fetch_cookie logs and returns UNDEFINED on other exceptions."""
        ## Arrange
        mock_get_cookie.side_effect = RuntimeError('unexpected error')

        ## Act
        result = transport.fetch_cookie()

        ## Assert
        assert result is UNDEFINED


class TestCheckCookie:
    @capture_logs()
    def test_check_cookie_returns_true_when_cookies_match(self, transport, mock_get_cookie):
        """WsTransport.check_cookie returns True when cookies match."""
        ## Arrange
        transport._cookie = 'test_cookie'
        mock_get_cookie.return_value = 'test_cookie'

        ## Act
        result = transport.check_cookie()

        ## Assert
        assert result is True

    @capture_logs()
    def test_check_cookie_returns_false_when_fetch_fails(self, transport, mock_get_cookie):
        """WsTransport.check_cookie returns False when fetch_cookie returns UNDEFINED."""
        ## Arrange
        mock_get_cookie.side_effect = TimeoutError('timeout')

        ## Act
        result = transport.check_cookie()

        ## Assert
        assert result is False

    @capture_logs(logger_level='WARNING', expected_errors=['Cookie changed'], partial_match=True)
    def test_check_cookie_returns_false_when_cookies_differ(self, transport, mock_get_cookie):
        """WsTransport.check_cookie returns False and logs when cookies differ."""
        ## Arrange
        transport._cookie = 'old_cookie'
        mock_get_cookie.return_value = 'new_cookie'

        ## Act
        result = transport.check_cookie()

        ## Assert
        assert result is False


class TestIsReady:
    @capture_logs()
    def test_is_ready_returns_false_when_wsa_is_none(self, transport):
        """WsTransport.is_ready returns False when WebSocketApp is None."""
        ## Arrange
        transport._wsa = None

        ## Act
        result = transport.is_ready()

        ## Assert
        assert result is False

    @capture_logs()
    def test_is_ready_returns_false_when_not_ready(self, transport):
        """WsTransport.is_ready returns False when WebSocketApp.ready is False."""
        ## Arrange
        transport._wsa = MagicMock()
        transport._wsa.ready = False

        ## Act
        result = transport.is_ready()

        ## Assert
        assert result is False

    @capture_logs()
    def test_is_ready_returns_false_when_sock_is_none(self, transport):
        """WsTransport.is_ready returns False when sock is None."""
        ## Arrange
        transport._wsa = MagicMock()
        transport._wsa.ready = True
        transport._wsa.sock = None

        ## Act
        result = transport.is_ready()

        ## Assert
        assert result is False

    @capture_logs()
    def test_is_ready_returns_false_when_sock_sock_is_none(self, transport):
        """WsTransport.is_ready returns False when sock.sock is None."""
        ## Arrange
        transport._wsa = MagicMock()
        transport._wsa.ready = True
        transport._wsa.sock = MagicMock()
        transport._wsa.sock.sock = None

        ## Act
        result = transport.is_ready()

        ## Assert
        assert result is False

    @capture_logs()
    def test_is_ready_returns_true_when_all_conditions_met(self, transport, ready_wsa):
        """WsTransport.is_ready returns True when all conditions are met."""
        ## Arrange
        transport._wsa = ready_wsa

        ## Act
        result = transport.is_ready()

        ## Assert
        assert result is True


class TestSend:
    @capture_logs()
    def test_send_raises_when_not_ready(self, transport):
        """WsTransport.send raises RuntimeError when WebSocketApp is not ready."""
        ## Arrange
        transport._wsa = None

        ## Act / Assert
        with pytest.raises(RuntimeError, match='WebSocketApp socket is not ready'):
            transport.send('test_payload')

    @capture_logs()
    def test_send_calls_wsa_send(self, transport, ready_wsa):
        """WsTransport.send calls WebSocketApp.send with payload."""
        ## Arrange
        transport._wsa = ready_wsa

        ## Act
        result = transport.send('test_payload')

        ## Assert
        transport._wsa.send.assert_called_once_with('test_payload')
        assert result is True

    @capture_logs(logger_level='ERROR', expected_errors=['Connection closed while sending payload'], partial_match=True)
    def test_send_logs_connection_closed_error(self, transport, ready_wsa):
        """WsTransport.send logs error when connection is closed."""
        ## Arrange
        transport._wsa = ready_wsa
        transport._wsa.send.side_effect = Exception('Connection is already closed')

        ## Act
        result = transport.send('test_payload')

        ## Assert
        assert result is False

    @capture_logs(logger_level='ERROR', expected_errors=['Sending payload failed'], partial_match=True)
    def test_send_logs_other_exceptions(self, transport, ready_wsa):
        """WsTransport.send logs other exceptions."""
        ## Arrange
        transport._wsa = ready_wsa
        transport._wsa.send.side_effect = RuntimeError('unexpected error')

        ## Act
        result = transport.send('test_payload')

        ## Assert
        assert result is False


class TestCallbackWrapping:
    @capture_logs(logger_level='ERROR', expected_errors=['Exception executing callback'], partial_match=True)
    def test_wrap_callback_logs_exceptions(self, transport):
        """WsTransport._wrap_callback logs exceptions from callbacks."""

        ## Arrange
        def failing_callback(ws):
            raise ValueError('callback error')

        wrapped = transport._wrap_callback(failing_callback)

        ## Act
        wrapped(MagicMock())


class TestOnOpen:
    @capture_logs()
    def test_on_open_emits_transport_opened_event(self, transport, mock_event_callback, mock_get_cookie):
        """WsTransport._on_open emits TransportOpened event when cookie is valid."""
        ## Arrange
        transport._cookie = 'test_cookie'
        mock_get_cookie.return_value = 'test_cookie'
        mock_wsa = MagicMock()

        ## Act
        transport._on_open(mock_wsa)

        ## Assert
        mock_event_callback.assert_called_once()
        event = mock_event_callback.call_args[0][0]
        assert isinstance(event, TransportOpened)

    @capture_logs(logger_level='WARNING', expected_errors=['Cookie changed, current: new_cookie, previous: old_cookie'], partial_match=True)
    def test_on_open_closes_connection_when_cookie_invalid(self, transport, mock_get_cookie):
        """WsTransport._on_open closes connection when cookie check fails."""
        ## Arrange
        transport._cookie = 'old_cookie'
        mock_get_cookie.return_value = 'new_cookie'
        transport._wsa = MagicMock()

        ## Act
        transport._on_open(transport._wsa)

        ## Assert
        transport._wsa.close.assert_called_once_with(status=STATUS_UNEXPECTED_CONDITION, timeout=TEST_CONNECTION_TIMEOUT)

    @capture_logs()
    def test_on_open_does_nothing_when_degraded(self, transport, mock_event_callback):
        """WsTransport._on_open does nothing when transport is degraded."""
        ## Arrange
        transport._degraded = True
        mock_wsa = MagicMock()

        ## Act
        transport._on_open(mock_wsa)

        ## Assert
        mock_event_callback.assert_not_called()


class TestOnMessage:
    @capture_logs()
    def test_on_message_emits_transport_message_event(self, transport, mock_event_callback):
        """WsTransport._on_message emits TransportMessage event."""
        ## Arrange
        mock_wsa = MagicMock()

        ## Act
        transport._on_message(mock_wsa, '{"test": "data"}')

        ## Assert
        mock_event_callback.assert_called_once()
        event = mock_event_callback.call_args[0][0]
        assert isinstance(event, TransportMessage)
        assert event.message == '{"test": "data"}'

    @capture_logs()
    def test_on_message_does_nothing_when_degraded(self, transport, mock_event_callback):
        """WsTransport._on_message does nothing when transport is degraded."""
        ## Arrange
        transport._degraded = True
        mock_wsa = MagicMock()

        ## Act
        transport._on_message(mock_wsa, '{"test": "data"}')

        ## Assert
        mock_event_callback.assert_not_called()


class TestOnClose:
    @capture_logs()
    def test_on_close_emits_transport_closed_event(self, transport, mock_event_callback):
        """WsTransport._on_close emits TransportClosed event."""
        ## Arrange
        mock_wsa = MagicMock()

        ## Act
        transport._on_close(mock_wsa, 1000, 'normal closure')

        ## Assert
        mock_event_callback.assert_called_once()
        event = mock_event_callback.call_args[0][0]
        assert isinstance(event, TransportClosed)
        assert event.close_status_code == 1000
        assert event.close_msg == 'normal closure'

    @capture_logs()
    def test_on_close_does_nothing_when_degraded(self, transport, mock_event_callback):
        """WsTransport._on_close does nothing when transport is degraded."""
        ## Arrange
        transport._degraded = True
        mock_wsa = MagicMock()

        ## Act
        transport._on_close(mock_wsa, 1000, 'normal closure')

        ## Assert
        mock_event_callback.assert_not_called()


class TestOnError:
    @capture_logs()
    def test_on_error_emits_transport_error_event(self, transport, mock_event_callback):
        """WsTransport._on_error emits TransportError event."""
        ## Arrange
        mock_wsa = MagicMock()
        error = RuntimeError('connection error')

        ## Act
        transport._on_error(mock_wsa, error)

        ## Assert
        mock_event_callback.assert_called_once()
        event = mock_event_callback.call_args[0][0]
        assert isinstance(event, TransportError)
        assert event.exception is error

    @capture_logs()
    def test_on_error_does_nothing_when_degraded(self, transport, mock_event_callback):
        """WsTransport._on_error does nothing when transport is degraded."""
        ## Arrange
        transport._degraded = True
        mock_wsa = MagicMock()
        error = RuntimeError('connection error')

        ## Act
        transport._on_error(mock_wsa, error)

        ## Assert
        mock_event_callback.assert_not_called()


class TestOnReconnect:
    @capture_logs()
    def test_on_reconnect_emits_transport_reconnect_event(self, transport, mock_event_callback, mock_get_cookie):
        """WsTransport._on_reconnect emits TransportReconnect event when cookie is valid."""
        ## Arrange
        transport._cookie = 'test_cookie'
        mock_get_cookie.return_value = 'test_cookie'
        mock_wsa = MagicMock()

        ## Act
        transport._on_reconnect(mock_wsa)

        ## Assert
        mock_event_callback.assert_called_once()
        event = mock_event_callback.call_args[0][0]
        assert isinstance(event, TransportReconnect)

    @capture_logs(logger_level='WARNING', expected_errors=['Cookie changed, current: new_cookie, previous: old_cookie'], partial_match=True)
    def test_on_reconnect_closes_connection_when_cookie_invalid(self, transport, mock_get_cookie):
        """WsTransport._on_reconnect closes connection when cookie check fails."""
        ## Arrange
        transport._cookie = 'old_cookie'
        mock_get_cookie.return_value = 'new_cookie'
        transport._wsa = MagicMock()

        ## Act
        transport._on_reconnect(transport._wsa)

        ## Assert
        transport._wsa.close.assert_called_once_with(status=STATUS_UNEXPECTED_CONDITION, timeout=TEST_CONNECTION_TIMEOUT)

    @capture_logs()
    def test_on_reconnect_does_nothing_when_degraded(self, transport, mock_event_callback):
        """WsTransport._on_reconnect does nothing when transport is degraded."""
        ## Arrange
        transport._degraded = True
        mock_wsa = MagicMock()

        ## Act
        transport._on_reconnect(mock_wsa)

        ## Assert
        mock_event_callback.assert_not_called()


class TestNewWsa:
    @capture_logs()
    def test_new_wsa_returns_none_when_cookie_fetch_fails(self, transport, mock_get_cookie):
        """WsTransport._new_wsa returns None when fetch_cookie returns UNDEFINED."""
        ## Arrange
        mock_get_cookie.side_effect = TimeoutError('timeout')

        ## Act
        result = transport._new_wsa()

        ## Assert
        assert result is None

    @capture_logs(logger_level='ERROR', expected_errors=['Failed to retrieve header'], partial_match=True)
    def test_new_wsa_returns_none_when_header_fetch_fails(self, transport, mock_get_header):
        """WsTransport._new_wsa returns None when get_header raises exception."""
        ## Arrange
        mock_get_header.side_effect = RuntimeError('header error')

        ## Act
        result = transport._new_wsa()

        ## Assert
        assert result is None

    @capture_logs()
    def test_new_wsa_returns_none_when_transport_stopped(self, transport):
        """WsTransport._new_wsa returns None when transport is stopped."""
        ## Arrange
        transport._running = False

        ## Act
        result = transport._new_wsa()

        ## Assert
        assert result is None

    @capture_logs(logger_level='DEBUG', expected_errors=['Created new WebSocketApp instance'], partial_match=True)
    def test_new_wsa_creates_websocket_app(self, transport, mock_get_cookie, mock_get_header):
        """WsTransport._new_wsa creates WebSocketApp with correct configuration."""
        ## Arrange
        transport._running = True
        mock_get_cookie.return_value = 'test_cookie'
        mock_get_header.return_value = {'User-Agent': 'test'}

        ## Act
        with patch('ibind.ws_v2.ws_transport.WebSocketApp') as mock_wsa_class:
            result = transport._new_wsa()

        ## Assert
        mock_wsa_class.assert_called_once()
        call_kwargs = mock_wsa_class.call_args[1]
        assert call_kwargs['url'] == 'wss://test.example.com'
        assert call_kwargs['cookie'] == 'test_cookie'
        assert call_kwargs['header'] == {'User-Agent': 'test'}
        assert transport._cookie == 'test_cookie'
        assert transport._header == {'User-Agent': 'test'}


class TestConnect:
    @capture_logs(logger_level='DEBUG', expected_errors=['Transport thread started'], partial_match=True)
    def test_connect_sets_running_and_thread_name(self, transport):
        """WsTransport.connect sets running flag and thread name."""
        ## Arrange
        transport._running = False

        ## Act
        with patch('ibind.ws_v2.ws_transport.tname', return_value='test_thread'):
            with patch.object(transport, '_new_wsa', return_value=None):
                with patch('time.sleep', side_effect=[None, KeyboardInterrupt]):
                    try:
                        transport.connect()
                    except KeyboardInterrupt:
                        pass

        ## Assert
        assert transport._tname == 'test_thread'

    @capture_logs(logger_level='DEBUG', expected_errors=['WebSocketApp stopped gracefully'], partial_match=True)
    def test_connect_runs_wsa_run_forever(self, transport):
        """WsTransport.connect calls WebSocketApp.run_forever with correct parameters."""
        ## Arrange
        mock_wsa = MagicMock()
        transport._running = True

        ## Act
        with patch.object(transport, '_new_wsa', return_value=mock_wsa):
            with patch.object(mock_wsa, 'run_forever', side_effect=lambda **kwargs: setattr(transport, '_running', False)) as mock_run_forever:
                transport.connect()

        ## Assert
        mock_run_forever.assert_called_once()
        call_kwargs = mock_run_forever.call_args[1]
        assert call_kwargs['ping_interval'] == TEST_PING_INTERVAL
        assert call_kwargs['reconnect'] == TEST_RECONNECT_TIMEOUT

    @capture_logs(logger_level='ERROR', expected_errors=['URL is invalid'], partial_match=True)
    def test_connect_logs_invalid_url_error(self, transport):
        """WsTransport.connect logs error when URL is invalid."""
        ## Arrange
        mock_wsa = MagicMock()
        mock_wsa.run_forever.side_effect = Exception('url is invalid')
        transport._running = True

        ## Act
        with patch.object(transport, '_new_wsa', return_value=mock_wsa):
            transport._cycle()

    @capture_logs(logger_level='ERROR', expected_errors=['Unexpected error while running WebSocketApp'], partial_match=True)
    def test_connect_logs_unexpected_errors(self, transport):
        """WsTransport.connect logs unexpected errors during run_forever."""
        ## Arrange
        mock_wsa = MagicMock()
        mock_wsa.run_forever.side_effect = RuntimeError('unexpected error')
        transport._running = True

        ## Act
        with patch.object(transport, '_new_wsa', return_value=mock_wsa):
            transport._cycle()

    @capture_logs()
    def test_connect_sets_wsa_to_none_in_finally(self, transport):
        """WsTransport.connect sets _wsa to None in finally block."""
        ## Arrange
        mock_wsa = MagicMock()
        transport._running = True

        ## Act
        with patch.object(transport, '_new_wsa', return_value=mock_wsa):
            with patch.object(mock_wsa, 'run_forever', side_effect=lambda **kwargs: setattr(transport, '_running', False)):
                transport._cycle()

        ## Assert
        assert transport._wsa is None
