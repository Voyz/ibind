from ibind.support.logs import project_logger
from ibind.support.py_utils import exception_to_string
from ibind.ws_v2._ws_events import WsEvent, CallbackSink, EventSink

_LOGGER = project_logger('ibkr_ws_client')


class WsEmitter:  # pragma: no cover
    """
    Emits WebSocket events to both internal and external sinks.

    Forwards events to a CallbackSink for internal listeners and an EventSink for external
    consumers. Exceptions from either sink are logged but do not prevent the other from
    receiving the event.
    """

    def __init__(self, internal_sink: CallbackSink, sink: EventSink):
        """
        Create an emitter with internal and external sinks.

        Args:
            internal_sink (CallbackSink): Sink for internal event listeners.
            sink (EventSink): Sink for external event consumers.
        """
        self._internal_sink = internal_sink
        self._sink = sink

    def emit(self, event: WsEvent):
        """
        Emit an event to both internal and external sinks.

        Args:
            event (WsEvent): The event to emit.
        """
        try:
            self._internal_sink.emit(event)
        except Exception as e:
            _LOGGER.error(f'{self}: Internal sink exception for {event}: {exception_to_string(e)}')

        try:
            self._sink.emit(event)
        except Exception as e:
            _LOGGER.error(f'{self}: External sink exception for {event}: {exception_to_string(e)}')

    def __str__(self):  # pragma: no cover
        return f'{self.__class__.__qualname__}()'
