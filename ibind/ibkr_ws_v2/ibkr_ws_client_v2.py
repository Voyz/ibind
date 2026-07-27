import json
from collections import defaultdict
from typing import Union, List, Dict, Type, Optional

from ibind import events
from ibind import var
from ibind import IbkrClient
from ibind.events import IbkrTopicEvent
from ibind.ibkr_ws_v2.ibkr_router import IbkrRouter
from ibind.ibkr_ws_v2.ibkr_subscriptions import IbkrSubscriptionResolver, MarketHistorySubscription
from ibind.support.logs import project_logger
from ibind.support.py_utils import OneOrMany, ensure_list_arg, wait_until
from ibind.ws_v2._ws_events import EventSink, Router, AsyncSink, NoopSink
from ibind.ws_v2.ws_subscriptions import Subscription, SubscriptionResolver, SubscriptionHandle, BindingStatus
from ibind.ws_v2.ws_runtime import WsRuntime, WsState

_LOGGER = project_logger('ibkr_ws_client')

_DEFAULT_CYCLE_INTERVAL = 0.25


def _build_ws_url(
    url: str | None,
    use_oauth: bool,
    access_token: str | None,
    host: str = '127.0.0.1',
    port: str = '5000',
    base_route: str = '/v1/api/ws',
) -> str:
    """
    Build WebSocket URL for IBKR connection.

    Args:
        url (str | None): Custom WebSocket URL. If None, constructs from host/port/base_route.
        use_oauth (bool): Whether to use OAuth authentication.
        access_token (str | None): OAuth access token. Required if use_oauth is True.
        host (str): Server host. Default: '127.0.0.1'.
        port (str): Server port. Default: '5000'.
        base_route (str): API base route. Default: '/v1/api/ws'.

    Returns:
        str: The constructed WebSocket URL.

    Raises:
        ValueError: If use_oauth is True but access_token is None.
    """
    url = var.IBIND_OAUTH1A_WS_URL if url is None and use_oauth else url

    if url is None:
        url = f'wss://{host}:{port}{base_route}'

    if use_oauth:
        if access_token is None:
            raise ValueError(
                'OAuth access token not found. Please set IBIND_OAUTH1A_ACCESS_TOKEN environment variable or provide it as `access_token` argument.'
            )
        url += f'?oauth_token={access_token}'

    return url


