from typing import Callable

from ibind.support.logs import project_logger
from ibind.support.py_utils import TimeoutLock, VerboseEnum

_LOGGER = project_logger('ibkr_ws_client')


class WsState(VerboseEnum):
    """WebSocket runtime states."""

    STOPPED = 'STOPPED'
    STARTING = 'STARTING'
    OPEN = 'OPEN'
    AUTHENTICATED = 'AUTHENTICATED'
    CLOSED = 'CLOSED'
    DEGRADED = 'DEGRADED'
    STOPPING = 'STOPPING'


class WsStateManager:
    """
    Manages WebSocket connection state with thread-safe transitions.

    Tracks the current state of the WebSocket connection and invokes a callback
    whenever the state changes. Uses a timeout lock to ensure thread-safe state
    transitions.
    """

    def __init__(
        self,
        on_state_change: Callable,
        lock_timeout: float = 60,
    ):
        """
        Initialise the WebSocket state manager.

        Args:
            on_state_change (Callable): Callback invoked on state transitions.
                Called with (previous_state, new_state).
            lock_timeout (float, optional): Timeout in seconds for acquiring the
                state lock. Default: 60 seconds.
        """
        self._on_state_change = on_state_change

        self._state = WsState.STOPPED
        self._state_lock = TimeoutLock(lock_timeout)
        self._last_heartbeat = None

    @property
    def last_heartbeat(self) -> float | None:  # pragma: no cover
        """Get the last heartbeat timestamp."""
        return self._last_heartbeat

    @last_heartbeat.setter
    def last_heartbeat(self, value: float | None):  # pragma: no cover
        """Set the last heartbeat timestamp."""
        self._last_heartbeat = value

    def get_state(self) -> WsState:
        """
        Get the current WebSocket state.

        Returns:
            WsState: The current connection state.
        """
        with self._state_lock:
            return self._state

    def is_authenticated(self) -> bool:
        """
        Check if the WebSocket is authenticated.

        Returns:
            bool: True if state is AUTHENTICATED, False otherwise.
        """
        return self._state == WsState.AUTHENTICATED

    def set_state(self, value: WsState):
        """
        Set the WebSocket state and invoke the state change callback.

        Args:
            value (WsState): The new state to set.
        """
        with self._state_lock:
            previous_state = self._state
            self._state = value

        self._on_state_change(previous_state, value)
