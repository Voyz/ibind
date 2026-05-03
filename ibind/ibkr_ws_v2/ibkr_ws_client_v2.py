import json
from collections import defaultdict
from typing import Union, List, Dict

import var
from base.queue_controller import QueueController
from ibind import IbkrClient, IbkrWsKey
from ibkr_ws_v2 import ibkr_events
from ibkr_ws_v2.ibkr_router import IbkrRouter
from ibkr_ws_v2.ibkr_subscriptions import IbkrSubscriptionResolver, MarketHistorySubscription
from support.logs import project_logger
from ws_v2.events import EventSink, LogSink, CallbackSink, CompositeSink, Router, AsyncSink
from ws_v2.subscriptions import Subscription, SubscriptionResolver, SubscriptionHandle
from ws_v2.ws_runtime import WsRuntime, WsState

_LOGGER = project_logger('websocket')

_DEFAULT_CYCLE_INTERVAL = 0.25


class IbkrWsClientV2():
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
        recreate_subscriptions_on_reconnect: bool = True,
        sink: EventSink = None,
        router: Router = None,
        subscription_resolver: SubscriptionResolver = None,
        synchronous_output_events: bool = False,
    ):
        self._account_id = account_id

        url = var.IBIND_OAUTH1A_WS_URL if url is None and use_oauth else url

        if url is None:
            url = f'wss://{host}:{port}{base_route}'

        if use_oauth:
            if access_token is None:
                raise ValueError(
                    'OAuth access token not found. Please set IBIND_OAUTH1A_ACCESS_TOKEN environment variable or provide it as `access_token` argument.'
                )
            url += f'?oauth_token={access_token}'

        if ibkr_client is None:
            ibkr_client = IbkrClient(account_id=account_id, host=host, port=port, cacert=cacert, use_oauth=use_oauth)

        self._ibkr_client = ibkr_client
        self._use_oauth = use_oauth
        self._recreate_subscriptions_on_reconnect = recreate_subscriptions_on_reconnect

        self._queue_controller = QueueController[IbkrWsKey]()
        self._queue_controller.register_queues(list(IbkrWsKey))

        if sink is None:
            # self._queue_controller.register_queues(['CLIENT_INTERNAL', 'IBKR'])
            # sink = QueueSink(queue_controller=self._queue_controller)

            sink = LogSink()
            # sink = NoopSink()

        self._internal_sink = CallbackSink()
        self._register_internal_callbacks()

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
            ready_state=WsState.AUTHENTICATED,
            cacert=cacert,
            sink=sink,
            internal_sink=self._internal_sink,
            router=router,
            subscription_resolver=subscription_resolver,
            get_cookie=self._get_cookie,
            get_header=self._get_header,
        )

        self._mh_subscriptions: List[MarketHistorySubscription] = []
        self._conid_server_id_pairs: Dict[IbkrWsKey, Dict[str, str]] = defaultdict(dict)

    def _register_internal_callbacks(self):
        self._internal_sink.on(ibkr_events.AuthenticationStatus, self._on_authentication_status)
        self._internal_sink.on(ibkr_events.WaitingForSession, self._set_unauthenticated)
        self._internal_sink.on(ibkr_events.System, self._on_system)
        self._internal_sink.on(ibkr_events.ServerId, self._on_server_id)

    def _set_unauthenticated(self, _):
        self._runtime.set_authenticated(False)

    def _on_authentication_status(self, event: ibkr_events.AuthenticationStatus):
        if event.authenticated is False:
            _LOGGER.error(f'{self}: Status unauthenticated: {event}')
        elif event.competing is True:
            _LOGGER.error(f'{self}: Authentication competing: {event}')

        self._runtime.set_authenticated(event.authenticated)

    def _on_system(self, event: ibkr_events.System):
        if 'hb' in event.data:
            self._runtime.set_last_heartbeat(int(event.data['hb']) / 1000)

    def _on_server_id(self, event: ibkr_events.ServerId):
        self._conid_server_id_pairs[event.target_key][event.conid] = event.server_id
        for subscription in self._mh_subscriptions:
            if subscription.key == event.target_key and subscription.conid == event.conid and not subscription.has_server_id():
                subscription.set_server_id(event.server_id)

    def _get_cookie(self):
        # try:
        status = self._ibkr_client.tickle()
        # except TimeoutError as e:
        #     if 'Reached max retries' in str(e):
        #         _LOGGER.warning(f'{self}: Acquiring session cookie timed out, connection to the Gateway may be broken.')
        #         return None
        #     raise
        # except ExternalBrokerError:
        #     _LOGGER.warning(f'{self}: Acquiring session cookie failed, connection to the Gateway may be broken.')
        #     return None
        session_id = status.data['session']
        if self._use_oauth:
            return f'api={session_id}'
        payload = {'session': session_id}
        return f'api={json.dumps(payload)}'

    def _get_header(self):
        return {'User-Agent': 'ClientPortalGW/1'} if self._use_oauth else None

    def start(self):
        self._runtime.start()

    def shutdown(self):
        self._runtime.stop()

    def hard_reset(self):
        self._runtime.hard_reset()

    def subscribe(self, subscription: Subscription) -> SubscriptionHandle:
        if isinstance(subscription, MarketHistorySubscription):
            self._mh_subscriptions.append(subscription)
        return self._runtime.subscription_controller.subscribe(subscription)

    def unsubscribe(self, subscription: Subscription) -> SubscriptionHandle:
        if isinstance(subscription, MarketHistorySubscription):
            self._handle_mh_unsubscription(subscription)
        return self._runtime.subscription_controller.unsubscribe(subscription)

    def get_server_id(self, key: IbkrWsKey, conid: str) -> str:
        return self._conid_server_id_pairs[key][conid]

    def _handle_mh_unsubscription(self, subscription: MarketHistorySubscription):
        if subscription.has_server_id():
            return
        server_id = self._conid_server_id_pairs.get(subscription.key, {}).get(subscription.conid)
        if server_id is None:
            raise RuntimeError(f'{self}: Unsubscribing from market history for conid={subscription.conid!r} without server_id. Could not find server_id in memory. Ensure at least one MarketHistory event is received before unsubscribing.')

        _LOGGER.warning(
            f'{self}: Unsubscribing from market history for conid={subscription.conid!r} without server_id. Setting from memory: {server_id!r}. '
            f'Unsubscribe using the same Subscription instance that was used for subscribing to avoid this warning, '
            f'or set it manually before calling unsubscribe by using '
            f'`subscription.set_server_id(ibkr_ws_client.get_server_id(IbkrWsKey.MARKET_HISTORY, conid))`'
        )
        subscription.set_server_id(server_id)

    def is_running(self) -> bool:
        return self._runtime.is_running()

    def __str__(self):
        return f'{self.__class__.__qualname__}()'
