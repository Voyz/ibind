import threading
from unittest import TestCase
from unittest.mock import patch, MagicMock
import asyncio

from requests import ReadTimeout, Timeout

from ibind.client.ibkr_client import IbkrClient
from ibind.support.errors import ExternalBrokerError
from ibind.support.logs import project_logger
from ibind.base.rest_client import Result, RestClient


@patch('ibind.base.rest_client.requests')
class TestRestClientI(TestCase):
    def setUp(self):
        self.url = 'https://localhost:5000'
        self.account_id = 'TEST_ACCOUNT_ID'
        self.timeout = 8
        self.max_retries = 4
        self.client = RestClient(
            url=self.url,
            timeout=self.timeout,
            max_retries=self.max_retries,
            use_session=False,
        )

        self.data = {'Test key': 'Test value'}

        self.response = MagicMock()
        self.response.json.return_value = self.data
        self.default_path = 'test/api/route'
        self.default_url = f'{self.url}/{self.default_path}'
        self.result = Result(data=self.data, request={'url': self.default_url})
        self.maxDiff = 9999

    def test_default_rest(self, requests_mock):
        requests_mock.request.return_value = self.response

        rv = self.client.get(self.default_path)
        self.assertEqual(self.result, rv)
        requests_mock.request.assert_called_with('GET', self.default_url, verify=False, headers={}, timeout=self.timeout)

        test_post_kwargs = {'field1': 'value1', 'field2': 'value2'}
        test_json = {'json': {**test_post_kwargs}}
        rv = self.client.post(self.default_path, params=test_post_kwargs)
        self.assertEqual(self.result.copy(request={'url': self.default_url, **test_json}), rv)
        requests_mock.request.assert_called_with('POST', self.default_url, verify=False, headers={}, timeout=self.timeout, **test_json)

        rv = self.client.delete(self.default_path)
        self.assertEqual(self.result, rv)
        requests_mock.request.assert_called_with('DELETE', self.default_url, verify=False, headers={}, timeout=self.timeout)

    def test_request_retries(self, requests_mock):
        requests_mock.request.side_effect = ReadTimeout()

        with self.assertLogs(project_logger(), level='INFO') as cm, self.assertRaises(TimeoutError) as cm_err:
            self.client.get(self.default_path)

        for i, record in enumerate(cm.records):
            self.assertEqual(f'RestClient: Timeout for GET {self.default_url} {{}}, retrying attempt {i + 1}/{self.max_retries}', record.msg)
        self.assertEqual(f'RestClient: Reached max retries ({self.max_retries}) for GET {self.default_url} {{}}', str(cm_err.exception))

    def test_response_raise_timeout(self, requests_mock):
        requests_mock.request.return_value = self.response
        self.response.raise_for_status.side_effect = Timeout()

        with self.assertRaises(ExternalBrokerError) as cm_err:
            self.client.get(self.default_path)

        self.assertEqual(f'RestClient: Timeout error ({self.timeout}S)', str(cm_err.exception))

    def test_response_raise_generic(self, requests_mock):
        requests_mock.request.return_value = self.response
        self.response.status_code = 400
        self.response.reason = 'Test reason'
        self.response.text = 'Test text'

        self.response.raise_for_status.side_effect = ValueError('Test generic error')

        with self.assertRaises(ExternalBrokerError) as cm_err:
            self.client.get(self.default_path)

        self.assertEqual(
            f'RestClient: response error {self.result.copy(data=None)} :: {self.response.status_code} :: {self.response.reason} :: {self.response.text}',
            str(cm_err.exception),
        )


class TestRestClientInThread(TestCase):
    def _worker(self, results: []):
        try:
            IbkrClient()
        except Exception as e:
            results.append(e)

    def test_in_thread(self):
        """Run in thread ensuring client still is constructed without an exception."""
        results = []
        t = threading.Thread(target=self._worker, args=(results,))
        t.daemon = True
        t.start()
        t.join(1)
        for result in results:
            if isinstance(result, Exception):
                raise result

    def test_without_thread(self):
        """Run without a thread to ensure it still works as expected."""
        results = []
        self._worker(results)
        for result in results:
            if isinstance(result, Exception):
                raise result


class TestRestClientAsync(TestCase):
    def _worker(self, results: []):
        """Runs the async test inside a new thread to check if signal handling breaks."""
        try:
            asyncio.run(self._async_worker(results))
        except Exception as e:
            results.append(e)

    async def _async_worker(self, results: []):
        """Async version of the worker function to run in an asyncio event loop."""
        try:
            IbkrClient()
        except Exception as e:
            results.append(e)

    def test_in_thread_async(self):
        """Test that IbkrClient() does not break in an asyncio thread."""
        results = []
        t = threading.Thread(target=self._worker, args=(results,))
        t.daemon = True
        t.start()
        t.join(1)
        for result in results:
            if isinstance(result, Exception):
                raise result

    def test_without_thread_async(self):
        """Test that IbkrClient() does not break in the main asyncio event loop."""
        results = []
        asyncio.run(self._async_worker(results))
        for result in results:
            if isinstance(result, Exception):
                raise result
