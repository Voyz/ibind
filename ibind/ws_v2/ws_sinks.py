import threading
from threading import Thread, Event

from _queue import Empty
from queue import Queue, Full
from typing import Protocol, TypeVar, Dict, List, Callable, Any

from ibind import var, QueueAccessor
from ibind.support.py_utils import exception_to_string, tname
from ibind.ws_v2._ws_events import WsEvent, _LOGGER


class EventSink(Protocol):  # pragma: no cover
    """Protocol for objects that can receive and process WebSocket events."""

    def emit(self, event: 'WsEvent') -> None:
        pass


class LogSink:  # pragma: no cover
    """Sink that logs events using the project logger."""

    def emit(self, event: WsEvent) -> None:
        _LOGGER.info(event)


class NoopSink:  # pragma: no cover
    """Sink that discards all events without processing."""

    def emit(self, event: WsEvent) -> None:
        pass


T = TypeVar('T', bound=WsEvent)


class CallbackSink:
    """
    Sink that invokes registered callbacks for specific event types.

    Callbacks are registered per event type and invoked when matching events are emitted.
    Exceptions from callbacks are logged but do not propagate.
    """

    def __init__(self):
        self._callbacks: Dict[type[WsEvent], List[Callable[[WsEvent], None]]] = {}
        self._callbacks_lock = threading.RLock()

    def on(self, event_type: type[WsEvent], callback: Callable[[T], None]) -> None:
        """
        Register a callback for a specific event type.

        Args:
            event_type (type[WsEvent]): The event type to listen for.
            callback (Callable): Function to invoke when events of this type are emitted.
        """
        with self._callbacks_lock:
            callbacks = self._callbacks.setdefault(event_type, [])
            if callback not in callbacks:
                callbacks.append(callback)

    def has_callback(self, event_type: type[WsEvent], callback: Callable[[T], None]) -> bool:
        """
        Check if a callback is registered for a specific event type.

        Args:
            event_type (type[WsEvent]): The event type to check.
            callback (Callable): The callback to look for.

        Returns:
            bool: True if the callback is registered, False otherwise.
        """
        with self._callbacks_lock:
            return callback in self._callbacks.get(event_type, [])

    def emit(self, event: WsEvent) -> None:
        """
        Emit an event to all registered callbacks for its type.

        Args:
            event (WsEvent): The event to emit.
        """
        with self._callbacks_lock:
            callbacks = list(self._callbacks.get(type(event), []))

        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                _LOGGER.error(f'{self}: Exception emitting event to callback {callback.__name__}: {exception_to_string(e)}')

    def __str__(self):  # pragma: no cover
        return f'{self.__class__.__qualname__}()'


class QueueSink:
    """
    Sink that stores events in separate queues per event type.

    Maintains a dictionary of queues, one for each event type. Events can be
    retrieved synchronously or asynchronously via queue accessors.

    When queues reach maxsize, events are dropped according to the drop_oldest policy.
    """

    def __init__(
        self,
        maxsize: int = var.IBIND_WS_MAX_QUEUE_SIZE,
        drop_oldest: bool = var.IBIND_WS_DROP_OLDEST,
    ):
        """
        Create a queue sink.

        Args:
            maxsize (int, optional): Maximum queue size per event type. 0 = unbounded. Default: var.IBIND_WS_MAX_QUEUE_SIZE.
            drop_oldest (bool, optional): Whether to drop oldest events when full.
                If False, drops newest events. Default: var.IBIND_WS_DROP_OLDEST (True).
        """
        self._queues = {}
        self._queues_lock = threading.RLock()
        self._maxsize = maxsize
        self._drop_oldest = drop_oldest

    def new_queue_accessor(self, event_type: type[WsEvent]) -> QueueAccessor:
        """
        Create a queue accessor for a specific event type.

        Args:
            event_type (type[WsEvent]): The event type to access.

        Returns:
            QueueAccessor: Accessor for the queue associated with this event type.
        """
        return QueueAccessor(self._get_queue(event_type), event_type)

    def _get_queue(self, event_type: type[WsEvent]) -> Queue:  # pragma: no cover
        with self._queues_lock:
            try:
                return self._queues[event_type]
            except KeyError:
                self._queues[event_type] = Queue(maxsize=self._maxsize)
                return self._queues[event_type]

    def get(self, event_type: type[WsEvent], block: bool = False, timeout: float = None) -> Any:
        """
        Retrieve an event from the queue for a specific event type.

        Args:
            event_type (type[WsEvent]): The event type to retrieve.
            block (bool, optional): Whether to block until an event is available. Default: False.
            timeout (float, optional): Maximum time to block in seconds. Default: None.

        Returns:
            WsEvent | None: The retrieved event, or None if the queue is empty and block=False.
        """
        try:
            return self._get_queue(event_type).get(block=block, timeout=timeout)
        except Empty:
            return None

    def empty(self, event_type: type[WsEvent]) -> bool:
        """
        Check if the queue for a specific event type is empty.

        Args:
            event_type (type[WsEvent]): The event type to check.

        Returns:
            bool: True if the queue is empty, False otherwise.
        """
        return self._get_queue(event_type).empty()

    def emit(self, event: WsEvent) -> None:
        """
        Emit an event by adding it to the queue for its type.

        Args:
            event (WsEvent): The event to emit.
        """
        queue = self._get_queue(type(event))

        if self._maxsize == 0:
            queue.put(event)
            return

        try:
            queue.put_nowait(event)
            return
        except Full:
            if not self._drop_oldest:
                _LOGGER.warning(f'{self}: Queue full for {type(event).__name__}; dropping newest event')
                return

            try:
                dropped = queue.get_nowait()
                _LOGGER.warning(f'{self}: Queue full for {type(event).__name__}; dropping oldest event: {dropped}')
            except Empty:
                pass

            try:
                queue.put_nowait(event)
            except Full:
                _LOGGER.warning(f'{self}: Queue still full for {type(event).__name__}; dropping event: {event}')

    def __str__(self):  # pragma: no cover
        return f'{self.__class__.__qualname__}()'