class IbkrWsClientV2:
    """
    WebSocket client for Interactive Brokers market data and account updates.

    Manages subscriptions to IBKR WebSocket topics, handles authentication,
    and routes incoming events to registered sinks. Supports both OAuth and
    Gateway-based authentication.
    """

    def __init__(
        self,
        account_id: str = var.IBIND_ACCOUNT_ID,
        url: str = var.IBIND_WS_URL,
        host: str = '127.0.0.1',
        port: str = '5000',
        base_route: str = '/v1/api/ws',
        ibkr_client: IbkrClient = None,
        use_oauth: bool = var.IBIND_USE_OAUTH,
        access_token: str = var.IBIND_OAUTH1A_ACCESS_TOKEN,
        cacert: Union[str, bool] = var.IBIND_CACERT,
        cycle_interval: float = _DEFAULT_CYCLE_INTERVAL,
        sink: EventSink = None,
        router: Router = None,
        subscription_resolver: SubscriptionResolver = None,
        synchronous_output_events: bool = False,
    ):
        """
        Initialize the IBKR WebSocket client.

        Args:
            account_id (str): IBKR account ID. Default: None.
            url (str): WebSocket server URL. Default: None.
            host (str): Server host for local connections. Default: '127.0.0.1'.
            port (str): Server port. Default: '5000'.
            base_route (str): API base route. Default: '/v1/api/ws'.
            ibkr_client (IbkrClient, optional): REST client for authentication. If None, creates new instance.
            use_oauth (bool): Whether to use OAuth authentication. Default: False.
            access_token (str): OAuth access token. Default: None.
            cacert (Union[str, bool]): CA certificate for SSL verification. Default: False.
            cycle_interval (float): Event loop cycle interval in seconds. Default: 0.25.
            sink (EventSink, optional): Event sink for output events. Default: NoopSink.
            router (Router, optional): Event router. Default: IbkrRouter.
            subscription_resolver (SubscriptionResolver, optional): Subscription resolver. Default: IbkrSubscriptionResolver.
            synchronous_output_events (bool): If True, emit events synchronously from runtime thread. Default: False.
        """
        self._account_id = account_id
        self._use_oauth = use_oauth

        url = _build_ws_url(url, use_oauth, access_token, host, port, base_route)

        if ibkr_client is None:
            ibkr_client = IbkrClient(account_id=account_id, host=host, port=port, cacert=cacert, use_oauth=use_oauth)
        self._ibkr_client = ibkr_client

        if sink is None:
            sink = NoopSink()

        if synchronous_output_events:
            _LOGGER.info(f'{self}: Output events will be emitted synchronously from the runtime thread')
        else:
            sink = AsyncSink(sink=sink)

        if router is None:
            router = IbkrRouter()

        if subscription_resolver is None:
            subscription_resolver = IbkrSubscriptionResolver(account_id)

        self._runtime = WsRuntime(
            url=url,
            cycle_interval=cycle_interval,
            cacert=cacert,
            sink=sink,
            router=router,
            subscription_resolver=subscription_resolver,
            connection_timeout=5,
            get_cookie=self._get_cookie,
            get_header=self._get_header,
            get_authenticated=self._get_authenticated,
        )
        self._register_internal_callbacks()

        self._mh_subscriptions: List[MarketHistorySubscription] = []
        self._conid_server_id_pairs: Dict[type[events.IbkrTopicEvent], Dict[str, str]] = defaultdict(dict)
        self._tic_message = {}

    def _register_internal_callbacks(self):
        self._runtime.add_internal_callback(events.AuthenticationStatus, self._on_authentication_status)
        self._runtime.add_internal_callback(events.WaitingForSession, self._on_waiting_for_session)
        self._runtime.add_internal_callback(events.System, self._on_system)
        self._runtime.add_internal_callback(events.ServerId, self._on_server_id)

    def _on_waiting_for_session(self, _):  # pragma: no cover
        self._runtime.set_state(WsState.OPEN)

    def _on_authentication_status(self, event: events.AuthenticationStatus):
        if event.authenticated is False and self._runtime.is_authenticated():
            _LOGGER.error(f'{self}: Status unauthenticated: {event}')
        elif event.competing is True:
            _LOGGER.error(f'{self}: Authentication competing: {event}')

        if event.authenticated is not None:
            self._runtime.set_authenticated(event.authenticated)

    def _on_system(self, event: events.System):
        if event.data.get('topic') == 'tic':
            self._tic_message = event.data

        if 'hb' in event.data:
            self._runtime.set_last_heartbeat(int(event.data['hb']) / 1000)

    def _on_server_id(self, event: events.ServerId):
        self._conid_server_id_pairs[event.target_event_type][event.conid] = event.server_id
        for subscription in self._mh_subscriptions:
            if subscription.event_type == event.target_event_type and subscription.conid == event.conid and not subscription.has_server_id():
                subscription.set_server_id(event.server_id)

    def _get_cookie(self):
        status = self._ibkr_client.tickle()
        session_id = status.data['session']
        if self._use_oauth:
            return f'api={session_id}'
        payload = {'session': session_id}
        return f'api={json.dumps(payload)}'

    def _get_header(self):
        return {'User-Agent': 'ClientPortalGW/1'} if self._use_oauth else None

    def _get_authenticated(self):
        sts = self._ibkr_client.authentication_status().data
        return sts['authenticated']

    def start(self) -> bool:  # pragma: no cover
        """
        Start the WebSocket client.

        Returns:
            bool: True if start was successful, False otherwise.
        """
        return self._runtime.start()

    def shutdown(self) -> bool:  # pragma: no cover
        """
        Shutdown the WebSocket client.

        Returns:
            bool: True if shutdown was successful, False otherwise.
        """
        return self._runtime.stop()

    def hard_reset(self):  # pragma: no cover
        """
        Perform a hard reset of the WebSocket client, stopping and restarting the runtime.
        """
        self._runtime.hard_reset()

    def reset_websocket_app(self):  # pragma: no cover
        """
        Reset the underlying WebSocketApp.
        """
        self._runtime.reset_websocket_app()

    def subscribe(self, subscription: Subscription) -> SubscriptionHandle:
        """
        Subscribe to a WebSocket topic.

        Args:
            subscription (Subscription): Subscription object specifying the topic and parameters.

        Returns:
            SubscriptionHandle: Handle to track subscription status and wait for completion.

        Note:
            - This method is non-blocking and idempotent.
        """
        if isinstance(subscription, MarketHistorySubscription):
            self._mh_subscriptions.append(subscription)
        return self._runtime.subscription_controller.subscribe(subscription)

    def unsubscribe(self, subscription: Subscription) -> SubscriptionHandle:
        """
        Unsubscribe from a WebSocket topic.

        Args:
            subscription (Subscription): Subscription object to unsubscribe from.

        Returns:
            SubscriptionHandle: Handle to track unsubscription status.

        Note:
            - This method is non-blocking and idempotent.
        """
        if isinstance(subscription, MarketHistorySubscription):
            self._handle_mh_unsubscription(subscription)
        return self._runtime.subscription_controller.unsubscribe(subscription)

    def get_binding_status(self, binding_key: str) -> BindingStatus:  # pragma: no cover
        """
        Get the status of a subscription binding.

        Args:
            binding_key (str): Unique identifier for the subscription binding.

        Returns:
            BindingStatus: Current status of the binding.
        """
        return self._runtime.subscription_controller.get_status(binding_key)

    def get_server_id(self, event_type: Type[IbkrTopicEvent], conid: str) -> str:  # pragma: no cover
        """
        Get the server ID for a given event type and contract ID.

        This is primarily used for Market History subscriptions.

        Args:
            event_type (Type[IbkrTopicEvent]): The event type to look up.
            conid (str): Contract ID.

        Returns:
            str: The server ID associated with the event type and contract ID.
        """
        return self._conid_server_id_pairs[event_type][conid]

    def _handle_mh_unsubscription(self, subscription: MarketHistorySubscription):
        if subscription.has_server_id():
            return
        server_id = self._conid_server_id_pairs.get(subscription.event_type, {}).get(subscription.conid)
        if server_id is None:
            raise RuntimeError(
                f'{self}: Unsubscribing from market history for conid={subscription.conid!r} without server_id. Could not find server_id in memory. Ensure at least one MarketHistory event is received before unsubscribing.'
            )

        _LOGGER.warning(
            f'{self}: Unsubscribing from market history for conid={subscription.conid!r} without server_id. Setting from memory: {server_id!r}. '
            f'Unsubscribe using the same Subscription instance that was used for subscribing to avoid this warning, '
            f'or set it manually before calling unsubscribe by using '
            f'`subscription.set_server_id(ibkr_ws_client.get_server_id(IbkrWsKey.MARKET_HISTORY, conid))`'
        )
        subscription.set_server_id(server_id)

    @ensure_list_arg('subscription_handles')
    def wait_all(
        self,
        subscription_handles: OneOrMany[SubscriptionHandle],
        timeout_each: float | None = None,
    ) -> List[SubscriptionHandle]:
        """
        Wait for multiple subscription handles to complete.

        Returns an empty list if all handles completed successfully.

        Args:
            subscription_handles (OneOrMany[SubscriptionHandle]): Single handle or list of handles to wait for.
            timeout_each (float | None): Maximum time to wait for each handle in seconds.
                If None, waits indefinitely for each handle.

        Returns:
            List[SubscriptionHandle]: Handles that failed to complete within their
                individual timeout.
        """
        failed = []
        for subscription_handle in subscription_handles:
            if not subscription_handle.wait(timeout_each):
                failed.append(subscription_handle)
        return failed

    def is_running(self) -> bool:  # pragma: no cover
        """
        Check if the WebSocket runtime is running.

        Returns:
            bool: True if runtime is running, False otherwise.
        """
        return self._runtime.is_running()

    def get_state(self) -> WsState:  # pragma: no cover
        """
        Get the current state of the WebSocket client.

        Returns:
            WsState: Current runtime state.
        """
        return self._runtime.get_state()

    def is_ready(self) -> bool:  # pragma: no cover
        return self._runtime.is_ready()

    def is_authenticated(self) -> bool:  # pragma: no cover
        """
        Check if the WebSocket connection is authenticated.

        Returns:
            bool: True if authenticated, False otherwise.
        """
        return self._runtime.is_authenticated()

    def is_subscription_active(self, binding_key: str) -> Optional[bool]:  # pragma: no cover
        """
        Check if a subscription binding is currently active.

        Args:
            binding_key (str): Unique identifier for the subscription binding.

        Returns:
            Optional[bool]: True if active, False if inactive, None if binding not found.
        """
        return self._runtime.subscription_controller.is_subscription_active(binding_key)

    def tic(self):
        """
        Sends a tic request to the IBKR WebSocket server and waits for the response.

        This method sends a 'tic' message to the server and waits for the server to update
        the internal tic message with a new timestamp. It uses the 'lastAccessed' field
        to detect when a fresh response has been received.

        Returns:
            dict: The tic message dictionary containing server response data, or None if
                  the send operation failed or the response timed out.
        """
        ts = self._tic_message.get('lastAccessed', 0)
        ret = self._runtime.send('tic')

        if not ret:
            return None

        def ts_changed():
            return self._tic_message.get('lastAccessed', 0) != ts

        if not wait_until(ts_changed, timeout=5):
            _LOGGER.error(f'tic timeout, ts={ts}')
            return None

        return self._tic_message

    def __str__(self):  # pragma: no cover
        return f'{self.__class__.__qualname__}()'
