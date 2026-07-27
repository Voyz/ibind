import json
import ssl
import time
import warnings
from pathlib import Path
from typing import Union, List, Dict, Callable

from ibind.support.logs import project_logger
from ibind.support.py_utils import noop
from ibind import events
from ibind.ws_v2._ws_events import EventSink, Router, CallbackSink, WsEvent, T, AsyncSink
from ibind.ws_v2.runtime.ws_emitter import WsEmitter
from ibind.ws_v2.runtime.ws_event_handler import WsEventHandler
from ibind.ws_v2.runtime.ws_health_monitor import WsHealthMonitor
from ibind.ws_v2.runtime.ws_lifecycle import WsLifecycle
from ibind.ws_v2.runtime.ws_runtime_worker import WsRuntimeWorker
from ibind.ws_v2.ws_subscriptions import SubscriptionController, SubscriptionResolver
from ibind.ws_v2.runtime.ws_state_manager import WsStateManager, WsState
from ibind.ws_v2.ws_transport import (
    WsTransport,
    TransportEvent,
)

_LOGGER = project_logger('ibkr_ws_client')

_DEFAULT_TIMEOUT = 5


def make_sslopt(cacert: Union[str, bool]):
    if not (cacert is False or Path(cacert).exists()):
        raise ValueError(f'Cacert must be a valid Path or False, found: {cacert}')

    if cacert is None or not cacert:
        return {'cert_reqs': ssl.CERT_NONE}
    else:
        return {'ca_certs': cacert}


