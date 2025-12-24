from threading import Thread
from typing import Optional
from unittest.mock import MagicMock

import pytest

from ibind.base.ws_client import WsClient
from ibind.support.py_utils import tname
from integration.base.websocketapp_mock import create_wsa_mock, init_wsa_mock
from test_utils import capture_logs

_URL = 'wss://localhost:5000/v1/api/ws'
_MAX_RECONNECT_ATTEMPTS = 4
_MAX_PING_INTERVAL = 38
_ERROR_MESSAGE = 'TEST_ERROR'


# --------------------------------------------------------------------------------------
# Log expectations
# --------------------------------------------------------------------------------------


def _logs_start_success_beginning():
    return [
        'WsClient: Starting',
        'WsClient: Trying to connect',
    ]


def _logs_start_success_end():
    return [
        'WsClient: Creating new WebSocketApp',
        f'WsClient: Thread started ({tname()})',
        'WsClient: Connection open',
        f'WsClient: Thread stopped ({tname()})',
    ]


def _logs_failed_attempt(max_reconnect_attempts: int, attempt: Optional[int]):
    logs = [
        'WsClient: Creating new WebSocketApp',
        'WsClient: New WebSocketApp connection timeout',
        'WsClient: on_close',
        'WsClient: on_close event while disconnected',
    ]
    if attempt is not None:
        logs.append(f'WsClient: Connect reattempt {attempt}/{max_reconnect_attempts}')
    return logs


def _logs_shutdown_success():
    return [
        'WsClient: Shutting down',
        'WsClient: on_close',
        'WsClient: Connection closed',
        'WsClient: Gracefully stopped',
    ]


def _logs_exception_starting(error_message: str, thread_mock: MagicMock):
    return [
        'WsClient: Creating new WebSocketApp',
        f'WsClient: Thread started ({tname()})',
        f'WsClient: Unexpected error while running WebSocketApp: {error_message}',
        'WsClient: Hard reset, restart=False, self._wsa is None=False',
        'WsClient: Forced restart',
        'WsClient: Reconnecting',
        f'WsClient: Thread already running: {thread_mock.name}-{thread_mock.ident}',
        f'WsClient: Thread stopped ({tname()})',
        'WsClient: Reconnecting',
        'WsClient: Trying to connect',
    ]


def _logs_check_health_error(max_ping_interval: int, time_ago: str):
    return [
        f'WsClient: Last WebSocket ping happened  {time_ago} seconds ago, exceeding the max ping interval of {max_ping_interval}. Restarting.',
        'WsClient: Hard reset, restart=True, self._wsa is None=False',
        'WsClient: Hard reset is closing the WebSocketApp',
    ]


def _logs_hard_restart_error(wsa_mock: MagicMock):
    return [
        'WsClient: Hard reset close timeout',
        f'WsClient: Abandoning current WebSocketApp that cannot be closed: {wsa_mock}',
        'WsClient: Forced restart',
        'WsClient: Reconnecting',
        'WsClient: Trying to connect',
    ]


def _verify_started(ws_client: WsClient, wsa_mock: MagicMock):
    wsa_mock.run_forever.assert_called_with(
        sslopt=ws_client._sslopt,
        ping_interval=ws_client._ping_interval,
        ping_timeout=0.95 * ws_client._ping_interval,
    )
    wsa_mock._on_open.assert_called_with(wsa_mock)


def _verify_failed_starting(wsa_mock: MagicMock):
    wsa_mock.run_forever.assert_not_called()
    wsa_mock._on_open.assert_not_called()
    wsa_mock.close.assert_called()


# --------------------------------------------------------------------------------------
# Test setup
# --------------------------------------------------------------------------------------


@pytest.fixture
def ws_client():
    return WsClient(
        subscription_processor=None,
        url=_URL,
        cacert=False,
        timeout=0.01,
        max_connection_attempts=_MAX_RECONNECT_ATTEMPTS,
        max_ping_interval=_MAX_PING_INTERVAL,
    )


@pytest.fixture
def wsa_mock():
    return create_wsa_mock()


@pytest.fixture
def thread_mock(ws_client, wsa_mock):
    thread_mock = MagicMock(spec=Thread)
    thread_mock.start.side_effect = lambda: ws_client._run_websocket(wsa_mock)
    return thread_mock


@pytest.fixture
def wsa_ctor_mock(mocker, wsa_mock):
    return mocker.patch(
        'ibind.base.ws_client.WebSocketApp',
        side_effect=lambda *args, **kwargs: init_wsa_mock(wsa_mock, *args, **kwargs),
    )


