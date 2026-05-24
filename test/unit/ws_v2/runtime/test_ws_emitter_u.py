from unittest.mock import MagicMock

import pytest

from ibind.events import WsOpen
from ibind.ws_v2._ws_events import CallbackSink, EventSink
from ibind.ws_v2.runtime.ws_emitter import WsEmitter
from test.test_utils import capture_logs


@pytest.fixture
def internal_sink():
    sink = MagicMock(spec=CallbackSink)
    return sink


@pytest.fixture
def external_sink():
    sink = MagicMock(spec=EventSink)
    return sink


@pytest.fixture
def emitter(internal_sink, external_sink):
    return WsEmitter(internal_sink=internal_sink, sink=external_sink)


class TestWsEmitterInit:
    @capture_logs()
    def test_init_sets_attributes(self, internal_sink, external_sink):
        """WsEmitter.__init__ initializes all attributes correctly."""
        ## Act
        emitter = WsEmitter(internal_sink=internal_sink, sink=external_sink)

        ## Assert
        assert emitter._internal_sink is internal_sink
        assert emitter._sink is external_sink


class TestWsEmitterEmit:
    @capture_logs()
    def test_emit_sends_to_both_sinks(self, emitter, internal_sink, external_sink):
        """emit sends event to both internal and external sinks."""
        ## Arrange
        event = WsOpen()

        ## Act
        emitter.emit(event)

        ## Assert
        internal_sink.emit.assert_called_once_with(event)
        external_sink.emit.assert_called_once_with(event)

    @capture_logs(logger_level='ERROR', expected_errors=['Internal sink exception'], partial_match=True)
    def test_emit_logs_internal_sink_exception(self, emitter, internal_sink, external_sink):
        """emit logs exceptions from internal sink and continues to external sink."""
        ## Arrange
        event = WsOpen()
        internal_sink.emit.side_effect = RuntimeError('internal error')

        ## Act
        emitter.emit(event)

        ## Assert
        internal_sink.emit.assert_called_once_with(event)
        external_sink.emit.assert_called_once_with(event)

    @capture_logs(logger_level='ERROR', expected_errors=['External sink exception'], partial_match=True)
    def test_emit_logs_external_sink_exception(self, emitter, internal_sink, external_sink):
        """emit logs exceptions from external sink."""
        ## Arrange
        event = WsOpen()
        external_sink.emit.side_effect = RuntimeError('external error')

        ## Act
        emitter.emit(event)

        ## Assert
        internal_sink.emit.assert_called_once_with(event)
        external_sink.emit.assert_called_once_with(event)

    @capture_logs(logger_level='ERROR', expected_errors=['Internal sink exception', 'External sink exception'], partial_match=True)
    def test_emit_logs_both_sink_exceptions(self, emitter, internal_sink, external_sink):
        """emit logs exceptions from both sinks."""
        ## Arrange
        event = WsOpen()
        internal_sink.emit.side_effect = RuntimeError('internal error')
        external_sink.emit.side_effect = RuntimeError('external error')

        ## Act
        emitter.emit(event)

        ## Assert
        internal_sink.emit.assert_called_once_with(event)
        external_sink.emit.assert_called_once_with(event)
