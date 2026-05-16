import time
from datetime import datetime
from typing import Callable, Any, cast, List, Union, Dict

from pydantic import BaseModel, ConfigDict, Field
from websocket import WebSocketApp, STATUS_UNEXPECTED_CONDITION, STATUS_NORMAL

from ibind import var
from ibind import ExternalBrokerError
from ibind.support.logs import project_logger
from ibind.support.py_utils import exception_to_string, tname, wait_until, UNDEFINED, noop

_LOGGER = project_logger('ibkr_ws_client')


class TransportEvent(BaseModel):
    """
    Base class for WebSocket transport-level events.

    Tracks when events were received and how many processing attempts have been made.
    Uses a list for attempt count to allow mutation despite frozen model.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    received_at: datetime = Field(default_factory=datetime.now)
    attempt: List[int] = Field(default_factory=lambda: [0])

    def add_attempt(self):
        self.attempt[0] += 1

    def get_attempt(self):
        return self.attempt[0]

    def __str__(self):  # pragma: no cover
        return f'{self.__class__.__qualname__}()'


class TransportOpened(TransportEvent):
    """Emitted when the WebSocket connection is successfully opened."""

    pass


class TransportClosed(TransportEvent):
    """Emitted when the WebSocket connection is closed."""

    close_status_code: int | None
    close_msg: str | None


class TransportError(TransportEvent):
    """Emitted when a WebSocket error occurs. Note that currently WebSocketApp only emits this once, due to reconnection logic then skipping this event."""

    exception: Exception


class TransportMessage(TransportEvent):
    """Emitted when a message is received from the WebSocket."""

    message: str


class TransportReconnect(TransportEvent):
    """Emitted when the WebSocket reconnects after a disconnection."""

    pass


class WsTransport:
    """
    Manages low-level WebSocket transport using WebSocketApp.

    Handles connection lifecycle, message sending, cookie validation, and ping monitoring.
    Runs in a dedicated thread and communicates via event callbacks.
    """

    def __init__(
        self,
        url: str,
        event_callback: Callable[[TransportEvent], None],
        sslopt: Dict[str, Any],
        get_cookie: Callable[[], str | None] = noop,
        get_header: Callable[[], Dict[str, Any] | None] = noop,
        ping_interval: float = 10,
        ping_timeout: float = 10,
        max_ping_interval: float = 20,
        connection_timeout: float = 5,
        reconnect_timeout: float = 5,
        skip_utf8_validation: bool = var.IBIND_WS_SKIP_UTF8_VALIDATION,
    ):
        """
        Create a WebSocket transport instance.

        Args:
            url (str): WebSocket URL to connect to.
            event_callback (Callable): Callback function invoked with TransportEvent instances.
            sslopt (dict[str, Any]): SSL options for the WebSocket connection.
            get_cookie (Callable, optional): Function to retrieve session cookie. Default: noop.
            get_header (Callable, optional): Function to retrieve HTTP headers. Default: noop.
            ping_interval (float, optional): Interval in seconds between ping messages. Default: 10.
            ping_timeout (float, optional): Timeout in seconds for ping responses. Default: 10.
            max_ping_interval (float, optional): Maximum acceptable time since last pong. Default: 20.
            connection_timeout (float, optional): Timeout in seconds for connection operations. Default: 5.
            reconnect_timeout (float, optional): Timeout in seconds before reconnect attempts. Default: 5.
            skip_utf8_validation (bool, optional): Whether to skip UTF-8 validation. Default: True
        """
        self._url = url
        self._event_callback = event_callback
        self._sslopt = sslopt
        self._get_cookie = get_cookie
        self._get_header = get_header
        self._ping_interval = ping_interval
        self._ping_timeout = ping_timeout
        self._max_ping_interval = max_ping_interval
        self._connection_timeout = connection_timeout
        self._reconnect_timeout = reconnect_timeout
        self._skip_utf8_validation = skip_utf8_validation

        self._running = False
        self._wsa: WebSocketApp | None = None
        self._degraded = False
        self._tname = None

        self._session_lacks_authentication = False

    def disconnect(self):
        """Gracefully disconnect the WebSocket connection."""
        if self._wsa is None:
            _LOGGER.info(f'{self}: WebSocketApp is None, skipping disconnect')
            return
        self._wsa.close(status=STATUS_NORMAL, timeout=self._connection_timeout)

    def stop(self):
        """Stop the transport thread and disconnect the WebSocket."""
        _LOGGER.debug(f'{self}: Stopping transport')
        self._running = False
        self.disconnect()

    def reset_websocket_app(self) -> bool:
        """
        Force close and recreate the WebSocketApp connection.

        Returns:
            bool: True if a new WebSocketApp was successfully created, False otherwise.

        Raises:
            RuntimeError: If called from within the transport thread.
        """
        if tname() == self._tname:
            raise RuntimeError(f'{self}: Resetting websocket app called from within transport thread. Ensure it is called from a separate thread')

        if self._wsa is None:
            _LOGGER.info(f'{self}: WebSocketApp is None, skipping reset')
            return False

        _LOGGER.info(f'{self}: Reset')

        self._wsa.close(status=STATUS_UNEXPECTED_CONDITION, timeout=self._connection_timeout)

        if not wait_until(lambda: self._wsa is None, timeout=self._connection_timeout * 2):
            _LOGGER.warning(f'{self}:  WebSocket reset close timeout. Abandoning current WebSocketApp that cannot be closed: {self._wsa}')
            self._wsa = None

        if not wait_until(lambda: self._wsa is not None, timeout=self._connection_timeout * 2):
            _LOGGER.error(f'{self}: WebSocket recreation timeout')

        return self._wsa is not None

    def check_ping(self, max_interval: float = None) -> bool:
        """
        Check if the last pong was received within the acceptable interval.

        Args:
            max_interval (float, optional): Maximum acceptable seconds since last pong.
                Default: self._max_ping_interval.

        Returns:
            bool: True if last pong was within the interval or WebSocketApp is not connected,
                False if the interval was exceeded.
        """
        if self._wsa is None:
            return True

        if self._wsa.last_pong_tm == 0:
            return True

        if max_interval is None:
            max_interval = self._max_ping_interval

        return self.get_time_since_last_ping() <= max_interval

    def get_time_since_last_ping(self) -> float:
        """Get seconds elapsed since the last pong was received."""
        return abs(time.time() - self._wsa.last_pong_tm)

    def fetch_cookie(self) -> Union[str, None]:
        """
        Retrieve session cookie using the configured callback.

        Returns:
            str | None | UNDEFINED: Cookie value, None if no cookie needed, or UNDEFINED if retrieval failed.
        """
        try:
            cookie = self._get_cookie()
            if self._session_lacks_authentication:
                self._session_lacks_authentication = False
            return cookie
        except Exception as e:
            if isinstance(e, TimeoutError):
                _LOGGER.info(f'{self}: Timeout retrieving cookie')
                return UNDEFINED
            if isinstance(e, ExternalBrokerError):
                if e.status_code == 401:
                    if not self._session_lacks_authentication:
                        self._session_lacks_authentication = True
                        _LOGGER.info(
                            f'{self}: Failed to retrieve cookie due to lack of authentication. Continuing reattempts silently until authentication is reestablished.'
                        )
                    return UNDEFINED
            _LOGGER.error(f'{self}: Failed to retrieve cookie: {exception_to_string(e)}')
            return UNDEFINED

    def check_cookie(self) -> bool:
        """
        Verify the current cookie matches the stored cookie.

        Returns:
            bool: True if cookies match, False if retrieval failed or cookies differ.
        """
        cookie = self.fetch_cookie()
        if cookie is UNDEFINED:
            return False

        if cookie != self._cookie:
            _LOGGER.warning(f'{self}: Cookie changed, current: {cookie}, previous: {self._cookie}')
            return False
        return True

    def set_degraded(self, value):  # pragma: no cover
        """Mark the transport as degraded to suppress event callbacks."""
        self._degraded = value

    def is_ready(self) -> bool:
        """Check if the WebSocketApp is ready to send messages."""
        return self._wsa is not None and self._wsa.ready and self._wsa.sock is not None and self._wsa.sock.sock is not None

    def send(self, payload: str) -> bool:
        """
        Send a message through the WebSocket.

        Args:
            payload (str): Message to send.

        Returns:
            bool: True if sent successfully, False otherwise.

        Raises:
            RuntimeError: If the WebSocketApp is not ready.
        """
        if not self.is_ready():
            raise RuntimeError(f'{self}: WebSocketApp socket is not ready')

        try:
            self._wsa.send(payload)
        except Exception as e:
            if 'Connection is already closed' in str(e):
                _LOGGER.error(f'{self}: Connection closed while sending payload: {payload}')
            else:
                _LOGGER.exception(f'{self}: Sending payload failed: {payload}\n{exception_to_string(e)}')
            return False

        return True

    def __str__(self):  # pragma: no cover
        return f'{self.__class__.__qualname__}({f"degraded:{tname()}" if self._degraded else ""})'

    # ======================
    # == Transport Thread ==
    # ======================

    def _wrap_callback(self, f):
        def wrapped_f(ws, *args, **kwargs):
            try:
                f(ws, *args, **kwargs)
            except Exception as e:
                _LOGGER.exception(f'{self}: Exception executing callback: \n{f} \nwith\n{args=}\n{kwargs=}\n{str(e)}')

        return wrapped_f

    def _on_open(self, wsa: WebSocketApp):
        if self._degraded:
            return

        if not self.check_cookie():
            self._wsa.close(status=STATUS_UNEXPECTED_CONDITION, timeout=self._connection_timeout)
            return

        self._event_callback(TransportOpened())

    def _on_message(self, wsa: WebSocketApp, message):
        if self._degraded:
            return

        self._event_callback(TransportMessage(message=message))

    def _on_close(self, wsa: WebSocketApp, close_status_code, close_msg):
        if self._degraded:
            return

        self._event_callback(TransportClosed(close_status_code=close_status_code, close_msg=close_msg))

    def _on_error(self, wsa: WebSocketApp, error):
        if self._degraded:
            return

        self._event_callback(TransportError(exception=error))

    def _on_reconnect(self, wsa: WebSocketApp):
        if self._degraded:
            return

        if not self.check_cookie():
            self._wsa.close(status=STATUS_UNEXPECTED_CONDITION, timeout=self._connection_timeout)
            return

        self._event_callback(TransportReconnect())

    def _new_wsa(self):
        """Create a new WebSocketApp instance with current cookie and header."""
        cookie = self.fetch_cookie()
        if cookie is UNDEFINED:
            return None

        self._cookie = cookie

        try:
            self._header = self._get_header()
        except Exception as e:
            _LOGGER.error(f'{self}: Failed to retrieve header: {exception_to_string(e)}')
            return None

        if not self._running:
            # Transport got stopped between invocation of this function and creating a WebSocketApp
            return None

        wsa = WebSocketApp(
            url=self._url,
            on_open=self._wrap_callback(self._on_open),
            on_message=self._wrap_callback(self._on_message),
            on_close=self._wrap_callback(self._on_close),
            on_error=self._wrap_callback(self._on_error),
            on_reconnect=self._wrap_callback(self._on_reconnect),
            cookie=self._cookie,
            header=self._header,
        )
        _LOGGER.debug(f'{self}: Created new WebSocketApp instance{f", cookie: {cookie}" if cookie is not None else ""}')

        return wsa

    def _cycle(self):
        if self._wsa is None:
            wsa = self._new_wsa()
            if wsa is None:
                time.sleep(1)
                return
            self._wsa = wsa

        try:
            self._wsa.run_forever(
                ping_interval=self._ping_interval,
                ping_timeout=self._ping_interval * 0.95,  # the timeout is set to a little sooner than the interval
                sslopt=self._sslopt,
                reconnect=cast(int, self._reconnect_timeout),  # floats are de facto valid, casting only for the linter
                skip_utf8_validation=self._skip_utf8_validation,
            )
            _LOGGER.debug(f'{self}: WebSocketApp stopped gracefully')
        except Exception as e:
            if 'url is invalid' in str(e):
                _LOGGER.error(f'{self}: URL is invalid: {self._url}')
            else:
                _LOGGER.exception(f'{self}: Unexpected error while running WebSocketApp: {e}')
        finally:
            self._wsa = None

    def connect(self):
        """Main transport thread loop that maintains the WebSocket connection."""
        _LOGGER.debug(f'{self}: Transport thread started ({tname()})')

        self._tname = tname()

        self._running = True

        while self._running:
            self._cycle()

        _LOGGER.debug(f'{self}: Transport thread stopped ({tname()})')