class CompositeSink:
    """
    Sink that forwards events to multiple child sinks.

    Exceptions from individual sinks are logged but do not prevent other sinks
    from receiving the event.
    """

    def __init__(self, *sinks: EventSink):
        """
        Create a composite sink.

        Args:
            *sinks (EventSink): One or more sinks to forward events to.
        """
        self._sinks = sinks

    def emit(self, event: WsEvent) -> None:
        """
        Emit an event to all registered sinks.

        Args:
            event (WsEvent): The event to emit.
        """
        for sink in self._sinks:
            try:
                sink.emit(event)
            except Exception as e:
                _LOGGER.error(f'{self}: Exception emitting event to sink: {exception_to_string(e)}')

    def __str__(self):  # pragma: no cover
        return f'{self.__class__.__qualname__}()'


class AsyncSink:
    """
    Sink that forwards events to another sink asynchronously via a background thread.

    Events are queued and processed in a separate thread. When the queue is full,
    events are dropped according to the drop_oldest policy.
    """

    def __init__(
        self,
        sink: EventSink,
        maxsize: int = var.IBIND_WS_MAX_QUEUE_SIZE,
        drop_oldest: bool = var.IBIND_WS_DROP_OLDEST,
        stop_timeout: float = 5,
        cycle_interval: float = 0.25,
    ):
        """
        Create an asynchronous sink.

        Args:
            sink (EventSink): The sink to forward events to.
            maxsize (int, optional): Maximum queue size. Default: var.IBIND_WS_MAX_QUEUE_SIZE.
            drop_oldest (bool, optional): Whether to drop oldest events when full.
                If False, drops newest events. Default: var.IBIND_WS_DROP_OLDEST (True).
            stop_timeout (float, optional): Maximum time to wait for thread to stop in seconds. Default: 5.
            cycle_interval (float, optional): Interval between queue processing cycles in seconds. Default: 0.25.
        """
        self._sink = sink
        self._queue = Queue(maxsize=maxsize)
        self._drop_oldest = drop_oldest
        self._stop_timeout = stop_timeout
        self._cycle_interval = cycle_interval

        self._running = False
        self._thread: Thread | None = None
        self._wait_event = Event()

    def start(self):
        """Start the background thread for processing events."""
        if self._running:
            return

        self._running = True
        self._thread = Thread(target=self._cycle, name='async_sink_thread', daemon=True)
        self._thread.start()

    def stop(self) -> bool:
        """
        Stop the background thread and discard remaining events.

        Returns:
            bool: True if the thread stopped successfully, False if it timed out.

        Raises:
            RuntimeError: If called from within the async sink thread.
        """
        if not self._running:
            return True

        if threading.current_thread() == self._thread:
            raise RuntimeError(f'{self}: Stopping async sink called from within async sink thread. Ensure it is stopped from a separate thread')

        self._running = False
        self._wait_event.set()

        succeeded = True
        if self._thread is not None:
            self._thread.join(self._stop_timeout)
            succeeded = not self._thread.is_alive()

        self._thread = None

        if self._queue.qsize() > 0:
            _LOGGER.warning(f'{self}: Event queue not empty when stopping; discarding {self._queue.qsize()} events')

        return succeeded

    def emit(self, event: WsEvent) -> None:
        """
        Queue an event for asynchronous processing.

        Args:
            event (WsEvent): The event to emit.
        """
        try:
            self._queue.put_nowait(event)
            self._wait_event.set()
            return
        except Full:
            if not self._drop_oldest:
                _LOGGER.warning(f'{self}: Event queue full; dropping newest event: {event}')
                return

            try:
                dropped = self._queue.get_nowait()
                _LOGGER.warning(f'{self}: Event queue full; dropping oldest event: {dropped}')
            except Empty:
                pass

            try:
                self._queue.put_nowait(event)
                self._wait_event.set()
            except Full:
                _LOGGER.warning(f'{self}: Event queue still full; dropping event: {event}')

    def _consume_queue(self):
        current_events = []
        while len(current_events) < 1000:
            try:
                event = self._queue.get_nowait()
            except Empty:
                break
            current_events.append(event)

        sorted_events = sorted(current_events, key=lambda event: event.received_at)

        for event in sorted_events:
            try:
                self._sink.emit(event)
            except Exception as e:
                _LOGGER.error(f'{self}: Exception emitting event to sink: {exception_to_string(e)}')

    def _cycle(self):  # pragma: no cover
        _LOGGER.debug(f'{self}: AsyncSink thread started ({tname()})')
        while self._running:
            self._wait_event.clear()
            self._wait_event.wait(self._cycle_interval)
            self._consume_queue()

        self._consume_queue()
        _LOGGER.debug(f'{self}: AsyncSink thread stopped ({tname()})')

    def __str__(self):  # pragma: no cover
        return f'{self.__class__.__qualname__}({self._queue.qsize()})'
