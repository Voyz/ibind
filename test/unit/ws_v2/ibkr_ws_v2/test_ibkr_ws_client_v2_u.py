import json
from unittest.mock import MagicMock, patch
from collections import defaultdict

import pytest

from ibind import events, var, IbkrClient
from ibind.ibkr_ws_v2.ibkr_events import System
from ibind.ibkr_ws_v2.ibkr_router import IbkrRouter
from ibind.ibkr_ws_v2.ibkr_ws_client_v2 import IbkrWsClientV2, _build_ws_url
from ibind.ibkr_ws_v2.ibkr_subscriptions import MarketHistorySubscription
from ibind.ws_v2.ws_sinks import AsyncSink
from ibind.ws_v2.ws_subscriptions import SubscriptionHandle, BindingStatus
from ibind.ws_v2.ws_runtime import WsState
from test.test_utils import capture_logs
from ibind.ibkr_ws_v2.ibkr_subscriptions import MarketDataSubscription


@pytest.fixture
def client():
    with patch('ibind.ibkr_ws_v2.ibkr_ws_client_v2.IbkrClient'), patch('ibind.ibkr_ws_v2.ibkr_ws_client_v2.WsRuntime'):
        return IbkrWsClientV2()


class TestBuildWsUrl:
    def test_build_ws_url_with_explicit_url_non_oauth(self):
        """_build_ws_url returns explicit URL when provided and not using OAuth."""
        result = _build_ws_url(
            url='wss://custom.example.com/ws',
            use_oauth=False,
            access_token=None,
            host='127.0.0.1',
            port='5000',
            base_route='/v1/api/ws',
        )
        assert result == 'wss://custom.example.com/ws'

    def test_build_ws_url_constructs_from_host_port(self):
        """_build_ws_url constructs URL from host and port when url is None."""
        result = _build_ws_url(
            url=None,
            use_oauth=False,
            access_token=None,
            host='192.168.1.1',
            port='8080',
            base_route='/api/ws',
        )
        assert result == 'wss://192.168.1.1:8080/api/ws'

    @patch('ibind.ibkr_ws_v2.ibkr_ws_client_v2.var')
    def test_build_ws_url_oauth_uses_env_url(self, mock_var):
        """_build_ws_url uses IBIND_OAUTH1A_WS_URL when url is None and use_oauth is True."""
        mock_var.IBIND_OAUTH1A_WS_URL = 'wss://oauth.example.com/ws'
        result = _build_ws_url(
            url=None,
            use_oauth=True,
            access_token='token_123',  # noqa: S106
            host='127.0.0.1',
            port='5000',
            base_route='/v1/api/ws',
        )
        assert result == 'wss://oauth.example.com/ws?oauth_token=token_123'

    def test_build_ws_url_oauth_appends_token(self):
        """_build_ws_url appends oauth_token parameter when use_oauth is True."""
        result = _build_ws_url(
            url='wss://example.com/ws',
            use_oauth=True,
            access_token='my_token_456',  # noqa: S106
            host='127.0.0.1',
            port='5000',
            base_route='/v1/api/ws',
        )
        assert result == 'wss://example.com/ws?oauth_token=my_token_456'

    def test_build_ws_url_oauth_without_token_raises(self):
        """_build_ws_url raises ValueError when use_oauth is True but access_token is None."""
        with pytest.raises(ValueError, match='OAuth access token not found'):
            _build_ws_url(
                url='wss://example.com/ws',
                use_oauth=True,
                access_token=None,
                host='127.0.0.1',
                port='5000',
                base_route='/v1/api/ws',
            )

    def test_build_ws_url_oauth_without_token_from_host_port_raises(self):
        """_build_ws_url raises ValueError when constructing URL from host/port with OAuth but no token."""
        with pytest.raises(ValueError, match='OAuth access token not found'):
            _build_ws_url(
                url=None,
                use_oauth=True,
                access_token=None,
                host='127.0.0.1',
                port='5000',
                base_route='/v1/api/ws',
            )