class WsRuntime:
    def __init__(
        self,
        url: str,
        cycle_interval: float,
        sink: EventSink,
        # internal_sink: CallbackSink,
        router: Router,
        subscription_resolver: SubscriptionResolver,
        cacert: Union[str, bool] = False,
        connection_timeout: float = _DEFAULT_TIMEOUT,
        reconnect_timeout: float | None = _DEFAULT_TIMEOUT,
        max_ping_interval: float = 20,
        get_cookie: Callable = noop,
        get_header: Callable = noop,
        get_authenticated: Callable = noop,
    ):
        self._sink = sink
        self._internal_sink = CallbackSink()
        self._register_internal_callbacks()

        self._state_manager = WsStateManager(on_state_change=self._on_state_change)

        sslopt = make_sslopt(cacert)

        self._emitter = WsEmitter(internal_sink=self._internal_sink, sink=sink)

        self.subscription_controller = SubscriptionController(
            send_payload=self.send,
            emitter=self._emitter,
            subscription_resolver=subscription_resolver,
        )
        self._event_handler = WsEventHandler(
            state_manager=self._state_manager,
            router=router,
            subscription_controller=self.subscription_controller,
            emitter=self._emitter,
        )

        self._transport = WsTransport(
            url=url,
            event_callback=self._transport_callback,
            sslopt=sslopt,
            get_cookie=get_cookie,
            get_header=get_header,
            max_ping_interval=max_ping_interval,
            connection_timeout=connection_timeout,
            reconnect_timeout=reconnect_timeout,
        )

        self._health_monitor = WsHealthMonitor(
            transport=self._transport,
            state_manager=self._state_manager,
            max_ping_interval=max_ping_interval,
            get_authenticated=get_authenticated,
            reconnect_timeout=reconnect_timeout,
        )

        self._runtime_worker = WsRuntimeWorker(
            state_manager=self._state_manager,
            subscription_controller=self.subscription_controller,
            event_handler=self._event_handler,
            health_monitor=self._health_monitor,
            cycle_interval=cycle_interval,
        )

        self._lifecycle = WsLifecycle(
            state_manager=self._state_manager,
            connection_timeout=connection_timeout,
            transport=self._transport,
            runtime_worker=self._runtime_worker,
        )

    def _register_internal_callbacks(self):
        self.add_internal_callback(events.WsStarting, self._on_starting)
        self.add_internal_callback(events.WsStopped, self._on_stopped)

    def add_internal_callback(self, event_type: type[WsEvent], callback: Callable[[T], None]) -> None:
        self._internal_sink.on(event_type, callback)

    def _on_starting(self, _):
        if isinstance(self._sink, AsyncSink):
            self._sink.start()

    def _on_stopped(self, event):
        if isinstance(self._sink, AsyncSink):
            self._sink.emit(event)
            self._sink.stop()

    def _on_state_change(self, previous_state: WsState, state: WsState):
        if state == previous_state:
            return

        _LOGGER.debug(f'{self}: {previous_state} -> {state}')

        if state == WsState.STOPPING:
            self.subscription_controller.invalidate_active_subscriptions()

        elif previous_state == WsState.AUTHENTICATED:
            self.subscription_controller.invalidate_subscriptions()

        elif state == WsState.DEGRADED:
            self.subscription_controller.invalidate_subscriptions()

        elif state == WsState.CLOSED and previous_state != WsState.STOPPING:
            self.subscription_controller.invalidate_subscriptions()

        if state == WsState.STARTING:
            self._emitter.emit(events.WsStarting(previous_state=previous_state, current_state=state))

        elif state == WsState.OPEN:
            self._state_manager.last_heartbeat = None
            self._emitter.emit(events.WsOpen(previous_state=previous_state, current_state=state))

        elif state == WsState.AUTHENTICATED:
            self._emitter.emit(events.WsAuthenticated(previous_state=previous_state, current_state=state))
            self._emitter.emit(events.WsReady(previous_state=previous_state, current_state=state))
            self._state_manager.last_heartbeat = time.time()
            _LOGGER.info(f'{self}: Websocket ready, setting last_heartbeat to {self._state_manager.last_heartbeat}')

        elif state == WsState.STOPPING:
            self._emitter.emit(events.WsStopping(previous_state=previous_state, current_state=state))

        elif state == WsState.DEGRADED:
            self._emitter.emit(events.WsDegraded(previous_state=previous_state, current_state=state))

        elif state == WsState.STOPPED:
            self._emitter.emit(events.WsStopped(previous_state=previous_state, current_state=state))

    def set_authenticated(self, value):
        if not value and self._state_manager.get_state() == WsState.AUTHENTICATED:
            self._state_manager.set_state(WsState.OPEN)
        elif value and self._state_manager.get_state() == WsState.OPEN:
            self._state_manager.set_state(WsState.AUTHENTICATED)

    def set_state(self, value):  # pragma: no cover
        self._state_manager.set_state(value)

    def get_state(self) -> WsState:  # pragma: no cover
        return self._state_manager.get_state()

    def is_ready(self) -> bool:  # pragma: no cover
        warnings.warn('is_ready is deprecated, use is_authenticated instead', DeprecationWarning)
        return self.is_authenticated()

    def is_authenticated(self) -> bool:  # pragma: no cover
        return self._state_manager.is_authenticated()

    def start(self) -> bool:  # pragma: no cover
        return self._lifecycle.start()

    def stop(self) -> bool:  # pragma: no cover
        return self._lifecycle.stop()

    def hard_reset(self):  # pragma: no cover
        self._lifecycle.hard_reset()

    def send(self, payload: str) -> bool:
        if not self._state_manager.is_authenticated():
            _LOGGER.error(
                f'{self}: State must be {WsState.AUTHENTICATED.value} before sending payloads, found {self._state_manager.get_state().value}'
            )
            return False

        _LOGGER.info(f'{self}: Sending payload: {payload}')

        return self._transport.send(payload)

    def send_json(self, payload: Union[List, Dict]) -> bool:  # pragma: no cover
        return self.send(json.dumps(payload))

    def is_running(self) -> bool:  # pragma: no cover
        return self._runtime_worker.running

    def set_last_heartbeat(self, value: float):  # pragma: no cover
        self._state_manager.last_heartbeat = value

    def reset_websocket_app(self):  # pragma: no cover
        self._lifecycle.reset_websocket_app()

    def _transport_callback(self, te: TransportEvent):  # pragma: no cover
        self._event_handler.put(te)
        self._runtime_worker.request_cycle()

    def __str__(self):  # pragma: no cover
        return f'{self.__class__.__qualname__}({self._state_manager.get_state()})'
