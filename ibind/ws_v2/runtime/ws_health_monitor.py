import time
from typing import Callable

from ibind.support.logs import project_logger
from ibind.ws_v2.runtime.ws_state_manager import WsStateManager, WsState
from ibind.ws_v2.ws_transport import WsTransport

_LOGGER = project_logger('ibkr_ws_client')
_HEALTH_CHECK_INTERVAL = 10


class WsHealthMonitor:
    """Monitors WebSocket connection health and triggers recovery."""

    def __init__(
        self,
        transport: WsTransport,
        state_manager: WsStateManager,
        max_ping_interval: float,
        get_authenticated: Callable[[], bool],
        reconnect_timeout: float | None,
        health_check_interval: float = _HEALTH_CHECK_INTERVAL,
    ):
        """
        Initialise the WebSocket health monitor.

        Args:
            transport (WsTransport): WebSocket transport instance to monitor.
            state_manager (WsStateManager): State manager for tracking connection state.
            max_ping_interval (float): Maximum acceptable seconds since last ping.
            get_authenticated (Callable[[], bool]): Function to retrieve current authentication status.
            reconnect_timeout (float | None): Timeout in seconds for reconnect attempts, or None to allow health monitor to trigger reset.
            health_check_interval (float, optional): Interval in seconds between health checks. Default: 10 seconds.
        """
        self._transport = transport
        self._state_manager = state_manager
        self._max_ping_interval = max_ping_interval
        self._get_authenticated = get_authenticated
        self._reconnect_timeout = reconnect_timeout
        self._health_check_interval = health_check_interval

        self._last_health_check = time.monotonic()

    def check_should_reset(self) -> bool:
        """
        Determine if the WebSocket connection should be reset due to health issues.

        Checks for ping timeouts, heartbeat timeouts, and authentication state mismatches.
        Only triggers reset if the transport is ready and connection is in OPEN or AUTHENTICATED state.

        Returns:
            bool: True if the connection should be reset, False otherwise.
        """
        # If WSA is not ready, we don't try to fix health
        if not self._transport.is_ready():
            return False

        # If we're not either open or authenticated, we let WSA handle the reconnect first
        state = self._state_manager.get_state()
        if state not in [WsState.OPEN, WsState.AUTHENTICATED]:
            return False

        ping_ok = self._transport.check_ping(self._max_ping_interval)
        if not ping_ok:
            _LOGGER.warning(
                f'{self}: Last WebSocket ping happened {self._transport.get_time_since_last_ping():.2f} seconds ago, '
                f'exceeding the max ping interval of {self._max_ping_interval}.'
            )
            # If we have a reconnect timeout, we let WSA handle the reconnect, otherwise let's reset the WSA
            return self._reconnect_timeout is None

        heartbeat_ok = True
        last_heartbeat = self._state_manager.last_heartbeat
        if last_heartbeat is not None:
            diff = abs(time.time() - last_heartbeat)  # heartbeat is in time.time(), not monotonic()
            if diff > self._max_ping_interval:
                _LOGGER.warning(
                    f'{self}: Last heartbeat happened {diff:.2f} seconds ago, exceeding the max ping interval of {self._max_ping_interval}.'
                )
                heartbeat_ok = False

        if not heartbeat_ok:
            return True

        if not self._state_manager.is_authenticated():
            is_authenticated = self._get_authenticated()
            if is_authenticated:
                _LOGGER.warning(f'{self}: State is not ready while reporting authenticated={is_authenticated}')
                self._state_manager.set_state(WsState.AUTHENTICATED)
                return False

        return False

    def health_ok(self) -> bool:
        """
        Check if the WebSocket connection is healthy.

        Performs health checks at the configured interval. If health issues are detected,
        marks the connection as DEGRADED and returns False.

        Returns:
            bool: True if the connection is healthy or check interval has not elapsed,
                False if health issues were detected.
        """
        if time.monotonic() - self._last_health_check < self._health_check_interval:
            return True

        self._last_health_check = time.monotonic()

        if not self.check_should_reset():
            return True

        self._state_manager.set_state(WsState.DEGRADED)
        return False

    def __str__(self):  # pragma: no cover
        return f'{self.__class__.__qualname__}()'
