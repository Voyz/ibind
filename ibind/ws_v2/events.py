from collections import defaultdict
from datetime import datetime
from typing import Hashable, Protocol, Callable

from pydantic import BaseModel, ConfigDict, Field

from base.queue_controller import QueueController
from support.logs import project_logger
from support.py_utils import OneOrMany

_LOGGER = project_logger(__file__)


# ======================
# ==  Events Classes  ==
# ======================

class WsEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    received_at: datetime = Field(default_factory=datetime.now)
    key: Hashable

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


class ClientInternalEvent(WsEvent):
    key: str = 'CLIENT_INTERNAL'


class WsOpen(ClientInternalEvent):
    ...


class WsAuthenticated(ClientInternalEvent):
    ...


class WsReady(ClientInternalEvent):
    ...


class WsReconnect(ClientInternalEvent):
    ...


class WsClose(ClientInternalEvent):
    close_status_code: int | None
    close_msg: str | None


class WsError(ClientInternalEvent):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)
    error: Exception


class WsCritical(ClientInternalEvent):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)
    exception: Exception


# =============
# ==  Sinks  ==
# =============

class EventSink(Protocol):
    def emit(self, event: "WsEvent") -> None:
        ...


class LogSink:
    def emit(self, event: WsEvent) -> None:
        _LOGGER.debug(f'{event.key}: {str(event)}')

class NoopSink:
    def emit(self, event: WsEvent) -> None:
        pass


class CallbackSink:
    def __init__(self):
        self._callbacks: dict[type[WsEvent], list[Callable[[WsEvent], None]]] = defaultdict(list)

    def on(self, event_type: type[WsEvent], callback: Callable[[WsEvent], None]) -> None:
        self._callbacks[event_type].append(callback)

    def emit(self, event: WsEvent) -> None:
        for callback in self._callbacks[type(event)]:
            callback(event)


class QueueSink:
    def __init__(self, queue_controller: QueueController):
        self._queue_controller = queue_controller

    def emit(self, event: WsEvent) -> None:
        self._queue_controller.put_to_queue(event.key, event)


class CompositeSink:
    def __init__(self, *sinks: EventSink):
        self._sinks = sinks

    def emit(self, event: WsEvent) -> None:
        for sink in self._sinks:
            sink.emit(event)


# ==============
# ==  Router  ==
# ==============

class Router(Protocol):
    def route(self, raw_message) -> OneOrMany[WsEvent]:
        ...

    def __str__(self):
        return f'{self.__class__.__qualname__}()'