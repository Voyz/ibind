from threading import Event, Thread
from unittest.mock import Mock

import pytest

from ibind import ExternalBrokerError
from ibind.ws_v2.runtime.ws_event_handler import WsEventHandler
from ibind.ws_v2.runtime.ws_health_monitor import WsHealthMonitor
from ibind.ws_v2.runtime.ws_lifecycle import WsLifecycle
from ibind.ws_v2.runtime.ws_runtime_worker import WsRuntimeWorker
from ibind.ws_v2.runtime.ws_state_manager import WsState, WsStateManager
from ibind.ws_v2.ws_subscriptions import SubscriptionController
from test.test_utils import capture_logs


@pytest.fixture
def state_manager():
    return Mock(spec=WsStateManager)


@pytest.fixture
def subscription_controller():
    return Mock(spec=SubscriptionController)


@pytest.fixture
def event_handler():
    return Mock(spec=WsEventHandler)


@pytest.fixture
def health_monitor():
    return Mock(spec=WsHealthMonitor)


@pytest.fixture
def lifecycle():
    return Mock(spec=WsLifecycle)


@pytest.fixture
def worker(state_manager, subscription_controller, event_handler, health_monitor):
    return WsRuntimeWorker(
        state_manager=state_manager,
        subscription_controller=subscription_controller,
        event_handler=event_handler,
        health_monitor=health_monitor,
        cycle_interval=0.01,
    )


class TestWsRuntimeWorkerMaintainSubscriptions:
    @capture_logs()
    def test_maintain_subscriptions_returns_early_when_not_authenticated(self, worker, state_manager, subscription_controller):
        """_maintain_subscriptions returns early when not authenticated."""
        ## Arrange
        state_manager.is_authenticated.return_value = False

        ## Act
        worker._maintain_subscriptions()

        ## Assert
        subscription_controller.reconcile_bindings.assert_not_called()

    @capture_logs()
    def test_maintain_subscriptions_reconciles_when_authenticated(self, worker, state_manager, subscription_controller):
        """_maintain_subscriptions reconciles bindings when authenticated."""
        ## Arrange
        state_manager.is_authenticated.return_value = True

        ## Act
        worker._maintain_subscriptions()

        ## Assert
        subscription_controller.reconcile_bindings.assert_called_once()

    @capture_logs(logger_level='ERROR', expected_errors=['Exception reconciling subscriptions'], partial_match=True)
    def test_maintain_subscriptions_logs_exception_first_time(self, worker, state_manager, subscription_controller):
        """_maintain_subscriptions logs exception on first occurrence and sets state to DEGRADED."""
        ## Arrange
        state_manager.is_authenticated.return_value = True
        subscription_controller.reconcile_bindings.side_effect = RuntimeError('reconcile error')

        ## Act
        worker._maintain_subscriptions()

        ## Assert
        state_manager.set_state.assert_called_once_with(WsState.DEGRADED)

    @capture_logs()
    def test_maintain_subscriptions_silently_handles_repeated_exception(self, worker, state_manager, subscription_controller):
        """_maintain_subscriptions silently handles repeated exceptions with same message."""
        ## Arrange
        state_manager.is_authenticated.return_value = True
        error_msg = 'reconcile error'
        subscription_controller.reconcile_bindings.side_effect = RuntimeError(error_msg)
        worker._last_error = error_msg

        ## Act
        worker._maintain_subscriptions()

        ## Assert
        state_manager.set_state.assert_not_called()