class TestIbkrWsClientV2Init:
    @capture_logs()
    @patch('ibind.ibkr_ws_v2.ibkr_ws_client_v2.IbkrClient')
    @patch('ibind.ibkr_ws_v2.ibkr_ws_client_v2.WsRuntime')
    def test_default_initialization(self, mock_ws_runtime, mock_ibkr_client):
        """IbkrWsClientV2 initializes with default parameters."""
        ## Arrange
        mock_client_instance = MagicMock()
        mock_ibkr_client.return_value = mock_client_instance

        ## Act
        with patch.object(IbkrWsClientV2, '_register_internal_callbacks'):
            client = IbkrWsClientV2()

        ## Assert
        assert client._account_id == var.IBIND_ACCOUNT_ID
        assert client._ibkr_client == mock_client_instance
        assert client._use_oauth is var.IBIND_USE_OAUTH
        assert client._mh_subscriptions == {}
        assert isinstance(client._conid_server_id_pairs, defaultdict)
        assert client._tic_message == {}

    @capture_logs()
    @patch('ibind.ibkr_ws_v2.ibkr_ws_client_v2.IbkrClient')
    @patch('ibind.ibkr_ws_v2.ibkr_ws_client_v2.WsRuntime')
    def test_custom_account_id(self, mock_ws_runtime, mock_ibkr_client):
        """IbkrWsClientV2 initializes with custom account_id."""
        ## Arrange
        mock_client_instance = MagicMock()
        mock_ibkr_client.return_value = mock_client_instance

        ## Act
        with patch.object(IbkrWsClientV2, '_register_internal_callbacks'):
            client = IbkrWsClientV2(account_id='CUSTOM_ACCOUNT')

        ## Assert
        assert client._account_id == 'CUSTOM_ACCOUNT'

    @capture_logs()
    @patch('ibind.ibkr_ws_v2.ibkr_ws_client_v2.IbkrClient')
    @patch('ibind.ibkr_ws_v2.ibkr_ws_client_v2.WsRuntime')
    def test_custom_ibkr_client(self, mock_ws_runtime, mock_ibkr_client):
        """IbkrWsClientV2 uses provided ibkr_client instead of creating new one."""
        ## Arrange
        custom_client = MagicMock(spec=IbkrClient)

        ## Act
        with patch.object(IbkrWsClientV2, '_register_internal_callbacks'):
            client = IbkrWsClientV2(ibkr_client=custom_client)

        ## Assert
        assert client._ibkr_client is custom_client
        mock_ibkr_client.assert_not_called()

    @capture_logs()
    @patch('ibind.ibkr_ws_v2.ibkr_ws_client_v2.IbkrClient')
    @patch('ibind.ibkr_ws_v2.ibkr_ws_client_v2.WsRuntime')
    def test_noop_sink_by_default(self, mock_ws_runtime, mock_ibkr_client):
        """IbkrWsClientV2 uses NoopSink when sink is None."""
        ## Arrange
        mock_client_instance = MagicMock()
        mock_ibkr_client.return_value = mock_client_instance

        ## Act
        with patch.object(IbkrWsClientV2, '_register_internal_callbacks'):
            IbkrWsClientV2()

        ## Assert
        call_kwargs = mock_ws_runtime.call_args[1]
        assert isinstance(call_kwargs['sink'], AsyncSink)

    @capture_logs()
    @patch('ibind.ibkr_ws_v2.ibkr_ws_client_v2.IbkrClient')
    @patch('ibind.ibkr_ws_v2.ibkr_ws_client_v2.WsRuntime')
    def test_synchronous_output_events(self, mock_ws_runtime, mock_ibkr_client):
        """IbkrWsClientV2 uses synchronous sink when synchronous_output_events is True."""
        ## Arrange
        mock_client_instance = MagicMock()
        mock_ibkr_client.return_value = mock_client_instance
        custom_sink = MagicMock()

        ## Act
        IbkrWsClientV2(sink=custom_sink, synchronous_output_events=True)

        ## Assert
        call_kwargs = mock_ws_runtime.call_args[1]
        assert call_kwargs['sink'] is custom_sink

    @capture_logs()
    @patch('ibind.ibkr_ws_v2.ibkr_ws_client_v2.IbkrClient')
    @patch('ibind.ibkr_ws_v2.ibkr_ws_client_v2.WsRuntime')
    def test_custom_router(self, mock_ws_runtime, mock_ibkr_client):
        """IbkrWsClientV2 uses provided router."""
        ## Arrange
        mock_client_instance = MagicMock()
        mock_ibkr_client.return_value = mock_client_instance
        custom_router = MagicMock()

        ## Act
        with patch.object(IbkrWsClientV2, '_register_internal_callbacks'):
            IbkrWsClientV2(router=custom_router)

        ## Assert
        call_kwargs = mock_ws_runtime.call_args[1]
        assert call_kwargs['router'] is custom_router

    @capture_logs()
    @patch('ibind.ibkr_ws_v2.ibkr_ws_client_v2.IbkrClient')
    @patch('ibind.ibkr_ws_v2.ibkr_ws_client_v2.WsRuntime')
    def test_custom_subscription_resolver(self, mock_ws_runtime, mock_ibkr_client):
        """IbkrWsClientV2 uses provided subscription_resolver."""
        ## Arrange
        mock_client_instance = MagicMock()
        mock_ibkr_client.return_value = mock_client_instance
        custom_resolver = MagicMock()

        ## Act
        with patch.object(IbkrWsClientV2, '_register_internal_callbacks'):
            IbkrWsClientV2(subscription_resolver=custom_resolver)

        ## Assert
        call_kwargs = mock_ws_runtime.call_args[1]
        assert call_kwargs['subscription_resolver'] is custom_resolver

    @capture_logs()
    @patch('ibind.ibkr_ws_v2.ibkr_ws_client_v2.IbkrClient')
    @patch('ibind.ibkr_ws_v2.ibkr_ws_client_v2.WsRuntime')
    def test_register_internal_callbacks_called(self, mock_ws_runtime, mock_ibkr_client):
        """IbkrWsClientV2 registers internal callbacks during initialization."""
        ## Arrange
        mock_client_instance = MagicMock()
        mock_ibkr_client.return_value = mock_client_instance
        mock_runtime_instance = MagicMock()
        mock_ws_runtime.return_value = mock_runtime_instance

        ## Act
        client = IbkrWsClientV2()

        ## Assert
        assert mock_runtime_instance.add_internal_callback.call_count == 5
        mock_runtime_instance.add_internal_callback.assert_any_call(events.AuthenticationStatus, client._on_authentication_status)
        mock_runtime_instance.add_internal_callback.assert_any_call(events.WaitingForSession, client._on_waiting_for_session)
        mock_runtime_instance.add_internal_callback.assert_any_call(events.System, client._on_system)
        mock_runtime_instance.add_internal_callback.assert_any_call(events.ServerId, client._on_server_id)
        mock_runtime_instance.add_internal_callback.assert_any_call(events.WsStopping, client._on_stopping)


