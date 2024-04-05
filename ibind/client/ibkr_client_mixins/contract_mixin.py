import pprint
from typing import TYPE_CHECKING

from ibind.base.rest_client import pass_result, Result
from ibind.client.ibkr_utils import StockQueries, query_to_symbols, filter_stocks
from ibind.support.py_utils import ensure_list_arg

if TYPE_CHECKING:
    from ibind import IbkrClient

class ContractMixin():
    @ensure_list_arg('queries')
    def get_stocks(self: 'IbkrClient', queries: StockQueries, default_filtering: bool = True) -> Result:
        """
        Retrieves and filters stock information based on specified queries.

        This function fetches stock data and applies filtering based on the provided queries,
        each represented by a StockQuery object. Each query can specify conditions on stock symbol,
        name matching, and additional criteria for instruments and contracts. The function processes
        these queries to filter and return the relevant stock data.

        Parameters:
           queries (List[StockQuery]): A list of StockQuery objects, each specifying filter conditions
                                       for the stocks to be retrieved. The StockQuery can include criteria
                                       like stock symbol, name matching, and specific conditions for
                                       instruments and contracts.

        Returns:
           support.rest_client.Result: The result object containing filtered stock information based on the provided queries,
           in form of {symbol: stock_data} dictionary data.

        See:
            StockQuery: for details on how to construct queries for filtering stocks.
        """
        symbols = query_to_symbols(queries)

        stocks_result = self.get('trsrv/stocks', params={"symbols": symbols})

        filtered_stocks_result = filter_stocks(queries, stocks_result, default_filtering)

        return filtered_stocks_result

    @ensure_list_arg('queries')
    def get_conids(self: 'IbkrClient', queries: StockQueries, default_filtering: bool = True, return_type: str = 'dict') -> Result:
        """
        Retrieves contract IDs (conids) for given stock queries, ensuring only one conid per query.

        This function fetches conids for each stock query provided. It is essential that each query's
        filtering criteria is specific enough to return exactly one instrument and one contract,
        hence one conid per symbol. If the filtering returns multiple instruments or contracts,
        a RuntimeError is raised to prevent ambiguity in conid selection.

        Parameters:
            queries (List[StockQuery]): A list of StockQuery objects to specify filtering criteria for stocks.
            default_filtering (bool, optional): Indicates whether to apply default filtering of {isUS: True}. Defaults to True.
            return_type (str, optional): Specifies the return type ('dict' or 'list') of the conids. Defaults to 'dict'.

        Returns:
            support.rest_client.Result: A Result object containing the conids, either as a dictionary with symbols as keys and
                    conids as values or as a list of conids, depending on the return_type parameter.

        Raises:
            RuntimeError: If the filtering criteria do not result in exactly one instrument and one contract
                          per query, thereby leading to ambiguity in conid selection.

        See:
            StockQuery: for details on how to construct queries for filtering stocks.
        """

        stocks_result = self.get_stocks(queries, default_filtering)

        conids = {}
        for i, (symbol, instruments), in enumerate(stocks_result.data.items()):
            if len(instruments) != 1 or len(instruments[0]["contracts"]) != 1:
                raise RuntimeError(
                    f'Filtering stock "{symbol}" returned {len(instruments)} instruments and {len(instruments[0]["contracts"]) if len(instruments) else 0} contracts using following query: {queries[i]}.\nPlease use filters to ensure that only one instrument and one contract per symbol is selected in order to avoid conid ambiguity.\nBe aware that contracts are filtered as {{"isUS": True}} by default. Set default_filtering=False to prevent this default filtering or specify custom filters. See inline documentation for more details.\nInstruments returned:\n{pprint.pformat(instruments)}')

            # this should always be a valid expression, otherwise the above exception will have raised
            conid = instruments[0]["contracts"][0]["conid"]
            conids[symbol] = conid

        if return_type == 'list':  # pragma: no cover
            conids = [conid for conid in conids.values()]

        return pass_result(conids, stocks_result)