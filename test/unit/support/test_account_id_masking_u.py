import importlib
import io
import logging
import sys
from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import ConnectionError as RequestsConnectionError, ReadTimeout

from ibind import var
from ibind.client.ibkr_client import IbkrClient
from ibind.ibkr_ws.ibkr_events import AccountSummary
from ibind.ibkr_ws.ibkr_subscriptions import AccountSummarySubscription, IbkrSubscriptionResolver
from ibind.support import logs
from ibind.support.errors import ExternalBrokerError
from ibind.support.logs import mask_account_ids
from ibind.ws.runtime.ws_state_manager import WsState
from ibind.ws.ws_runtime import WsRuntime
from ibind.ws.ws_sinks import LogSink, NoopSink
from ibind.ws.ws_subscriptions import SubscriptionController

LIVE_ID = 'U00000001'
LIVE_MASKED = 'U***0001'
PAPER_ID = 'DU0000002'
PAPER_MASKED = 'DU***0002'

CONSOLE_FORMAT = '%(name)s|%(levelname)s| %(message)s'


def _ibind_loggers():
    names = [name for name in logging.root.manager.loggerDict if name == 'ibind' or name.startswith(('ibind.', 'ibind_fh'))]
    return {name: logging.getLogger(name) for name in names + ['ibind', 'ibind_fh']}


class LogOutput:
    def __init__(self, stream, logs_dir):
        self._stream = stream
        self._logs_dir = logs_dir

    def console(self) -> str:
        return self._stream.getvalue()

    def files(self) -> str:
        return ''.join(path.read_text(encoding='utf-8') for path in sorted(self._logs_dir.rglob('*.txt')))


@pytest.fixture
def log_output(monkeypatch, tmp_path):
    """
    Initialises IBind logging as an application would: the built-in console handler writing to a captured
    stdout, and the built-in daily rotating file handlers writing to `tmp_path`.
    """
    stream = io.StringIO()
    monkeypatch.setattr(sys, 'stdout', stream)
    monkeypatch.setattr(var, 'LOGS_DIR', str(tmp_path))
    monkeypatch.setattr(logs, '_initialized', False)
    monkeypatch.setattr(logs, '_log_to_file', logs._log_to_file)

    snapshot = {name: (list(logger.handlers), list(logger.filters)) for name, logger in _ibind_loggers().items()}
    for name, logger in _ibind_loggers().items():
        if name.startswith('ibind_fh'):
            logger.filters = []

    logs.ibind_logs_initialize(log_to_console=True, log_to_file=True, log_level='DEBUG', log_format=CONSOLE_FORMAT, print_file_logs=False)

    yield LogOutput(stream, tmp_path)

    for name, logger in _ibind_loggers().items():
        handlers, filters = snapshot.get(name, ([], []))
        for handler in logger.handlers:
            if handler not in handlers:
                handler.close()
        logger.handlers = handlers
        logger.filters = filters


@pytest.fixture(params=[True, False], ids=['masking_on', 'masking_off'])
def masking(request, monkeypatch):
    monkeypatch.setattr(var, 'MASK_ACCOUNT_IDS', request.param, raising=False)
    return request.param


def _assert_masking(text, enabled, *pairs):
    for raw, masked in pairs:
        if enabled:
            assert raw not in text, f'raw account id {raw!r} in log output:\n{text}'
            assert masked in text, f'masked account id {masked!r} missing from log output:\n{text}'
        else:
            assert raw in text, f'account id {raw!r} missing from unmasked log output:\n{text}'
            assert masked not in text


@pytest.fixture
def client():
    c = IbkrClient(use_oauth=False)
    c.post = MagicMock()
    return c


def test_mask_account_ids_in_free_text():
    text = f"GET /portfolio/{LIVE_ID}/positions {{'params': {{'acctId': '{PAPER_ID}'}}}} conid=265598 orderId=U123456789012"

    masked = mask_account_ids(text)

    assert LIVE_ID not in masked and PAPER_ID not in masked
    assert LIVE_MASKED in masked and PAPER_MASKED in masked
    assert 'conid=265598' in masked
    assert 'orderId=U123456789012' in masked
    assert mask_account_ids('DU1234567') == 'DU***4567'


def test_mask_account_ids_is_enabled_by_default(monkeypatch):
    try:
        monkeypatch.delenv('IBIND_MASK_ACCOUNT_IDS', raising=False)
        importlib.reload(var)
        assert var.MASK_ACCOUNT_IDS is True

        monkeypatch.setenv('IBIND_MASK_ACCOUNT_IDS', 'False')
        importlib.reload(var)
        assert var.MASK_ACCOUNT_IDS is False
    finally:
        monkeypatch.undo()
        importlib.reload(var)


##### Built-in handlers #####