class TestIbkrWsClientV2Callbacks:
    @capture_logs()
    def test_on_waiting_for_session(self, client):
        """_on_waiting_for_session sets runtime state to OPEN."""
        ## Arrange
        client._runtime = MagicMock()

        ## Act
        client._on_waiting_for_session(None)

        ## Assert
        client._runtime.set_state.assert_called_once_with(WsState.OPEN)

    @capture_logs(expected_errors=['Status unauthenticated:'], partial_match=True)
    def test_on_authentication_status_unauthenticated_when_was_authenticated(self, client):
        """_on_authentication_status logs error when becoming unauthenticated."""
        ## Arrange
        client._runtime = MagicMock()
        client._runtime.is_authenticated.return_value = True
        event = events.AuthenticationStatus(authenticated=False, competing=None, data={})

        ## Act
        client._on_authentication_status(event)

        ## Assert
        client._runtime.set_authenticated.assert_called_once_with(False)

    @capture_logs(expected_errors=['Authentication competing:'], partial_match=True)
    def test_on_authentication_status_competing(self, client):
        """_on_authentication_status logs error when competing is True."""
        ## Arrange
        client._runtime = MagicMock()
        client._runtime.is_authenticated.return_value = False
        event = events.AuthenticationStatus(authenticated=None, competing=True, data={})

        ## Act
        client._on_authentication_status(event)

        ## Assert

    @capture_logs()
    def test_on_authentication_status_authenticated(self, client):
        """_on_authentication_status sets authenticated state."""
        ## Arrange
        client._runtime = MagicMock()
        client._runtime.is_authenticated.return_value = False
        event = events.AuthenticationStatus(authenticated=True, competing=None, data={})

        ## Act
        client._on_authentication_status(event)

        ## Assert
        client._runtime.set_authenticated.assert_called_once_with(True)

    @capture_logs()
    def test_on_authentication_status_none_authenticated_not_set(self, client):
        """_on_authentication_status does not set state when authenticated is None."""
        ## Arrange
        client._runtime = MagicMock()
        event = events.AuthenticationStatus(authenticated=None, competing=None, data={})

        ## Act
        client._on_authentication_status(event)

        ## Assert
        client._runtime.set_authenticated.assert_not_called()

    @capture_logs()
    def test_on_system_with_heartbeat(self, client):
        """_on_system sets last heartbeat when hb is present."""
        ## Arrange
        client._runtime = MagicMock()
        event = events.System(data={'hb': 1234567890000})

        ## Act
        client._on_system(event)

        ## Assert
        client._runtime.set_last_heartbeat.assert_called_once_with(1234567890.0)

    @capture_logs()
    def test_on_system_without_heartbeat(self, client):
        """_on_system does not set heartbeat when hb is missing."""
        ## Arrange
        client._runtime = MagicMock()
        event = events.System(data={'other': 'data'})

        ## Act
        client._on_system(event)

        ## Assert
        client._runtime.set_last_heartbeat.assert_not_called()

    @capture_logs()
    def test_on_server_id_stores_mapping(self, client):
        """_on_server_id stores conid to server_id mapping."""
        ## Arrange
        event = events.ServerId(conid='12345', server_id='srv_abc', target_event_type=events.MarketHistory)

        ## Act
        client._on_server_id(event)

        ## Assert
        assert client._conid_server_id_pairs[events.MarketHistory]['12345'] == 'srv_abc'

    @capture_logs()
    def test_on_server_id_updates_mh_subscription(self, client):
        """_on_server_id updates MarketHistorySubscription with server_id."""
        ## Arrange
        subscription = MarketHistorySubscription(conid='12345')
        key = (events.MarketHistory, '12345')
        client._mh_subscriptions[key] = subscription
        event = events.ServerId(conid='12345', server_id='srv_abc', target_event_type=events.MarketHistory)

        ## Act
        client._on_server_id(event)

        ## Assert
        assert subscription.has_server_id() is True
        assert subscription.get_server_id() == 'srv_abc'

    @capture_logs()
    def test_on_server_id_does_not_update_subscription_with_different_conid(self, client):
        """_on_server_id does not update subscription with different conid."""
        ## Arrange
        subscription = MarketHistorySubscription(conid='99999')
        key = (events.MarketHistory, '99999')
        client._mh_subscriptions[key] = subscription
        event = events.ServerId(conid='12345', server_id='srv_abc', target_event_type=events.MarketHistory)

        ## Act
        client._on_server_id(event)

        ## Assert
        assert subscription.has_server_id() is False

    @capture_logs()
    def test_on_server_id_replaces_stale_server_id(self, client):
        """_on_server_id clears and replaces stale server_id (reconnect scenario)."""
        ## Arrange
        subscription = MarketHistorySubscription(conid='12345')
        subscription.set_server_id('srv_old')
        key = (events.MarketHistory, '12345')
        client._mh_subscriptions[key] = subscription
        event = events.ServerId(conid='12345', server_id='srv_new', target_event_type=events.MarketHistory)

        ## Act
        client._on_server_id(event)

        ## Assert
        assert subscription.get_server_id() == 'srv_new'


