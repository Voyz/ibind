import json
from typing import Union

import var
from ibind import ExternalBrokerError, IbkrClient
from ibkr_ws_v2 import ibkr_events
from ibkr_ws_v2.ibkr_router import IbkrRouter
from ibkr_ws_v2.ibkr_subscriptions import IbkrSubscriptionResolver
from support.logs import project_logger
from ws_v2 import events
from ws_v2.events import EventSink, LogSink, CallbackSink, CompositeSink, Router, NoopSink
from ws_v2.subscriptions import Subscription, SubscriptionResolver, SubscriptionHandle
from ws_v2.ws_runtime import WsRuntime, WsState

_LOGGER = project_logger(__file__)

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

        if sink is None:
            # self._queue_controller = QueueController[IbkrWsKey]()
            # self._queue_controller.register_queues(['CLIENT_INTERNAL', 'IBKR'])
            # sink = QueueSink(queue_controller=self._queue_controller)

            sink = LogSink()
            # sink = NoopSink()

        self._internal_sink = CallbackSink()
        self._register_internal_callbacks()
        sink = CompositeSink(self._internal_sink, sink)

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
            router=router,
            subscription_resolver=subscription_resolver,
            get_cookie=self._get_cookie,
            get_header=self._get_header,
        )

    def _register_internal_callbacks(self):
        self._internal_sink.on(ibkr_events.AuthenticationStatus, self._on_authentication_status)
        self._internal_sink.on(ibkr_events.WaitingForSession, self._set_unauthenticated)
        self._internal_sink.on(ibkr_events.System, self._on_system)
        # self._internal_sink.on(events.WsReconnect, self._on_open)
        # self._internal_sink.on(events.WsOpen, self._on_open)

    def _on_open(self, event: events.WsOpen):
        _LOGGER.info(f'{self}: WSA opened, cookie: {self._get_cookie()}')

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
        return self._runtime.subscription_controller.subscribe(subscription)

    def unsubscribe(self, subscription: Subscription) -> SubscriptionHandle:
        return self._runtime.subscription_controller.unsubscribe(subscription)

    def is_running(self) -> bool:
        return self._runtime.is_running()

    def __str__(self):
        return f'{self.__class__.__qualname__}()'