def test_console_output(log_output, masking):
    ## Act
    logging.getLogger('ibind').info(f'GET portfolio/{LIVE_ID}/positions acctId={PAPER_ID}')

    ## Assert
    _assert_masking(log_output.console(), masking, (LIVE_ID, LIVE_MASKED), (PAPER_ID, PAPER_MASKED))


def test_file_output(log_output, masking):
    ## Arrange
    logger = logs.new_daily_rotating_file_handler('MaskingTest', str(log_output._logs_dir / 'masking_test'))

    ## Act
    logger.info(f'GET portfolio/{LIVE_ID}/positions acctId={PAPER_ID}')

    ## Assert
    _assert_masking(log_output.files(), masking, (LIVE_ID, LIVE_MASKED), (PAPER_ID, PAPER_MASKED))


def test_console_output_of_child_logger(log_output, masking):
    ## Act
    logging.getLogger('ibind.ibkr_ws_client.some.child').info(f'Sending payload: ssd+{PAPER_ID}+{{}}')

    ## Assert
    _assert_masking(log_output.console(), masking, (PAPER_ID, PAPER_MASKED))


def test_file_output_of_child_logger(log_output, masking):
    ## Arrange
    logs.new_daily_rotating_file_handler('MaskingTest', str(log_output._logs_dir / 'masking_test'))

    ## Act
    logging.getLogger('ibind_fh.MaskingTest.child').info(f'GET portfolio/{LIVE_ID}/positions')

    ## Assert
    _assert_masking(log_output.files(), masking, (LIVE_ID, LIVE_MASKED))


def _log_exception(logger):
    try:
        raise ValueError(f'Unknown account {PAPER_ID}')
    except ValueError:
        logger.exception('Request failed')


def test_console_exception_traceback(log_output, masking):
    ## Act
    _log_exception(logging.getLogger('ibind.ibkr_ws_client'))

    ## Assert
    output = log_output.console()
    assert 'Traceback (most recent call last)' in output
    assert f'ValueError: Unknown account {PAPER_MASKED if masking else PAPER_ID}' in output
    _assert_masking(output, masking, (PAPER_ID, PAPER_MASKED))


def test_file_exception_traceback(log_output, masking):
    ## Arrange
    logger = logs.new_daily_rotating_file_handler('MaskingTest', str(log_output._logs_dir / 'masking_test'))

    ## Act
    _log_exception(logger)

    ## Assert
    output = log_output.files()
    assert 'Traceback (most recent call last)' in output
    assert f'ValueError: Unknown account {PAPER_MASKED if masking else PAPER_ID}' in output
    _assert_masking(output, masking, (PAPER_ID, PAPER_MASKED))


def test_formatter_for_application_handlers(masking):
    ## Arrange
    from ibind import AccountIdMaskingFormatter

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(AccountIdMaskingFormatter('%(message)s'))
    logger = logging.getLogger('ibind.application_handler_test')
    logger.addHandler(handler)

    ## Act
    try:
        logger.info(f'GET portfolio/{LIVE_ID}/positions')
    finally:
        logger.removeHandler(handler)

    ## Assert
    _assert_masking(stream.getvalue(), masking, (LIVE_ID, LIVE_MASKED))


##### Log sites #####


def test_ws_runtime_send(log_output, masking):
    ## Arrange
    runtime = WsRuntime(
        url='wss://test.example.com',
        cycle_interval=0.01,
        sink=NoopSink(),
        router=MagicMock(),
        subscription_resolver=MagicMock(),
        connection_timeout=1.0,
        reconnect_timeout=1.0,
        max_ping_interval=20,
    )
    runtime._state_manager.set_state(WsState.AUTHENTICATED)
    runtime._transport.send = MagicMock(return_value=True)
    payload = f'ssd+{PAPER_ID}+{{}}'

    ## Act
    runtime.send(payload)

    ## Assert
    runtime._transport.send.assert_called_once_with(payload)
    assert 'Sending payload' in log_output.console()
    _assert_masking(log_output.console(), masking, (PAPER_ID, PAPER_MASKED))


def test_subscription_registration(log_output, masking):
    ## Arrange
    controller = SubscriptionController(
        send_payload=MagicMock(return_value=True), emitter=MagicMock(), subscription_resolver=IbkrSubscriptionResolver(PAPER_ID)
    )

    ## Act
    handle = controller.subscribe(AccountSummarySubscription(account_id=PAPER_ID))

    ## Assert
    assert handle.binding_key == f'sd+{PAPER_ID}'
    assert 'Registered subscription intent' in log_output.console()
    _assert_masking(log_output.console(), masking, (PAPER_ID, PAPER_MASKED))


def test_log_sink(log_output, masking):
    ## Arrange
    event = AccountSummary(account_id=PAPER_ID, data={'acctId': PAPER_ID})

    ## Act
    LogSink().emit(event)

    ## Assert
    assert event.account_id == PAPER_ID
    assert 'AccountSummary(' in log_output.console()
    _assert_masking(log_output.console(), masking, (PAPER_ID, PAPER_MASKED))


