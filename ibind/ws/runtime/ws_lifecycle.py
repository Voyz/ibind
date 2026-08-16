import threading
from threading import Thread
from typing import TYPE_CHECKING

from ibind.support.logs import project_logger
from ibind.support.py_utils import wait_until
from ibind.ws.runtime.ws_state_manager import WsStateManager, WsState
from ibind.ws.ws_transport import WsTransport

_LOGGER = project_logger('ibkr_ws_client')

if TYPE_CHECKING:
    from ibind.ws.ws_runtime import WsRuntimeWorker


class WsLifecycle:
    """Manages WebSocket runtime and transport thread lifecycle."""

    def __init__(
        self,
        state_manager: WsStateManager,
        connection_timeout: float,
        runtime_worker: 'WsRuntimeWorker',
        transport: WsTransport,
    ):
        """
        Initialize WebSocket lifecycle manager.

        Args:
            state_manager (WsStateManager): Manages WebSocket connection state.
            connection_timeout (float): Timeout in seconds for connection and thread operations.
            runtime_worker (WsRuntimeWorker): Worker that runs the main event loop.
            transport (WsTransport): WebSocket transport layer.
        """
        self._state_manager = state_manager
        self._connection_timeout = connection_timeout
        self._runtime_worker = runtime_worker
        self._transport = transport

        self._transport_thread: Thread | None = None
        self._runtime_thread: Thread | None = None

    def new_transport_thread(self):  # pragma: no cover
        """Create and start a new transport thread."""
        self._transport_thread = Thread(target=self._transport.connect, name='ws_transport_thread')
        self._transport_thread.daemon = True
        self._transport_thread.start()

    def _new_runtime_thread(self):  # pragma: no cover
        """Create and start a new runtime thread."""
        self._runtime_thread = Thread(target=self._runtime_worker.run, name='ws_runtime_thread', args=(self,))
        self._runtime_thread.daemon = True
        self._runtime_thread.start()

    def _stop_transport_thread(self) -> bool:
        """
        Stop the transport thread and wait for it to terminate.

        Returns:
            bool: True if transport thread stopped successfully, False otherwise.
        """
        try:
            self._transport.stop()
            if self._transport_thread is None:
                return True

            _LOGGER.debug(f'{self}: Joining transport thread')

            self._transport_thread.join(self._connection_timeout)
            is_alive = self._transport_thread.is_alive()
            if not is_alive:
                self._transport_thread = None
                return True
            else:
                _LOGGER.error(f'{self}: Transport thread failed to stop within timeout, still alive')
                return False
        except Exception as e:
            _LOGGER.error(f'{self}: Failed to stop transport thread: {e}')

        return False

    def start(self):
        """
        Start the WebSocket runtime and wait for authentication.

        Returns:
            bool: True if connection authenticated within timeout, False on timeout or if already started.
        """
        if self._state_manager.get_state() != WsState.STOPPED:
            return False

        if self._runtime_thread is not None and self._runtime_thread.is_alive():
            _LOGGER.error(f'{self}: Runtime thread must be stopped and joined before starting')
            return False

        if self._transport_thread is not None and self._transport_thread.is_alive():
            _LOGGER.error(f'{self}: Transport thread must be stopped and joined before starting')
            return False

        self._transport.set_degraded(False)
        _LOGGER.info(f'{self}: Starting WebSocket runtime')

        self._state_manager.set_state(WsState.STARTING)
        self._runtime_worker.running = True

        self._new_runtime_thread()

        connection_success = wait_until(self._state_manager.is_authenticated, timeout=self._connection_timeout)
        if not connection_success:
            _LOGGER.error(f'{self}: Starting timeout')
        return connection_success

    def stop(self):
        """
        Stop the WebSocket runtime and all associated threads.

        Waits for one runtime cycle before stopping to allow pending unsubscriptions
        to complete. Must be called from a thread other than the runtime thread.

        Returns:
            bool: True if all threads stopped cleanly, False if threads failed to stop within timeout.

        Raises:
            RuntimeError: If called from within the runtime thread.
        """
        if self._state_manager.get_state() == WsState.STOPPED:
            return True

        if threading.current_thread() == self._runtime_thread:
            raise RuntimeError(f'{self}: Stopping runtime called from within runtime thread. Ensure it is called from a separate thread')

        _LOGGER.info(f'{self}: Stopping WebSocket runtime')

        # wait until one more pass of the runtime thread has occurred to allow unsubscriptions to complete
        self._runtime_worker.wait_for_one_cycle()

        self._state_manager.set_state(WsState.STOPPING)
        transport_thread_stopped = self._stop_transport_thread()
        if not transport_thread_stopped:
            _LOGGER.error(f'{self}: Failed to stop transport thread')

        self._transport.set_degraded(True)

        self._runtime_worker.running = False
        runtime_thread_stopped = True
        if self._runtime_thread is not None:
            self._runtime_thread.join(self._connection_timeout)
            if self._runtime_thread.is_alive():
                _LOGGER.error(f'{self}: Runtime thread failed to stop within timeout, still alive')
                runtime_thread_stopped = False
            else:
                self._runtime_thread = None

        if transport_thread_stopped and runtime_thread_stopped:
            self._state_manager.set_state(WsState.STOPPED)
            return True
        else:
            _LOGGER.error(f'{self}: Stop incomplete - transport_ok={transport_thread_stopped}, runtime_ok={runtime_thread_stopped}')
            return False

    def hard_reset(self) -> bool:
        """
        Perform a hard reset by stopping and restarting the runtime.

        Must be called from a thread other than the runtime or transport threads.

        Returns:
            bool: True if reset completed successfully, False if stop failed.

        Raises:
            RuntimeError: If called from within the runtime or transport thread.
        """
        _LOGGER.info(f'{self}: Hard reset')

        if threading.current_thread() in [self._runtime_thread, self._transport_thread]:
            raise RuntimeError(f'{self}: Hard reset called from Runtime or Transport thread. Ensure it is called from a separate thread')

        stop_ok = self.stop()
        if not stop_ok:
            _LOGGER.error(f'{self}: Hard reset aborted - stop failed, threads may still be running')
            return False
        return self.start()

    def reset_websocket_app(self):  # pragma: no cover
        """Reset the transport's WebSocketApp."""
        self._transport.reset_websocket_app()

    def maintain_transport(self):
        """
        Ensure transport thread is running, creating it if necessary.

        Does nothing if the lifecycle is in STOPPING state or if the transport
        thread is already alive.
        """
        # Don't maintain the transport thread if we are stopping
        if self._state_manager.get_state() == WsState.STOPPING:
            return

        if self._transport_thread is None or not self._transport_thread.is_alive():
            self.new_transport_thread()

    def __str__(self):  # pragma: no cover
        return f'{self.__class__.__qualname__}()'
