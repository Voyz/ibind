import datetime
import os
import pprint
from typing import List, Union, Optional

from requests import ConnectTimeout

from ibind import var
from ibind.base.rest_client import RestClient, Result, pass_result
from ibind.client.ibkr_definitions import decode_data_availability
from ibind.client.ibkr_utils import query_to_symbols, StockQuery, filter_stocks, Answers, handle_questions, StockQueries
from ibind.client.ibkr_client_mixins.accounts_mixin import AccountsMixin
from ibind.client.ibkr_client_mixins.contract_mixin import ContractMixin
from ibind.client.ibkr_client_mixins.marketdata_mixin import MarketdataMixin
from ibind.client.ibkr_client_mixins.order_mixin import OrderMixin
from ibind.client.ibkr_client_mixins.portfolio_mixin import PortfolioMixin
from ibind.client.ibkr_client_mixins.session_mixin import SessionMixin
from ibind.support.errors import ExternalBrokerError
from ibind.support.logs import new_daily_rotating_file_handler, project_logger
from ibind.support.py_utils import ensure_list_arg, execute_in_parallel, OneOrMany

_LOGGER = project_logger(__file__)




class IbkrClient(RestClient, MarketdataMixin, ContractMixin, SessionMixin, OrderMixin, PortfolioMixin, AccountsMixin):
    """
    A client class for interfacing with the Interactive Brokers API, extending the RestClient class.

    This subclass of RestClient is specifically designed for the Interactive Brokers API. It inherits
    the foundational REST API interaction capabilities from RestClient and adds functionalities
    particular to the Interactive Brokers API, such as specific endpoint handling.

    The class provides methods to perform various operations with the Interactive Brokers API, such as
    fetching stock data, submitting orders, and managing account information.

    See: https://interactivebrokers.github.io/cpwebapi/endpoints
    """

    def __init__(
            self,
            account_id: Optional[str] = var.IBKR_ACCOUNT_ID,
            url: str = var.IBKR_URL,
            cacert: Union[str, os.PathLike, bool] = var.IBKR_CACERT,
            timeout: float = 10,
            max_retries: int = 3,
    ) -> None:
        """
        Parameters:
            url (str): The base URL for the REST API.
            account_id (str): An identifier for the account.
            cacert (Union[os.PathLike, bool], optional): Path to the CA certificate file for SSL verification,
                                                         or False to disable SSL verification. Defaults to False.
            timeout (float, optional): Timeout in seconds for the API requests. Defaults to 10.
            max_retries (int, optional): Maximum number of retries for failed API requests. Defaults to 3.
        """

        self.account_id = account_id
        super().__init__(url=url, cacert=cacert, timeout=timeout, max_retries=max_retries)

        self.logger.info('#################')
        self.logger.info(f'New IbkrClient(base_url={self.base_url!r}, account_id={self.account_id!r}, ssl={self.cacert!r}, timeout={self._timeout}, max_retries={self._max_retries})')

    def make_logger(self):
        self._logger = new_daily_rotating_file_handler('IbkrClient', os.path.join(var.LOGS_DIR, f'ibkr_client_{self.account_id}'))

    ###### SIMPLE ENDPOINTS ######
    # def tickle(self: 'IbkrClient') -> Result:  # pragma: no cover
    #     return self.post('tickle', log=False)
    #
    # def auth_status(self: 'IbkrClient') -> Result:  # pragma: no cover
    #     return self.post('iserver/auth/status')
    #
    # def reauthenticate(self: 'IbkrClient') -> Result:  # pragma: no cover
    #     return self.post('iserver/reauthenticate')
    #
    # def log_out(self: 'IbkrClient') -> Result:  # pragma: no cover
    #     return self.post('logout')

    # def get_accounts(self: 'IbkrClient') -> Result:  # pragma: no cover
    #     return self.get('portfolio/accounts')
    #
    # def get_ledger(self: 'IbkrClient') -> Result:  # pragma: no cover
    #     return self.get(f'portfolio/{self.account_id}/ledger')
    #
    # def get_positions(self: 'IbkrClient',page: int = 0) -> Result:  # pragma: no cover
    #     return self.get(f'portfolio/{self.account_id}/positions/{page}')

    # def get_order(self: 'IbkrClient',order_id: str) -> Result:  # pragma: no cover
    #     return self.get(f'iserver/account/order/status/{order_id}')

    # marketdata_history_by_conid = marketdata_mixin.marketdata_history_by_conid

    # def marketdata_history_by_conid(
    #         self,
    #         conid: str,
    #         exchange: str = None,
    #         period: str = None,
    #         bar: str = None,
    #         outside_rth: bool = None
    # ) -> Result:  # pragma: no cover
    #     """
    #     period: {1-30}min, {1-8}h, {1-1000}d, {1-792}w, {1-182}m, {1-15}y
    #     bar: 1min, 2min, 3min, 5min, 10min, 15min, 30min, 1h, 2h, 3h, 4h, 8h, 1d, 1w, 1m
    #     """
    #     return self.get('iserver/marketdata/history', params={"conid": int(conid), "exchange": exchange, "period": period, "bar": bar, "outsideRth": outside_rth})

    # def marketdata_history_by_symbol(
    #         self,
    #         symbol: Union[str, StockQuery],
    #         exchange: str = None,
    #         period: str = None,
    #         bar: str = None,
    #         outside_rth: bool = None
    # ) -> Result:  # pragma: no cover
    #     conid = self.get_conids(symbol).data[symbol]
    #     return self.marketdata_history_by_conid(conid, exchange, period, bar, outside_rth)

    # @ensure_list_arg('queries')
    # def marketdata_history_by_symbols(
    #         self,
    #         queries: StockQueries,
    #         period: str = "1min",
    #         bar: str = "1min",
    #         outside_rth: bool = True
    # ) -> dict:
    #     conids = self.get_conids(queries).data
    #
    #     static_params = {"period": period, "bar": bar, "outside_rth": outside_rth}
    #     requests = {symbol: {"kwargs": {'conid': conid} | static_params} for symbol, conid in conids.items()}
    #
    #     # /iserver/marketdata/history accepts 5 concurrent requests at a time
    #     history = execute_in_parallel(self.marketdata_history_by_conid, requests=requests, max_workers=5)
    #
    #     results = {}
    #     for symbol, entry in history.items():
    #         if isinstance(entry, Exception):  # pragma: no cover
    #             _LOGGER.error(f'Error fetching market data for {symbol}')
    #             raise entry
    #
    #         # check if entry['mdAvailability'] has 'S' or 'R' in it
    #         if 'mdAvailability' in entry.data and not (any((key in entry.data['mdAvailability'].upper()) for key in ['S', 'R'])):
    #             _LOGGER.warning(f'Market data for {symbol} is not live: {decode_data_availability(entry.data["mdAvailability"])}')
    #
    #         data = entry.data['data']
    #         records = []
    #         for record in data:
    #             records.append({
    #                 "open": record['o'],
    #                 "high": record['h'],
    #                 "low": record['l'],
    #                 "close": record['c'],
    #                 "volume": record['v'],
    #                 "date": datetime.datetime.fromtimestamp(record['t'] / 1000)
    #             })
    #         results[symbol] = records
    #
    #     return results

    # def reply(self: 'IbkrClient',question_id: str, reply: bool) -> Result:  # pragma: no cover
    #     return self.post(f'iserver/reply/{question_id}', params={"confirmed": reply})

    # def portfolio_invalidate(self: 'IbkrClient',account_id: str = None) -> Result:  # pragma: no cover
    #     if account_id is None:
    #         account_id = self.account_id
    #     return self.post(f'portfolio/{account_id}/positions/invalidate')

    # def marketdata_unsubscribe_all(self: 'IbkrClient') -> Result:  # pragma: no cover
    #     return self.get(f'iserver/marketdata/unsubscribeall')

    # def cancel_order(self: 'IbkrClient',order_id: str, account_id: str = None) -> Result:  # pragma: no cover
    #     if account_id is None:
    #         account_id = self.account_id
    #     return self.delete(f'iserver/account/{account_id}/order/{order_id}')

    ###### COMPLEX ENDPOINTS ######



    # def get_live_orders(self: 'IbkrClient',filters: OneOrMany[str] = None, force: bool = False) -> Result:
    #     """
    #     Retrieves live orders with optional filtering. The filters, if provided, should be a list of strings. These filters are then converted and sent as a comma-separated string in the request to the API.
    #
    #     Parameters:
    #         filters (List[str], optional): A list of strings representing the filters to be applied. Defaults to None
    #         force (bool, optional): Force the system to clear saved information and make a fresh request for orders. Submission will appear as a blank array. Defaults to False.
    #
    #     Available filters:
    #         inactive:
    #             Order was received by the system but is no longer active because it was rejected or cancelled.
    #         pending_submit:
    #             Order has been transmitted but have not received confirmation yet that order accepted by destination exchange or venue.
    #         pre_submitted:
    #             Simulated order transmitted but the order has yet to be elected. Order is held by IB system until election criteria are met.
    #         submitted:
    #             Order has been accepted by the system.
    #         filled:
    #             Order has been completely filled.
    #         pending_cancel:
    #             Sent an order cancellation request but have not yet received confirmation order cancelled by destination exchange or venue.
    #         cancelled:
    #             The balance of your order has been confirmed canceled by the system.
    #         warn_state:
    #             Order has a specific warning message such as for basket orders.
    #         sort_by_time:
    #             There is an initial sort by order state performed so active orders are always above inactive and filled then orders are sorted chronologically.
    #
    #     """
    #     if filters is None and force is False:
    #         params = None
    #     else:
    #         params = {}
    #         if filters is not None:
    #             if not isinstance(filters, list):
    #                 filters = [filters]
    #             params["filters"] = ",".join(filters)
    #         if force is True:
    #             params['force'] = True
    #
    #     return self.get('iserver/account/orders', params=params)

    # def switch_account(self: 'IbkrClient',account_id: str) -> Result:
    #     result = self.post('iserver/account', params={"acctId": account_id})
    #     self.account_id = account_id
    #     self.make_logger()
    #     _LOGGER.warning(f'ALSO NEED TO SWITCH WEBSOCKET ACCOUNT TO {self.account_id}')
    #     return result

    # @ensure_list_arg('queries')
    # def get_stocks(self: 'IbkrClient',queries: StockQueries, default_filtering: bool = True) -> Result:
    #     """
    #     Retrieves and filters stock information based on specified queries.
    #
    #     This function fetches stock data and applies filtering based on the provided queries,
    #     each represented by a StockQuery object. Each query can specify conditions on stock symbol,
    #     name matching, and additional criteria for instruments and contracts. The function processes
    #     these queries to filter and return the relevant stock data.
    #
    #     Parameters:
    #        queries (List[StockQuery]): A list of StockQuery objects, each specifying filter conditions
    #                                    for the stocks to be retrieved. The StockQuery can include criteria
    #                                    like stock symbol, name matching, and specific conditions for
    #                                    instruments and contracts.
    #
    #     Returns:
    #        support.rest_client.Result: The result object containing filtered stock information based on the provided queries,
    #        in form of {symbol: stock_data} dictionary data.
    #
    #     See:
    #         StockQuery: for details on how to construct queries for filtering stocks.
    #     """
    #     symbols = query_to_symbols(queries)
    #
    #     stocks_result = self.get('trsrv/stocks', params={"symbols": symbols})
    #
    #     filtered_stocks_result = filter_stocks(queries, stocks_result, default_filtering)
    #
    #     return filtered_stocks_result

    # @ensure_list_arg('queries')
    # def get_conids(self: 'IbkrClient',queries: StockQueries, default_filtering: bool = True, return_type: str = 'dict') -> Result:
    #     """
    #     Retrieves contract IDs (conids) for given stock queries, ensuring only one conid per query.
    #
    #     This function fetches conids for each stock query provided. It is essential that each query's
    #     filtering criteria is specific enough to return exactly one instrument and one contract,
    #     hence one conid per symbol. If the filtering returns multiple instruments or contracts,
    #     a RuntimeError is raised to prevent ambiguity in conid selection.
    #
    #     Parameters:
    #         queries (List[StockQuery]): A list of StockQuery objects to specify filtering criteria for stocks.
    #         default_filtering (bool, optional): Indicates whether to apply default filtering of {isUS: True}. Defaults to True.
    #         return_type (str, optional): Specifies the return type ('dict' or 'list') of the conids. Defaults to 'dict'.
    #
    #     Returns:
    #         support.rest_client.Result: A Result object containing the conids, either as a dictionary with symbols as keys and
    #                 conids as values or as a list of conids, depending on the return_type parameter.
    #
    #     Raises:
    #         RuntimeError: If the filtering criteria do not result in exactly one instrument and one contract
    #                       per query, thereby leading to ambiguity in conid selection.
    #
    #     See:
    #         StockQuery: for details on how to construct queries for filtering stocks.
    #     """
    #
    #     stocks_result = self.get_stocks(queries, default_filtering)
    #
    #     conids = {}
    #     for i, (symbol, instruments), in enumerate(stocks_result.data.items()):
    #         if len(instruments) != 1 or len(instruments[0]["contracts"]) != 1:
    #             raise RuntimeError(
    #                 f'Filtering stock "{symbol}" returned {len(instruments)} instruments and {len(instruments[0]["contracts"]) if len(instruments) else 0} contracts using following query: {queries[i]}.\nPlease use filters to ensure that only one instrument and one contract per symbol is selected in order to avoid conid ambiguity.\nBe aware that contracts are filtered as {{"isUS": True}} by default. Set default_filtering=False to prevent this default filtering or specify custom filters. See inline documentation for more details.\nInstruments returned:\n{pprint.pformat(instruments)}')
    #
    #         # this should always be a valid expression, otherwise the above exception will have raised
    #         conid = instruments[0]["contracts"][0]["conid"]
    #         conids[symbol] = conid
    #
    #     if return_type == 'list':  # pragma: no cover
    #         conids = [conid for conid in conids.values()]
    #
    #     return pass_result(conids, stocks_result)

    # def submit_order(self: 'IbkrClient',order_request: dict, answers: Answers, account_id: str = None) -> Result:
    #     """
    #     Keep this in mind:
    #     https://interactivebrokers.github.io/tws-api/automated_considerations.html#order_placement
    #     """
    #     if account_id is None:
    #         account_id = self.account_id
    #
    #     if isinstance(order_request, list):
    #         raise RuntimeError(f'IbkrClient.submit_order() does not accept a list of orders, found: {order_request}')
    #
    #     result = self.post(
    #         f'iserver/account/{account_id}/orders',
    #         params={"orders": [order_request]}
    #     )
    #
    #     return handle_questions(result, answers, self.reply)

    # def modify_order(self: 'IbkrClient',order_id: str, order_request: dict, answers: Answers, account_id: str = None) -> Result:
    #     if account_id is None:
    #         account_id = self.account_id
    #
    #     result = self.post(f'iserver/account/{account_id}/order/{order_id}', params=order_request)
    #
    #     return handle_questions(result, answers, self.reply)

    # def check_health(self: 'IbkrClient'):
    #     """
    #     Verifies the health and authentication status of the IBKR Gateway server.
    #
    #     This method checks if the Gateway server is alive and whether the user is authenticated.
    #     It also checks for any competing connections and the connection status.
    #
    #     Returns:
    #         bool: True if the Gateway server is authenticated, not competing, and connected, False otherwise.
    #
    #     Raises:
    #         AttributeError: If the Gateway health check request returns invalid data.
    #     """
    #     try:
    #         result = self.tickle()
    #     except Exception as e:
    #         if isinstance(e, ExternalBrokerError) and e.status_code == 401:
    #             _LOGGER.info(f'Gateway session is not authenticated.')
    #         elif isinstance(e, ConnectTimeout):
    #             _LOGGER.error(f'ConnectTimeout raised when communicating with the Gateway. This could indicate that the Gateway is not running or other connectivity issues.')
    #         else:
    #             _LOGGER.error(f'Tickle request failed: {e}')
    #         return False
    #
    #     if result.data.get('iserver', {}).get('authStatus', {}).get('authenticated', None) is None:
    #         raise AttributeError(f'Health check requests returns invalid data: {result}')
    #
    #     auth_status = result.data['iserver']['authStatus']
    #
    #     authenticated = auth_status['authenticated']
    #     competing = auth_status['competing']
    #     connected = auth_status['connected']
    #
    #     return authenticated and (not competing) and connected
