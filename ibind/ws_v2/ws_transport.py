import time
from datetime import datetime
from typing import Callable, Any, cast

from pydantic import BaseModel, ConfigDict, Field
from websocket import WebSocketApp, STATUS_UNEXPECTED_CONDITION, STATUS_NORMAL

import var
from ibind import ExternalBrokerError
from support.logs import project_logger
from support.py_utils import exception_to_string, tname, wait_until, UNDEFINED, NOOP

_LOGGER = project_logger('ibkr_ws_client')


class TransportEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)
    received_at: datetime = Field(default_factory=datetime.now)
    attempt: int = 0

    def __str__(self):
        return f'{self.__class__.__qualname__}()'


class TransportOpened(TransportEvent):
    ...


class TransportClosed(TransportEvent):
    close_status_code: int | None
    close_msg: str | None


class TransportError(TransportEvent):
    exception: Exception


class TransportMessage(TransportEvent):
    message: str


class TransportReconnect(TransportEvent):
    ...


class WsTransport():

    def __init__(
        self,
        url: str,
        event_callback: Callable,
        sslopt: dict[str, Any],
        get_cookie: Callable = NOOP,
        get_header: Callable = NOOP,
        ping_interval: float = 10,
        ping_timeout: float = 10,
        max_ping_interval: float = 20,
        connection_timeout: float = 5,
        reconnect_timeout: float = 5,
        skip_utf8_validation: bool = var.IBIND_WS_SKIP_UTF8_VALIDATION,
    ):
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

    def disconnect(self):
        if self._wsa is None:
            _LOGGER.info(f'{self}: WSA is None, skipping disconnect')
            return
        self._wsa.close(status=STATUS_NORMAL, timeout=self._connection_timeout)

    def stop(self):
        _LOGGER.info(f'{self}: Stopping')
        self._running = False
        self.disconnect()

    def reset_websocket_app(self) -> bool:
        if tname() == self._tname:
            raise RuntimeError(f'{self}: Resetting websocket app called from within transport thread. Ensure it is called from a separate thread')

        if self._wsa is None:
            _LOGGER.info(f'{self}: WSA is None, skipping reset')
            return False

        _LOGGER.info(f'{self}: Reset')

        self._wsa.close(status=STATUS_UNEXPECTED_CONDITION, timeout=self._connection_timeout)

        if not wait_until(lambda: self._wsa is None, f'{self}: WebSocket reset close timeout', timeout=self._connection_timeout * 2):
            _LOGGER.warning(f'{self}: Abandoning current WebSocketApp that cannot be closed: {self._wsa}')
            self._wsa = None

        wait_until(lambda: self._wsa is not None, f'{self}: WebSocket recreation timeout', timeout=self._connection_timeout * 2)

        return self._wsa is not None

    def check_ping(self, max_interval: float = None) -> bool:
        """
        Checks the last ping response time of the WebSocketApp connection.

        Verifies whether the last ping response from the WebSocketApp was within the acceptable time interval
        defined by 'max_ping_interval' parameter. If the last ping response exceeds this interval, a hard reset of the connection is triggered.

        Returns:
            bool: True if the last ping was within the acceptable interval or if the WebSocketApp is not connected,
                  False if the ping interval was exceeded and a hard reset was initiated.

        Note:
            - A ping interval exceeding 'max_ping_interval' indicates potential issues with the WebsocketApp connection.
        """
        if self._wsa is None:
            return True

        if self._wsa.last_pong_tm == 0:
            return True

        if max_interval is None:
            max_interval = self._max_ping_interval

        return self.get_time_since_last_ping() <= max_interval

    def get_time_since_last_ping(self) -> float:
        return abs(time.time() - self._wsa.last_pong_tm)

    def fetch_cookie(self):
        """
        Using UNDEFINED since _get_cookie could in fact return a None, and they mean different things
        """
        try:
            return self._get_cookie()
        except Exception as e:
            if isinstance(e, TimeoutError):
                _LOGGER.info(f'{self}: Timeout retrieving cookie')
                return UNDEFINED
            if isinstance(e, ExternalBrokerError):
                if e.status_code == 401:
                    _LOGGER.info(f'{self}: Failed to retrieve cookie due to lack of authentication')
                    return UNDEFINED
            _LOGGER.error(f'{self}: Failed to retrieve cookie: {exception_to_string(e)}')
            return UNDEFINED

    def check_cookie(self) -> bool:
        cookie = self.fetch_cookie()
        if cookie is UNDEFINED:
            return False

        if cookie != self._cookie:
            _LOGGER.warning(f'{self}: Cookie changed, current: {cookie}, previous: {self._cookie}')
            return False
        return True

    def set_degraded(self, value):
        self._degraded = value

    def is_ready(self) -> bool:
        return self._wsa is not None and self._wsa.ready and self._wsa.sock is not None and self._wsa.sock.sock is not None

    def send(self, payload: str) -> bool:
        if not self.is_ready():
            raise RuntimeError(f'{self}: WSA socket is not ready')

        try:
            self._wsa.send(payload)
        except Exception as e:
            if 'Connection is already closed' in str(e):
                _LOGGER.error(f'{self}: Connection closed while sending payload: {payload}')
            else:
                _LOGGER.exception(f'{self}: Sending payload failed: {payload}\n{exception_to_string(e)}')
            return False

        return True

    def __str__(self):
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

    def new_wsa(self):
        cookie = self.fetch_cookie()
        if cookie is UNDEFINED:
            return None

        self._cookie = cookie
        if cookie is not None:
            _LOGGER.info(f'{self}: Current cookie: {cookie}')

        try:
            self._header = self._get_header()
        except Exception as e:
            _LOGGER.error(f'{self}: Failed to retrieve header: {exception_to_string(e)}')
            return None

        if not self._running:
            # Transport got stopped between invocation of new_wsa and creating one
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

        return wsa

    def connect(self):
        _LOGGER.info(f'{self}: Transport thread started ({tname()})')

        self._tname = tname()

        self._running = True

        while self._running:
            if self._wsa is None:
                wsa = self.new_wsa()
                if wsa is None:
                    time.sleep(1)
                    continue
                self._wsa = wsa

            try:
                self._wsa.run_forever(
                    ping_interval=self._ping_interval,
                    ping_timeout=self._ping_interval * 0.95,  # the timeout is set to a little sooner than the interval
                    sslopt=self._sslopt,
                    reconnect=cast(int, self._reconnect_timeout),  # floats are de facto valid, casting only for the linter
                    skip_utf8_validation=self._skip_utf8_validation
                )
                _LOGGER.info(f'{self}: WSA run_forever stopped gracefully')
            except Exception as e:
                if 'url is invalid' in str(e):
                    _LOGGER.error(f'{self}: URL is invalid: {self._url}')
                else:
                    _LOGGER.exception(f'{self}: Unexpected error while running WebSocketApp: {e}')
            finally:
                self._wsa = None

        _LOGGER.info(f'{self}: Transport thread stopped ({tname()})')