@pytest.fixture
def thread_ctor_mock(mocker, thread_mock):
    return mocker.patch('ibind.base.ws_client.Thread', return_value=thread_mock)


@pytest.fixture
def patched_constructors(wsa_ctor_mock, thread_ctor_mock):
    return None


# --------------------------------------------------------------------------------------
# Start / reconnect behavior
# --------------------------------------------------------------------------------------

@capture_logs(logger_level='DEBUG')
def test_start_success(ws_client, wsa_mock, thread_ctor_mock, patched_constructors, **kwargs):
    """Starts successfully and logs the expected connection sequence."""
    ## Arrange
    cm = kwargs['_cm_ibind']

    ## Act
    success = ws_client.start()

    ## Assert
    assert success is True
    thread_ctor_mock.assert_called_with(target=ws_client._run_websocket, args=(wsa_mock,), name='ws_client_thread')
    _verify_started(ws_client, wsa_mock)
    assert _logs_start_success_beginning() + _logs_start_success_end() == [r.msg for r in cm.records]


@capture_logs(logger_level='DEBUG', expected_errors=['WsClient: New WebSocketApp connection timeout'])
def test_start_success_on_second_attempt(ws_client, wsa_mock, thread_mock, thread_ctor_mock, patched_constructors, **kwargs):
    """Reconnects and succeeds on the second attempt after a timeout on the first."""
    ## Arrange
    cm = kwargs['_cm_ibind']
    counter = [0]

    def delayed_start():
        if counter[0] >= 1:
            ws_client._run_websocket(wsa_mock)
        counter[0] += 1

    thread_mock.start.side_effect = delayed_start

    ## Act
    success = ws_client.start()

    ## Assert
    assert success is True
    thread_ctor_mock.assert_called_with(target=ws_client._run_websocket, args=(wsa_mock,), name='ws_client_thread')
    _verify_started(ws_client, wsa_mock)
    assert (
        _logs_start_success_beginning()
        + _logs_failed_attempt(_MAX_RECONNECT_ATTEMPTS, 2)
        + _logs_start_success_end()
        == [r.msg for r in cm.records]
    )
    thread_mock.join.assert_called_with(60)


@capture_logs(
    logger_level='DEBUG',
    expected_errors=[
        'WsClient: New WebSocketApp connection timeout',
        f'WsClient: Connection failed after {_MAX_RECONNECT_ATTEMPTS} attempts',
    ],
)
def test_start_reattempt_failure(ws_client, wsa_mock, thread_mock, thread_ctor_mock, patched_constructors, **kwargs):
    """Fails after exhausting reconnect attempts and closes the WebSocketApp."""
    ## Arrange
    cm = kwargs['_cm_ibind']
    thread_mock.start.side_effect = lambda: None

    ## Act
    success = ws_client.start()

    ## Assert
    assert success is False
    thread_ctor_mock.assert_called_with(target=ws_client._run_websocket, args=(wsa_mock,), name='ws_client_thread')

    _verify_failed_starting(wsa_mock)

    expected_logs = _logs_start_success_beginning()
    for i in range(_MAX_RECONNECT_ATTEMPTS):
        if i < _MAX_RECONNECT_ATTEMPTS - 1:
            expected_logs += _logs_failed_attempt(_MAX_RECONNECT_ATTEMPTS, i + 2)
        else:
            expected_logs += _logs_failed_attempt(_MAX_RECONNECT_ATTEMPTS, None)
    expected_logs.append(f"WsClient: Connection failed after {_MAX_RECONNECT_ATTEMPTS} attempts")

    assert expected_logs == [r.msg for r in cm.records]
    assert wsa_mock.keep_running is False


# --------------------------------------------------------------------------------------
# Error handling
# --------------------------------------------------------------------------------------


@capture_logs(
    logger_level='DEBUG',
    expected_errors=[
        f"WsClient: Unexpected error while running WebSocketApp: {_ERROR_MESSAGE}",
        'WsClient: Thread already running:',
    ],
    partial_match=True,
)
def test_open_exception(ws_client, wsa_mock, thread_mock, thread_ctor_mock, patched_constructors, **kwargs):
    """Hard-resets and reconnects when WebSocketApp.run_forever raises an exception."""
    ## Arrange
    cm = kwargs['_cm_ibind']
    old_run_forever = wsa_mock.run_forever.side_effect

    def run_forever_exception(
        wsa_mock: MagicMock,
        sslopt: dict = None,
        ping_interval: float = 0,
        ping_timeout: Optional[float] = None,
    ):
        wsa_mock.run_forever.side_effect = old_run_forever
        raise RuntimeError(_ERROR_MESSAGE)

    wsa_mock.run_forever.side_effect = lambda *args, **kwargs: run_forever_exception(wsa_mock, *args, **kwargs)

    ## Act
    ws_client.start()
    ws_client.shutdown()

    ## Assert
    thread_ctor_mock.assert_called_with(target=ws_client._run_websocket, args=(wsa_mock,), name='ws_client_thread')
    assert (
        _logs_start_success_beginning()
        + _logs_exception_starting(_ERROR_MESSAGE, thread_mock)
        + _logs_start_success_end()
        + _logs_shutdown_success()
        == [r.msg for r in cm.records]
    )


