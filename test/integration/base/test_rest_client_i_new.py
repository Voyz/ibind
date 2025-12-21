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


@pytest.fixture
def client_fixture():
    ibind_logs_initialize(log_to_console=True)
    url = 'https://localhost:5000'
    timeout = 8
    max_retries = 4
    client = RestClient(
        url=url,
        timeout=timeout,
        max_retries=max_retries,
        use_session=False,
    )
    data = {'Test key': 'Test value'}
    response = MagicMock()
    response.json.return_value = data
    default_path = 'test/api/route'
    default_url = f'{url}/{default_path}'
    result = Result(data=data, request={'url': default_url})
    return client, response, default_path, default_url, result, timeout, max_retries


def test_default_rest_get(client_fixture, mocker):
    # Arrange
    client, response, default_path, default_url, result, timeout, _ = client_fixture
    requests_mock = mocker.patch('ibind.base.rest_client.requests')
    requests_mock.request.return_value = response

    # Act
    rv = client.get(default_path)

    # Assert
    assert result == rv
    requests_mock.request.assert_called_with('GET', default_url, verify=False, headers={}, timeout=timeout)


def test_default_rest_post(client_fixture, mocker):
    # Arrange
    client, response, default_path, default_url, result, timeout, _ = client_fixture
    requests_mock = mocker.patch('ibind.base.rest_client.requests')
    requests_mock.request.return_value = response
    test_post_kwargs = {'field1': 'value1', 'field2': 'value2'}
    test_json = {'json': {**test_post_kwargs}}

    # Act
    rv = client.post(default_path, params=test_post_kwargs)

    # Assert
    assert result.copy(request={'url': default_url, **test_json}) == rv
    requests_mock.request.assert_called_with('POST', default_url, verify=False, headers={}, timeout=timeout, **test_json)


def test_default_rest_delete(client_fixture, mocker):
    # Arrange
    client, response, default_path, default_url, result, timeout, _ = client_fixture
    requests_mock = mocker.patch('ibind.base.rest_client.requests')
    requests_mock.request.return_value = response

    # Act
    rv = client.delete(default_path)

    # Assert
    assert result == rv
    requests_mock.request.assert_called_with('DELETE', default_url, verify=False, headers={}, timeout=timeout)


def test_request_retries(client_fixture, mocker):
    # Arrange
    client, _, default_path, default_url, _, _, max_retries = client_fixture
    requests_mock = mocker.patch('ibind.base.rest_client.requests')
    requests_mock.request.side_effect = ReadTimeout()

    # Act
    with CaptureLogsContext('ibind.rest_client', level='INFO') as cm, pytest.raises(TimeoutError) as excinfo:
        client.get(default_path)

    # Assert
    for i in range(max_retries):
        assert f'RestClient: Timeout for GET {default_url} {{}}, retrying attempt {i + 1}/{max_retries}' in cm.output

    assert f'RestClient: Reached max retries ({max_retries}) for GET {default_url} {{}}' == str(excinfo.value)


def test_response_raise_timeout(client_fixture, mocker):
    # Arrange
    client, response, default_path, _, _, timeout, _ = client_fixture
    requests_mock = mocker.patch('ibind.base.rest_client.requests')
    requests_mock.request.return_value = response
    response.raise_for_status.side_effect = Timeout()

    # Act
    with pytest.raises(ExternalBrokerError) as excinfo:
        client.get(default_path)

    # Assert
    assert f'RestClient: Timeout error ({timeout}S)' == str(excinfo.value)


def test_response_raise_generic(client_fixture, mocker):
    # Arrange
    client, response, default_path, _, result, _, _ = client_fixture
    requests_mock = mocker.patch('ibind.base.rest_client.requests')
    requests_mock.request.return_value = response
    response.status_code = 400
    response.reason = 'Test reason'
    response.text = 'Test text'
    response.raise_for_status.side_effect = ValueError('Test generic error')

    # Act
    with pytest.raises(ExternalBrokerError) as excinfo:
        client.get(default_path)

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
