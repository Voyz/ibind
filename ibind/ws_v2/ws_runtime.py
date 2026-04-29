import json
import ssl
import threading
from pathlib import Path
from queue import Queue
from threading import Thread, Event
from typing import Union, List, Dict, Callable, Literal

from websocket import WebSocketApp, STATUS_UNEXPECTED_CONDITION

from support.logs import project_logger
from support.py_utils import wait_until, tname, VerboseEnum, exception_to_string, TimeoutLock
from ws_v2 import events
from ws_v2.events import WsEvent, EventSink, Router
from ws_v2.subscription_controller import SubscriptionController, SubscriptionResolver
from ws_v2.ws_transport import WsTransport, TransportEvent, TransportOpened, TransportClosed, TransportError, TransportMessage, TransportCritical, TransportReconnect

_LOGGER = project_logger(__file__)

_NOOP = lambda: None

_DEFAULT_TIMEOUT = 5


class WsState(VerboseEnum):
    STOPPED = 'STOPPED',
    STARTING = 'STARTING',
    CONNECTING = 'CONNECTING',
    OPEN = 'OPEN',
    AUTHENTICATED = 'AUTHENTICATED',
    CLOSED = 'CLOSED',
    DEGRADED = 'DEGRADED',
    RECONNECTING = 'RECONNECTING',
    STOPPING = 'STOPPING',


