from unittest.mock import Mock

import pytest

from ibind import WsState, events
from ibind.ws_v2._ws_events import WsEvent
from ibind.ws_v2.runtime.ws_emitter import WsEmitter
from ibind.ws_v2.runtime.ws_event_handler import WsEventHandler
from ibind.ws_v2.runtime.ws_state_manager import WsStateManager
from ibind.ws_v2.ws_subscriptions import SubscriptionController
from ibind.ws_v2.ws_transport import TransportEvent, TransportOpened, TransportReconnect, TransportClosed, TransportError, TransportMessage
from test.test_utils import capture_logs


@pytest.fixture
def state_manager():
    return Mock(spec=WsStateManager)


@pytest.fixture
def router():
    return Mock()


@pytest.fixture
def subscription_controller():
    return Mock(spec=SubscriptionController)


@pytest.fixture
def emitter():
    return Mock(spec=WsEmitter)


@pytest.fixture
def handler(state_manager, router, subscription_controller, emitter):
    return WsEventHandler(
        state_manager=state_manager,
        router=router,
        subscription_controller=subscription_controller,
        emitter=emitter,
    )


class TestWsEventHandlerProcessTransportQueue:
    @capture_logs()
    def test_empty_queue_does_nothing(self, handler):
        """process_transport_queue handles empty queue gracefully."""
        ## Act
        handler.process_transport_queue()

        ## Assert
        assert handler._transport_queue.empty()

    @capture_logs()
    def test_processes_single_event(self, handler, state_manager):
        """process_transport_queue processes single event."""
        ## Arrange
        event = TransportOpened()
        handler.put(event)

        ## Act
        handler.process_transport_queue()

        ## Assert
        assert handler._transport_queue.empty()
        state_manager.set_state.assert_called_once_with(WsState.OPEN)

    @capture_logs()
    def test_processes_multiple_events_in_order(self, handler, state_manager):
        """process_transport_queue processes events sorted by received_at."""
        ## Arrange
        from datetime import datetime, timedelta

        base_time = datetime.now()
        event1 = TransportOpened(received_at=base_time)
        event2 = TransportReconnect(received_at=base_time + timedelta(seconds=1))
        handler.put(event2)
        handler.put(event1)

        ## Act
        handler.process_transport_queue()

        ## Assert
        assert handler._transport_queue.empty()
        assert state_manager.set_state.call_count == 2
        calls = state_manager.set_state.call_args_list
        assert calls[0][0][0] == WsState.OPEN
        assert calls[1][0][0] == WsState.OPEN

    @capture_logs(expected_errors=['Exception processing transport event'], partial_match=True)
    def test_exception_during_processing_retries_event(self, handler, state_manager):
        """process_transport_queue retries event on exception."""
        ## Arrange
        event = TransportOpened()
        handler.put(event)
        state_manager.set_state.side_effect = [Exception('test error'), None]

        ## Act 1
        handler.process_transport_queue()

        ## Assert 1
        assert not handler._transport_queue.empty()
        assert event.get_attempt() == 1

        ## Act 2
        handler.process_transport_queue()

        ## Assert 2
        assert handler._transport_queue.empty()
        assert state_manager.set_state.call_count == 2
        assert event.get_attempt() == 1

    @capture_logs(expected_errors=['Exception processing transport event', 'Max retries'], partial_match=True)
    def test_drops_event_after_max_retries(self, handler, state_manager):
        """process_transport_queue drops event after max retries."""
        ## Arrange
        event = TransportOpened()
        handler.put(event)
        state_manager.set_state.side_effect = Exception('test error')

        ## Act
        for _ in range(6):
            handler.process_transport_queue()

        ## Assert
        assert handler._transport_queue.empty()
        assert event.get_attempt() == 6


