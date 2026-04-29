from datetime import datetime
from typing import Callable, Any

from pydantic import BaseModel, ConfigDict, Field
from websocket import WebSocketApp

from support.logs import project_logger
from support.py_utils import exception_to_string, tname

_LOGGER = project_logger(__file__)

_NOOP = lambda: None


class TransportEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    received_at: datetime = Field(default_factory=datetime.now)
    wsa: WebSocketApp

    def __str__(self):
        return f'{self.__class__.__qualname__}()'


class TransportOpened(TransportEvent):
    ...


class TransportClosed(TransportEvent):
    close_status_code: int | None
    close_msg: str | None


class TransportError(TransportEvent):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)
    error: Exception


class TransportMessage(TransportEvent):
    message: str

class TransportReconnect(TransportEvent):
    ...

class TransportCritical(TransportEvent):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)
    exception: Exception


class WsTransport():

    def __init__(
        self,
        url: str,
        event_callback: Callable,
        sslopt: dict[str, Any],
        get_cookie: Callable = _NOOP,
        get_header: Callable = _NOOP,
        ping_interval: float = 10,
        ping_timeout: float = 10,
    ):
        self._url = url
        self._event_callback = event_callback
        self._get_cookie = get_cookie
        self._get_header = get_header
        self._ping_interval = ping_interval
        self._ping_timeout = ping_timeout
        self._sslopt = sslopt

        self._running = False
        self._wsa: WebSocketApp | None = None

    def _wrap_callback(self, f):
        def wrapped_f(ws, *args, **kwargs):
            try:
                f(ws, *args, **kwargs)
            except Exception as e:
                _LOGGER.exception(f'{self}: Exception executing callback: \n{f} \nwith\n{args=}\n{kwargs=}\n{str(e)}')

        return wrapped_f

    def _on_open(self, wsa: WebSocketApp):
        self._event_callback(TransportOpened(wsa=wsa))

    def _on_message(self, wsa: WebSocketApp, message):
        self._event_callback(TransportMessage(wsa=wsa, message=message))

    def _on_close(self, wsa: WebSocketApp, close_status_code, close_msg):
        self._event_callback(TransportClosed(wsa=wsa, close_status_code=close_status_code, close_msg=close_msg))

    def _on_error(self, wsa: WebSocketApp, error):
        self._event_callback(TransportError(wsa=wsa, error=error))

    def _on_reconnect(self, wsa: WebSocketApp):
        self._event_callback(TransportReconnect(wsa=wsa))

    def new_wsa(self):
        try:
            cookie = self._get_cookie()
        except Exception as e:
            _LOGGER.error(f'{self}: Failed to retrieve cookie: {exception_to_string(e)}')
            cookie = None

        try:
            header = self._get_header()
        except Exception as e:
            _LOGGER.error(f'{self}: Failed to retrieve header: {exception_to_string(e)}')
            header = None

        wsa = WebSocketApp(
            url=self._url,
            on_open=self._wrap_callback(self._on_open),
            on_message=self._wrap_callback(self._on_message),
            on_close=self._wrap_callback(self._on_close),
            on_error=self._wrap_callback(self._on_error),
            on_reconnect=self._wrap_callback(self._on_reconnect),
            cookie=cookie,
            header=header,
        )

        self._wsa = wsa

    def send(self, payload: str) -> bool:
        if not self._wsa.ready:
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

    def connect(self):
        _LOGGER.debug(f'{self}: Transport thread started ({tname()})')

        if self._wsa is None:
            self.new_wsa()

        try:
            # the timeout is set to a little sooner than the interval
            self._wsa.run_forever(ping_interval=self._ping_interval, ping_timeout=self._ping_interval * 0.95, sslopt=self._sslopt, reconnect=3)

        except ValueError as e:
            if 'url is invalid' in str(e):
                _LOGGER.error(f'{self}: URL is invalid: {self._url}')
        except Exception as e:
            _LOGGER.exception(f'{self}: Unexpected error while running WebSocketApp: {e}')
            self._event_callback(TransportCritical(wsa=self._wsa, exception=e))
        finally:
            self._wsa = None

        _LOGGER.debug(f'{self}: Transport thread stopped ({tname()})')

        # if self._restart_on_close and self._running:
        #     self._reconnect()

    def disconnect(self):
        self._wsa.close()

    def __str__(self):
        return f'{self.__class__.__qualname__}()'