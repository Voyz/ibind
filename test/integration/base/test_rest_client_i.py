import asyncio
import logging
import threading

import pytest
from unittest.mock import MagicMock

from requests import ReadTimeout, Timeout

from ibind.client.ibkr_client import IbkrClient
from ibind.support.errors import ExternalBrokerError
from ibind.base.rest_client import Result, RestClient
from ibind.support.logs import ibind_logs_initialize
from test.test_utils_new import CaptureLogsContext


_URL = 'https://localhost:5000'
_TIMEOUT = 8
_MAX_RETRIES = 4
_DEFAULT_PATH = 'test/api/route'


@pytest.fixture
def client():
    ibind_logs_initialize(log_to_console=True)
    return RestClient(
        url=_URL,
        timeout=_TIMEOUT,
        max_retries=_MAX_RETRIES,
        use_session=False,
    )


@pytest.fixture
def data():
    return {'Test key': 'Test value'}


@pytest.fixture
def response(data):
    response = MagicMock()
    response.json.return_value = data
    return response


@pytest.fixture(autouse=True)
def requests_mock(mocker, response):
    requests_mock = mocker.patch('ibind.base.rest_client.requests')
    requests_mock.request.return_value = response
    return requests_mock


@pytest.fixture
def default_url():
    return f'{_URL}/{_DEFAULT_PATH}'


@pytest.fixture
def result(data, default_url):
    return Result(data=data, request={'url': default_url})


def test_default_rest_get(client, default_url, result, requests_mock):
    # Arrange
    # Act
    rv = client.get(_DEFAULT_PATH)

    # Assert
    assert result == rv
    requests_mock.request.assert_called_with('GET', default_url, verify=False, headers={}, timeout=_TIMEOUT)


def test_default_rest_post(client, default_url, result, requests_mock):
    # Arrange
    test_post_kwargs = {'field1': 'value1', 'field2': 'value2'}
    test_json = {'json': {**test_post_kwargs}}

    # Act
    rv = client.post(_DEFAULT_PATH, params=test_post_kwargs)

    # Assert
    assert result.copy(request={'url': default_url, **test_json}) == rv
    requests_mock.request.assert_called_with('POST', default_url, verify=False, headers={}, timeout=_TIMEOUT, **test_json)


def test_default_rest_delete(client, default_url, result, requests_mock):
    # Arrange
    # Act
    rv = client.delete(_DEFAULT_PATH)

    # Assert
    assert result == rv
    requests_mock.request.assert_called_with('DELETE', default_url, verify=False, headers={}, timeout=_TIMEOUT)


def test_request_retries(client, default_url, requests_mock):
    # Arrange
    requests_mock.request.side_effect = ReadTimeout()

    # Act
    with CaptureLogsContext('ibind.rest_client', level='INFO') as cm, pytest.raises(TimeoutError) as excinfo:
        client.get(_DEFAULT_PATH)

    # Assert
    for i in range(_MAX_RETRIES):
        assert f'RestClient: Timeout for GET {default_url} {{}}, retrying attempt {i + 1}/{_MAX_RETRIES}' in cm.output

    assert f'RestClient: Reached max retries ({_MAX_RETRIES}) for GET {default_url} {{}}' == str(excinfo.value)


def test_response_raise_timeout(client, requests_mock):
    # Arrange
    requests_mock.request.return_value.raise_for_status.side_effect = Timeout()

    # Act
    with pytest.raises(ExternalBrokerError) as excinfo:
        client.get(_DEFAULT_PATH)

    # Assert
    assert f'RestClient: Timeout error ({_TIMEOUT}S)' == str(excinfo.value)


def test_response_raise_generic(client, result, requests_mock):
    # Arrange
    response = requests_mock.request.return_value
    response.status_code = 400
    response.reason = 'Test reason'
    response.text = 'Test text'
    response.raise_for_status.side_effect = ValueError('Test generic error')

    # Act
    with pytest.raises(ExternalBrokerError) as excinfo:
        client.get(_DEFAULT_PATH)

    # Assert
    assert f'RestClient: response error {result.copy(data=None)} :: {response.status_code} :: {response.reason} :: {response.text}' == str(excinfo.value)


def _worker_in_thread(results: []):
    try:
        IbkrClient()
    except Exception as e:
        results.append(e)


def test_in_thread():
    """Run in thread ensuring client still is constructed without an exception."""
    # Arrange
    results = []
    t = threading.Thread(target=_worker_in_thread, args=(results,))
    t.daemon = True

    # Act
    t.start()
    t.join(1)

    # Assert
    for result in results:
        if isinstance(result, Exception):
            raise result


def test_without_thread():
    """Run without a thread to ensure it still works as expected."""
    # Arrange
    results = []

    # Act
    _worker_in_thread(results)

    # Assert
    for result in results:
        if isinstance(result, Exception):
            raise result


async def _async_worker(results: []):
    """Async version of the worker function to run in an asyncio event loop."""
    try:
        IbkrClient()
    except Exception as e:
        results.append(e)


def _worker_in_async_thread(results: []):
    """Runs the async test inside a new thread to check if signal handling breaks."""
    try:
        asyncio.run(_async_worker(results))
    except Exception as e:
        results.append(e)


def test_in_thread_async():
    """Test that IbkrClient() does not break in an asyncio thread."""
    # Arrange
    results = []
    t = threading.Thread(target=_worker_in_async_thread, args=(results,))
    t.daemon = True

    # Act
    t.start()
    t.join(1)

    # Assert
    for result in results:
        if isinstance(result, Exception):
            raise result


def test_without_thread_async():
    """Test that IbkrClient() does not break in the main asyncio event loop."""
    # Arrange
    results = []

    # Act
    asyncio.run(_async_worker(results))

    # Assert
    for result in results:
        if isinstance(result, Exception):
            raise result