class WsRuntime():
    def __init__(
        self,
        url: str,
        cycle_interval: float,
        sink: EventSink,
        router: Router,
        subscription_resolver: SubscriptionResolver,
        ready_state: Literal[WsState.OPEN, WsState.AUTHENTICATED] = WsState.OPEN,
        cacert: Union[str, bool] = False,
        connection_timeout: float = _DEFAULT_TIMEOUT,
        restart_on_close: bool = True,
        restart_on_critical: bool = True,
        get_cookie: Callable = _NOOP,
        get_header: Callable = _NOOP
    ):
        self._url = url
        self._cycle_interval = cycle_interval
        self._sink = sink
        self._router = router
        self._subscription_resolver = subscription_resolver
        self._ready_state = ready_state
        self._connection_timeout = connection_timeout
        self._restart_on_close = restart_on_close
        self._restart_on_critical = restart_on_critical

        self._state = WsState.STOPPED
        self._authenticated = False

        self._transport_thread = None
        self._runtime_thread = None
        self._transport_queue = Queue()
        self._wait_event = Event()

        self._state_lock = TimeoutLock(60)

        if not (cacert is False or Path(cacert).exists()):
            raise ValueError(f'{self}: cacert must be a valid Path or False')

        if cacert is None or not cacert:
            sslopt = {'cert_reqs': ssl.CERT_NONE}
        else:
            sslopt = {'ca_certs': cacert}

        self._transport = WsTransport(
            url=url,
            event_callback=self._transport_callback,
            sslopt=sslopt,
            get_cookie=get_cookie,
            get_header=get_header,
        )

        self.subscription_controller = SubscriptionController(send_payload=self.send, subscription_resolver=self._subscription_resolver)

    @property
    def state(self):
        _LOGGER.debug(f'{self}: State: {self._state.value}')
        with self._state_lock:
            return self._state

    @state.setter
    def state(self, value):
        _LOGGER.debug(f'{self}: {self._state.value} -> {value.value}')
        with self._state_lock:
            self._state = value

        if self._state == self._ready_state:
            self._sink.emit(events.WsReady())

    def set_authenticated(self, value: bool):
        if value != self._authenticated:
            _LOGGER.debug(f'{self}: Authenticated: {value}')
        self._authenticated = value

        if value and self._state == WsState.OPEN:
            self._sink.emit(events.WsAuthenticated())
            self.state = WsState.AUTHENTICATED

        if value == False:
            self.subscription_controller.invalidate_subscriptions()

    def get_authenticated(self) -> bool:
        return self._authenticated

    def _new_transport_thread(self):
        self._transport_thread = Thread(target=self._transport.connect, name='ws_transport_thread')
        self._transport_thread.daemon = True
        self._transport_thread.start()

    def _new_runtime_thread(self):
        self._runtime_thread = Thread(target=self._cycle, name='ws_runtime_thread')
        self._runtime_thread.daemon = True
        self._runtime_thread.start()

    def start(self):
        if self.state != WsState.STOPPED:
            return

        if self._runtime_thread is not None and self._runtime_thread.is_alive():
            _LOGGER.error(f'{self}: Runtime thread is not stopped')
            return

        self.state = WsState.STARTING
        self._running = True

        self._new_runtime_thread()

        connection_success = wait_until(lambda: self._state == self._ready_state, f'{self}: Starting timeout', timeout=self._connection_timeout)
        return connection_success

    def stop(self):
        if self.state == WsState.STOPPED:
            return

        # wait until one more pass of the runtime thread has occurred to allow unsubscriptions to complete
        wait_until(lambda: not self._wait_event.is_set(), timeout=self._connection_timeout)
        self._wait_event.set()
        wait_until(lambda: not self._wait_event.is_set(), timeout=self._connection_timeout)

        # TODO: decide which thread should stop first - transport or runtime
        self.state = WsState.STOPPING
        try:
            self._transport.disconnect()
            self._transport_thread.join(self._connection_timeout)
        except Exception as e:
            _LOGGER.error(f'{self}: Failed to disconnect: {e}')
            # TODO: decide what to do if transport disconnect fails

        self._running = False
        self._runtime_thread.join(self._connection_timeout)

        self.state = WsState.STOPPED

    def send(self, payload: str) -> bool:
        if self._state != self._ready_state:
            _LOGGER.error(f'{self}: State must be {self._ready_state.value} before sending payloads, found {self._state.value}')
            return False

        _LOGGER.debug(f'{self}: Sending payload: {payload}')

        return self._transport.send(payload)

    def send_json(self, payload: Union[List, Dict]) -> bool:  # pragma: no cover
        return self.send(json.dumps(payload))

    def is_running(self) -> bool:
        return self._running

    def __str__(self):
        return f'{self.__class__.__qualname__}({self._state})'

    # ======================
    # == Transport Thread ==
    # ======================

    def _transport_callback(self, te: TransportEvent):
        # _LOGGER.debug(f'{self}: {te}')
        self._transport_queue.put(te)
        self._wait_event.set()

    # ======================
    # ==  Runtime Thread  ==
    # ======================

    def _maintain_transport(self):
        # Don't maintain the transport thread if we are stopping
        if self._state == WsState.STOPPING:
            return

        if self._transport_thread is None or not self._transport_thread.is_alive():
            _LOGGER.debug(f'{self}: Starting new transport thread')
            self.state = WsState.CONNECTING
            self._new_transport_thread()

    def _maintain_subscriptions(self):
        if self._state != self._ready_state:
            return

        self.subscription_controller.parse_bindings()

    def _cycle(self):
        _LOGGER.debug(f'{self}: Runtime thread started ({tname()})')
        while self._running:
            self._maintain_transport()
            self._maintain_subscriptions()

            self.process_transport_queue()

            self._wait_event.clear()
            self._wait_event.wait(self._cycle_interval)

        # final pass through the router queue to flush any remaining events
        self.process_transport_queue()
        # final pass through the subscription controller to carry out final unsubscribe events
        self.subscription_controller.parse_bindings()
        _LOGGER.debug(f'{self}: Runtime thread stopped ({tname()})')

    def process_transport_queue(self):
        while not self._transport_queue.empty():
            te = self._transport_queue.get()
            try:
                self._handle_transport_event(te)
            except Exception as e:
                _LOGGER.error(f'{self}: Exception processing transport event: {exception_to_string(e)} for {te}')

    def _handle_transport_event(self, te: TransportEvent):
        if isinstance(te, TransportOpened):
            self._handle_on_open(te.wsa)
        elif isinstance(te, TransportClosed):
            self._handle_on_close(te.wsa, te.close_status_code, te.close_msg)
        elif isinstance(te, TransportError):
            self._handle_on_error(te.wsa, te.error)
        elif isinstance(te, TransportMessage):
            self._handle_on_message(te.wsa, te.message)
        elif isinstance(te, TransportCritical):
            self._handle_on_critical(te.wsa, te.exception)
        elif isinstance(te, TransportReconnect):
            self._handle_on_reconnect(te.wsa)
        else:
            _LOGGER.error(f'{self}: Unknown event type: {type(te)}: {te}')

    def _handle_on_message(self, wsa: WebSocketApp, message):  # pragma: no cover
        events = self._router.route(message)

        # Router decided to skip this message
        if events is None:
            return

        # Handle lists and individual events
        if not isinstance(events, list) and isinstance(events, WsEvent):
            events = [events]

        # Propagate events to the sink
        for event in events:
            try:
                self.subscription_controller.observe(event)
            except Exception as e:
                _LOGGER.error(f'{self}: Exception observing subscription: {exception_to_string(e)} for {event}')

            try:
                self._sink.emit(event)
            except Exception as e:
                _LOGGER.error(f'{self}: Exception propagating event: {exception_to_string(e)} for {event}')

    def _handle_on_open(self, wsa: WebSocketApp):
        _LOGGER.info(f'{self}: Connection open')
        self.state = WsState.OPEN  ## connected = True
        self._sink.emit(events.WsOpen())

    def _handle_on_error(self, wsa: WebSocketApp, exception: Exception):  # pragma: no cover
        _LOGGER.error(f'{self}: on_error: {exception}')
        if str(exception) in ['Connection to remote host was lost.', 'No connection could be made because the target machine actively refused it']:
            self.state = WsState.DEGRADED
        self._sink.emit(events.WsError(error=exception))

    def _handle_on_reconnect(self, wsa: WebSocketApp):  # pragma: no cover
        _LOGGER.error(f'{self}: on_reconnect')
        self.set_authenticated(False)
        self.state = WsState.OPEN
        self._sink.emit(events.WsReconnect())

    def _handle_on_critical(self, wsa: WebSocketApp, exception):  # pragma: no cover
        self._sink.emit(events.WsCritical(exception=exception))
        if self._restart_on_critical:
            # TODO: following comment is not true - no restarting in on_close takes place
            # if restart_on_close is set, restarting will happen in on_close callback
            self.hard_reset(restart=not self._restart_on_close)

    def _handle_on_close(self, wsa: WebSocketApp, close_status_code, close_msg):
        _LOGGER.info(f'{self}: on_close')
        self.subscription_controller.invalidate_subscriptions()
        self._sink.emit(events.WsClose(close_status_code=close_status_code, close_msg=close_msg))
        # if we're not connected we shouldn't need to do anything
        if self.state not in [self._ready_state, WsState.OPEN, WsState.STOPPING]:  ## not self._connected:
            _LOGGER.info(f'{self}: Unexpected on_close event while not open')
            return

        if close_status_code is not None or close_msg is not None:  # this means an error
            try:
                msg = close_msg.decode('utf-8')
            except AttributeError:
                msg = close_msg

            _LOGGER.error(f'{self}: on_close error: {close_status_code} | {msg}')

        else:  # otherwise it's a close success confirmation
            _LOGGER.info(f'{self}: Connection closed')

        if self.state == WsState.STOPPING:
            _LOGGER.info(f'{self}: Gracefully closed')

        self.state = WsState.CLOSED  ## self._connected = False

        # if not self._running:  # if close happened due to shutting down, acknowledge and return
        #     _LOGGER.info(f'{self}: Gracefully closed')
        #     return

    def hard_reset(self, restart: bool = False) -> None:
        """
        Performs a hard reset of the WebSocket connection.

        This method forcefully closes the current WebSocketApp connection and optionally restarts it. It is
        used to handle scenarios where the connection is unresponsive or encounters a critical error.

        This method cannot be called from the transport thread.

        Parameters:
            restart (bool, optional): Specifies whether to restart the WebSocketApp connection after resetting.
                                      Defaults to False.

        Note:
            - Closes the current WebSocketApp connection, if any, and clears related resources.
            - If the WebSocketApp is unresponsive or cannot be closed, it will be abandoned and the connection will be reset.
            - If 'restart' is True, the method attempts to re-establish a new WebSocketApp connection after resetting.
        """
        _LOGGER.info(f'{self}: Hard reset, {restart=}, {self._wsa is None=}')

        # we want the websocket closed before reconnecting
        if self._wsa is not None:
            if not self._connected:
                # this means that we get a bad error before we could even get a connection confirmation
                # which shouldn't really happen, but if it does the original WebSocketApp is bad
                # so let's drop it anyway.
                self._wsa = None
                restart = True  # since we've abandoned the WebSocketApp, let's ensure we restart
            else:
                _LOGGER.info(f'{self}: Hard reset is closing the WebSocketApp')
                # check if current thread is the same as _transport_thread
                if threading.current_thread() == self._transport_thread:
                    raise RuntimeError(f'{self}: Hard reset called from transport thread. Ensure it is started from a separate thread')

                self._wsa.close(status=STATUS_UNEXPECTED_CONDITION)

        # ensure the websocket is closed and abandoned
        if not wait_until(lambda: self._wsa is None, f'{self}: Hard reset close timeout', timeout=self._timeout):
            _LOGGER.warning(f'{self}: Abandoning current WebSocketApp that cannot be closed: {self._wsa}')
            self._wsa = None
            restart = True  # since we've abandoned the WebSocketApp, let's ensure we restart

        # in some cases, closing the websocket will cause the restart elsewhere, therefore only closing it is enough
        if restart:
            _LOGGER.info(f'{self}: Forced restart')
            self._reconnect()

    def _reconnect(self):
        with self._reconnect_lock:
            if self.state not in [WsState.OPEN, self._ready_state]:  ## not self._has_active_connection():
                _LOGGER.info(f'{self}: Reconnecting')
                self._try_connecting()

            if self._has_active_connection():
                self._on_reconnect()