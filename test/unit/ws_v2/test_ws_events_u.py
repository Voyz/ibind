import threading
import time
from datetime import datetime
from queue import Empty, Full
from unittest.mock import MagicMock, patch

import pytest

from ibind.events import (
    WsOpen,
    WsAuthenticated,
    WsDegraded,
    WsReady,
    WsClose,
    WsError,
)
from ibind import (
    NoopSink,
    CallbackSink,
    QueueSink,
    CompositeSink,
    EventSink,
)
from test.test_utils import capture_logs
from ws_v2._ws_events import AsyncSink


@pytest.fixture
def noop_sink():
    return NoopSink()


@pytest.fixture
def callback_sink():
    return CallbackSink()


@pytest.fixture
def queue_sink():
    sink = QueueSink()
    sink._queues.clear()
    return sink


@pytest.fixture
def sample_event():
    return WsOpen()


class TestWsEvent:
    @capture_logs()
    def test_immutability(self):
        """WsEvent instances are immutable after creation."""
        ## Arrange
        event = WsOpen()

        ## Act / Assert
        with pytest.raises(Exception):
            event.received_at = datetime.now()  # NOQA

    @capture_logs()
    def test_extra_fields_forbidden(self):
        """WsEvent rejects extra fields not in the model."""
        ## Arrange / Act / Assert
        with pytest.raises(Exception):
            WsOpen(extra_field='value')  # NOQA


@capture_logs()
def test_lifecycle_events():
    """Lifecycle events can be created with default received_at and optional fields."""
    ## Arrange / Act
    ws_open = WsOpen()
    ws_authenticated = WsAuthenticated()
    ws_degraded = WsDegraded()
    ws_ready = WsReady()
    ws_close_with_fields = WsClose(close_status_code=1000, close_msg='normal closure')
    ws_close_with_none = WsClose(close_status_code=None, close_msg=None)
    error = RuntimeError('connection failed')
    ws_error = WsError(error=error)

    ## Assert
    assert isinstance(ws_open.received_at, datetime)
    assert isinstance(ws_authenticated.received_at, datetime)
    assert isinstance(ws_degraded.received_at, datetime)
    assert isinstance(ws_ready.received_at, datetime)
    assert ws_close_with_fields.close_status_code == 1000
    assert ws_close_with_fields.close_msg == 'normal closure'
    assert ws_close_with_none.close_status_code is None
    assert ws_close_with_none.close_msg is None
    assert ws_error.error is error


class TestCallbackSink:
    @capture_logs()
    def test_on_registers_callback(self, callback_sink):
        """CallbackSink.on registers a callback for an event type."""
        ## Arrange
        callback = MagicMock()

        ## Act
        callback_sink.on(WsOpen, callback)

        ## Assert
        assert WsOpen in callback_sink._callbacks
        assert callback in callback_sink._callbacks[WsOpen]

    @capture_logs()
    def test_emit_calls_registered_callback(self, callback_sink, sample_event):
        """CallbackSink.emit invokes callbacks registered for the event type."""
        ## Arrange
        callback = MagicMock()
        callback_sink.on(WsOpen, callback)

        ## Act
        callback_sink.emit(sample_event)

        ## Assert
        callback.assert_called_once_with(sample_event)

    @capture_logs()
    def test_emit_ignores_unregistered_event_types(self, callback_sink):
        """CallbackSink.emit does not call callbacks for unregistered event types."""
        ## Arrange
        callback = MagicMock()
        callback_sink.on(WsOpen, callback)
        event = WsClose(close_status_code=1000, close_msg='')

        ## Act
        callback_sink.emit(event)

        ## Assert
        callback.assert_not_called()

    @capture_logs()
    def test_emit_multiple_callbacks(self, callback_sink, sample_event):
        """CallbackSink.emit calls all callbacks registered for an event type."""
        ## Arrange
        callback1 = MagicMock()
        callback2 = MagicMock()
        callback_sink.on(WsOpen, callback1)
        callback_sink.on(WsOpen, callback2)

        ## Act
        callback_sink.emit(sample_event)

        ## Assert
        callback1.assert_called_once_with(sample_event)
        callback2.assert_called_once_with(sample_event)

    @capture_logs(logger_level='ERROR', expected_errors=['Exception emitting event to callback test_fn'], partial_match=True)
    def test_emit_logs_callback_exception(self, callback_sink, sample_event):
        """CallbackSink.emit logs exceptions raised by callbacks without propagating."""
        ## Arrange
        def test_fn(event):
            raise ValueError('callback error')
        callback_sink.on(WsOpen, test_fn)

        ## Act
        callback_sink.emit(sample_event)


