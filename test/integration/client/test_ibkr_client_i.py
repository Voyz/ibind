import datetime
from pprint import pformat
from unittest import TestCase
from unittest.mock import patch, MagicMock

from requests import ConnectTimeout

from ibind.base.rest_client import Result
from ibind.client.ibkr_client import IbkrClient
from ibind.client.ibkr_utils import StockQuery, filter_stocks
from ibind.support.errors import ExternalBrokerError
from ibind.support.logs import project_logger
from test.integration.client import ibkr_responses
from test_utils import verify_log, SafeAssertLogs, RaiseLogsContext


@patch('ibind.base.rest_client.requests')
class TestIbkrClientI(TestCase):
    def setUp(self):
        self.url = 'https://localhost:5000'
        self.account_id = 'TEST_ACCOUNT_ID'
        self.timeout = 8
        self.max_retries = 4
        self.client = IbkrClient(
            url=self.url,
            account_id=self.account_id,
            timeout=self.timeout,
            max_retries=self.max_retries,
            use_session=False,
        )

        self.data = {'Test key': 'Test value'}

        self.response = MagicMock()
        self.response.json.return_value = self.data
        self.default_path = '/test/api/route'
        self.default_url = f'{self.url}/{self.default_path}'
        self.result = Result(data=self.data, request={'url': self.default_url})
        self.maxDiff = 9999

    def test_get_conids(self, requests_mock):
        requests_mock.request.return_value = self.response
        self.response.json.return_value = ibkr_responses.responses['stocks']

        queries = [
            StockQuery(symbol='AAPL', contract_conditions={'isUS': False, 'exchange': 'AEQLIT'}, name_match='APPLE'),
            StockQuery(symbol='BBVA', contract_conditions={'exchange': 'NYSE'}),
            StockQuery(symbol='CDN', contract_conditions={'isUS': False}),
            StockQuery(symbol='CFC', contract_conditions={}),
            StockQuery(symbol='GOOG', contract_conditions={'isUS': False, 'exchange': 'MEXI'}, instrument_conditions={'chineseName': 'Alphabet&#x516C;&#x53F8;'}),
            'HUBS',
            StockQuery(symbol='META', name_match='meta ', contract_conditions={'isUS': False, 'exchange': 'MEXI'}, instrument_conditions={}),
            StockQuery(symbol='MSFT', contract_conditions={'exchange': 'NASDAQ'}),
            StockQuery(symbol='SAN', name_match='SANTANDER', contract_conditions={'isUS': True}),
            StockQuery(symbol='SCHW', contract_conditions={'exchange': 'NYSE'}),
            StockQuery(symbol='TEAM', name_match='ATLASSIAN'),
            StockQuery(symbol='INVALID_SYMBOL')
        ]  # fmt: skip

        with self.assertLogs(project_logger(), level='INFO'):
            rv = self.client.stock_conid_by_symbol(queries, default_filtering=False)

        for symbol, conid in rv.data.items():
            self.assertIn(symbol, ibkr_responses.responses['filtered_conids'])
            self.assertEqual(conid, ibkr_responses.responses['filtered_conids'][symbol])

    def test_get_conids_exception(self, requests_mock):
        requests_mock.request.return_value = self.response
        self.response.json.return_value = ibkr_responses.responses['stocks']

        symbol = 'AAPL'
        query = StockQuery(symbol=symbol, contract_conditions={'isUS': False}, name_match='APPLE')

        instruments = filter_stocks(query, Result(data={symbol: ibkr_responses.responses['stocks'][symbol]}), default_filtering=False).data[symbol]

        with self.assertRaises(RuntimeError) as cm_err:
            self.client.stock_conid_by_symbol(query, default_filtering=False)

        self.maxDiff = None
        self.assertEqual(
            f'Filtering stock "{symbol}" returned 2 instruments and 2 contracts using following query: {query}.\nPlease use filters to ensure that only one instrument and one contract per symbol is selected in order to avoid conid ambiguity.\nBe aware that contracts are filtered as {{"isUS": True}} by default. Set default_filtering=False to prevent this default filtering or specify custom filters. See inline documentation for more details.\nInstruments returned:\n{pformat(instruments)}',
            str(cm_err.exception),
        )

    def test_get_live_orders_no_filters(self, requests_mock):
        self.client.get = MagicMock(return_value=self.result)
        self.client.live_orders()
        self.client.get.assert_called_with('iserver/account/orders', params=None)

    def test_get_live_orders_with_valid_filters(self, requests_mock):
        self.client.get = MagicMock(return_value=self.result)
        filters = ['inactive', 'filled']
        self.client.live_orders(filters=filters)
        self.client.get.assert_called_with('iserver/account/orders', params={'filters': 'inactive,filled'})

    def test_get_live_orders_with_single_filter(self, requests_mock):
        self.client.get = MagicMock(return_value=self.result)
        self.client.live_orders(filters='submitted')
        self.client.get.assert_called_with('iserver/account/orders', params={'filters': 'submitted'})

    def test_get_live_orders_with_incorrect_filter_type(self, requests_mock):
        self.client.get = MagicMock(return_value=self.result)
        with self.assertRaises(TypeError):
            self.client.live_orders(filters=123)  # Non-list, non-string filter
        self.client.get.assert_not_called()

    def _marketdata_request(self, method, url, *args, **kwargs):
        leaf = url.split('/')[-1]
        if leaf == 'stocks':
            return MagicMock(json=lambda: ibkr_responses.responses['stocks'])  # Mock response for get_conids
        elif leaf == 'history':
            conid = kwargs['params']['conid']
            return MagicMock(json=lambda: self._history_by_conid[conid])

    def test_marketdata_history_by_symbols(self, requests_mock):
        # Mocking the requests module for external interaction
        self._history_by_conid = {
            ibkr_responses.responses['filtered_conids'][key]: value for key, value in ibkr_responses.responses['history'].items()
        }
        requests_mock.request.side_effect = self._marketdata_request

        queries = [
            StockQuery(symbol='AAPL', contract_conditions={'isUS': False, 'exchange': 'AEQLIT'}, name_match='APPLE'),
            StockQuery(symbol='BBVA', contract_conditions={'exchange': 'NYSE'}),
            StockQuery(symbol='CDN', contract_conditions={'isUS': False}),
            StockQuery(symbol='CFC', contract_conditions={}),
            StockQuery(symbol='GOOG', contract_conditions={'isUS': False, 'exchange': 'MEXI'}, instrument_conditions={'chineseName': 'Alphabet&#x516C;&#x53F8;'}),
            StockQuery(symbol='HUBS'),
            StockQuery(symbol='META', name_match='meta ', contract_conditions={'isUS': False, 'exchange': 'MEXI'}, instrument_conditions={}),
            StockQuery(symbol='MSFT', contract_conditions={'exchange': 'NASDAQ'}),
            StockQuery(symbol='SAN', name_match='SANTANDER', contract_conditions={'isUS': True}),
            StockQuery(symbol='SCHW', contract_conditions={'exchange': 'NYSE'}),
            StockQuery(symbol='TEAM', name_match='ATLASSIAN'),
        ]  # fmt: skip

        expected_results = {}

        for query in queries:
            data = ibkr_responses.responses['history'][query.symbol]['data'][0]
            output = {
                'conid': ibkr_responses.responses['filtered_conids'][query.symbol],
                'symbol': query.symbol,
                'open': data['o'],
                'high': data['h'],
                'low': data['l'],
                'close': data['c'],
                'volume': data['v'],
                'date': datetime.datetime.fromtimestamp(data['t'] / 1000),
            }
            expected_results[query.symbol] = output

        expected_errors = ['Market data for CDN is not live: Delayed', 'Market data for CFC is not live: Delayed']

        with SafeAssertLogs(self, 'ibind', level='INFO', logger_level='DEBUG', no_logs=False) as cm, \
                RaiseLogsContext(self, 'ibind', level='ERROR', expected_errors=expected_errors):  # fmt: skip
            results = self.client.marketdata_history_by_symbols(queries)

        verify_log(self, cm, expected_errors)

        # Assertions to verify the correctness of each field in the result
        for symbol, expected in expected_results.items():
            result = results[symbol][-1]
            self.assertIn(symbol, results)
            self.assertAlmostEqual(result['open'], expected['open'])
            self.assertAlmostEqual(result['high'], expected['high'])
            self.assertAlmostEqual(result['low'], expected['low'])
            self.assertAlmostEqual(result['close'], expected['close'])
            self.assertAlmostEqual(result['volume'], expected['volume'])
            self.assertEqual(result['date'], expected['date'])

    def test_check_health_authenticated_and_connected(self, requests_mock):
        response_data = {'iserver': {'authStatus': {'authenticated': True, 'competing': False, 'connected': True}}}
        requests_mock.request.return_value = MagicMock(json=lambda: response_data)
        self.client.tickle = MagicMock(return_value=Result(data=response_data, request={'url': self.default_url}))

        health_status = self.client.check_health()
        self.assertTrue(health_status)
        self.client.tickle.assert_called_once()

    def test_check_health_not_authenticated(self, requests_mock):
        response_data = {'iserver': {'authStatus': {'authenticated': False, 'competing': False, 'connected': True}}}
        requests_mock.request.return_value = MagicMock(json=lambda: response_data)
        self.client.tickle = MagicMock(return_value=Result(data=response_data, request={'url': self.default_url}))

        health_status = self.client.check_health()
        self.assertFalse(health_status)

    def test_check_health_competing_connection(self, requests_mock):
        response_data = {'iserver': {'authStatus': {'authenticated': True, 'competing': True, 'connected': True}}}
        requests_mock.request.return_value = MagicMock(json=lambda: response_data)
        self.client.tickle = MagicMock(return_value=Result(data=response_data, request={'url': self.default_url}))

        health_status = self.client.check_health()
        self.assertFalse(health_status)

    def test_check_health_connection_error(self, requests_mock):
        requests_mock.request.side_effect = ConnectTimeout
        self.client.tickle = MagicMock(side_effect=ConnectTimeout)

        with self.assertLogs(level='ERROR') as cm:
            health_status = self.client.check_health()
        self.assertFalse(health_status)
        self.assertIn('ConnectTimeout raised when communicating with the Gateway', cm.output[0])

    def test_check_health_external_broker_error_unauthenticated(self, requests_mock):
        requests_mock.request.side_effect = ExternalBrokerError(status_code=401)
        self.client.tickle = MagicMock(side_effect=ExternalBrokerError(status_code=401))

        with self.assertLogs(level='INFO') as cm:
            health_status = self.client.check_health()
        self.assertFalse(health_status)
        self.assertIn('Gateway session is not authenticated.', cm.output[0])

    def test_check_health_invalid_data(self, requests_mock):
        response_data = {}  # Invalid data format
        requests_mock.request.return_value = MagicMock(json=lambda: response_data)
        self.client.tickle = MagicMock(return_value=Result(data=response_data, request={'url': self.default_url}))

        with self.assertRaises(AttributeError) as cm:
            self.client.check_health()
        self.assertIn('Health check requests returns invalid data', str(cm.exception))

    def test_marketdata_unsubscribe_success(self, requests_mock):
        conids = [12345, 67890]
        responses = {12345: MagicMock(status_code=200), 67890: MagicMock(status_code=200)}
        requests_mock.request.side_effect = lambda method, url, **kwargs: responses[kwargs['json']['conid']]
        self.client.get = MagicMock(
            side_effect=lambda url, *args, **kwargs: Result(data={'success': True}, request={'url': url}), __name__='client_get_mock'
        )

        results = self.client.marketdata_unsubscribe(conids)

        for conid, result in results.items():
            self.assertIn(conid, conids)
            self.assertIsInstance(result, Result)
            self.assertTrue(result.data['success'])

    def test_marketdata_unsubscribe_with_error(self, requests_mock):
        conids = [12345, 67890]
        responses = {
            12345: MagicMock(status_code=404),  # Simulate not found error for one conid
            67890: MagicMock(status_code=200),
        }
        requests_mock.request.side_effect = lambda method, url, **kwargs: responses[kwargs['json']['conid']]
        self.client.get = MagicMock(
            side_effect=lambda url, *args, **kwargs: Result(data={'success': True}, request={'url': url})
            if '67890' in url
            else ExternalBrokerError(status_code=404),
            __name__='client_get_mock',
        )

        results = self.client.marketdata_unsubscribe(conids)

        self.assertIn(12345, results)
        self.assertIn(67890, results)
        self.assertTrue(results[67890].data['success'])

    def test_marketdata_unsubscribe_raises_exception_on_failure(self, requests_mock):
        conids = [12345]
        responses = {
            12345: MagicMock(status_code=500),  # Simulate server error
        }
        requests_mock.request.side_effect = lambda method, url, **kwargs: responses[int(url.split('/')[-2])]
        self.client.post = MagicMock(side_effect=lambda url, *args, **kwargs: ExternalBrokerError(status_code=500), __name__='client_get_mock')

        with self.assertRaises(ExternalBrokerError):
            self.client.marketdata_unsubscribe(conids)
