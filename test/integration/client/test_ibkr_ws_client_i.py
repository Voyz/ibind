import json
from threading import Thread
from typing import Optional
from unittest.mock import MagicMock, call

import pytest
import requests

from ibind import Result
from ibind.client.ibkr_client import IbkrClient
from ibind.client.ibkr_ws_client import IbkrWsClient, IbkrSubscriptionProcessor, IbkrWsKey
from integration.base.websocketapp_mock import create_wsa_mock, init_wsa_mock
from test_utils_new import capture_logs

_URL_WS = 'wss://localhost:5000/v1/api/ws'
_URL_REST = 'https://localhost:5000'
_ACCOUNT_ID = 'TEST_ACCOUNT_ID'
_TIMEOUT_REST = 8
_MAX_RETRIES_REST = 4
_MAX_RECONNECT_ATTEMPTS = 4
_MAX_PING_INTERVAL = 38
_SUBSCRIPTION_RETRIES = 3
_CONID = 265598
_UPDATE_TIME = 5678765456


# --------------------------------------------------------------------------------------
# Test setup
# --------------------------------------------------------------------------------------


@pytest.fixture
def preprocess_ws_client():
    return IbkrWsClient(
        url=_URL_WS,
        ibkr_client=None,
        account_id=None,
        subscription_processor_class=lambda: None,
    )


@pytest.fixture
def client_mock():
    client = MagicMock(
        spec=IbkrClient(
            url=_URL_REST,
            account_id=_ACCOUNT_ID,
            timeout=_TIMEOUT_REST,
            max_retries=_MAX_RETRIES_REST,
        )
    )
    client.tickle.return_value.data = {'session': 'TEST_COOKIE'}
    return client


