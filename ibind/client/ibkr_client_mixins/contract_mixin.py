import pprint
from typing import TYPE_CHECKING, List

from ibind.base.rest_client import pass_result, Result
from ibind.client.ibkr_utils import StockQueries, query_to_symbols, filter_stocks
from ibind.support.py_utils import ensure_list_arg, OneOrMany, params_dict

if TYPE_CHECKING:  # pragma: no cover
    from ibind import IbkrClient



class ContractMixin():

    @ensure_list_arg('conids')
    def security_definition_by_conid(self: 'IbkrClient', conids: OneOrMany[str]) -> Result:
        return self.get('trsrv/secdef', {'conids': ",".join(conids)})

    def all_conids_by_exchange(self: 'IbkrClient', exchange: str) -> Result:
        return self.get('trsrv/all-conids', {'exchange': exchange})

    def contract_information_by_conid(self: 'IbkrClient', conid: str) -> Result:
        return self.get(f'iserver/contract/{conid}/info')

    def currency_pairs(self: 'IbkrClient', currency: str) -> Result:
        return self.get(f'iserver/currency/pairs', {'currency': currency})

    def currency_exchange_rate(self: 'IbkrClient', source: str, target: str) -> Result:
        return self.get(f'iserver/exchangerate', {'source': source, target: target})

    def info_and_rules_by_conid(self: 'IbkrClient', conid: str, is_buy: bool) -> Result:
        return self.get(f'iserver/contract/{conid}/info-and-rules', {'isBuy': is_buy})

    def algo_params_by_conid(
            self: 'IbkrClient',
            conid: str,
            algos: List[str] = None,
            add_description: str = None,
            add_params: str = None
    ) -> Result:
        params = params_dict(
            optional={
                'algos': algos,
                'addDescription': add_description,
                'addParams': add_params
            }, preprocessors={'algos': ';'.join}
        )

        return self.get(f'iserver/contract/{conid}/algos', params)

    def search_bond_filter_information(self: 'IbkrClient', symbol: str, issuer_id: str) -> Result:
        return self.get(f'iserver/secdef/bond-filters', {'symbol': symbol, 'issuerId': issuer_id})

    def search_contract_by_symbol(
            self: 'IbkrClient',
            symbol: str,
            name: bool = None,
            sec_type: str = None
    ) -> Result:
        params = params_dict(
            {'symbol': symbol},
            optional={'name': name, 'secType': sec_type}
        )

        return self.get(f'iserver/secdef/search', params)

    def search_contract_rules(
            self: 'IbkrClient',
            conid: int,
            exchange: str = None,
            is_buy: bool = None,
            modify_order: bool = None,
            order_id: int = None,
    ) -> Result:
        params = params_dict(
            {'conid': conid},
            optional={
                'exchange': exchange,
                'isBuy': is_buy,
                'modifyOrder': modify_order,
                'orderId': order_id
            }
        )

        return self.post(f'iserver/contract/rules', params)

    def search_secdef_info_by_conid(
            self: 'IbkrClient',
            conid: str,
            sectype: str,
            month: str,
            exchange: str = None,
            strike: str = None,
            right: str = None,
            issuer_id: str = None,
    ) -> Result:
        params = params_dict(
            {
                'conid': conid,
                'sectype': sectype,
                'month': month,
            },
            optional={
                'exchange': exchange,
                'strike': strike,
                'right': right,
                'issuerId': issuer_id,
            }
        )

        return self.get(f'iserver/secdef/info', params)

    def search_strikes_by_conid(
            self: 'IbkrClient',
            conid: str,
            sectype: str,
            month: str,
            exchange: str = None,
    ) -> Result:
        params = params_dict(
            {
                'conid': conid,
                'sectype': sectype,
                'month': month,
            },
            optional={'exchange': exchange}
        )

        return self.get(f'iserver/secdef/strikes', params)

    @ensure_list_arg('symbols')
    def search_future_by_symbol(self: 'IbkrClient', symbols: OneOrMany[str]) -> Result:
        return self.get(f'trsrv/futures', {'symbols': ','.join(symbols)})

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

    def trading_schedule_by_symbol(
            self: 'IbkrClient',
            asset_class: str,
            symbol: str,
            exchange: str = None,
            exchange_filter: str = None,
    ) -> Result:
        params = params_dict(
            {'assetClass': asset_class, 'symbol': symbol, },
            optional={'exchange': exchange, 'exchangeFilter': exchange_filter}
        )

        return self.get(f'trsrv/secdef/schedule', params)