class TestQueueSink:
    @capture_logs()
    def test_new_queue_accessor_creates_accessor(self, queue_sink):
        """QueueSink.new_queue_accessor returns a QueueAccessor for the event type."""
        ## Act
        accessor = queue_sink.new_queue_accessor(WsOpen)

        ## Assert
        assert accessor.key == WsOpen

    @capture_logs()
    def test_emit_puts_event_in_queue(self, queue_sink, sample_event):
        """QueueSink.emit adds the event to the queue for its type."""
        ## Act
        queue_sink.emit(sample_event)

        ## Assert
        retrieved = queue_sink.get(WsOpen, block=False)
        assert retrieved is sample_event

    @capture_logs()
    def test_get_returns_none_when_empty(self, queue_sink):
        """QueueSink.get returns None when the queue is empty and block=False."""
        ## Act
        result = queue_sink.get(WsOpen, block=False)

        ## Assert
        assert result is None


    @capture_logs()
    def test_empty_returns_true_when_empty(self, queue_sink):
        """QueueSink.empty returns True when no events are queued."""
        ## Act
        result = queue_sink.empty(WsOpen)

        ## Assert
        assert result is True

    @capture_logs()
    def test_empty_returns_false_when_not_empty(self, queue_sink):
        """QueueSink.empty returns False when events are queued."""
        ## Arrange
        queue_sink.emit(WsOpen())

        ## Act
        result = queue_sink.empty(WsOpen)

        ## Assert
        assert result is False

    @capture_logs()
    def test_separate_queues_per_event_type(self, queue_sink):
        """QueueSink maintains separate queues for different event types."""
        ## Arrange
        event1 = WsOpen()
        event2 = WsClose(close_status_code=1000, close_msg='')

        ## Act
        queue_sink.emit(event1)
        queue_sink.emit(event2)

        ## Assert
        retrieved1 = queue_sink.get(WsOpen, block=False)
        retrieved2 = queue_sink.get(WsClose, block=False)
        assert isinstance(retrieved1, WsOpen)
        assert isinstance(retrieved2, WsClose)
        assert queue_sink.get(WsOpen, block=False) is None


class TestCompositeSink:
    @capture_logs()
    def test_emit_calls_all_sinks(self, sample_event):
        """CompositeSink.emit forwards the event to all registered sinks."""
        ## Arrange
        sink1 = MagicMock()
        sink2 = MagicMock()
        composite = CompositeSink(sink1, sink2)

        ## Act
        composite.emit(sample_event)

        ## Assert
        sink1.emit.assert_called_once_with(sample_event)
        sink2.emit.assert_called_once_with(sample_event)

    @capture_logs(logger_level='WARNING', expected_errors=['Exception emitting event to sink'], partial_match=True)
    def test_emit_logs_sink_exception(self, sample_event):
        """CompositeSink.emit logs exceptions from sinks without propagating."""
        ## Arrange
        sink1 = MagicMock()
        sink1.emit.side_effect = ValueError('sink error')
        sink2 = MagicMock()
        composite = CompositeSink(sink1, sink2)

        ## Act
        composite.emit(sample_event)

        ## Assert
        sink2.emit.assert_called_once_with(sample_event)