class TestIbkrWsClientV2GetCookie:
    @capture_logs()
    def test_get_cookie_non_oauth(self, client):
        """_get_cookie returns cookie with session JSON for non-OAuth."""
        ## Arrange
        client._use_oauth = False
        client._ibkr_client = MagicMock()
        status_response = MagicMock()
        status_response.data = {'session': 'test_session_123'}
        client._ibkr_client.tickle.return_value = status_response

        ## Act
        result = client._get_cookie()

        ## Assert
        expected = 'api=' + json.dumps({'session': 'test_session_123'})
        assert result == expected

    @capture_logs()
    def test_get_cookie_oauth(self, client):
        """_get_cookie returns cookie with session string for OAuth."""
        ## Arrange
        client._use_oauth = True
        client._ibkr_client = MagicMock()
        status_response = MagicMock()
        status_response.data = {'session': 'oauth_session_456'}
        client._ibkr_client.tickle.return_value = status_response

        ## Act
        result = client._get_cookie()

        ## Assert
        assert result == 'api=oauth_session_456'


class TestIbkrWsClientV2GetHeader:
    @capture_logs()
    def test_get_header_oauth(self, client):
        """_get_header returns User-Agent header for OAuth."""
        ## Arrange
        client._use_oauth = True

        ## Act
        result = client._get_header()

        ## Assert
        assert result == {'User-Agent': 'ClientPortalGW/1'}

    @capture_logs()
    def test_get_header_non_oauth(self, client):
        """_get_header returns None for non-OAuth."""
        ## Arrange
        client._use_oauth = False

        ## Act
        result = client._get_header()

        ## Assert
        assert result is None