class TestWsEventHandlerHandleTransportEvent:
    @capture_logs()
    def test_handles_transport_opened(self, handler, state_manager):
        """_handle_transport_event handles TransportOpened."""
        ## Arrange
        event = TransportOpened()

        ## Act
        handler._handle_transport_event(event)

        ## Assert
        state_manager.set_state.assert_called_once_with(WsState.OPEN)

    @capture_logs()
    def test_handles_transport_reconnect(self, handler, state_manager):
        """_handle_transport_event handles TransportReconnect."""
        ## Arrange
        event = TransportReconnect()

        ## Act
        handler._handle_transport_event(event)

        ## Assert
        state_manager.set_state.assert_called_once_with(WsState.OPEN)

    @capture_logs(error_level='INFO', expected_errors=['on_close error'], partial_match=True)
    def test_handles_transport_closed(self, handler, state_manager, emitter):
        """_handle_transport_event handles TransportClosed."""
        ## Arrange
        event = TransportClosed(close_status_code=1000, close_msg='Normal closure')
        state_manager.get_state.return_value = WsState.OPEN

        ## Act
        handler._handle_transport_event(event)

        ## Assert
        state_manager.set_state.assert_called_once_with(WsState.CLOSED)
        assert emitter.emit.call_count == 1

    @capture_logs(expected_errors=['Connection error'], partial_match=True)
    def test_handles_transport_error(self, handler, emitter):
        """_handle_transport_event handles TransportError."""
        ## Arrange
        exception = Exception('Connection error')
        event = TransportError(exception=exception)

        ## Act
        handler._handle_transport_event(event)

        ## Assert
        emitter.emit.assert_called_once()
        emitted_event = emitter.emit.call_args[0][0]
        assert isinstance(emitted_event, events.WsError)
        assert emitted_event.error is exception

    @capture_logs()
    def test_handles_transport_message(self, handler, router, subscription_controller, emitter):
        """_handle_transport_event handles TransportMessage."""
        ## Arrange
        message = '{"topic": "test"}'
        event = TransportMessage(message=message)
        mock_ws_event = Mock(spec=WsEvent)
        router.route.return_value = mock_ws_event

        ## Act
        handler._handle_transport_event(event)

        ## Assert
        router.route.assert_called_once_with(message)
        subscription_controller.observe.assert_called_once_with(mock_ws_event)
        emitter.emit.assert_called_once_with(mock_ws_event)

    @capture_logs(expected_errors=['Unknown event type'], partial_match=True)
    def test_unknown_event_type_logs_error(self, handler):
        """_handle_transport_event logs error for unknown event type."""
        ## Arrange
        event = Mock(spec=TransportEvent)

        ## Act
        handler._handle_transport_event(event)

        ## Assert


class TestWsEventHandlerHandleOnMessage:
    @capture_logs()
    def test_router_returns_none_skips_processing(self, handler, router, subscription_controller, emitter):
        """_handle_on_message skips processing when router returns None."""
        ## Arrange
        router.route.return_value = None

        ## Act
        handler._handle_on_message('test message')

        ## Assert
        router.route.assert_called_once_with('test message')
        subscription_controller.observe.assert_not_called()
        emitter.emit.assert_not_called()

    @capture_logs()
    def test_router_returns_single_event(self, handler, router, subscription_controller, emitter):
        """_handle_on_message processes single WsEvent."""
        ## Arrange
        mock_event = Mock(spec=WsEvent)
        router.route.return_value = mock_event

        ## Act
        handler._handle_on_message('test message')

        ## Assert
        subscription_controller.observe.assert_called_once_with(mock_event)
        emitter.emit.assert_called_once_with(mock_event)

    @capture_logs()
    def test_router_returns_list_of_events(self, handler, router, subscription_controller, emitter):
        """_handle_on_message processes list of WsEvents."""
        ## Arrange
        event1 = Mock(spec=WsEvent)
        event2 = Mock(spec=WsEvent)
        router.route.return_value = [event1, event2]

        ## Act
        handler._handle_on_message('test message')

        ## Assert
        assert subscription_controller.observe.call_count == 2
        assert emitter.emit.call_count == 2

    @capture_logs(expected_errors=['Exception observing subscription'], partial_match=True)
    def test_subscription_controller_exception_continues_processing(self, handler, router, subscription_controller, emitter):
        """_handle_on_message continues processing on subscription exception."""
        ## Arrange
        mock_event = Mock(spec=WsEvent)
        router.route.return_value = mock_event
        subscription_controller.observe.side_effect = Exception('subscription error')

        ## Act
        handler._handle_on_message('test message')

        ## Assert
        subscription_controller.observe.assert_called_once_with(mock_event)
        emitter.emit.assert_called_once_with(mock_event)


class TestWsEventHandlerHandleOnOpen:
    @capture_logs(logger_level='INFO', expected_errors=['Connection open'], partial_match=True)
    def test_sets_state_to_open(self, handler, state_manager):
        """_handle_on_open sets state to OPEN."""
        ## Act
        handler._handle_on_open()

        ## Assert
        state_manager.set_state.assert_called_once_with(WsState.OPEN)