def test_rest_client_connection_error_retry(log_output, masking):
    ## Arrange
    client = IbkrClient(use_oauth=False, max_retries=1, verbose_retries=True, auto_recreate_session=False)
    client.use_session = True
    client._session = MagicMock()
    client._session.request.side_effect = RequestsConnectionError(f'Max retries exceeded with url: /v1/api/portfolio/{LIVE_ID}/positions/0')

    ## Act
    with patch('ibind.base.rest_client.time.sleep'), pytest.raises(ExternalBrokerError):
        client._request('GET', f'portfolio/{LIVE_ID}/positions/0')

    ## Assert
    assert 'Connection error detected' in log_output.console()
    assert 'Connection error detected' in log_output.files()
    _assert_masking(log_output.console(), masking, (LIVE_ID, LIVE_MASKED))
    _assert_masking(log_output.files(), masking, (LIVE_ID, LIVE_MASKED))


def test_rest_client_unexpected_error_traceback(log_output, masking):
    ## Arrange
    client = IbkrClient(use_oauth=False)
    client.use_session = True
    client._session = MagicMock()
    client._session.request.side_effect = ValueError(f'Unexpected response for account {LIVE_ID}')

    ## Act
    with pytest.raises(ExternalBrokerError):
        client._request('GET', f'portfolio/{LIVE_ID}/summary')

    ## Assert
    output = log_output.files()
    assert 'Traceback (most recent call last)' in output
    _assert_masking(output, masking, (LIVE_ID, LIVE_MASKED))


@pytest.mark.parametrize('raw, masked', [(LIVE_ID, LIVE_MASKED), (PAPER_ID, PAPER_MASKED)])
def test_switch_account(log_output, client, raw, masked):
    ## Act
    client.switch_account(raw)

    ## Assert
    client.post.assert_called_once_with('iserver/account', params={'acctId': raw})
    assert client.account_id == raw
    assert f'ALSO NEED TO SWITCH WEBSOCKET ACCOUNT TO {masked}' in log_output.console()
    _assert_masking(log_output.console() + log_output.files(), True, (raw, masked))


def test_switch_account_reminder_is_debug(client, caplog):
    ## Arrange
    caplog.set_level(logging.DEBUG)

    ## Act
    client.switch_account(PAPER_ID)

    ## Assert
    levels = [r.levelno for r in caplog.records if 'SWITCH WEBSOCKET ACCOUNT' in r.getMessage()]
    assert levels == [logging.DEBUG]


def test_new_client_banner(log_output, masking):
    ## Act
    IbkrClient(use_oauth=False, account_id=LIVE_ID)

    ## Assert
    assert 'New IbkrClient(' in log_output.files()
    _assert_masking(log_output.files(), masking, (LIVE_ID, LIVE_MASKED))
    _assert_masking(log_output.console(), masking, (LIVE_ID, LIVE_MASKED))


def test_request_and_retry_logs(log_output, masking):
    ## Arrange
    client = IbkrClient(use_oauth=False, max_retries=1, verbose_retries=True)
    client.use_session = True
    client._session = MagicMock()
    client._session.request.side_effect = ReadTimeout('timeout')

    ## Act
    with pytest.raises(TimeoutError):
        client._request('GET', f'portfolio/{LIVE_ID}/positions/0', params={'acctId': PAPER_ID})

    ## Assert
    assert 'Timeout for GET' in log_output.console()
    assert 'Timeout for GET' in log_output.files()
    _assert_masking(log_output.console(), masking, (LIVE_ID, LIVE_MASKED), (PAPER_ID, PAPER_MASKED))
    _assert_masking(log_output.files(), masking, (LIVE_ID, LIVE_MASKED), (PAPER_ID, PAPER_MASKED))


def test_response_log(log_output, masking):
    ## Arrange
    client = IbkrClient(use_oauth=False, log_responses=True)
    client.use_session = True
    client._session = MagicMock()
    client._session.request.return_value.json.return_value = {'accountId': LIVE_ID}

    ## Act
    result = client._request('GET', f'portfolio/{LIVE_ID}/summary')

    ## Assert
    assert result.data == {'accountId': LIVE_ID}
    assert 'Result(' in log_output.files()
    _assert_masking(log_output.files(), masking, (LIVE_ID, LIVE_MASKED))


def test_file_handler_path_logs(log_output, masking):
    ## Arrange
    filepath = str(log_output._logs_dir / f'ibkr_client_{LIVE_ID}')

    ## Act
    logs.new_daily_rotating_file_handler('MaskingTest', filepath)
    logs.new_daily_rotating_file_handler('MaskingTest', filepath)

    ## Assert
    output = log_output.console()
    assert 'New daily rotating file handler' in output
    assert 'Existing daily rotating file handler' in output
    _assert_masking(output, masking, (LIVE_ID, LIVE_MASKED))
