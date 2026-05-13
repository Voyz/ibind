import ssl
from unittest.mock import MagicMock

from ibind import events
from ibind.ibkr_ws_v2.ibkr_router import IbkrRouter
from ibind.ibkr_ws_v2.ibkr_ws_client_v2 import IbkrWsClientV2
from ibind.ws_v2._ws_events import CallbackSink, QueueSink
from ibind.ws_v2.ws_runtime import WsState
from ibind.ws_v2.ws_transport import WsTransport


def test_ws_state_values_are_strings():
    assert WsState.OPEN.value == 'OPEN'
    assert str(WsState.AUTHENTICATED) == 'AUTHENTICATED'


def test_callback_sink_instances_do_not_share_callbacks():
    ## Arrange
    first_callback = MagicMock()
    second_callback = MagicMock()
    first = CallbackSink()
    second = CallbackSink()

    ## Act
    first.on(events.WsOpen, first_callback)
    second.emit(events.WsOpen())

    ## Assert
    first_callback.assert_not_called()
    second_callback.assert_not_called()


def test_queue_sink_instances_do_not_share_queues():
    ## Arrange
    first = QueueSink()
    second = QueueSink()

    ## Act
    first.emit(events.WsOpen())

    ## Assert
    assert second.get(events.WsOpen) is None


def test_transport_liveness_fails_when_pong_predates_ping(mocker):
    ## Arrange
    transport = WsTransport(url='wss://example.test/ws', event_callback=lambda _: None, sslopt={})
    transport._wsa = MagicMock(last_ping_tm=100, last_pong_tm=90)
    mocker.patch('ibind.ws_v2.ws_transport.time.time', return_value=160)

    ## Act / Assert
    assert transport.check_ping(max_interval=50) is False


def test_transport_liveness_tracks_first_unanswered_ping(mocker):
    ## Arrange
    current_time = [100.0]
    transport = WsTransport(url='wss://example.test/ws', event_callback=lambda _: None, sslopt={})
    transport._wsa = MagicMock(last_ping_tm=100.0, last_pong_tm=0)
    mocker.patch('ibind.ws_v2.ws_transport.time.time', side_effect=lambda: current_time[0])

    ## Act / Assert
    assert transport.check_ping(max_interval=50) is True
    current_time[0] = 130.0
    transport._wsa.last_ping_tm = 130.0
    assert transport.check_ping(max_interval=50) is True
    current_time[0] = 151.0
    transport._wsa.last_ping_tm = 151.0
    assert transport.check_ping(max_interval=50) is False


def test_transport_liveness_allows_fresh_pong_after_ping(mocker):
    ## Arrange
    transport = WsTransport(url='wss://example.test/ws', event_callback=lambda _: None, sslopt={})
    transport._wsa = MagicMock(last_ping_tm=100, last_pong_tm=120)
    mocker.patch('ibind.ws_v2.ws_transport.time.time', return_value=140)

    ## Act / Assert
    assert transport.check_ping(max_interval=50) is True


def test_ibkr_ws_client_v2_oauth_url_preserves_existing_query_and_forces_tls():
    ## Arrange / Act
    client = IbkrWsClientV2(
        url='wss://localhost:5000/v1/api/ws?existing=1',
        ibkr_client=MagicMock(),
        use_oauth=True,
        access_token='TOKEN VALUE',  # noqa: S106
        cacert=False,
    )

    ## Assert
    assert client._runtime._url == 'wss://localhost:5000/v1/api/ws?existing=1&oauth_token=TOKEN+VALUE'
    assert client._runtime._sslopt == {'cert_reqs': ssl.CERT_REQUIRED}


def test_router_unknown_auth_status_is_not_silently_ignored():
    ## Arrange
    router = IbkrRouter()

    ## Act
    event = router.route('{"topic":"sts","args":{"unexpected":true}}')

    ## Assert
    assert isinstance(event, events.GenericIbkrEvent)
    assert event.topic == 'sts'
    assert event.data == {'unexpected': True}


def test_client_v2_competing_false_does_not_change_authentication(mocker):
    ## Arrange
    client = IbkrWsClientV2(ibkr_client=MagicMock(), use_oauth=False)
    client._runtime.set_authenticated = MagicMock()
    logger_error = mocker.patch('ibind.ibkr_ws_v2.ibkr_ws_client_v2._LOGGER.error')

    ## Act
    client._on_authentication_status(events.AuthenticationStatus(data={'competing': False}, authenticated=None, competing=False))

    ## Assert
    logger_error.assert_not_called()
    client._runtime.set_authenticated.assert_not_called()
