import threading
from collections import defaultdict
from datetime import datetime
from queue import Queue, Full, Empty
from threading import Thread, Event
from typing import Protocol, Callable, TypeVar, List, Dict, Any

from pydantic import BaseModel, ConfigDict, Field

from base.queue_controller import QueueAccessor
from support.logs import project_logger
from support.py_utils import OneOrMany, exception_to_string, tname

_LOGGER = project_logger('ibkr_ws_client')


# ======================
# ==  Events Classes  ==
# ======================

class WsEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    received_at: datetime = Field(default_factory=datetime.now)

    def __str__(self):
        return self._format()

    def __repr__(self):
        return self._format()

    def _format(self):
        data = self.model_dump()

        # remove key (already logged elsewhere)
        data.pop("key", None)

        # normalize values
        for k, v in data.items():
            if isinstance(v, datetime):
                data[k] = v.isoformat()
            elif isinstance(v, Exception):
                data[k] = str(v)

        # move received_at to the end
        items = [(k, v) for k, v in data.items() if k != "received_at"]
        if "received_at" in data:
            items.append(("received_at", data["received_at"]))

        fields = ", ".join(
            f"{k}={v}" if isinstance(v, str) and "T" in v else f"{k}={repr(v)}"
            for k, v in items
        )

        return f"{self.__class__.__name__}({fields})"


class LifecycleEvent(WsEvent):
    ...


class WsOpen(LifecycleEvent):
    ...


class WsAuthenticated(LifecycleEvent):
    ...


class WsDegraded(LifecycleEvent):
    ...


class WsReady(LifecycleEvent):
    ...


class WsClose(LifecycleEvent):
    close_status_code: int | None
    close_msg: str | None


class WsError(LifecycleEvent):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)
    error: Exception


# =============
# ==  Sinks  ==
# =============

class EventSink(Protocol):
    def emit(self, event: "WsEvent") -> None:
        pass


class LogSink:
    def emit(self, event: WsEvent) -> None:
        _LOGGER.debug(event)


class NoopSink:
    def emit(self, event: WsEvent) -> None:
        pass


T = TypeVar("T", bound=WsEvent)


class CallbackSink:
    def __init__(self):
        self._callbacks: Dict[type[WsEvent], List[Callable[[WsEvent], None]]] = defaultdict(list)

    def on(self, event_type: type[WsEvent], callback: Callable[[T], None]) -> None:
        self._callbacks[event_type].append(callback)

    def emit(self, event: WsEvent) -> None:
        for callback in self._callbacks[type(event)]:
            try:
                callback(event)
            except Exception as e:
                _LOGGER.error(f'{self}: Exception emitting event to callback: {exception_to_string(e)}')

    def __str__(self):
        return f'{self.__class__.__qualname__}()'


class QueueSink:
    def __init__(self):
        self._queues = {}

    def new_queue_accessor(self, event_type: type[WsEvent]) -> QueueAccessor:
        return QueueAccessor(self._get_queue(event_type), event_type)

    def _get_queue(self, event_type: type[WsEvent]) -> Queue:  # pragma: no cover
        try:
            return self._queues[event_type]
        except KeyError:
            self._queues[event_type] = Queue()
            return self._queues[event_type]

    def get(self, event_type: type[WsEvent], block: bool = False, timeout=None) -> Any:
        try:
            return self._get_queue(event_type).get(block=block, timeout=timeout)
        except Empty:
            return None

    def empty(self, event_type: type[WsEvent]) -> bool:
        return self._get_queue(event_type).empty()

    def emit(self, event: WsEvent) -> None:
        queue = self._get_queue(type(event))
        queue.put(event)


class CompositeSink:
    def __init__(self, *sinks: EventSink):
        self._sinks = sinks

    def emit(self, event: WsEvent) -> None:
        for sink in self._sinks:
            try:
                sink.emit(event)
            except Exception as e:
                _LOGGER.error(f'{self}: Exception emitting event to sink: {exception_to_string(e)}')

    def __str__(self):
        return f'{self.__class__.__qualname__}()'


class AsyncSink:
    def __init__(
        self,
        sink: EventSink,
        maxsize: int = 10_000,
        drop_oldest: bool = True,
        stop_timeout: float = 5,
        cycle_interval: float = 0.25,
    ):
        self._sink = sink
        self._queue = Queue(maxsize=maxsize)
        self._drop_oldest = drop_oldest
        self._stop_timeout = stop_timeout
        self._cycle_interval = cycle_interval

        self._running = False
        self._thread: Thread | None = None
        self._wait_event = Event()

    def start(self):
        if self._running:
            return

        self._running = True
        self._thread = Thread(target=self._cycle, name="async_sink_thread", daemon=True)
        self._thread.start()

    def stop(self) -> bool:
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
        _LOGGER.info(f'{self}: AsyncSink thread started ({tname()})')
        while self._running:
            self._wait_event.clear()
            self._wait_event.wait(self._cycle_interval)
            self._consume_queue()

        self._consume_queue()
        _LOGGER.info(f'{self}: AsyncSink thread stopped ({tname()})')

    def __str__(self):
        return f'{self.__class__.__qualname__}({self._queue.qsize()})'


# ==============
# ==  Router  ==
# ==============

class Router(Protocol):
    def route(self, raw_message) -> OneOrMany[WsEvent]:
        ...

    def __str__(self):
        return f'{self.__class__.__qualname__}()'