class TestWsEventHandlerHandleOnReconnect:
    @capture_logs(logger_level='INFO', expected_errors=['Connection reopened'], partial_match=True)
    def test_sets_state_to_open(self, handler, state_manager):
        """_handle_on_reconnect sets state to OPEN."""
        ## Act
        handler._handle_on_reconnect()

        ## Assert
        state_manager.set_state.assert_called_once_with(WsState.OPEN)


class TestWsEventHandlerHandleOnError:
    @capture_logs(expected_errors=['Connection error'], partial_match=True)
    def test_logs_error_and_emits_event(self, handler, emitter):
        """_handle_on_error logs error and emits WsError event."""
        ## Arrange
        exception = Exception('Connection error')

        ## Act
        handler._handle_on_error(exception)

        ## Assert
        emitter.emit.assert_called_once()
        emitted_event = emitter.emit.call_args[0][0]
        assert isinstance(emitted_event, events.WsError)
        assert emitted_event.error is exception

    @capture_logs(expected_errors=['Connection to remote host was lost'], partial_match=True)
    def test_connection_lost_sets_degraded_state(self, handler, state_manager, emitter):
        """_handle_on_error sets DEGRADED state for connection lost."""
        ## Arrange
        exception = Exception('Connection to remote host was lost.')

        ## Act
        handler._handle_on_error(exception)

        ## Assert
        state_manager.set_state.assert_called_once_with(WsState.DEGRADED)
        emitter.emit.assert_called_once()

    @capture_logs(expected_errors=['No connection could be made'], partial_match=True)
    def test_connection_refused_sets_degraded_state(self, handler, state_manager, emitter):
        """_handle_on_error sets DEGRADED state for connection refused."""
        ## Arrange
        exception = Exception('No connection could be made because the target machine actively refused it')

        ## Act
        handler._handle_on_error(exception)

        ## Assert
        state_manager.set_state.assert_called_once_with(WsState.DEGRADED)
        emitter.emit.assert_called_once()


class TestWsEventHandlerHandleOnClose:
    @capture_logs(logger_level='INFO', expected_errors=['Connection closed'], partial_match=True)
    def test_normal_close_sets_state_to_closed(self, handler, state_manager, emitter):
        """_handle_on_close sets state to CLOSED on normal close."""
        ## Arrange
        state_manager.get_state.return_value = WsState.OPEN

        ## Act
        handler._handle_on_close(None, None)

        ## Assert
        assert state_manager.last_heartbeat is None
        state_manager.set_state.assert_called_once_with(WsState.CLOSED)
        emitter.emit.assert_called_once()

    @capture_logs(logger_level='INFO', expected_errors=[': Connection gracefully closed'], partial_match=True)
    def test_graceful_close_when_stopping(self, handler, state_manager, emitter):
        """_handle_on_close handles graceful close when STOPPING."""
        ## Arrange
        state_manager.get_state.return_value = WsState.STOPPING

        ## Act
        handler._handle_on_close(None, None)

        ## Assert
        state_manager.set_state.assert_called_once_with(WsState.CLOSED)
        emitter.emit.assert_called_once()

    @capture_logs(logger_level='INFO', expected_errors=['on_close error'], partial_match=True)
    def test_close_with_error_code_logs_error(self, handler, state_manager, emitter):
        """_handle_on_close logs error when close_status_code is provided."""
        ## Arrange
        state_manager.get_state.return_value = WsState.OPEN

        ## Act
        handler._handle_on_close(1006, 'Abnormal closure')

        ## Assert
        state_manager.set_state.assert_called_once_with(WsState.CLOSED)
        emitter.emit.assert_called_once()

    @capture_logs(error_level='INFO', expected_errors=['on_close error'], partial_match=True)
    def test_close_with_bytes_message_decodes(self, handler, state_manager, emitter):
        """_handle_on_close decodes bytes close_msg to utf-8."""
        ## Arrange
        state_manager.get_state.return_value = WsState.OPEN
        close_msg = b'Error message'

        ## Act
        handler._handle_on_close(1006, close_msg)

        ## Assert
        state_manager.set_state.assert_called_once_with(WsState.CLOSED)
        emitter.emit.assert_called_once()