class TestIbkrWsClientV2GetAuthenticated:
    @capture_logs()
    def test_get_authenticated_true(self, client):
        """_get_authenticated returns True when authenticated."""
        ## Arrange
        client._ibkr_client = MagicMock()
        auth_response = MagicMock()
        auth_response.data = {'authenticated': True}
        client._ibkr_client.authentication_status.return_value = auth_response

        ## Act
        result = client._get_authenticated()

        ## Assert
        assert result is True

    @capture_logs()
    def test_get_authenticated_false(self, client):
        """_get_authenticated returns False when not authenticated."""
        ## Arrange
        client._ibkr_client = MagicMock()
        auth_response = MagicMock()
        auth_response.data = {'authenticated': False}
        client._ibkr_client.authentication_status.return_value = auth_response

        ## Act
        result = client._get_authenticated()

        ## Assert
        assert result is False


class TestIbkrWsClientV2Subscribe:
    @capture_logs()
    def test_subscribe_market_history_adds_to_dict(self, client):
        """subscribe adds MarketHistorySubscription to internal dict."""
        ## Arrange
        client._runtime = MagicMock()
        subscription = MarketHistorySubscription(conid='12345')
        handle = MagicMock(spec=SubscriptionHandle)
        handle.binding_key = 'smh+12345'

        binding = MagicMock()
        binding.subscription = subscription
        client._runtime.subscription_controller._bindings = {'smh+12345': binding}
        client._runtime.subscription_controller.subscribe.return_value = handle

        ## Act
        result = client.subscribe(subscription)

        ## Assert
        key = (events.MarketHistory, '12345')
        assert key in client._mh_subscriptions
        assert client._mh_subscriptions[key] is subscription
        assert result is handle

    @capture_logs()
    def test_subscribe_non_market_history(self, client):
        """subscribe does not add non-MarketHistory subscriptions to dict."""
        ## Arrange
        client._runtime = MagicMock()

        subscription = MarketDataSubscription(conid='12345', fields=['31'])
        handle = MagicMock(spec=SubscriptionHandle)
        client._runtime.subscription_controller.subscribe.return_value = handle

        ## Act
        result = client.subscribe(subscription)

        ## Assert
        assert len(client._mh_subscriptions) == 0
        assert result is handle

    @capture_logs()
    def test_subscribe_market_history_replaces_existing_for_same_conid(self, client):
        """subscribe tracks controller's retained subscription, not caller's instance."""
        ## Arrange
        client._runtime = MagicMock()
        subscription1 = MarketHistorySubscription(conid='12345', period='1d')
        subscription2 = MarketHistorySubscription(conid='12345', period='1w')
        handle = MagicMock(spec=SubscriptionHandle)
        handle.binding_key = 'smh+12345'

        binding = MagicMock()
        binding.subscription = subscription1
        client._runtime.subscription_controller._bindings = {'smh+12345': binding}
        client._runtime.subscription_controller.subscribe.return_value = handle

        ## Act
        client.subscribe(subscription1)
        client.subscribe(subscription2)

        ## Assert - controller retained subscription1, so that's what gets tracked
        key = (events.MarketHistory, '12345')
        assert len(client._mh_subscriptions) == 1
        assert client._mh_subscriptions[key] is subscription1


