from queue import Queue

from ibind import WsState, events
from ibind.support.logs import project_logger
from ibind.support.py_utils import exception_to_string, OneOrMany
from ibind.ws_v2._ws_events import WsEvent, Router
from ibind.ws_v2.runtime.ws_emitter import WsEmitter
from ibind.ws_v2.runtime.ws_state_manager import WsStateManager
from ibind.ws_v2.ws_subscriptions import SubscriptionController
from ibind.ws_v2.ws_transport import TransportEvent, TransportOpened, TransportReconnect, TransportClosed, TransportError, TransportMessage

_LOGGER = project_logger('ibkr_ws_client')
_MAX_TRANSPORT_EVENT_RETRIES = 5


class WsEventHandler:
    """
    Handles transport events and routes them to appropriate handlers.

    Processes transport events from a queue, routes messages through a router,
    and emits domain events to subscribers. Manages state transitions and handles
    connection lifecycle events (open, reconnect, close, error).
    """

    def __init__(
        self,
        state_manager: WsStateManager,
        router: Router,
        subscription_controller: SubscriptionController,
        emitter: WsEmitter,
    ):
        self._state_manager = state_manager
        self._router = router
        self._subscription_controller = subscription_controller
        self._emitter = emitter

        # TODO: add queue size limits
        self._transport_queue = Queue()

    def put(self, te: TransportEvent):  # pragma: no cover
        """
        Add a transport event to the processing queue.

        Args:
            te (TransportEvent): The transport event to queue.
        """
        self._transport_queue.put(te)

    def process_transport_queue(self):
        """
        Process all queued transport events in chronological order.

        Dequeues up to 1000 events, sorts them by received_at timestamp, and
        processes each. Events that raise exceptions are retried up to
        _MAX_TRANSPORT_EVENT_RETRIES times before being dropped.
        """
        retry_events = []
        current_events = []
        while not self._transport_queue.empty() and len(current_events) < 1000:
            te = self._transport_queue.get()
            current_events.append(te)

        sorted_events = sorted(current_events, key=lambda te: te.received_at)
        for te in sorted_events:
            try:
                self._handle_transport_event(te)
            except Exception as e:
                _LOGGER.error(f'{self}: Exception processing transport event {te}: {exception_to_string(e)}')
                te.add_attempt()
                if te.get_attempt() > _MAX_TRANSPORT_EVENT_RETRIES:
                    _LOGGER.error(f'{self}: Max retries ({_MAX_TRANSPORT_EVENT_RETRIES}) reached for transport event {te}, dropping event.')
                    continue
                retry_events.append(te)

        for event in retry_events:
            self._transport_queue.put(event)

    def _handle_transport_event(self, transport_event: TransportEvent):
        """
        Dispatch a transport event to the appropriate handler.

        Args:
            transport_event (TransportEvent): The transport event to handle.
        """
        if isinstance(transport_event, TransportOpened):
            self._handle_on_open()
        elif isinstance(transport_event, TransportReconnect):
            self._handle_on_reconnect()
        elif isinstance(transport_event, TransportClosed):
            self._handle_on_close(transport_event.close_status_code, transport_event.close_msg)
        elif isinstance(transport_event, TransportError):
            self._handle_on_error(transport_event.exception)
        elif isinstance(transport_event, TransportMessage):
            self._handle_on_message(transport_event.message)
        else:
            _LOGGER.error(f'{self}: Unknown event type: {type(transport_event)}: {transport_event}')

    def _handle_on_message(self, message):
        """
        Route a message and emit resulting events to subscribers.

        Routes the message through the router. If router returns None, skips
        processing. Normalises single events to a list, then observes each
        event through the subscription controller and emits it. Continues
        emitting even if subscription observation fails.

        Args:
            message: The message to route and process.
        """
        events: OneOrMany[WsEvent] = self._router.route(message)

        # Router decided to skip this message
        if events is None:
            return

        # Handle both lists and individual events
        if not isinstance(events, list) and isinstance(events, WsEvent):
            events = [events]

        # Propagate events to the sink
        for event in events:
            try:
                self._subscription_controller.observe(event)
            except Exception as e:
                _LOGGER.error(f'{self}: Exception observing subscription for {event}: {exception_to_string(e)}')

            self._emitter.emit(event)

    def _handle_on_open(self):  # pragma: no cover
        """
        Handle connection opened event.

        Sets the state to OPEN and logs the event.
        """
        self._state_manager.set_state(WsState.OPEN)
        _LOGGER.info(f'{self}: Connection open')

    def _handle_on_reconnect(self):  # pragma: no cover
        """
        Handle connection reconnected event.

        Sets the state to OPEN and logs the event.
        """
        self._state_manager.set_state(WsState.OPEN)
        _LOGGER.info(f'{self}: Connection reopened')

    def _handle_on_error(self, exception: Exception):
        """
        Handle connection error event.

        Logs the error and emits a WsError event. Sets state to DEGRADED for
        specific connection errors (lost connection or refused connection).

        Args:
            exception (Exception): The exception that occurred.
        """
        _LOGGER.error(f'{self}: Connection error: {exception}')
        previous_state = self._state_manager.get_state()
        if str(exception) in ['Connection to remote host was lost.', 'No connection could be made because the target machine actively refused it']:
            self._state_manager.set_state(WsState.DEGRADED)
            current_state = WsState.DEGRADED
        else:
            current_state = previous_state
        self._emitter.emit(events.WsError(error=exception, previous_state=previous_state, current_state=current_state))

    def _handle_on_close(self, close_status_code, close_msg):
        """
        Handle connection closed event.

        Clears the last heartbeat, sets state to CLOSED, and emits a WsClose
        event. Logs gracefully if state is STOPPING, otherwise logs as
        unexpected close. Logs error details if close_status_code or close_msg
        is provided.

        Args:
            close_status_code: WebSocket close status code, if any.
            close_msg: WebSocket close message (str or bytes), if any.
        """
        self._state_manager.last_heartbeat = None

        previous_state = self._state_manager.get_state()

        if previous_state != WsState.STOPPING:
            _LOGGER.info(f'{self}: Connection closed')
        else:
            _LOGGER.info(f'{self}: Connection gracefully closed')

        if close_status_code is not None or close_msg is not None:  # this means an error
            try:
                msg = close_msg.decode('utf-8')
            except AttributeError:
                msg = close_msg

            _LOGGER.error(f'{self}: on_close error: {close_status_code} | {msg}')

        self._state_manager.set_state(WsState.CLOSED)
        self._emitter.emit(
            events.WsClose(close_status_code=close_status_code, close_msg=close_msg, previous_state=previous_state, current_state=WsState.CLOSED)
        )

    def __str__(self):  # pragma: no cover
        return f'{self.__class__.__qualname__}()'
