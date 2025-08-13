import datetime
from typing import Union, TYPE_CHECKING, List, Dict

from ibind.base.rest_client import Result
from ibind.client.ibkr_definitions import snapshot_by_id
from ibind.client.ibkr_utils import StockQuery, StockQueries, cleanup_market_history_responses
from ibind.support.errors import ExternalBrokerError
from ibind.support.logs import project_logger
from ibind.support.py_utils import ensure_list_arg, OneOrMany, execute_in_parallel, params_dict

if TYPE_CHECKING:  # pragma: no cover
    from ibind import IbkrClient

_LOGGER = project_logger(__file__)


class MarketdataMixin:
    """
    https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#md
    """

    @ensure_list_arg('conids', 'fields')
    def live_marketdata_snapshot(self: 'IbkrClient', conids: OneOrMany[str], fields: OneOrMany[str]) -> Result:  # pragma: no cover
        """
        Get Market Data for the given conid(s).

        A pre-flight request must be made prior to ever receiving data.

        Parameters:
            conids (OneOrMany[str]): Contract identifier(s) for the contract of interest.
            fields (OneOrMany[str]): Specify a series of tick values to be returned.

        Note:
            - The endpoint /iserver/accounts must be called prior to /iserver/marketdata/snapshot.
            - For derivative contracts, the endpoint /iserver/secdef/search must be called first.
        """
        params = {'conids': ','.join(conids), 'fields': ','.join(fields)}
        return self.get('iserver/marketdata/snapshot', params)

    def live_marketdata_snapshot_by_symbol(self: 'IbkrClient', queries: StockQueries, fields: OneOrMany[str]) -> dict:
        """
        Get Market Data for the given symbols(s).

        A pre-flight request must be made prior to ever receiving data.

        Parameters:
            queries (List[StockQuery]): A list of StockQuery objects to specify filtering criteria for stocks.
            fields (OneOrMany[str]): Specify a series of tick values to be returned.

        Note:
            - The endpoint /iserver/accounts must be called prior to /iserver/marketdata/snapshot.
            - For derivative contracts, the endpoint /iserver/secdef/search must be called first.
        """
        conids_by_symbol = self.stock_conid_by_symbol(queries).data

        conids = []
        symbols_by_conids = {}
        for symbol, conid in conids_by_symbol.items():
            conids.append(str(conid))
            symbols_by_conids[conid] = symbol

        # There needs to be a pre-flight request for some reason, so we default to calling this twice
        self.receive_brokerage_accounts()
        self.live_marketdata_snapshot(conids, fields=fields)
        entries = self.live_marketdata_snapshot(conids, fields=fields).data

        results = {}
        for entry in entries:
            try:
                result = {}

                for key, value in entry.items():
                    if key not in snapshot_by_id:
                        continue

                    result[snapshot_by_id[key]] = value
                results[entry['conid']] = result
            except Exception as e:  # pragma: no cover
                _LOGGER.exception(f'Error post-processing live market data for {entry}: {str(e)}')

        # reformat the results by symbol instead of conid
        results_by_symbol = {symbols_by_conids[conid]: result for conid, result in results.items()}

        return results_by_symbol

    def regulatory_snapshot(self: 'IbkrClient', conid: str) -> Result:  # pragma: no cover
        """
        Send a request for a regulatory snapshot. This will cost $0.01 USD per request unless you are subscribed to the direct exchange market data already.

        WARNING: Each regulatory snapshot made will incur a fee of $0.01 USD to the account. This applies to both live and paper accounts.

        Parameters:
            conid (str): Provide the contract identifier to retrieve market data for.

        Note:
            - If you are already paying for, or are subscribed to, a specific US Network subscription, your account will not be charged.
            - For stocks, there are individual exchange-specific market data subscriptions necessary to receive streaming quotes.
        """
        return self.get('md/regsnapshot', {'conid': conid})

    def marketdata_history_by_conid(
        self: 'IbkrClient',
        conid: str,
        bar: str,
        exchange: str = None,
        period: str = None,
        outside_rth: bool = None,
        start_time: datetime.datetime = None,
    ) -> Result:  # pragma: no cover
        """
        Get historical market Data for given conid, length of data is controlled by 'period' and 'bar'.

        Parameters:
            conid (str): Contract identifier for the ticker symbol of interest.
            bar (str): Individual bars of data to be returned. Possible values– 1min, 2min, 3min, 5min, 10min, 15min, 30min, 1h, 2h, 3h, 4h, 8h, 1d, 1w, 1m.
            exchange (str, optional): Returns the exchange you want to receive data from.
            period (str): Overall duration for which data should be returned. Default to 1w. Available time period– {1-30}min, {1-8}h, {1-1000}d, {1-792}w, {1-182}m, {1-15}y.
            outside_rth (bool, optional): Determine if you want data after regular trading hours.
            start_time (datetime.datetime, optional): Starting date of the request duration.

        Note:
            - There's a limit of 5 concurrent requests. Excessive requests will return a 'Too many requests' status 429 response.
        """
        params = params_dict(
            {'conid': conid, 'bar': bar},
            optional={'exchange': exchange, 'period': period, 'outsideRth': outside_rth, 'startTime': start_time},
            preprocessors={'startTime': lambda x: x.strftime('%Y%m%d-%H:%M:%S')},
        )

        return self.get('iserver/marketdata/history', params)

    def historical_marketdata_beta(
        self: 'IbkrClient',
        conid: str,
        period: str,
        bar: str,
        outside_rth: bool = None,
        start_time: datetime.datetime = None,
        direction: str = None,
        bar_type: str = None,
    ) -> Result:  # pragma: no cover
        """
        Using a direct connection to the market data farm, will provide a list of historical market data for given conid.

        Parameters:
            conid (str): The contract identifier for which data should be requested.
            period (str): The duration for which data should be requested. Available Values: See HMDS Period Units.
            bar (str): The bar size for which bars should be returned. Available Values: See HMDS Bar Sizes.
            outside_rth (bool, optional): Define if data should be returned for trades outside regular trading hours.
            start_time (datetime.datetime, optional): Specify the value from where historical data should be taken. Value Format: UTC; YYYYMMDD-HH:mm:dd. Defaults to the current date and time.
            direction (str, optional): Specify the direction from which market data should be returned. Available Values: -1: time from the start_time to now; 1: time from now to the end of the period. Defaults to 1.
            bar_type (str, optional): Returns valid bar types for which data may be requested. Available Values: Last, Bid, Ask, Midpoint, FeeRate, Inventory. Defaults to Last for Stocks, Options, Futures, and Futures Options.

        Note:
            - The first time a user makes a request to the /hmds/history endpoints will result in a 404 error. This initial request instantiates the historical market data services allowing future requests to return data. Subsequent requests will return data as expected.
        """
        params = params_dict(
            {'conid': conid, 'period': period, 'bar': bar},
            optional={
                'outsideRth': outside_rth,
                'startTime': start_time,
                'direction': direction,
                'barType': bar_type,
            },
            preprocessors={'startTime': lambda x: x.strftime('%Y%m%d-%H:%M:%S')},
        )

        return self.get('hmds/history', params)

    def marketdata_history_by_symbol(
        self: 'IbkrClient',
        symbol: Union[str, StockQuery],
        bar: str,
        exchange: str = None,
        period: str = None,
        outside_rth: bool = None,
        start_time: datetime.datetime = None,
    ) -> Result:  # pragma: no cover
        """
        Get historical market Data for given symbol, length of data is controlled by 'period' and 'bar'.

        Parameters:
            symbol (Union[str, StockQuery]): StockQuery or str symbol for the ticker of interest.
            bar (str): Individual bars of data to be returned. Possible values– 1min, 2min, 3min, 5min, 10min, 15min, 30min, 1h, 2h, 3h, 4h, 8h, 1d, 1w, 1m.
            exchange (str, optional): Returns the exchange you want to receive data from.
            period (str): Overall duration for which data should be returned. Default to 1w. Available time period– {1-30}min, {1-8}h, {1-1000}d, {1-792}w, {1-182}m, {1-15}y.
            outside_rth (bool, optional): Determine if you want data after regular trading hours.
            start_time (datetime.datetime, optional): Starting date of the request duration.

        """
        conid = str(self.stock_conid_by_symbol(symbol).data[symbol])
        return self.marketdata_history_by_conid(conid, bar, exchange, period, outside_rth, start_time)

    def marketdata_history_by_conids(
        self: 'IbkrClient',
        conids: Union[List[str], Dict[str, str]],
        period: str = '1min',
        bar: str = '1min',
        outside_rth: bool = True,
        start_time: datetime.datetime = None,
        raise_on_error: bool = False,
        run_in_parallel: bool = True,
    ) -> dict:
        """
        An extended version of the marketdata_history_by_conid method.

        For each conid provided, it queries the marketdata history for the specified symbols. The results are then cleaned up and unified. Due to this grouping and post-processing, this method returns data directly without the Result dataclass.

        Parameters:
            conids (OneOrMany[str]): A list of conids to get market data for.
            exchange (str, optional): Returns the exchange you want to receive data from.
            period (str): Overall duration for which data should be returned. Default to 1w. Available time period– {1-30}min, {1-8}h, {1-1000}d, {1-792}w, {1-182}m, {1-15}y.
            bar (str): Individual bars of data to be returned. Possible values– 1min, 2min, 3min, 5min, 10min, 15min, 30min, 1h, 2h, 3h, 4h, 8h, 1d, 1w, 1m.
            outside_rth (bool, optional): Determine if you want data after regular trading hours.
            start_time (datetime.datetime, optional): Starting date of the request duration.
            raise_on_error (bool, optional): If True, raise an exception if an error occurs during the request. Defaults to False.
            run_in_parallel (bool, optional): If True, send requests in parallel to speed up the response. Defaults to True.

        Note:
            - This method returns data directly without the `Result` dataclass.
        """

        if not isinstance(conids, dict):
            # In case conids aren't a symbol->conid dict, generate a dummy conid->conid dict in order to preserve the functionality. In such case, the 'symbol' variable actually is a 'conid'.
            conids = {conid: conid for conid in conids}

        static_params = {'period': period, 'bar': bar, 'outside_rth': outside_rth, 'start_time': start_time}
        requests = {symbol: {'kwargs': {'conid': conid} | static_params} for symbol, conid in conids.items()}

        # when there is only one conid, we avoid running in parallel
        if run_in_parallel and len(conids) > 1:
            # /iserver/marketdata/history accepts 5 concurrent requests in theory, but sometime throttles above 4
            market_history_responses = execute_in_parallel(self.marketdata_history_by_conid, requests=requests, max_workers=4)
        else:
            market_history_responses = {}
            for symbol, request in requests.items():
                try:
                    market_history_responses[symbol] = self.marketdata_history_by_conid(**request['kwargs'])
                except Exception as e:
                    market_history_responses[symbol] = e

        results = cleanup_market_history_responses(market_history_responses, raise_on_error=raise_on_error)

        return results

    @ensure_list_arg('queries')
    def marketdata_history_by_symbols(
        self: 'IbkrClient',
        queries: StockQueries,
        period: str = '1min',
        bar: str = '1min',
        outside_rth: bool = True,
        start_time: datetime.datetime = None,
        raise_on_error: bool = False,
        run_in_parallel: bool = True,
    ) -> dict:
        """
        An extended version of the marketdata_history_by_conids method.

        For each StockQuery provided, it queries the marketdata history for the specified symbols. The results are then cleaned up and unified. Due to this grouping and post-processing, this method returns data directly without the Result dataclass.

        Parameters:
            queries (List[StockQuery]): A list of StockQuery objects to specify filtering criteria for stocks.
            exchange (str, optional): Returns the exchange you want to receive data from.
            period (str): Overall duration for which data should be returned. Default to 1w. Available time period– {1-30}min, {1-8}h, {1-1000}d, {1-792}w, {1-182}m, {1-15}y.
            bar (str): Individual bars of data to be returned. Possible values– 1min, 2min, 3min, 5min, 10min, 15min, 30min, 1h, 2h, 3h, 4h, 8h, 1d, 1w, 1m.
            outside_rth (bool, optional): Determine if you want data after regular trading hours.
            start_time (datetime.datetime, optional): Starting date of the request duration.
            raise_on_error (bool, optional): If True, raise an exception if an error occurs during the request. Defaults to False.
            run_in_parallel (bool, optional): If True, send requests in parallel to speed up the response. Defaults to True.

        Note:
            - This method returns data directly without the `Result` dataclass.
        """
        conids = self.stock_conid_by_symbol(queries).data
        return self.marketdata_history_by_conids(
            conids=conids,
            period=period,
            bar=bar,
            outside_rth=outside_rth,
            start_time=start_time,
            raise_on_error=raise_on_error,
            run_in_parallel=run_in_parallel,
        )

    @ensure_list_arg('conids')
    def marketdata_unsubscribe(self: 'IbkrClient', conids: OneOrMany[str]) -> List[Result]:
        """
        Cancel market data for given conid(s).

        Parameters:
            conids (OneOrMany[str]): Enter the contract identifier to cancel the market data feed. This can clear all standing market data feeds to invalidate your cache and start fresh.
        """
        # we unsubscribe from all conids simultaneously
        unsubscribe_requests = {conid: {'args': ['iserver/marketdata/unsubscribe'], 'kwargs': {'params': {'conid': int(conid)}}} for conid in conids}
        results = execute_in_parallel(self.post, unsubscribe_requests)

        for conid, result in results.items():
            if isinstance(result, Exception):
                # 404 means that no such subscription was found in first place, which we ignore
                if isinstance(result, ExternalBrokerError) and result.status_code == 404:
                    continue
                raise result

        return results

    def marketdata_unsubscribe_all(self: 'IbkrClient') -> Result:  # pragma: no cover
        """
        Cancel all market data request(s). To cancel market data for a specific conid, see /iserver/marketdata/{conid}/unsubscribe.
        """
        return self.get('iserver/marketdata/unsubscribeall')