class TestIbkrWsClientV2Unsubscribe:
    @capture_logs()
    def test_unsubscribe_market_history_with_server_id(self, client):
        """unsubscribe handles MarketHistorySubscription with server_id."""
        ## Arrange
        client._runtime = MagicMock()
        subscription = MarketHistorySubscription(conid='12345')
        subscription.set_server_id('srv_abc')
        handle = MagicMock(spec=SubscriptionHandle)
        client._runtime.subscription_controller.unsubscribe.return_value = handle

        ## Act
        result = client.unsubscribe(subscription)

        ## Assert
        assert result is handle

    @capture_logs(expected_errors=['Unsubscribing from market history for conid'], partial_match=True)
    def test_unsubscribe_market_history_without_server_id_uses_memory(self, client):
        """unsubscribe sets server_id from memory when missing."""
        ## Arrange
        client._runtime = MagicMock()
        subscription = MarketHistorySubscription(conid='12345')
        client._conid_server_id_pairs[events.MarketHistory]['12345'] = 'srv_from_memory'
        handle = MagicMock(spec=SubscriptionHandle)
        client._runtime.subscription_controller.unsubscribe.return_value = handle

        ## Act
        result = client.unsubscribe(subscription)

        ## Assert
        assert subscription.get_server_id() == 'srv_from_memory'
        assert result is handle

    @capture_logs()
    def test_unsubscribe_market_history_without_server_id_not_in_memory_raises(self, client):
        """unsubscribe raises RuntimeError when server_id not found."""
        ## Arrange
        client._runtime = MagicMock()
        subscription = MarketHistorySubscription(conid='99999')

        ## Act & Assert
        with pytest.raises(RuntimeError, match='Could not find server_id in memory'):
            client.unsubscribe(subscription)

    @capture_logs()
    def test_unsubscribe_non_market_history(self, client):
        """unsubscribe handles non-MarketHistory subscriptions normally."""
        ## Arrange
        client._runtime = MagicMock()

        subscription = MarketDataSubscription(conid='12345', fields=['31'])
        handle = MagicMock(spec=SubscriptionHandle)
        client._runtime.subscription_controller.unsubscribe.return_value = handle

        ## Act
        result = client.unsubscribe(subscription)

        ## Assert
        assert result is handle

    @capture_logs()
    def test_unsubscribe_market_history_removes_from_dict(self, client):
        """unsubscribe removes MarketHistorySubscription from dict."""
        ## Arrange
        client._runtime = MagicMock()
        subscription = MarketHistorySubscription(conid='12345')
        subscription.set_server_id('srv_abc')
        key = (events.MarketHistory, '12345')
        client._mh_subscriptions[key] = subscription
        handle = MagicMock(spec=SubscriptionHandle)
        client._runtime.subscription_controller.unsubscribe.return_value = handle

        ## Act
        result = client.unsubscribe(subscription)

        ## Assert
        assert key not in client._mh_subscriptions
        assert len(client._mh_subscriptions) == 0
        assert result is handle

    @capture_logs()
    def test_unsubscribe_market_history_not_in_dict_is_safe(self, client):
        """unsubscribe handles MarketHistorySubscription not in dict gracefully."""
        ## Arrange
        client._runtime = MagicMock()
        subscription = MarketHistorySubscription(conid='12345')
        subscription.set_server_id('srv_abc')
        handle = MagicMock(spec=SubscriptionHandle)
        client._runtime.subscription_controller.unsubscribe.return_value = handle

        ## Act
        result = client.unsubscribe(subscription)

        ## Assert
        assert len(client._mh_subscriptions) == 0
        assert result is handle


class TestIbkrWsClientV2GetStatus:
    @capture_logs()
    def test_get_status(self, client):
        """get_status delegates to subscription controller."""
        ## Arrange
        client._runtime = MagicMock()
        status = MagicMock(spec=BindingStatus)
        client._runtime.subscription_controller.get_status.return_value = status

        ## Act
        result = client.get_binding_status('md+12345')

        ## Assert
        assert result is status
        client._runtime.subscription_controller.get_status.assert_called_once_with('md+12345')


