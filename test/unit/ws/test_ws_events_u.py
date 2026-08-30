from datetime import datetime

import pytest

from ibind import WsState
from ibind.events import (
    WsOpen,
    WsAuthenticated,
    WsDegraded,
    WsReady,
    WsClose,
    WsError,
)
from test.test_utils import capture_logs


class TestWsEvent:
    @capture_logs()
    def test_immutability(self):
        """WsEvent instances are immutable after creation."""
        ## Arrange
        event = WsOpen(previous_state=WsState.STARTING, current_state=WsState.OPEN)

        ## Act / Assert
        with pytest.raises(Exception):
            event.received_at = datetime.now()  # NOQA

    @capture_logs()
    def test_extra_fields_forbidden(self):
        """WsEvent rejects extra fields not in the model."""
        ## Arrange / Act / Assert
        with pytest.raises(Exception):
            WsOpen(previous_state=WsState.STARTING, current_state=WsState.OPEN, extra_field='value')  # NOQA


@capture_logs()
def test_lifecycle_events():
    """Lifecycle events can be created with default received_at and optional fields."""
    ## Arrange / Act
    ws_open = WsOpen(previous_state=WsState.STARTING, current_state=WsState.OPEN)
    ws_authenticated = WsAuthenticated(previous_state=WsState.OPEN, current_state=WsState.AUTHENTICATED)
    ws_degraded = WsDegraded(previous_state=WsState.AUTHENTICATED, current_state=WsState.DEGRADED)
    ws_ready = WsReady(previous_state=WsState.AUTHENTICATED, current_state=WsState.AUTHENTICATED)
    ws_close_with_fields = WsClose(close_status_code=1000, close_msg='normal closure', previous_state=WsState.OPEN, current_state=WsState.CLOSED)
    ws_close_with_none = WsClose(close_status_code=None, close_msg=None, previous_state=WsState.STOPPING, current_state=WsState.CLOSED)
    error = RuntimeError('connection failed')
    ws_error = WsError(error=error, previous_state=WsState.OPEN, current_state=WsState.DEGRADED)

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
