import json
import ssl
import threading
import time
from pathlib import Path
from threading import Thread, RLock
from typing import Optional, Union, Dict, List

from websocket import WebSocketApp, STATUS_UNEXPECTED_CONDITION

from ibind.base.subscription_controller import SubscriptionController, SubscriptionProcessor
from ibind.support.logs import project_logger
from ibind.support.py_utils import exception_to_string, wait_until, tname

_LOGGER = project_logger(__file__)

_DEFAULT_TIMEOUT = 5
_DEFAULT_PING_INTERVAL = 45
_DEFAULT_MAX_PING_INTERVAL = 60


class WsClient(SubscriptionController):
    """
    A client class for handling WebSocket connections.

    This class manages WebSocket connections, providing functionalities to start, manage, and shut down
    the WebSocketApp. It supports automatic reconnection, sending payloads, and managing the connection state.

    Note:
        - This class is designed to be used as a base class and extended with specific logic for message handling and other WebSocket events.
    """

    def __init__(
            self,
            subscription_processor: SubscriptionProcessor,
            url: str,
            timeout: float = _DEFAULT_TIMEOUT,
            restart_on_close: bool = True,
            restart_on_critical: bool = True,
            ping_interval: int = _DEFAULT_PING_INTERVAL,
            max_ping_interval: int = _DEFAULT_MAX_PING_INTERVAL,
            max_connection_attempts: int = 10,
            cacert: Union[str, bool] = False,
            subscription_retries: int = 5,
            subscription_timeout: float = 2,
    ):
        """
        Parameters:
            subscription_processor (SubscriptionProcessor): The processor to create subscription payloads.
            url (str): The WebSocket URL to connect to.
            timeout (float, optional): Timeout for waiting on operations like connection and shutdown. Defaults to _DEFAULT_TIMEOUT.
            restart_on_close (bool, optional): Flag to restart the connection if it closes unexpectedly. Defaults to True.
            restart_on_critical (bool, optional): Flag to restart the connection on critical errors. Defaults to True.
            ping_interval (int, optional): Interval in seconds for sending pings to keep the connection alive. Defaults to _DEFAULT_PING_INTERVAL.
            max_ping_interval (int, optional): Maximum interval in seconds to wait for a ping response. Defaults to _DEFAULT_MAX_PING_INTERVAL.
            max_connection_attempts (int, optional): Maximum number of attempts for connecting to the WebSocket. Defaults to 10.
            cacert (Union[str, bool], optional): Path to the CA certificate file for SSL verification, or False to disable SSL verification. Defaults to False.
            subscription_retries (int, optional): Number of retries for subscription requests. Defaults to 5.
            subscription_timeout (float, optional): Timeout for subscription requests. Defaults to 2.
        """
        if url is None:
            raise ValueError("url must not be None")

        self._url = url
        self._timeout = timeout
        self._restart_on_close = restart_on_close
        self._restart_on_critical = restart_on_critical
        self._max_ping_interval = max_ping_interval
        self._ping_interval = ping_interval
        self._max_connection_attempts = max_connection_attempts

        super().__init__(
            subscription_processor=subscription_processor,
            subscription_retries=subscription_retries,
            subscription_timeout=subscription_timeout
        )

        self._connected = False
        self._running = False
        self._authenticated = True # True by default in case of an WS API that doesn't support authentication messages
        self._connect_lock = RLock()
        self._reconnect_lock = RLock()
        self._wsa: Optional[WebSocketApp] = None
        self._thread = None
        self._thread_ids = {}
        self._next_thread_id = 0

        if not (cacert is False or Path(cacert).exists()):
            raise ValueError(f"{self}: cacert must be a valid Path or False")

        if cacert is None or cacert == False:
            self._sslopt = {"cert_reqs": ssl.CERT_NONE}
        else:
            self._sslopt = {'ca_certs': cacert}

    def send(self, payload: str) -> bool:
        """
        Sends a payload over the WebSocket.

        Attempts to send a given payload through the WebSocket connection. If the client is not running
        or if there's no active connection, it tries to establish a connection before sending the payload.

        Parameters:
            payload (str): The payload to be sent over the WebSocket.

        Returns:
            bool: True if the payload was sent successfully, False otherwise.

        Note:
            - If the WebSocketApp is not running or if the connection is inactive, the method attempts to connect first.
        """
        if not self._running:
            _LOGGER.error(f'{self}: Must be started before sending payloads')
            return False

        if not self._has_active_connection():
            connection_success = self._try_connecting()
            if not connection_success:
                return False

        try:
            self._wsa.send(payload)
        except Exception as e:
            if 'Connection is already closed' in str(e):
                _LOGGER.error(f'{self}: Connection closed while sending payload: {payload}')
            else:
                _LOGGER.exception(f'{self}: Sending payload failed: {payload}\n{exception_to_string(e)}')
            return False

        return True

    def send_json(self, payload: Union[List, Dict]) -> bool:  # pragma: no cover
        """
        Sends a JSON-formatted payload over the WebSocket.

        Converts the given payload to a JSON string and sends it through the WebSocket connection. This method
        is a convenience wrapper around the 'send' method for JSON data.

        Parameters:
            payload (Union[List, Dict]): The payload to be sent, structured as a list or dictionary.

        Returns:
            bool: True if the JSON payload was sent successfully, False otherwise.
        """
        return self.send(json.dumps(payload))

    def _wrap_callback(self, f):
        def wrapped_f(ws, *args, **kwargs):
            if not (ws is self._wsa):
                _LOGGER.error(f'{self}: Invalid ws returned: {ws} | expected: {self._wsa}')

            try:
                f(ws, *args, **kwargs)
            except Exception as e:
                _LOGGER.error(f'{self}: Exception executing callback: \n{f} \nwith\n{args=}\n{kwargs=}\n{exception_to_string(e)}')

        return wrapped_f

    def _run_websocket(self, wsa: WebSocketApp):
        _LOGGER.debug(f'{self}: Thread started ({tname()})')

        try:
            # the timeout is set to a little sooner than the interval
            wsa.run_forever(ping_interval=self._ping_interval, ping_timeout=self._ping_interval * 0.95, sslopt=self._sslopt)

        except ValueError as e:
            if 'url is invalid' in str(e):
                _LOGGER.error(f'{self}: URL is invalid: {self._url}')
        except Exception as e:
            _LOGGER.exception(f'{self}: Unexpected error while running WebSocketApp: {e}')
            if self._restart_on_critical:
                # if restart_on_close is set, restarting will happen in on_close callback
                self.hard_reset(restart=not self._restart_on_close)

        _LOGGER.debug(f'{self}: Thread stopped ({tname()})')
        self._thread = None

        if self._restart_on_close and self._running:
            self._reconnect()

    def get_cookie(self):
        return None

    def get_header(self):
        return None

    def _new_websocket_app(self) -> bool:
        if self._wsa is not None:
            raise RuntimeError(f"{self}: WebSocketApp should be closed before attempting to create a new one")

        _LOGGER.debug(f'{self}: Creating new WebSocketApp')

        try:
            cookie = self.get_cookie()
        except Exception as e:
            _LOGGER.error(f'{self}: Failed to retrieve cookie: {exception_to_string(e)}')
            cookie = None

        try:
            header = self.get_header()
        except Exception as e:
            _LOGGER.error(f'{self}: Failed to retrieve header: {exception_to_string(e)}')
            header = None

        wsa = WebSocketApp(
            url=self._url,
            on_open=self._wrap_callback(self._handle_on_open),
            on_message=self._wrap_callback(self._handle_on_message),
            on_close=self._wrap_callback(self._handle_on_close),
            on_error=self._wrap_callback(self._handle_on_error),
            cookie=cookie,
            header=header,
        )

        self._wsa = wsa

        self._thread = Thread(target=self._run_websocket, args=(self._wsa,), name='ws_client_thread')
        self._thread.daemon = True
        self._thread.start()

        connection_success = wait_until(lambda: self._connected, f'{self}: New WebSocketApp connection timeout', timeout=self._timeout)

        # attempt to shut down if connection fails
        if not connection_success:
            wsa.keep_running = False
            wsa.close()
            if self._thread is not None:
                self._thread.join(60)
                self._thread = None
            self._wsa = None

        return connection_success

    def _try_connecting(self) -> bool:
        with self._connect_lock:
            if self._has_active_connection():
                return True

            if self._thread is not None:
                _LOGGER.warning(f'{self}: Thread already running: {self._thread.name}-{self._thread.ident}')
                return False

            _LOGGER.info(f'{self}: Trying to connect')
            for i in range(self._max_connection_attempts):
                if not self._running:
                    return False

                if i > 0:
                    _LOGGER.info(f'{self}: Connect reattempt {i + 1}/{self._max_connection_attempts}')

                try:
                    connection_success = self._new_websocket_app()
                except Exception as e:
                    _LOGGER.exception(f'{self}: Exception creating new WebSocketApp:\n{exception_to_string(e)}')
                    connection_success = False

                if connection_success:
                    return True

            _LOGGER.warning(f'{self}: Connection failed after {self._max_connection_attempts} attempts')
            return False

    def set_authenticated(self, authenticated:bool):
        self._authenticated = authenticated == True
        if authenticated == False:
            if self._wsa is not None:
                _LOGGER.warning(f'{self}: Not authenticated, closing WebSocketApp')
                self._wsa.close(status=STATUS_UNEXPECTED_CONDITION)

    def on_message(self, wsa: WebSocketApp, message):  # pragma: no cover
        pass

    def on_reconnect(self):  # pragma: no cover
        if not wait_until(lambda: self._authenticated, f'{self}: Reconnecting and recreating subscriptions stopped due to lack of authentication.', timeout=10):
            # This may appear in the flow of reestablishing connection after loss of authentication
            # Returning should be expected and fine, as we should only recreate subscriptions once we're authenticated
            return
        self.recreate_subscriptions()

    def on_open(self, was: WebSocketApp):  # pragma: no cover
        pass

    def on_close(self, wsa: WebSocketApp, close_status_code, close_msg):  # pragma: no cover
        self.invalidate_subscriptions()

    def on_error(self, wsa: WebSocketApp, error):  # pragma: no cover
        pass

    def _handle_on_message(self, wsa: WebSocketApp, message):  # pragma: no cover
        self.on_message(wsa, message)

    def _handle_on_open(self, wsa: WebSocketApp):
        _LOGGER.info(f'{self}: Connection open')
        self._connected = True
        self.on_open(wsa)

    def _handle_on_error(self, wsa: WebSocketApp, error):  # pragma: no cover
        _LOGGER.error(f'{self}: on_error: {error}')
        self.on_error(wsa, error)

    def _handle_on_close(self, wsa: WebSocketApp, close_status_code, close_msg):
        _LOGGER.info(f'{self}: on_close')
        self.on_close(wsa, close_status_code, close_msg)
        # if we're not connected we shouldn't need to do anything
        if not self._connected:
            _LOGGER.info(f'{self}: on_close event while disconnected')
            return

        self._connected = False
        self._wsa = None

        if close_status_code is not None or close_msg is not None:  # this means an error
            try:
                msg = close_msg.decode("utf-8")
            except AttributeError:
                msg = close_msg

            _LOGGER.error(f'{self}: on_close error: {close_status_code} | {msg}')

        else:  # otherwise it's a close success confirmation
            _LOGGER.info(f'{self}: Connection closed')

        if not self._running:  # if close happened due to shutting down, acknowledge and return
            _LOGGER.info(f'{self}: Gracefully stopped')
            return

    def hard_reset(self, restart: bool = False) -> None:
        """
        Performs a hard reset of the WebSocket connection.

        This method forcefully closes the current WebSocketApp connection and optionally restarts it. It is
        used to handle scenarios where the connection is unresponsive or encounters a critical error.

        This method cannot be called from the WsClient thread.

        Parameters:
            restart (bool, optional): Specifies whether to restart the WebSocketApp connection after resetting.
                                      Defaults to False.

        Note:
            - Closes the current WebSocketApp connection, if any, and clears related resources.
            - If the WebSocketApp is unresponsive or cannot be closed, it will be abandoned and the connection will be reset.
            - If 'restart' is True, the method attempts to re-establish a new WebSocketApp connection after resetting.
        """
        _LOGGER.info(f'{self}: Hard reset, {restart=}, {self._wsa is None=}')

        # we want the websocket closed before reconnecting
        if self._wsa is not None:
            if not self._connected:
                # this means that we get a bad error before we could even get a connection confirmation
                # which shouldn't really happen, but if it does the original WebSocketApp is bad
                # so let's drop it anyway.
                self._wsa = None
                restart = True  # since we've abandoned the WebSocketApp, let's ensure we restart
            else:
                _LOGGER.info(f'{self}: Hard reset is closing the WebSocketApp')
                # check if current thread is the same as _thread
                if threading.current_thread() == self._thread:
                    raise RuntimeError(f'{self}: Hard reset called from WsClient thread. Ensure it is started from a separate thread')

                self._wsa.close(status=STATUS_UNEXPECTED_CONDITION)

        # ensure the websocket is closed and abandoned
        if not wait_until(lambda: self._wsa is None, f'{self}: Hard reset close timeout', timeout=self._timeout):
            _LOGGER.warning(f'{self}: Abandoning current WebSocketApp that cannot be closed: {self._wsa}')
            self._wsa = None
            restart = True  # since we've abandoned the WebSocketApp, let's ensure we restart

        # in some cases, closing the websocket will cause the restart elsewhere, therefore only closing it is enough
        if restart:
            _LOGGER.info(f'{self}: Forced restart')
            self._reconnect()

    def _reconnect(self):
        with self._reconnect_lock:
            if not self._has_active_connection():
                _LOGGER.info(f'{self}: Reconnecting')
                self._try_connecting()

            if self._has_active_connection():
                self.on_reconnect()

    def disconnect(self):  # pragma: no cover
        """
        Disconnects the WebSocketApp connection.

        This method closes the active WebSocketApp connection if it exists. If the WebSocketApp is not
        currently connected, it sets the connected status to False.
        """
        if self._wsa is not None:
            self._wsa.close()
        else:
            self._connected = False

    def start(self) -> bool:
        """
        Starts the WsClient and establishes the WebSocketApp connection.

        This method sets the WsClient to running state and attempts to establish a WebSocketApp connection.
        It returns the success status of the connection attempt.

        Returns:
            bool: True if the WebSocketApp connection was successfully established, False otherwise.

        Note:
            - The success of the connection is determined by the ability to establish and maintain the WebSocketApp connection.
        """
        _LOGGER.info(f'{self}: Starting')
        self._running = True
        success = self._try_connecting()
        return success

    def shutdown(self):
        """
        Shuts down the WsClient and its WebSocketApp connection.

        This method stops the WsClient and closes the active WebSocketApp connection, if any.
        It ensures that all resources are cleanly released.

        Note:
            - The method sets the WsClient to a non-running state and closes the WebSocketApp connection.
            - If the WebSocketApp connection is active, it is disconnected.
        """
        self._running = False
        with self._connect_lock:
            if not self._connected and self._thread is None:
                return

            _LOGGER.info(f'{self}: Shutting down')

            if self._connected:
                self.disconnect()

            if self._thread is not None:
                self._thread.join(60)
                self._thread = None

    def check_ping(self) -> bool:
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

        if self._wsa.last_ping_tm == 0:
            return True

        diff = abs(time.time() - self._wsa.last_ping_tm)
        if diff > self._max_ping_interval:
            _LOGGER.warning(f'{self}: Last WebSocket ping happened {diff: .2f} seconds ago, exceeding the max ping interval of {self._max_ping_interval}. Restarting.')
            self.hard_reset(restart=True)
            return False

        return True

    def _has_active_connection(self) -> bool:  # pragma: no cover
        return self._wsa is not None and self._connected

    @property
    def connected(self) -> bool:  # pragma: no cover
        """
        Whether the WebSocketApp connection is active.

        Returns:
            - bool: True if the WebSocketApp is connected, False otherwise.
        """
        return self._connected

    def ready(self) -> bool:  # pragma: no cover
        """
        Whether the WsClient is ready for use.

        Returns:
            - bool: True if the WsClient is ready for use, False otherwise.
        """
        return self._connected and self._running and self._wsa is not None

    @property
    def running(self) -> bool:  # pragma: no cover
        """
        Whether the WsClient has been started.

        Returns:
            - bool: True if the WsClient is running, False otherwise.
        """
        return self._running

    def __str__(self):
        return f'{self.__class__.__qualname__}'
