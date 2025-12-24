import datetime
from pprint import pformat
import pytest
from unittest.mock import MagicMock

from requests import ConnectTimeout

from ibind.base.rest_client import Result
from ibind.client.ibkr_client import IbkrClient
from ibind.client.ibkr_utils import StockQuery, filter_stocks
from ibind.support.errors import ExternalBrokerError
from ibind.support.logs import ibind_logs_initialize
from integration.client import ibkr_responses
from test_utils_new import CaptureLogsContext


_URL = 'https://localhost:5000'
_TIMEOUT = 8
_MAX_RETRIES = 4
_DEFAULT_PATH = '/test/api/route'
_ACCOUNT_ID = 'TEST_ACCOUNT_ID'


@pytest.fixture
def client():
    ibind_logs_initialize(log_to_console=True)
    return IbkrClient(
        url=_URL,
        account_id=_ACCOUNT_ID,
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


def test_get_conids(client, response):
    # Arrange
    response.json.return_value = ibkr_responses.responses['stocks']

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
    ]

    # Act
    rv = client.stock_conid_by_symbol(queries, default_filtering=False)

    # Assert
    for symbol, conid in rv.data.items():
        assert symbol in ibkr_responses.responses['filtered_conids']
        assert conid == ibkr_responses.responses['filtered_conids'][symbol]


def test_get_conids_exception(client, response):
    # Arrange
    response.json.return_value = ibkr_responses.responses['stocks']

    symbol = 'AAPL'
    query = StockQuery(symbol=symbol, contract_conditions={'isUS': False}, name_match='APPLE')

    instruments = filter_stocks(query, Result(data={symbol: ibkr_responses.responses['stocks'][symbol]}), default_filtering=False).data[symbol]

    # Act and Assert
    with pytest.raises(RuntimeError) as excinfo:
        client.stock_conid_by_symbol(query, default_filtering=False)

    assert str(excinfo.value) == f'Filtering stock "{symbol}" returned 2 instruments and 2 contracts using following query: {query}.' \
                                 f'\nPlease use filters to ensure that only one instrument and one contract per symbol is selected in order to avoid conid ambiguity.' \
                                 f'\nBe aware that contracts are filtered as {{"isUS": True}} by default. Set default_filtering=False to prevent this default filtering or specify custom filters. See inline documentation for more details.' \
                                 f'\nInstruments returned:\n{pformat(instruments)}'


def test_get_live_orders_no_filters(client, result):
    # Arrange
    client.get = MagicMock(return_value=result)

    # Act
    client.live_orders()

    # Assert
    client.get.assert_called_with('iserver/account/orders', params=None)


def test_get_live_orders_with_valid_filters(client, result):
    # Arrange
    client.get = MagicMock(return_value=result)
    filters = ['inactive', 'filled']

    # Act
    client.live_orders(filters=filters)

    # Assert
    client.get.assert_called_with('iserver/account/orders', params={'filters': 'inactive,filled'})


def test_get_live_orders_with_single_filter(client, result):
    # Arrange
    client.get = MagicMock(return_value=result)

    # Act
    client.live_orders(filters='submitted')

    # Assert
    client.get.assert_called_with('iserver/account/orders', params={'filters': 'submitted'})


def test_get_live_orders_with_incorrect_filter_type(client, result):
    # Arrange
    client.get = MagicMock(return_value=result)

    # Act and Assert
    with pytest.raises(TypeError):
        client.live_orders(filters=123)  # Non-list, non-string filter
    client.get.assert_not_called()


def _marketdata_request(method, url, *args, **kwargs):
    leaf = url.split('/')[-1]
    if leaf == 'stocks':
        return MagicMock(json=lambda: ibkr_responses.responses['stocks'])
    elif leaf == 'history':
        conid = kwargs['params']['conid']
        history_by_conid = {
            ibkr_responses.responses['filtered_conids'][key]: value for key, value in ibkr_responses.responses['history'].items()
        }
        return MagicMock(json=lambda: history_by_conid[conid])


def test_marketdata_history_by_symbols(client, requests_mock):
    # Arrange
    requests_mock.request.side_effect = _marketdata_request

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
    ]

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
            'date': datetime.datetime.fromtimestamp(data['t'] / 1000, tz=datetime.timezone.utc),
        }
        expected_results[query.symbol] = output

    expected_errors = ['Market data for CDN is not live: Delayed', 'Market data for CFC is not live: Delayed']

    # Act
    with CaptureLogsContext('ibind', level='INFO', logger_level='DEBUG', expected_errors=expected_errors, partial_match=True) as cm:
        results = client.marketdata_history_by_symbols(queries)

    # Assert
    for msg in expected_errors:
        assert msg in cm.output

    for symbol, expected in expected_results.items():
        result = results[symbol][-1]
        assert symbol in results
        assert result['open'] == pytest.approx(expected['open'])
        assert result['high'] == pytest.approx(expected['high'])
        assert result['low'] == pytest.approx(expected['low'])
        assert result['close'] == pytest.approx(expected['close'])
        assert result['volume'] == pytest.approx(expected['volume'])
        assert result['date'] == expected['date']


