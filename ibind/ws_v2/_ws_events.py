import threading
from datetime import datetime
from queue import Queue, Full, Empty
from threading import Thread, Event
from typing import Protocol, Callable, TypeVar, List, Dict, Any

from pydantic import BaseModel, ConfigDict, Field

from ibind.base.queue_controller import QueueAccessor
from ibind.support.logs import project_logger
from ibind.support.py_utils import OneOrMany, exception_to_string, tname

__all__ = []

_LOGGER = project_logger('ibkr_ws_client')


# ======================
# ==  Events Classes  ==
# ======================


class WsEvent(BaseModel):  # pragma: no cover
    """
    Base class for all WebSocket events.

    Immutable event model that tracks when it was received.
    """

    model_config = ConfigDict(frozen=True, extra='forbid')

    received_at: datetime = Field(default_factory=datetime.now)

    def __str__(self):
        return self._format()

    def __repr__(self):
        return self._format()

    def _format(self):
        data = self.model_dump()

        # normalize values
        for k, v in data.items():
            if isinstance(v, datetime):
                data[k] = v.isoformat()
            elif isinstance(v, Exception):
                data[k] = str(v)

        # move received_at to the end
        items = [(k, v) for k, v in data.items() if k != 'received_at']
        if 'received_at' in data:
            items.append(('received_at', data['received_at']))

        fields = ', '.join(f'{k}={v}' if isinstance(v, str) and 'T' in v else f'{k}={repr(v)}' for k, v in items)

        return f'{self.__class__.__name__}({fields})'


class LifecycleEvent(WsEvent):
    """Base class for WebSocket connection lifecycle events."""

    pass


class WsOpen(LifecycleEvent):
    """Emitted when the WebSocket connection is successfully opened."""

    pass


class WsAuthenticated(LifecycleEvent):
    """Emitted when the WebSocket connection is authenticated."""

    pass


class WsDegraded(LifecycleEvent):
    """Emitted when the WebSocket connection enters a degraded state."""

    pass


class WsReady(LifecycleEvent):
    """Emitted when the WebSocket connection is ready for use."""

    pass


class WsClose(LifecycleEvent):
    """Emitted when the WebSocket connection is closed."""

    close_status_code: int | None
    close_msg: str | None


class WsError(LifecycleEvent):
    """Emitted when a WebSocket error occurs."""

    model_config = ConfigDict(frozen=True, extra='forbid', arbitrary_types_allowed=True)
    error: Exception


# =============
# ==  Sinks  ==
# =============


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

    _callbacks: Dict[type[WsEvent], List[Callable[[WsEvent], None]]] = {}

    def on(self, event_type: type[WsEvent], callback: Callable[[T], None]) -> None:
        """
        Register a callback for a specific event type.

        Args:
            event_type (type[WsEvent]): The event type to listen for.
            callback (Callable): Function to invoke when events of this type are emitted.
        """
        self._callbacks.setdefault(event_type, []).append(callback)

    def emit(self, event: WsEvent) -> None:
        """
        Emit an event to all registered callbacks for its type.

        Args:
            event (WsEvent): The event to emit.
        """
        for callback in self._callbacks.get(type(event), []):
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
    """

    _queues = {}

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
        try:
            return self._queues[event_type]
        except KeyError:
            self._queues[event_type] = Queue()
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
        queue.put(event)

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
        maxsize: int = 10_000,
        drop_oldest: bool = True,
        stop_timeout: float = 5,
        cycle_interval: float = 0.25,
    ):
        """
        Create an asynchronous sink.

        Args:
            sink (EventSink): The sink to forward events to.
            maxsize (int, optional): Maximum queue size. Default: 10,000.
            drop_oldest (bool, optional): Whether to drop oldest events when full.
                If False, drops newest events. Default: True.
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
        while True:
            try:
                event = self._queue.get_nowait()
            except Empty:
                break

            try:
                self._sink.emit(event)
            except Exception as e:
                _LOGGER.error(f'{self}: Exception emitting event to sink: {exception_to_string(e)}')

    def _cycle(self):
        _LOGGER.debug(f'{self}: AsyncSink thread started ({tname()})')
        while self._running:
            self._wait_event.clear()
            self._wait_event.wait(self._cycle_interval)
            self._consume_queue()

        self._consume_queue()
        _LOGGER.debug(f'{self}: AsyncSink thread stopped ({tname()})')

    def __str__(self):  # pragma: no cover
        return f'{self.__class__.__qualname__}({self._queue.qsize()})'


# ==============
# ==  Router  ==
# ==============


class Router(Protocol):  # pragma: no cover
    """
    Protocol for routing raw WebSocket messages to typed events.

    Implementations parse raw messages and convert them to one or more WsEvent instances.
    """

    def route(self, raw_message) -> OneOrMany[WsEvent]:
        """
        Route a raw message to one or more events.

        Args:
            raw_message: The raw message to route.

        Returns:
            OneOrMany[WsEvent]: One or more events, or None to skip the message.
        """
        pass

    def __str__(self):
        return f'{self.__class__.__qualname__}()'