class TestIbkrWsClientV2WaitAll:
    @capture_logs()
    def test_wait_all_success(self, client):
        """wait_all returns empty list when all handles succeed."""
        ## Arrange
        handle1 = MagicMock(spec=SubscriptionHandle)
        handle1.wait.return_value = True
        handle2 = MagicMock(spec=SubscriptionHandle)
        handle2.wait.return_value = True

        ## Act
        result = client.wait_all([handle1, handle2])

        ## Assert
        assert result == []

    @capture_logs()
    def test_wait_all_some_fail(self, client):
        """wait_all returns failed handles."""
        ## Arrange
        handle1 = MagicMock(spec=SubscriptionHandle)
        handle1.wait.return_value = True
        handle2 = MagicMock(spec=SubscriptionHandle)
        handle2.wait.return_value = False
        handle3 = MagicMock(spec=SubscriptionHandle)
        handle3.wait.return_value = False

        ## Act
        result = client.wait_all([handle1, handle2, handle3])

        ## Assert
        assert result == [handle2, handle3]

    @capture_logs()
    def test_wait_all_single_handle(self, client):
        """wait_all handles single handle (decorator converts to list)."""
        ## Arrange
        handle = MagicMock(spec=SubscriptionHandle)
        handle.wait.return_value = True

        ## Act
        result = client.wait_all(handle)

        ## Assert
        assert result == []

    def test_wait_all_with_timeout_each(self, client):
        """wait_all applies timeout_each independently to every handle."""
        ## Arrange
        handle1 = MagicMock(spec=SubscriptionHandle)
        handle2 = MagicMock(spec=SubscriptionHandle)
        handle1.wait.return_value = True
        handle2.wait.return_value = True

        ## Act
        client.wait_all([handle1, handle2], timeout_each=10.0)

        ## Assert
        handle1.wait.assert_called_once_with(10.0)
        handle2.wait.assert_called_once_with(10.0)


class TestIbkrWsClientV2Tic:
    @capture_logs()
    @patch('ibind.ibkr_ws_v2.ibkr_ws_client_v2.wait_until')
    def test_tic_returns_routed_tic_response(self, mock_wait_until, client):
        """tic records and returns a tic response routed through the System event callback."""
        ## Arrange
        response = {'topic': 'tic', 'lastAccessed': 2000}
        client._runtime = MagicMock()
        client._tic_message = {'lastAccessed': 1000}

        def send_tic(_):
            event = IbkrRouter().route(json.dumps(response))
            if not isinstance(event, System):
                raise ValueError(f'Expected System event, got {event}')

            client._on_system(event)
            return True

        client._runtime.send.side_effect = send_tic
        mock_wait_until.side_effect = lambda predicate, timeout: predicate()

        ## Act
        result = client.tic()

        ## Assert
        assert result == response
        client._runtime.send.assert_called_once_with('tic')

    @capture_logs()
    @patch('ibind.ibkr_ws_v2.ibkr_ws_client_v2.wait_until')
    def test_tic_success(self, mock_wait_until, client):
        """tic sends tic request and waits for response."""
        ## Arrange
        client._runtime = MagicMock()
        client._runtime.send.return_value = True
        client._tic_message = {'lastAccessed': 1000}
        mock_wait_until.return_value = True

        ## Act
        result = client.tic()

        ## Assert
        client._runtime.send.assert_called_once_with('tic')
        assert result == {'lastAccessed': 1000}

    @capture_logs()
    def test_tic_send_fails(self, client):
        """tic returns None when send fails."""
        ## Arrange
        client._runtime = MagicMock()
        client._runtime.send.return_value = False

        ## Act
        result = client.tic()

        ## Assert
        assert result is None

    @capture_logs(expected_errors=['tic timeout'], partial_match=True)
    @patch('ibind.ibkr_ws_v2.ibkr_ws_client_v2.wait_until')
    def test_tic_timeout(self, mock_wait_until, client):
        """tic returns None when wait times out."""
        ## Arrange
        client._runtime = MagicMock()
        client._runtime.send.return_value = True
        client._tic_message = {'lastAccessed': 1000}
        mock_wait_until.return_value = False

        ## Act
        result = client.tic()

        ## Assert
        assert result is None

    @capture_logs()
    @patch('ibind.ibkr_ws_v2.ibkr_ws_client_v2.wait_until')
    def test_tic_updates_message(self, mock_wait_until, client):
        """tic detects when tic_message is updated."""
        ## Arrange
        client._runtime = MagicMock()
        client._runtime.send.return_value = True
        client._tic_message = {'lastAccessed': 1000}

        def side_effect(func, timeout):
            client._tic_message = {'lastAccessed': 2000}
            return True

        mock_wait_until.side_effect = side_effect

        ## Act
        result = client.tic()

        ## Assert
        assert result == {'lastAccessed': 2000}

    @capture_logs()
    @patch('ibind.ibkr_ws_v2.ibkr_ws_client_v2.wait_until')
    def test_tic_callback_function(self, mock_wait_until, client):
        """tic creates callback that detects timestamp change."""
        ## Arrange
        client._runtime = MagicMock()
        client._runtime.send.return_value = True
        client._tic_message = {'lastAccessed': 1000}
        mock_wait_until.return_value = True

        ## Act
        client.tic()

        ## Assert
        mock_wait_until.assert_called_once()
        callback_func = mock_wait_until.call_args[0][0]
        assert callable(callback_func)
        assert callback_func() is False
        client._tic_message = {'lastAccessed': 2000}
        assert callback_func() is True