def test_check_health_authenticated_and_connected(client, default_url, requests_mock):
    # Arrange
    response_data = {'iserver': {'authStatus': {'authenticated': True, 'competing': False, 'connected': True}}}
    requests_mock.request.return_value = MagicMock(json=lambda: response_data)
    client.tickle = MagicMock(return_value=Result(data=response_data, request={'url': default_url}))

    # Act
    health_status = client.check_health()

    # Assert
    assert health_status is True
    client.tickle.assert_called_once()


def test_check_health_not_authenticated(client, default_url, requests_mock):
    # Arrange
    response_data = {'iserver': {'authStatus': {'authenticated': False, 'competing': False, 'connected': True}}}
    requests_mock.request.return_value = MagicMock(json=lambda: response_data)
    client.tickle = MagicMock(return_value=Result(data=response_data, request={'url': default_url}))

    # Act
    health_status = client.check_health()

    # Assert
    assert health_status is False


def test_check_health_competing_connection(client, default_url, requests_mock):
    # Arrange
    response_data = {'iserver': {'authStatus': {'authenticated': True, 'competing': True, 'connected': True}}}
    requests_mock.request.return_value = MagicMock(json=lambda: response_data)
    client.tickle = MagicMock(return_value=Result(data=response_data, request={'url': default_url}))

    # Act
    health_status = client.check_health()

    # Assert
    assert health_status is False


def test_check_health_connection_error(client, requests_mock):
    # Arrange
    requests_mock.request.side_effect = ConnectTimeout
    client.tickle = MagicMock(side_effect=ConnectTimeout)

    # Act
    with CaptureLogsContext(
        'ibind.session_mixin',
        level='ERROR',
        expected_errors=['ConnectTimeout raised when communicating with the Gateway'],
        partial_match=True,
    ) as cm:
        health_status = client.check_health()

    # Assert
    assert health_status is False
    assert 'ConnectTimeout raised when communicating with the Gateway' in cm.output[0]


def test_check_health_external_broker_error_unauthenticated(client, requests_mock):
    # Arrange
    requests_mock.request.side_effect = ExternalBrokerError(status_code=401)
    client.tickle = MagicMock(side_effect=ExternalBrokerError(status_code=401))

    # Act
    with CaptureLogsContext('ibind.session_mixin', level='INFO', expected_errors=['Gateway session is not authenticated.']) as cm:
        health_status = client.check_health()

    # Assert
    assert health_status is False
    assert 'Gateway session is not authenticated.' in cm.output[0]


def test_check_health_invalid_data(client, default_url, requests_mock):
    # Arrange
    response_data = {}  # Invalid data format
    requests_mock.request.return_value = MagicMock(json=lambda: response_data)
    client.tickle = MagicMock(return_value=Result(data=response_data, request={'url': default_url}))

    # Act and Assert
    with pytest.raises(AttributeError) as excinfo:
        client.check_health()
    assert 'Health check requests returns invalid data' in str(excinfo.value)


def test_marketdata_unsubscribe_success(client, mocker):
    # Arrange
    conids = [12345, 67890]

    def post_side_effect(url, *args, **kwargs):
        conid = kwargs['params']['conid']
        if conid in conids:
            return Result(data={'success': True}, request={'url': url})
        raise ExternalBrokerError(status_code=404)

    client.post = MagicMock(side_effect=post_side_effect, __name__='client_post_mock')

    # Act
    results = client.marketdata_unsubscribe(conids)

    # Assert
    for conid, result in results.items():
        assert int(conid) in conids
        assert isinstance(result, Result)
        assert result.data['success'] is True


def test_marketdata_unsubscribe_with_error(client, mocker):
    # Arrange
    conids = [12345, 67890]

    def post_side_effect(url, *args, **kwargs):
        conid = kwargs['params']['conid']
        if conid == 12345:
            raise ExternalBrokerError(status_code=404)
        return Result(data={'success': True}, request={'url': url})

    client.post = MagicMock(side_effect=post_side_effect, __name__='client_post_mock')

    # Act
    results = client.marketdata_unsubscribe(conids)

    # Assert
    assert 12345 in results
    assert 67890 in results
    assert results[67890].data['success'] is True
    assert isinstance(results[12345], ExternalBrokerError)


def test_marketdata_unsubscribe_raises_exception_on_failure(client, mocker):
    # Arrange
    conids = [12345]
    client.post = MagicMock(side_effect=ExternalBrokerError(status_code=500), __name__='client_post_mock')

    # Act
    with pytest.raises(ExternalBrokerError) as excinfo:
        client.marketdata_unsubscribe(conids)

    # Assert
    assert excinfo.value.status_code == 500