class TestWsRuntimeWorkerRun:
    @capture_logs(logger_level='DEBUG', expected_errors=['Runtime thread stopped'], partial_match=True)
    def test_run_starts_and_stops_cleanly(self, worker, lifecycle, state_manager):
        """run starts thread, processes cycles, and stops cleanly."""
        ## Arrange
        worker._running = True
        state_manager.get_state.return_value = WsState.STOPPED
        call_count = [0]

        def cycle_side_effect():
            call_count[0] += 1
            if call_count[0] >= 2:
                worker._running = False

        worker._cycle = Mock(side_effect=cycle_side_effect)

        ## Act
        worker.run(lifecycle)

        ## Assert
        assert worker._lifecycle is lifecycle
        assert call_count[0] == 2

    @capture_logs(logger_level='ERROR', expected_errors=['External error in runtime thread'], partial_match=True)
    def test_run_handles_external_broker_error(self, worker, lifecycle, state_manager):
        """run catches and logs ExternalBrokerError."""
        ## Arrange
        worker._running = True
        state_manager.get_state.return_value = WsState.STOPPED
        call_count = [0]

        def cycle_side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                raise ExternalBrokerError('test error')
            worker._running = False

        worker._cycle = Mock(side_effect=cycle_side_effect)

        ## Act
        worker.run(lifecycle)

        ## Assert
        assert call_count[0] == 2

    @capture_logs(logger_level='ERROR', expected_errors=['Runtime thread exception'], partial_match=True)
    def test_run_handles_generic_exception(self, worker, lifecycle, state_manager):
        """run catches and logs generic exceptions."""
        ## Arrange
        worker._running = True
        state_manager.get_state.return_value = WsState.STOPPED
        call_count = [0]

        def cycle_side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError('test error')
            worker._running = False

        worker._cycle = Mock(side_effect=cycle_side_effect)

        ## Act
        worker.run(lifecycle)

        ## Assert
        assert call_count[0] == 2

    @capture_logs(logger_level='DEBUG', expected_errors=['Runtime thread stopped'], partial_match=True)
    def test_run_final_pass_when_not_stopped_or_closed(self, worker, lifecycle, state_manager, event_handler, subscription_controller):
        """run performs final pass when state is not STOPPED or CLOSED."""
        ## Arrange
        worker._running = True
        state_manager.get_state.return_value = WsState.DEGRADED
        call_count = [0]

        def cycle_side_effect():
            call_count[0] += 1
            if call_count[0] >= 1:
                worker._running = False

        worker._cycle = Mock(side_effect=cycle_side_effect)

        ## Act
        worker.run(lifecycle)

        ## Assert
        event_handler.process_transport_queue.assert_called()
        subscription_controller.reconcile_bindings.assert_called()

    @capture_logs(logger_level='DEBUG', expected_errors=['Runtime thread started'], partial_match=True)
    def test_run_skips_final_pass_when_stopped(self, worker, lifecycle, state_manager, event_handler, subscription_controller):
        """run skips final pass when state is STOPPED."""
        ## Arrange
        worker._running = True
        state_manager.get_state.return_value = WsState.STOPPED
        call_count = [0]

        def cycle_side_effect():
            call_count[0] += 1
            if call_count[0] >= 1:
                worker._running = False

        worker._cycle = Mock(side_effect=cycle_side_effect)

        ## Act
        worker.run(lifecycle)

        ## Assert
        event_handler.process_transport_queue.assert_not_called()
        subscription_controller.reconcile_bindings.assert_not_called()

    @capture_logs(logger_level='DEBUG', expected_errors=['Runtime thread stopped'], partial_match=True)
    def test_run_skips_final_pass_when_closed(self, worker, lifecycle, state_manager, event_handler, subscription_controller):
        """run skips final pass when state is CLOSED."""
        ## Arrange
        worker._running = True
        state_manager.get_state.return_value = WsState.CLOSED
        call_count = [0]

        def cycle_side_effect():
            call_count[0] += 1
            if call_count[0] >= 1:
                worker._running = False

        worker._cycle = Mock(side_effect=cycle_side_effect)

        ## Act
        worker.run(lifecycle)

        ## Assert
        event_handler.process_transport_queue.assert_not_called()
        subscription_controller.reconcile_bindings.assert_not_called()


class TestWsRuntimeWorkerCycle:
    @capture_logs()
    def test_cycle_maintains_transport(self, worker, lifecycle, event_handler):
        """_cycle calls maintain_transport on lifecycle."""
        ## Arrange
        worker._lifecycle = lifecycle
        worker._maintain_subscriptions = Mock()

        ## Act
        worker._cycle()

        ## Assert
        lifecycle.maintain_transport.assert_called_once()
        worker._maintain_subscriptions.assert_called_once()
        event_handler.process_transport_queue.assert_called_once()

    @capture_logs()
    def test_cycle_waits_for_interval(self, worker, lifecycle):
        """_cycle waits for cycle_interval."""
        ## Arrange
        worker._lifecycle = lifecycle
        worker._wait_event = Mock(spec=Event)

        ## Act
        worker._cycle()

        ## Assert
        worker._wait_event.wait.assert_called_once_with(0.01)
        worker._wait_event.clear.assert_called_once()

    @capture_logs(logger_level='WARNING', expected_errors=['Health check failed, resetting transport websocket'], partial_match=True)
    def test_cycle_resets_websocket_when_health_fails(self, worker, lifecycle, health_monitor):
        """_cycle resets websocket when health check fails."""
        ## Arrange
        worker._lifecycle = lifecycle
        worker._running = True
        health_monitor.health_ok.return_value = False

        ## Act
        worker._cycle()

        ## Assert
        lifecycle.reset_websocket_app.assert_called_once()

    @capture_logs()
    def test_cycle_returns_false_when_health_fails_and_not_running(self, worker, lifecycle, health_monitor):
        """_cycle returns False when health fails and runtime stopped."""
        ## Arrange
        worker._lifecycle = lifecycle
        worker._running = False
        health_monitor.health_ok.return_value = False

        ## Act
        result = worker._cycle()

        ## Assert
        assert result is False
        lifecycle.reset_websocket_app.assert_not_called()

    @capture_logs()
    def test_cycle_does_not_reset_when_health_ok(self, worker, lifecycle, health_monitor):
        """_cycle does not reset websocket when health is ok."""
        ## Arrange
        worker._lifecycle = lifecycle
        health_monitor.health_ok.return_value = True

        ## Act
        worker._cycle()

        ## Assert
        lifecycle.reset_websocket_app.assert_not_called()

    @capture_logs()
    def test_cycle_increments_counter(self, worker, lifecycle):
        """_cycle increments the cycle counter."""
        ## Arrange
        worker._lifecycle = lifecycle
        initial_count = worker._cycle_counter

        ## Act
        worker._cycle()

        ## Assert
        assert worker._cycle_counter == initial_count + 1


class TestWsRuntimeWorkerWaitForOneCycle:
    @capture_logs()
    def test_wait_for_one_cycle_waits_for_exactly_one_cycle(self, worker, lifecycle):
        """wait_for_one_cycle waits for exactly one cycle to complete."""
        ## Arrange
        worker.running = True
        initial_count = worker._cycle_counter

        thread = Thread(target=worker.run, daemon=True, args=(lifecycle,))
        thread.start()

        ## Act
        worker.wait_for_one_cycle()
        worker.running = False
        count_after_wait = worker._cycle_counter

        ## Assert
        assert count_after_wait >= initial_count + 1

        thread.join(timeout=1)