class TestIbkrWsClientV2MarketHistoryServerIdTracking:
    @capture_logs()
    def test_subscribe_tracks_controller_retained_instance(self, client):
        """subscribe stores controller's retained subscription instance, not caller's instance."""
        ## Arrange
        client._runtime = MagicMock()
        subscription_a = MarketHistorySubscription(conid='12345', period='1d')
        subscription_b = MarketHistorySubscription(conid='12345', period='1d')

        handle = MagicMock(spec=SubscriptionHandle)
        handle.binding_key = 'smh+12345'

        binding = MagicMock()
        binding.subscription = subscription_a
        client._runtime.subscription_controller._bindings = {'smh+12345': binding}
        client._runtime.subscription_controller.subscribe.return_value = handle

        ## Act - subscribe with instance A first
        client.subscribe(subscription_a)

        ## Assert - instance A is tracked
        key = (events.MarketHistory, '12345')
        assert client._mh_subscriptions[key] is subscription_a

        ## Act - subscribe with equivalent instance B (idempotent)
        client.subscribe(subscription_b)

        ## Assert - controller's retained instance A is still tracked, not B
        assert client._mh_subscriptions[key] is subscription_a
        assert client._mh_subscriptions[key] is not subscription_b

    @capture_logs()
    def test_on_server_id_clears_stale_id_on_reconnect(self, client):
        """_on_server_id clears stale server_id before setting new one on reconnect."""
        ## Arrange
        subscription = MarketHistorySubscription(conid='12345')
        subscription.set_server_id('old_server_id')
        key = (events.MarketHistory, '12345')
        client._mh_subscriptions[key] = subscription

        event = events.ServerId(conid='12345', server_id='new_server_id', target_event_type=events.MarketHistory)

        ## Act
        client._on_server_id(event)

        ## Assert - old ID was cleared and new ID was set
        assert subscription.has_server_id() is True
        assert subscription.get_server_id() == 'new_server_id'

    @capture_logs()
    def test_on_stopping_clears_all_market_history_server_ids(self, client):
        """_on_stopping clears all Market History server IDs to prepare for reconnect."""
        ## Arrange
        sub1 = MarketHistorySubscription(conid='12345')
        sub1.set_server_id('srv_1')
        sub2 = MarketHistorySubscription(conid='67890')
        sub2.set_server_id('srv_2')
        sub3 = MarketHistorySubscription(conid='11111')

        client._mh_subscriptions = {
            (events.MarketHistory, '12345'): sub1,
            (events.MarketHistory, '67890'): sub2,
            (events.MarketHistory, '11111'): sub3,
        }

        stopping_event = events.WsStopping(previous_state=WsState.AUTHENTICATED, current_state=WsState.STOPPING)

        ## Act
        client._on_stopping(stopping_event)

        ## Assert - all server IDs cleared
        assert sub1.has_server_id() is False
        assert sub2.has_server_id() is False
        assert sub3.has_server_id() is False

    @capture_logs()
    def test_clear_market_history_server_ids_handles_empty_subscriptions(self, client):
        """_clear_market_history_server_ids handles empty subscription dict without error."""
        ## Arrange
        client._mh_subscriptions = {}

        ## Act & Assert - should not raise
        client._clear_market_history_server_ids()

    @capture_logs()
    def test_clear_market_history_server_ids_only_clears_subscriptions_with_ids(self, client):
        """_clear_market_history_server_ids only clears subscriptions that have server IDs."""
        ## Arrange
        sub_with_id = MarketHistorySubscription(conid='12345')
        sub_with_id.set_server_id('srv_1')
        sub_without_id = MarketHistorySubscription(conid='67890')

        client._mh_subscriptions = {
            (events.MarketHistory, '12345'): sub_with_id,
            (events.MarketHistory, '67890'): sub_without_id,
        }

        ## Act
        client._clear_market_history_server_ids()

        ## Assert
        assert sub_with_id.has_server_id() is False
        assert sub_without_id.has_server_id() is False