@pytest.fixture
def ws_client(client_mock):
    return IbkrWsClient(
        url=_URL_WS,
        ibkr_client=client_mock,
        account_id=_ACCOUNT_ID,
        subscription_processor_class=IbkrSubscriptionProcessor,
        subscription_retries=_SUBSCRIPTION_RETRIES,
        subscription_timeout=0.01,
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
def ws_app_factory(wsa_mock):
    # Use a mutable side-effect so individual tests can temporarily override WebSocketApp behavior.
    return {
        'fn': lambda *args, **kwargs: init_wsa_mock(wsa_mock, *args, **kwargs),
    }


@pytest.fixture
def patched_constructors(mocker, thread_mock, ws_app_factory):
    mocker.patch('ibind.base.ws_client.WebSocketApp', side_effect=lambda *args, **kwargs: ws_app_factory['fn'](*args, **kwargs))
    mocker.patch('ibind.base.ws_client.Thread', return_value=thread_mock)
    return None



def _send_payload(ws_client, payload: dict):
    success = ws_client.start()
    ws_client.send(json.dumps(payload))
    ws_client.shutdown()
    return success


def _subscribe(ws_client, wsa_mock, request: dict, response: Optional[dict]):
    def override_on_message(wsa_mock: MagicMock, message: str):
        if response is None:
            return
        raw_message = json.dumps(response)
        wsa_mock.__on_message__(wsa_mock, raw_message)

    ws_client.start()
    wsa_mock._on_message.side_effect = override_on_message

    rv = ws_client.subscribe(
        **{
            'channel': request.get('channel'),
            'data': request.get('data'),
            'needs_confirmation': request.get('needs_confirmation'),
        }
    )
    ws_client.unsubscribe(
        **{
            'channel': request.get('channel'),
            'data': request.get('data'),
            'needs_confirmation': request.get('confirms_unsubscription'),
        }
    )
    ws_client.shutdown()
    return rv



def _logs_subscriptions(full_channel, data=None, needs_confirmation_sub: bool = False, needs_confirmation_unsub: bool = True):
    return [
        f'IbkrWsClient: Subscribed: s{full_channel}{"" if data is None else f"+{json.dumps(data)}"}{"" if not needs_confirmation_sub else " without confirmation."}',
        f'IbkrWsClient: Unsubscribed: u{full_channel}+{json.dumps(data if data is not None else {})}{"" if not needs_confirmation_unsub else " without confirmation."}',
    ]


# --------------------------------------------------------------------------------------
# Message preprocessing
# --------------------------------------------------------------------------------------


def test_preprocess_with_well_formed_message(preprocess_ws_client):
    """Preprocesses a well-formed raw message into (message, topic, data, subscribed, channel)."""
    ## Arrange
    raw_message = json.dumps({'topic': 'actABC', 'args': {'key': 'value'}})
    expected_result = (
        {'topic': 'actABC', 'args': {'key': 'value'}},  # message
        'actABC',  # topic
        {'key': 'value'},  # data
        'a',  # subscribed
        'ctABC',  # channel
    )

    ## Act
    rv = preprocess_ws_client._preprocess_raw_message(raw_message)

    ## Assert
    assert rv == expected_result


def test_preprocess_with_unsubscribed_message(preprocess_ws_client):
    """Returns empty preprocess result for unsubscribed messages."""
    ## Arrange
    raw_message = json.dumps({'message': 'Unsubscribed'})

    ## Act
    rv = preprocess_ws_client._preprocess_raw_message(raw_message)

    ## Assert
    assert rv == ({'message': 'Unsubscribed'}, None, None, None, None)


# --------------------------------------------------------------------------------------
# On-message handling
# --------------------------------------------------------------------------------------


@capture_logs(logger_level='DEBUG')
def test_on_message_system_heartbeat(ws_client, patched_constructors):
    """Updates last heartbeat on system heartbeat message."""
    ## Arrange
    hb = 12345678

    ## Act
    _send_payload(ws_client, {'topic': 'system', 'hb': hb})

    ## Assert
    assert ws_client._last_heartbeat == hb

@capture_logs(logger_level='DEBUG', expected_errors = ["IbkrWsClient: Account ID mismatch: expected=TEST_ACCOUNT_ID, received=['OTHER_ACCOUNT_ID']"])
def test_on_message_act_account_mismatch(ws_client, patched_constructors):
    """Logs a warning when account list in act message mismatches expected account."""
    ## Act
    _send_payload(ws_client, {'topic': 'act', 'args': {'accounts': ['OTHER_ACCOUNT_ID']}})


@capture_logs(logger_level='DEBUG')
def test_on_message_blt(ws_client, patched_constructors, mocker):
    """Dispatches bulletin messages to _handle_bulletin."""
    ## Arrange
    bulletin_message = {'topic': 'blt', 'args': {'bulletin_key': 'some_info'}}
    mock_handle_bulletin = mocker.patch.object(ws_client, '_handle_bulletin', MagicMock())

    ## Act
    _send_payload(ws_client, bulletin_message)

    ## Assert
    mock_handle_bulletin.assert_called_once_with(bulletin_message)

@capture_logs(logger_level='DEBUG', expected_errors=[
    "IbkrWsClient: Status unauthenticated: {'authenticated': False}",
    'IbkrWsClient: Not authenticated, closing WebSocketApp',
])
def test_on_message_sts_unauthenticated(ws_client, client_mock, patched_constructors, mocker):
    """On unauthenticated status, refetches session and closes websocket."""
    ## Arrange
    message_data = {'topic': 'sts', 'args': {'authenticated': False}}
    session_id = 6545676

    response_mock = MagicMock(spec=requests.Response)
    response_mock.status_code = 200
    response_mock.json.return_value = {'session': session_id, 'data_to_be_ignored': '1234'}

    client_mock.tickle.return_value = Result(data=response_mock.json.return_value)

    requests_mock = mocker.patch('ibind.base.rest_client.requests')
    requests_mock.request.return_value = response_mock

    ## Act
    _send_payload(ws_client, message_data)

    ## Assert
    assert ws_client._authenticated is False

@capture_logs(logger_level='DEBUG')
def test_on_message_sts_authenticated(ws_client, patched_constructors):
    """Accepts authenticated status without logging warnings."""
    ## Act
    _send_payload(ws_client, {'topic': 'sts', 'args': {'authenticated': True}})


@capture_logs(logger_level='DEBUG', expected_errors = [f'IbkrWsClient: Error message:'], partial_match=True)
def test_on_message_error(ws_client, patched_constructors):
    """Logs error-topic messages as warnings."""
    ## Act
    _send_payload(ws_client, {'topic': 'error', 'args': {'error_key': 'error_details'}})



@capture_logs(logger_level='DEBUG', expected_errors=['unrecognised. Message:'], partial_match=True)
def test_on_message_no_topic_handler(ws_client, patched_constructors):
    """Logs a warning when no handler exists for a topic."""
    ## Arrange
    message_data = {'topic': 'unrecognized_topic', 'args': {'some_key': 'some_value'}}

    ## Act
    _send_payload(ws_client, message_data)


@capture_logs(logger_level='DEBUG', expected_errors = [
    'message that is missing a subscription. Message:'
], partial_match=True)
def test_on_message_handled_without_subscription(ws_client, patched_constructors, mocker):
    """Logs a warning if a subscribed message arrives without a known subscription."""
    ## Arrange
    mocker.patch.object(ws_client, '_handle_subscribed_message', return_value=True)

    ## Act
    _send_payload(ws_client, {'topic': 'some_topic', 'args': {'channel': 'XYZ', 'data': 'info'}})



# --------------------------------------------------------------------------------------
# Subscription + channel-specific handling
# --------------------------------------------------------------------------------------


@capture_logs(logger_level='DEBUG')
def test_on_message_market_data_channel_handling(ws_client, wsa_mock, patched_constructors, mocker, **kwargs):
    """Routes market data updates into the MARKET_DATA queue."""
    ## Arrange
    cm = kwargs['_cm_ibind']
    queue = ws_client.new_queue_accessor(IbkrWsKey.MARKET_DATA)
    full_channel = f'{queue.key.channel}+{_CONID}'
    request = {
        'channel': f'{full_channel}',
        'data': {'fields': ['55', '71', '84', '86', '88', '85', '87', '7295', '7296', '70']},
    }
    response = {
        'topic': f's{full_channel}',
        'conid': _CONID,
        '_updated': _UPDATE_TIME,
        55: 'AAPL',
        70: '195.34',
        71: '193.67',
        87: '24.2M',
        7295: '194.10',
        84: '195.25',
        86: '195.26',
        88: '3,500',
        85: '500',
        6508: '&serviceID1=122&serviceID2=123&serviceID3=203&serviceID4=775&serviceID5=204&serviceID6=206&serviceID7=108&serviceID8=109',
    }

    assert queue.empty() is True

    mocker.patch.object(ws_client, 'has_subscription', return_value=True)

    ## Act
    success = _subscribe(ws_client, wsa_mock, request, response)

    ## Assert
    assert success is True
    cm.partial_log(_logs_subscriptions(full_channel, request['data']))
    assert (
        {
            _CONID: {
                '_updated': _UPDATE_TIME,
                'conid': _CONID,
                'topic': f'smd+{_CONID}',
                'ask_price': '195.26',
                'ask_size': '500',
                'bid_price': '195.25',
                'bid_size': '3,500',
                'high': '195.34',
                'low': '193.67',
                'open': '194.10',
                'service_params': '&serviceID1=122&serviceID2=123&serviceID3=203&serviceID4=775&serviceID5=204&serviceID6=206&serviceID7=108&serviceID8=109',
                'symbol': 'AAPL',
                'volume': '24.2M',
            }
        }
        == queue.get()
    )


@capture_logs(logger_level='DEBUG')
def test_on_message_market_history_channel_handling(ws_client, wsa_mock, patched_constructors, mocker, **kwargs):
    """Routes market history updates into the MARKET_HISTORY queue and tracks server IDs."""
    ## Arrange
    cm = kwargs['_cm_ibind']
    queue = ws_client.new_queue_accessor(IbkrWsKey.MARKET_HISTORY)
    server_id = 87567
    full_channel = f'{queue.key.channel}+{_CONID}'
    request = {
        'channel': f'{full_channel}',
        'data': {'period': '1min', 'bar': '1min', 'outsideRTH': True, 'source': 'trades', 'format': '%o/%c/%h/%l'},
        'confirms_unsubscription': False,
    }
    response = {
        'topic': f's{full_channel}',
        'serverId': server_id,
        '_updated': _UPDATE_TIME,
        'conid': _CONID,
        'foo': 'bar',
    }

    assert queue.empty() is True

    mocker.patch.object(ws_client, 'has_subscription', return_value=True)

    ## Act
    success = _subscribe(ws_client, wsa_mock, request, response)

    ## Assert
    assert success is True
    cm.partial_log(_logs_subscriptions(full_channel, request['data']))
    assert response == queue.get()
    assert server_id in ws_client.server_ids(IbkrWsKey.MARKET_HISTORY)


@capture_logs(logger_level='DEBUG')
def test_on_message_trade_channel_handling(ws_client, wsa_mock, patched_constructors, mocker, **kwargs):
    """Routes trade updates into the TRADES queue."""
    ## Arrange
    cm = kwargs['_cm_ibind']
    queue = ws_client.new_queue_accessor(IbkrWsKey.TRADES)
    full_channel = f'{queue.key.channel}+{_CONID}'
    request = {'channel': f'{full_channel}'}
    response = {
        'topic': f's{full_channel}',
        '_updated': _UPDATE_TIME,
        'conid': _CONID,
        'args': [{'foo': 'bar'}],
    }

    assert queue.empty() is True

    mocker.patch.object(ws_client, 'has_subscription', return_value=True)

    ## Act
    success = _subscribe(ws_client, wsa_mock, request, response)

    ## Assert
    assert success is True
    cm.partial_log(_logs_subscriptions(full_channel))
    assert response == queue.get()


@capture_logs(logger_level='DEBUG')
def test_on_message_orders_channel_handling(ws_client, wsa_mock, patched_constructors, mocker, **kwargs):
    """Routes order updates into the ORDERS queue."""
    ## Arrange
    cm = kwargs['_cm_ibind']
    queue = ws_client.new_queue_accessor(IbkrWsKey.ORDERS)
    full_channel = f'{queue.key.channel}+{_CONID}'
    request = {'channel': f'{full_channel}'}
    response = {
        'topic': f's{full_channel}',
        '_updated': _UPDATE_TIME,
        'conid': _CONID,
        'args': [{'foo': 'bar'}],
    }

    assert queue.empty() is True

    mocker.patch.object(ws_client, 'has_subscription', return_value=True)

    ## Act
    success = _subscribe(ws_client, wsa_mock, request, response)

    ## Assert
    assert success is True
    cm.partial_log(_logs_subscriptions(full_channel, None, True, True))
    assert response == queue.get()


@capture_logs(logger_level='DEBUG')
def test_subscription_without_confirmation(ws_client, wsa_mock, patched_constructors, mocker, **kwargs):
    """Subscribes/unsubscribes without confirmation when requested."""
    ## Arrange
    cm = kwargs['_cm_ibind']
    channel = 'fake'
    full_channel = f'{channel}+{_CONID}'
    request = {
        'channel': f'{full_channel}',
        'needs_confirmation': False,
        'confirms_unsubscription': False,
    }
    response = None

    mocker.patch.object(ws_client, 'has_subscription', return_value=True)

    ## Act
    success = _subscribe(ws_client, wsa_mock, request, response)

    ## Assert
    assert success is True
    cm.partial_log([
        f'IbkrWsClient: Subscribed: s{full_channel} without confirmation.',
        f'IbkrWsClient: Unsubscribed: u{full_channel}+{{}} without confirmation.',
    ])



# --------------------------------------------------------------------------------------
# Health checks
# --------------------------------------------------------------------------------------


@capture_logs(logger_level='DEBUG', expected_errors=[
    f'IbkrWsClient: Last IBKR heartbeat happened 162.00 seconds ago, exceeding the max ping interval of {_MAX_PING_INTERVAL}. Restarting.',
])
def test_check_health(ws_client, wsa_mock, ws_app_factory, patched_constructors, mocker, **kwargs):
    """Restarts and recreates subscriptions when heartbeat exceeds max ping interval."""
    ## Arrange
    cm = kwargs['_cm_ibind']
    start_time = [100]
    has_active_connection_counter = [0]

    def fake_time():
        start_time[0] += 100
        return start_time[0]

    def has_active_connection():
        has_active_connection_counter[0] += 1
        if has_active_connection_counter[0] <= 2:
            return False
        return True

    queue = ws_client.new_queue_accessor(IbkrWsKey.TRADES)
    full_channel = f'{queue.key.channel}+{_CONID}'
    request = {'channel': f'{full_channel}', 'data': {'foo': 'bar'}}
    response = {
        'topic': f's{full_channel}',
        '_updated': _UPDATE_TIME,
        'conid': _CONID,
        'args': [{'foo': 'bar'}],
    }

    ## Act
    def override_init_wsa_mock(wsa_mock: MagicMock, *args, **kwargs):
        wsa_mock = init_wsa_mock(wsa_mock, *args, **kwargs)
        wsa_mock._on_message.side_effect = lambda wsa_mock, message: wsa_mock.__on_message__(wsa_mock, json.dumps(response))
        return wsa_mock

    ws_client.start()
    ws_client.check_health()
    wsa_mock._on_message.side_effect = lambda wsa_mock, message: wsa_mock.__on_message__(wsa_mock, json.dumps(response))

    ws_client.subscribe(**request)

    # Override time, ignore ping check, and control active-connection health checks.
    time_mock = mocker.patch('ibind.client.ibkr_ws_client.time')
    time_mock.time.side_effect = fake_time

    mocker.patch.object(ws_client, 'check_ping', return_value=True)
    mocker.patch.object(ws_client, '_has_active_connection', side_effect=has_active_connection)

    # Ensure each reconnect creates a WebSocketApp whose on_message pushes our fake response.
    ws_app_factory['fn'] = lambda *args, **kwargs: override_init_wsa_mock(wsa_mock, *args, **kwargs)

    ws_client._last_heartbeat = _MAX_PING_INTERVAL * 1000
    ws_client.check_health()

    assert ws_client.ready() is True
    assert [call()] * 6 == ws_client._has_active_connection.call_args_list

    ws_client.shutdown()


    ## Assert
    channel_subscribed_log = f'IbkrWsClient: Subscribed: s{full_channel}+{json.dumps(request["data"])}'
    cm.partial_log(
        [channel_subscribed_log]
        + [
            f'IbkrWsClient: Invalidated subscription: {full_channel}',
            f"IbkrWsClient: Recreating 1/1 subscriptions: {{'{full_channel}': {{'status': False, 'data': {request['data']}, 'needs_confirmation': True, 'subscription_processor': None}}}}",
            channel_subscribed_log,
            f'IbkrWsClient: Invalidated subscription: {full_channel}',
        ]
    )