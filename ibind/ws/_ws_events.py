from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from ibind.support.logs import project_logger
from ibind.support.py_utils import OneOrMany
from ibind.ws.runtime.ws_state_manager import WsState

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
    """
    Base class for WebSocket connection lifecycle events.

    Attributes:
        previous_state (WsState): The state before the transition.
        current_state (WsState): The state after the transition.
    """

    previous_state: WsState
    current_state: WsState

    pass


class WsStarting(LifecycleEvent):
    """Emitted when the WebSocket connection is starting."""

    pass


class WsStopping(LifecycleEvent):
    """Emitted when the WebSocket connection is stopping."""

    pass


class WsStopped(LifecycleEvent):
    """Emitted when the WebSocket connection is stopped."""

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
