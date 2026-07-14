from threading import Event, Lock

from ibind.support.logs import project_logger
from ibind.support.py_utils import tname, exception_to_string, wait_until, TimeoutLock
from ibind import ExternalBrokerError
from ibind.ws_v2.runtime.ws_event_handler import WsEventHandler
from ibind.ws_v2.runtime.ws_health_monitor import WsHealthMonitor
from ibind.ws_v2.runtime.ws_lifecycle import WsLifecycle
from ibind.ws_v2.ws_subscriptions import SubscriptionController
from ibind.ws_v2.runtime.ws_state_manager import WsStateManager, WsState

_LOGGER = project_logger('ibkr_ws_client')


class WsRuntimeWorker:
    """
    Manages the main runtime loop for WebSocket connection and event processing.

    Runs in a dedicated thread and continuously cycles through transport maintenance,
    subscription reconciliation, event processing, and health monitoring. Handles
    graceful shutdown with final cleanup passes.
    """

    def __init__(
        self,
        state_manager: WsStateManager,
        subscription_controller: SubscriptionController,
        event_handler: WsEventHandler,
        health_monitor: WsHealthMonitor,
        cycle_interval: float,
    ):
        """
        Initialise the runtime worker.

        Args:
            state_manager (WsStateManager): Manages WebSocket connection state.
            subscription_controller (SubscriptionController): Manages subscription bindings.
            event_handler (WsEventHandler): Processes transport events from the queue.
            health_monitor (WsHealthMonitor): Monitors connection health.
            cycle_interval (float): Time in seconds to wait between runtime cycles.
        """
        self._state_manager = state_manager
        self._subscription_controller = subscription_controller
        self._event_handler = event_handler
        self._health_monitor = health_monitor
        self._cycle_interval = cycle_interval

        self._lifecycle: WsLifecycle | None = None

        self._running_lock = TimeoutLock(60)

        self._running = False
        self._wait_event = Event()
        self._cycle_counter = 0
        self._cycle_counter_lock = Lock()
        self._last_error = None

    @property
    def running(self):
        """Check if the runtime worker is currently running."""
        with self._running_lock:  # pragma: no cover
            return self._running

    @running.setter
    def running(self, value):  # pragma: no cover
        """Set the running state of the runtime worker."""
        with self._running_lock:
            self._running = value

    def _maintain_subscriptions(self):
        """Reconcile subscription bindings if authenticated."""
        if not self._state_manager.is_authenticated():
            return
        try:
            self._subscription_controller.reconcile_bindings()
        except Exception as e:
            if self._last_error != str(e):
                self._last_error = str(e)
                _LOGGER.error(f'{self}: Exception reconciling subscriptions: {str(e)}. Silencing further repetitions of this message.')
                self._state_manager.set_state(WsState.DEGRADED)

    def run(self, lifecycle: WsLifecycle):
        """
        Run the main runtime loop until stopped.

        Continuously cycles through maintenance, event processing, and health checks.
        On shutdown, performs final cleanup passes to flush remaining events and
        complete unsubscriptions. Catches and logs both external broker errors and
        generic exceptions without stopping the loop.

        Args:
            lifecycle (WsLifecycle): Manages transport and runtime thread lifecycle.
        """
        self._lifecycle = lifecycle
        _LOGGER.debug(f'{self}: Runtime thread started ({tname()})')
        while self.running:
            try:
                self._cycle()
            except ExternalBrokerError as e:
                _LOGGER.error(f'{self}: External error in runtime thread: {e}')
            except Exception as e:
                _LOGGER.error(f'{self}: Runtime thread exception: {exception_to_string(e)}')

        # if not stopped or closed yet, attempt to do one last pass before the thread dies
        if self._state_manager.get_state() not in [WsState.STOPPED, WsState.CLOSED]:
            # final pass through the transport queue to flush any remaining events
            self._event_handler.process_transport_queue()

            # final pass through the subscription controller to carry out final unsubscribe events
            self._subscription_controller.reconcile_bindings()

        _LOGGER.debug(f'{self}: Runtime thread stopped ({tname()})')

    def _cycle(self):
        """
        Execute one cycle of the runtime loop.

        Performs transport maintenance, subscription reconciliation, event processing,
        and health monitoring. Resets the WebSocket app if health check fails. Waits
        for the configured cycle interval before returning.

        Returns:
            False if health check fails and runtime is stopped, otherwise None.
        """
        self._lifecycle.maintain_transport()
        self._maintain_subscriptions()

        self._event_handler.process_transport_queue()

        if not self._health_monitor.health_ok():
            if not self.running:  # return early if runtime got stopped in the meantime
                return False
            _LOGGER.warning(f'{self}: Health check failed, resetting transport websocket')
            self._lifecycle.reset_websocket_app()

        self._wait_event.wait(self._cycle_interval)
        self._wait_event.clear()

        with self._cycle_counter_lock:
            self._cycle_counter += 1

    def request_cycle(self):  # pragma: no cover
        """Request an immediate cycle by signalling the wait event."""
        self._wait_event.set()

    def wait_for_one_cycle(self):
        """
        Block until at least one complete cycle has been executed.

        Useful for synchronisation during shutdown to ensure subscriptions
        are fully reconciled before stopping.

        Raises:
            TimeoutError: If a cycle does not complete within 10 seconds.
        """
        with self._cycle_counter_lock:
            start_count = self._cycle_counter

        self.request_cycle()

        wait_until(lambda: self._cycle_counter > start_count, timeout=10)

    def __str__(self):  # pragma: no cover
        return f'{self.__class__.__qualname__}({self._state_manager.get_state()})'