class TestAsyncSink:
    @capture_logs()
    def test_start_launches_thread(self, noop_sink):
        """AsyncSink.start launches a background thread."""
        ## Arrange
        sink = AsyncSink(noop_sink)

        ## Act
        sink.start()

        ## Assert
        assert sink._running is True
        assert sink._thread is not None
        assert sink._thread.is_alive()

        ## Cleanup
        sink.stop()

    @capture_logs()
    def test_start_idempotent(self, noop_sink):
        """AsyncSink.start does not launch multiple threads if already running."""
        ## Arrange
        sink = AsyncSink(noop_sink)
        sink.start()
        first_thread = sink._thread

        ## Act
        sink.start()

        ## Assert
        assert sink._thread is first_thread

        ## Cleanup
        sink.stop()

    @capture_logs()
    def test_stop_terminates_thread(self, noop_sink):
        """AsyncSink.stop terminates the background thread."""
        ## Arrange
        sink = AsyncSink(noop_sink)
        sink.start()

        ## Act
        result = sink.stop()

        ## Assert
        assert result is True
        assert sink._running is False
        assert sink._thread is None

    @capture_logs()
    def test_stop_idempotent(self, noop_sink):
        """AsyncSink.stop returns True when already stopped."""
        ## Arrange
        sink = AsyncSink(noop_sink)

        ## Act
        result = sink.stop()

        ## Assert
        assert result is True

    @capture_logs()
    def test_stop_from_same_thread_raises(self, noop_sink):
        """AsyncSink.stop raises RuntimeError when called from the sink thread."""
        ## Arrange
        sink = AsyncSink(noop_sink)
        exception_holder = {'exception': None}
        ev = threading.Event()

        def stop_from_thread():
            try:
                sink.stop()
            except RuntimeError as e:
                exception_holder['exception'] = e
                ev.set()

        sink._cycle = stop_from_thread
        ev.clear()
        sink.start()
        ev.wait(10)

        ## Assert
        assert exception_holder['exception'] is not None
        assert 'Stopping async sink called from within async sink thread' in str(exception_holder['exception'])

        ## Cleanup
        sink._running = False

    @capture_logs()
    def test_emit_queues_event(self, sample_event):
        """AsyncSink.emit adds events to the internal queue."""
        ## Arrange
        inner_sink = MagicMock()
        sink = AsyncSink(inner_sink)
        sink.start()

        ## Act
        sink.emit(sample_event)
        sink._consume_queue()

        ## Assert
        inner_sink.emit.assert_called_with(sample_event)

        ## Cleanup
        sink.stop()

    @capture_logs(logger_level='WARNING', expected_errors=['dropping newest event'], partial_match=True)
    def test_emit_drops_newest_when_full(self):
        """AsyncSink.emit drops the newest event when queue is full and drop_oldest=False."""
        ## Arrange
        inner_sink = MagicMock()
        sink = AsyncSink(inner_sink, maxsize=1, drop_oldest=False)
        event1 = WsOpen()
        event2 = WsAuthenticated()

        ## Act

        sink.emit(event1)
        sink.emit(event2)

    @capture_logs(logger_level='WARNING', expected_errors=['dropping oldest event'], partial_match=True)
    def test_emit_drops_oldest_when_full(self):
        """AsyncSink.emit drops the oldest event when queue is full and drop_oldest=True."""
        ## Arrange
        inner_sink = MagicMock()
        sink = AsyncSink(inner_sink, maxsize=1, drop_oldest=True)
        event1 = WsOpen()
        event2 = WsAuthenticated()

        ## Act
        sink.emit(event1)
        sink.emit(event2)

    @capture_logs()
    def test_consume_queue_forwards_events(self):
        """AsyncSink forwards queued events to the inner sink."""
        ## Arrange
        inner_sink = MagicMock()
        sink = AsyncSink(inner_sink)
        sink.start()
        event1 = WsOpen()
        event2 = WsAuthenticated()

        ## Act
        sink.emit(event1)
        sink.emit(event2)
        sink._consume_queue()

        ## Assert
        assert inner_sink.emit.call_count == 2
        inner_sink.emit.assert_any_call(event1)
        inner_sink.emit.assert_any_call(event2)

        ## Cleanup
        sink.stop()

    @capture_logs(logger_level='ERROR', expected_errors=['sink error'], partial_match=True)
    def test_consume_queue_logs_exception(self):
        """AsyncSink logs exceptions from the inner sink without stopping."""
        ## Arrange
        inner_sink = MagicMock(spec=EventSink)
        inner_sink.emit.side_effect = ValueError('sink error')
        sink = AsyncSink(inner_sink)
        event = WsOpen()

        sink.emit(event)
        sink._consume_queue()

    @capture_logs()
    def test_cycle_consumes_remaining_events_on_stop(self):
        """AsyncSink processes remaining events in queue when stopping."""
        ## Arrange
        inner_sink = MagicMock()
        sink = AsyncSink(inner_sink, cycle_interval=0.5)
        sink.start()
        event1 = WsOpen()
        event2 = WsAuthenticated()

        ## Act
        sink.emit(event1)
        sink.emit(event2)
        sink.stop()

        ## Assert
        assert inner_sink.emit.call_count >= 2

    @capture_logs(logger_level='WARNING', expected_errors=['Event queue not empty when stopping'], partial_match=True)
    def test_stop_warns_when_queue_not_empty(self):
        """AsyncSink logs warning when stopping with events still in queue."""
        ## Arrange
        inner_sink = MagicMock()
        sink = AsyncSink(inner_sink, maxsize=10)
        event = WsOpen()

        ## Act
        sink._running = True
        sink._queue.put(event)
        sink.stop()

    def test_emit_handles_empty_exception_when_dropping_oldest(self):
        """AsyncSink handles Empty exception when queue becomes empty between full check and get."""
        ## Arrange
        inner_sink = MagicMock()
        sink = AsyncSink(inner_sink, maxsize=1, drop_oldest=True)
        event1 = WsOpen()
        event2 = WsAuthenticated()

        ## Act
        with patch.object(sink._queue, 'put_nowait', side_effect=[Full, None]) as mock_put:
            with patch.object(sink._queue, 'get_nowait', side_effect=Empty):
                sink.emit(event1)

        ## Assert
        assert mock_put.call_count == 2

    @capture_logs(
        logger_level='WARNING',
        expected_errors=['Event queue full; dropping oldest event', 'Event queue still full; dropping event'],
        partial_match=True,
    )
    def test_emit_warns_when_queue_still_full_after_drop(self):
        """AsyncSink logs warning when queue is still full after dropping oldest event."""
        ## Arrange
        inner_sink = MagicMock()
        sink = AsyncSink(inner_sink, maxsize=1, drop_oldest=True)
        event1 = WsOpen()
        event2 = WsAuthenticated()

        ## Act
        with patch.object(sink._queue, 'put_nowait', side_effect=[Full, Full]) as mock_put:
            with patch.object(sink._queue, 'get_nowait', return_value=event1):
                sink.emit(event2)