# --------------------------------------------------------------------------------------
# Shutdown
# --------------------------------------------------------------------------------------


@capture_logs(logger_level='DEBUG')
def test_open_and_close(ws_client, wsa_mock, thread_ctor_mock, patched_constructors, **kwargs):
    """Shuts down cleanly after a successful start."""
    ## Arrange
    cm = kwargs['_cm_ibind']

    ## Act
    success = ws_client.start()
    ws_client.shutdown()

    ## Assert
    assert success is True
    thread_ctor_mock.assert_called_with(target=ws_client._run_websocket, args=(wsa_mock,), name='ws_client_thread')
    assert _logs_start_success_beginning() + _logs_start_success_end() + _logs_shutdown_success() == [r.msg for r in cm.records]


# --------------------------------------------------------------------------------------
# Sending payloads
# --------------------------------------------------------------------------------------


@capture_logs(logger_level='DEBUG')
def test_send(ws_client, wsa_mock, thread_ctor_mock, patched_constructors, **kwargs):
    """Delivers outbound payloads to the on_message callback (mocked echo)."""
    ## Arrange
    cm = kwargs['_cm_ibind']

    ws_client._on_message = MagicMock()

    ## Act
    success = ws_client.start()
    ws_client.send('test')
    ws_client.shutdown()

    ## Assert
    assert success is True
    thread_ctor_mock.assert_called_with(target=ws_client._run_websocket, args=(wsa_mock,), name='ws_client_thread')
    ws_client._on_message.assert_called_once_with(wsa_mock, 'test')
    assert _logs_start_success_beginning() + _logs_start_success_end() + _logs_shutdown_success() == [r.msg for r in cm.records]


@capture_logs(logger_level='DEBUG', expected_errors=['WsClient: Must be started before sending payloads'])
def test_send_without_start(ws_client, **kwargs):
    """Logs an error when trying to send before calling start()."""
    ## Arrange
    cm = kwargs['_cm_ibind']

    ws_client._on_message = MagicMock()

    ## Act
    ws_client.send('test')
    ws_client.shutdown()

    ## Assert
    assert ['WsClient: Must be started before sending payloads'] == [r.msg for r in cm.records]


# --------------------------------------------------------------------------------------
# Health checks
# --------------------------------------------------------------------------------------


@capture_logs(
    logger_level='DEBUG',
    expected_errors=[
        'WsClient: Last WebSocket ping happened',
        'WsClient: Hard reset close timeout',
        'WsClient: Abandoning current WebSocketApp that cannot be closed:',
    ],
    partial_match=True,
)
def test_check_ping(ws_client, wsa_mock, patched_constructors, mocker, **kwargs):
    """Triggers a hard reset when the last ping exceeds max_ping_interval."""
    ## Arrange
    cm = kwargs['_cm_ibind']
    start_time = [100]

    def fake_time():
        start_time[0] += 100
        return start_time[0]

    ws_client._on_message = MagicMock()

    ## Act
    ws_client.start()
    ws_client.check_ping()

    # Simulate that closing the WebSocketApp doesn't work since we have connectivity issues
    wsa_mock._on_close.side_effect = lambda x, y, z: None

    time_mock = mocker.patch('ibind.base.ws_client.time')
    time_mock.time.side_effect = fake_time

    wsa_mock.last_ping_tm = _MAX_PING_INTERVAL
    ws_client.check_ping()
    assert ws_client.ready() is True
    ws_client.shutdown()

    ## Assert
    assert (
        _logs_start_success_beginning()
        + _logs_start_success_end()
        + _logs_check_health_error(_MAX_PING_INTERVAL, '162.00')
        + _logs_hard_restart_error(wsa_mock)
        + _logs_start_success_end()
        + _logs_shutdown_success()
        == [r.msg for r in cm.records]
    )