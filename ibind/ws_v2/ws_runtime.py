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
_MAX_TRANSPORT_EVENT_RETRIES = 5
_HEALTH_CHECK_INTERVAL = 10


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
        # self._url = url
        # self._cycle_interval = cycle_interval
        self._sink = sink
        # self._internal_sink = internal_sink
        # self._router = router
        # self._connection_timeout = connection_timeout
        # self._reconnect_timeout = reconnect_timeout
        # self._max_ping_interval = max_ping_interval

        # self._running = False
        # self._last_health_check = time.time()

        # self._transport_thread: Thread | None = None
        # self._runtime_thread: Thread | None = None
        # self._transport_queue = Queue()
        # self._wait_event = Event()

        self._internal_sink = CallbackSink()
        # self._register_internal_callbacks()

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

    def _on_starting(self, _):
        if isinstance(self._sink, AsyncSink):
            self._sink.start()

    def _on_stopped(self, _):
        if isinstance(self._sink, AsyncSink):
            self._sink.stop()

    def add_internal_callback(self, event_type: type[WsEvent], callback: Callable[[T], None]) -> None:
        self._internal_sink.on(event_type, callback)

    def _on_state_change(self, previous_state: WsState, state: WsState):
        if state == previous_state:
            return

        _LOGGER.debug(f'{self}: {previous_state} -> {state}')

        if state == WsState.STARTING:
            self._emitter.emit(events.WsStarting())

        elif state == WsState.OPEN:
            self._state_manager.last_heartbeat = None
            self._emitter.emit(events.WsOpen())

        elif state == WsState.AUTHENTICATED:
            self._emitter.emit(events.WsAuthenticated())
            self._websocket_ready()

        elif state not in [WsState.AUTHENTICATED, WsState.STOPPING] and previous_state == WsState.AUTHENTICATED:
            self.subscription_controller.invalidate_subscriptions()

        elif state == WsState.DEGRADED:
            self.subscription_controller.invalidate_subscriptions()
            self._emitter.emit(events.WsDegraded())

        elif state == WsState.CLOSED:
            if previous_state != WsState.STOPPING:
                self.subscription_controller.invalidate_subscriptions()

        elif state == WsState.STOPPED:
            self._emitter.emit(events.WsStopped())

    def set_authenticated(self, value):
        if not value and self._state_manager.get_state() == WsState.AUTHENTICATED:
            self._state_manager.set_state(WsState.OPEN)
        elif value and self._state_manager.get_state() == WsState.OPEN:
            self._state_manager.set_state(WsState.AUTHENTICATED)

    def _websocket_ready(self):
        self._emitter.emit(events.WsReady())
        self._state_manager.last_heartbeat = time.time()
        _LOGGER.info(f'{self}: Websocket ready, setting last_heartbeat to {self._state_manager.last_heartbeat}')

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

    # def _new_transport_thread(self):  # pragma: no cover
    #     self._transport_thread = Thread(target=self._transport.connect, name='ws_transport_thread')
    #     self._transport_thread.daemon = True
    #     self._transport_thread.start()
    #
    # def _new_runtime_thread(self):  # pragma: no cover
    #     self._runtime_thread = Thread(target=self._runtime_worker, name='ws_runtime_thread')
    #     self._runtime_thread.daemon = True
    #     self._runtime_thread.start()

    # def _stop_transport_thread(self) -> bool:
    #     try:
    #         self._transport.stop()
    #         if self._transport_thread is None:
    #             return True
    #
    #         _LOGGER.debug(f'{self}: Joining transport thread')
    #
    #         self._transport_thread.join(self._connection_timeout)
    #         is_alive = self._transport_thread.is_alive()
    #         self._transport_thread = None
    #         return not is_alive
    #     except Exception as e:
    #         _LOGGER.error(f'{self}: Failed to stop transport thread: {e}')
    #
    #     return False
    #
    # def start(self):
    #     if self.state_manager.get_state() != WsState.STOPPED:
    #         return
    #
    #     if self._runtime_thread is not None and self._runtime_thread.is_alive():
    #         _LOGGER.error(f'{self}: Runtime thread must be stopped and joined before starting')
    #         return
    #
    #     _LOGGER.info(f'{self}: Starting WebSocket runtime')
    #
    #     self.state_manager.set_state(WsState.STARTING)
    #     self._running = True
    #
    #     self._new_runtime_thread()
    #
    #     if isinstance(self._sink, AsyncSink):
    #         self._sink.start()
    #
    #     connection_success = wait_until(lambda: self.state_manager.is_authenticated(), timeout=self._connection_timeout)
    #     if not connection_success:
    #         _LOGGER.error(f'{self}: Starting timeout')
    #     return connection_success
    #
    # def stop(self):
    #     if self.state_manager.get_state() == WsState.STOPPED:
    #         return
    #
    #     if threading.current_thread() == self._runtime_thread:
    #         raise RuntimeError(f'{self}: Stopping runtime called from within runtime thread. Ensure it is called from a separate thread')
    #
    #     _LOGGER.info(f'{self}: Stopping WebSocket runtime')
    #
    #     # wait until one more pass of the runtime thread has occurred to allow unsubscriptions to complete
    #     wait_until(lambda: not self._wait_event.is_set(), timeout=self._connection_timeout)
    #     self._wait_event.set()
    #     wait_until(lambda: not self._wait_event.is_set(), timeout=self._connection_timeout)
    #
    #     self.state_manager.set_state(WsState.STOPPING)
    #     transport_thread_stopped = self._stop_transport_thread()
    #     if not transport_thread_stopped:
    #         _LOGGER.error(f'{self}: Failed to stop transport thread, abandoning...')
    #         self._transport_thread = None
    #     self._transport.set_degraded(True)
    #
    #     self._running = False
    #     if self._runtime_thread is not None:
    #         self._runtime_thread.join(self._connection_timeout)
    #
    #     if self._runtime_thread.is_alive():
    #         _LOGGER.error(f'{self}: Runtime thread failed to stop, abandoning...')
    #
    #     self._runtime_thread = None
    #
    #     if isinstance(self._sink, AsyncSink):
    #         self._sink.stop()
    #
    #     self.state_manager.set_state(WsState.STOPPED)

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

    # def hard_reset(self) -> None:
    #     _LOGGER.info(f'{self}: Hard reset')
    #
    #     if threading.current_thread() in [self._runtime_thread, self._transport_thread]:
    #         raise RuntimeError(f'{self}: Hard reset called from Runtime or Transport thread. Ensure it is called from a separate thread')
    #
    #     self.stop()
    #     self.start()
    #
    # def restart_transport(self):
    #     if threading.current_thread() == self._transport_thread:
    #         raise RuntimeError(f'{self}: Resetting transport thread called from within transport thread. Ensure it is called from a separate thread')
    #
    #     transport_thread_stopped = self._stop_transport_thread()
    #     if not transport_thread_stopped:
    #         _LOGGER.error(f'{self}: Failed to stop transport thread, abandoning...')
    #         self._transport_thread = None
    #
    #     self._transport.set_degraded(True)
    #     self._transport = self._new_transport()
    #     self._new_transport_thread()

    def reset_websocket_app(self):  # pragma: no cover
        self._lifecycle.reset_websocket_app()
        # self._transport.reset_websocket_app()

    def __str__(self):  # pragma: no cover
        return f'{self.__class__.__qualname__}({self._state_manager.get_state()})'

    # ======================
    # == Transport Thread ==
    # ======================

    def _transport_callback(self, te: TransportEvent):  # pragma: no cover
        self._event_handler.put(te)
        self._runtime_worker.request_cycle()
        # self._transport_queue.put(te)
        # self._wait_event.set()

    # ======================
    # ==  Runtime Thread  ==
    # ======================

    # def _maintain_transport(self):
    #     # Don't maintain the transport thread if we are stopping
    #     if self._state_manager.get_state() == WsState.STOPPING:
    #         return
    #
    #     if self._transport_thread is None or not self._transport_thread.is_alive():
    #         self._state_manager.set_state(WsState.CONNECTING)
    #         self._lifecycle.new_transport_thread()
    #         # self._new_transport_thread()

    # def _maintain_subscriptions(self):
    #     if not self._state_manager.is_authenticated():
    #         return
    #
    #     self.subscription_controller.reconcile_bindings()

    # def check_should_reset(self):
    #     # If WSA is not ready, we don't try to fix health
    #     if not self._transport.is_ready():
    #         return False
    #
    #     # If we're not either open or authenticated, we let WSA handle the reconnect first
    #     state = self.state_manager.get_state()
    #     if state not in [WsState.OPEN, WsState.AUTHENTICATED]:
    #         return False
    #
    #     ping_ok = self._transport.check_ping(self._max_ping_interval)
    #     if not ping_ok:
    #         _LOGGER.warning(
    #             f'{self}: Last WebSocket ping happened {self._transport.get_time_since_last_ping():.2f} seconds ago, '
    #             f'exceeding the max ping interval of {self._max_ping_interval}.'
    #         )
    #         # If we have a reconnect timeout, we let WSA handle the reconnect, otherwise let's reset the WSA
    #         return self._reconnect_timeout is None
    #
    #     heartbeat_ok = True
    #     last_heartbeat = self.state_manager.last_heartbeat
    #     if last_heartbeat is not None:
    #         diff = abs(time.time() - last_heartbeat)
    #         if diff > self._max_ping_interval:
    #             _LOGGER.warning(
    #                 f'{self}: Last heartbeat happened {diff:.2f} seconds ago, exceeding the max ping interval of {self._max_ping_interval}.'
    #             )
    #             heartbeat_ok = False
    #
    #     if not heartbeat_ok:
    #         return True
    #
    #     if not self.state_manager.is_authenticated():
    #         is_authenticated = self._get_authenticated()
    #         if is_authenticated:
    #             _LOGGER.warning(f'{self}: State is not ready while reporting authenticated={is_authenticated}')
    #             self.set_state(WsState.AUTHENTICATED)
    #             # self.set_authenticated(True)
    #             return False
    #
    #     return False
    #
    # def health_check(self) -> bool:
    #     if not self.check_should_reset():
    #         return True
    #
    #     if not self._running:  # return early if runtime got stopped in the meantime
    #         return False
    #
    #     self.set_state(WsState.DEGRADED)
    #
    #     _LOGGER.warning(f'{self}: Health check failed, resetting transport websocket')
    #     self.reset_websocket_app()
    #     return False

    # def _runtime_worker(self):
    #     _LOGGER.debug(f'{self}: Runtime thread started ({tname()})')
    #     while self._running:
    #         try:
    #             self._cycle()
    #         except ExternalBrokerError as e:
    #             _LOGGER.error(f'{self}: External error in runtime thread: {e}')
    #         except Exception as e:
    #             _LOGGER.error(f'{self}: Runtime thread exception: {exception_to_string(e)}')
    #
    #     # if not stopped or closed yet, attempt to do one last pass before the thread dies
    #     state = self._state_manager.get_state()
    #     if state not in [WsState.STOPPED, WsState.CLOSED]:
    #         # final pass through the transport queue to flush any remaining events
    #         self._event_handler._process_transport_queue()
    #         # self._process_transport_queue()
    #
    #         # final pass through the subscription controller to carry out final unsubscribe events
    #         self.subscription_controller.reconcile_bindings()
    #
    #     _LOGGER.debug(f'{self}: Runtime thread stopped ({tname()})')
    #
    # def _cycle(self):
    #     self._lifecycle.maintain_transport()
    #     self._maintain_subscriptions()
    #
    #     # self._process_transport_queue()
    #     self._event_handler._process_transport_queue()
    #
    #     if not self._health_monitor.health_ok():
    #         if not self._running:  # return early if runtime got stopped in the meantime
    #             return False
    #         _LOGGER.warning(f'{self}: Health check failed, resetting transport websocket')
    #         self.reset_websocket_app()
    #
    #     # if time.time() - self._last_health_check > _HEALTH_CHECK_INTERVAL:
    #     #     self._last_health_check = time.time()
    #     #     self.health_check()
    #
    #     self._wait_event.wait(self._cycle_interval)
    #     self._wait_event.clear()

    # def _process_transport_queue(self):
    #     retry_events = []
    #     current_events = []
    #     while not self._transport_queue.empty() and len(current_events) < 1000:
    #         te = self._transport_queue.get()
    #         current_events.append(te)
    #
    #     sorted_events = sorted(current_events, key=lambda te: te.received_at)
    #     for te in sorted_events:
    #         try:
    #             self._handle_transport_event(te)
    #         except Exception as e:
    #             _LOGGER.error(f'{self}: Exception processing transport event {te}: {exception_to_string(e)}')
    #             te.add_attempt()
    #             if te.get_attempt() > _MAX_TRANSPORT_EVENT_RETRIES:
    #                 _LOGGER.error(f'{self}: Max retries ({_MAX_TRANSPORT_EVENT_RETRIES}) reached for transport event {te}, dropping event.')
    #                 continue
    #             retry_events.append(te)
    #
    #     for event in retry_events:
    #         self._transport_queue.put(event)
    #
    # def _handle_transport_event(self, transport_event: TransportEvent):
    #     if isinstance(transport_event, TransportOpened):
    #         self._handle_on_open()
    #     elif isinstance(transport_event, TransportReconnect):
    #         self._handle_on_reconnect()
    #     elif isinstance(transport_event, TransportClosed):
    #         self._handle_on_close(transport_event.close_status_code, transport_event.close_msg)
    #     elif isinstance(transport_event, TransportError):
    #         self._handle_on_error(transport_event.exception)
    #     elif isinstance(transport_event, TransportMessage):
    #         self._handle_on_message(transport_event.message)
    #     else:
    #         _LOGGER.error(f'{self}: Unknown event type: {type(transport_event)}: {transport_event}')
    #
    # def _handle_on_message(self, message):  # pragma: no cover
    #     events: OneOrMany[WsEvent] = self._router.route(message)
    #
    #     # Router decided to skip this message
    #     if events is None:
    #         return
    #
    #     # Handle both lists and individual events
    #     if not isinstance(events, list) and isinstance(events, WsEvent):
    #         events = [events]
    #
    #     # Propagate events to the sink
    #     for event in events:
    #         try:
    #             self.subscription_controller.observe(event)
    #         except Exception as e:
    #             _LOGGER.error(f'{self}: Exception observing subscription for {event}: {exception_to_string(e)}')
    #
    #         self._emitter.emit(event)
    #
    # def _handle_on_open(self):
    #     # self.state_manager.reset_heartbeat()
    #     self._state_manager.set_state(WsState.OPEN)
    #     _LOGGER.info(f'{self}: Connection open')
    #     # self.set_authenticated(False)
    #     # self._emitter.emit(events.WsOpen())
    #
    # def _handle_on_reconnect(self):
    #     # self.state_manager.reset_heartbeat()
    #     self._state_manager.set_state(WsState.OPEN)
    #     _LOGGER.info(f'{self}: Connection reopened')
    #     # self.set_authenticated(False)
    #     # self._emitter.emit(events.WsOpen())
    #
    # def _handle_on_error(self, exception: Exception):
    #     _LOGGER.error(f'{self}: Connection error: {exception}')
    #     if str(exception) in ['Connection to remote host was lost.', 'No connection could be made because the target machine actively refused it']:
    #         self.set_state(WsState.DEGRADED)
    #         # self.set_authenticated(False)
    #     self._emitter.emit(events.WsError(error=exception))
    #
    # def _handle_on_close(self, close_status_code, close_msg):
    #     self._state_manager.reset_heartbeat()
    #
    #     if self._state_manager.get_state() != WsState.STOPPING:
    #         _LOGGER.info(f'{self}: Connection closed')
    #         # self.set_authenticated(False)
    #         self.subscription_controller.invalidate_subscriptions()
    #     else:
    #         _LOGGER.info(f'{self}: Connection gracefully closed')
    #
    #     self._state_manager.set_state(WsState.CLOSED)
    #
    #     if close_status_code is not None or close_msg is not None:  # this means an error
    #         try:
    #             msg = close_msg.decode('utf-8')
    #         except AttributeError:
    #             msg = close_msg
    #
    #         _LOGGER.error(f'{self}: on_close error: {close_status_code} | {msg}')
    #
    #     self._emitter.emit(events.WsClose(close_status_code=close_status_code, close_msg=close_msg))

    # def _emit(self, event: WsEvent):
    #     try:
    #         self._internal_sink.emit(event)
    #     except Exception as e:
    #         _LOGGER.error(f'{self}: Internal sink exception for {event}: {exception_to_string(e)}')
    #
    #     try:
    #         self._sink.emit(event)
    #     except Exception as e:
    #         _LOGGER.error(f'{self}: External sink exception for {event}: {exception_to_string(e)}')
