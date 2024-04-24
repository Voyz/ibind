import pprint
from typing import TYPE_CHECKING, List

from ibind.base.rest_client import pass_result, Result
from ibind.client.ibkr_utils import StockQueries, query_to_symbols, filter_stocks
from ibind.support.py_utils import ensure_list_arg, OneOrMany, params_dict

if TYPE_CHECKING:  # pragma: no cover
    from ibind import IbkrClient


class ContractMixin():
    """
    https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#contract
    """

    @ensure_list_arg('conids')
    def security_definition_by_conid(self: 'IbkrClient', conids: OneOrMany[str]) -> Result:  # pragma: no cover
        """
        Returns a list of security definitions for the given conids.

        Parameters:
            conids (OneOrMany[str]): One or many contract ID strings. Value Format: 1234.
        """
        return self.get('trsrv/secdef', {'conids': ",".join(conids)})

    def all_conids_by_exchange(self: 'IbkrClient', exchange: str) -> Result:  # pragma: no cover
        """
        Send out a request to retrieve all contracts made available on a requested exchange. This returns all contracts that are tradable on the exchange, even those that are not using the exchange as their primary listing.

        Note: This is only available for Stock contracts.

        Parameters:
            exchange (str): Specify a single exchange to receive conids for.
        """
        return self.get('trsrv/all-conids', {'exchange': exchange})

    def contract_information_by_conid(self: 'IbkrClient', conid: str) -> Result:  # pragma: no cover
        """
        Requests full contract details for the given conid.

        Parameters:
            conid (str): Contract ID for the desired contract information.
        """
        return self.get(f'iserver/contract/{conid}/info')

    def currency_pairs(self: 'IbkrClient', currency: str) -> Result:  # pragma: no cover
        """
        Obtains available currency pairs corresponding to the given target currency.

        Parameters:
            currency (str): Specify the target currency you would like to receive official pairs of. Valid Structure: “USD”.
        """
        return self.get(f'iserver/currency/pairs', {'currency': currency})

    def currency_exchange_rate(self: 'IbkrClient', source: str, target: str) -> Result:  # pragma: no cover
        """
        Obtains the exchange rates of the currency pair.

        Parameters:
            source (str): Specify the base currency to request data for. Valid Structure: “AUD”
            target (str): Specify the quote currency to request data for. Valid Structure: “USD”
        """
        return self.get(f'iserver/exchangerate', {'source': source, target: target})

    def info_and_rules_by_conid(self: 'IbkrClient', conid: str, is_buy: bool) -> Result:  # pragma: no cover
        """
        Returns both contract info and rules from a single endpoint.

        Parameters:
            conid (str): Contract identifier for the given contract.
            is_buy (bool, optional): Indicates whether you are searching for Buy or Sell order rules. Set to true for Buy Orders, set to false for Sell Orders.
        """
        return self.get(f'iserver/contract/{conid}/info-and-rules', {'isBuy': is_buy})

    def algo_params_by_conid(
            self: 'IbkrClient',
            conid: str,
            algos: List[str] = None,
            add_description: str = None,
            add_params: str = None
    ) -> Result:  # pragma: no cover
        """
        Returns supported IB Algos for contract.

        Parameters:
            conid (str): Contract identifier for the requested contract of interest.
            algos (str, optional): List of algo ids. Max of 8 algos ids can be specified. Case sensitive to algo id.
            add_description (str, optional): Whether or not to add algo descriptions to response. Set to 1 for yes, 0 for no.
            add_params (str, optional): Whether or not to show algo parameters. Set to 1 for yes, 0 for no.
        """
        params = params_dict(
            optional={
                'algos': algos,
                'addDescription': add_description,
                'addParams': add_params
            }, preprocessors={'algos': ';'.join}
        )

        return self.get(f'iserver/contract/{conid}/algos', params)

    def search_bond_filter_information(self: 'IbkrClient', symbol: str, issuer_id: str) -> Result:  # pragma: no cover
        """
        Request a list of filters relating to a given Bond issuerID.

        Parameters:
            symbol (str): This should always be set to “BOND”
            issuer_id (str): Specifies the issuerId value used to designate the bond issuer type.
        """
        return self.get(f'iserver/secdef/bond-filters', {'symbol': symbol, 'issuerId': issuer_id})

    def search_contract_by_symbol(
            self: 'IbkrClient',
            symbol: str,
            name: bool = None,
            sec_type: str = None
    ) -> Result:  # pragma: no cover
        """
        Search by underlying symbol or company name. Relays back what derivative contract(s) it has. This endpoint must be called before using /secdef/info.

        Parameters:
            symbol (str): Underlying symbol of interest. May also pass company name if 'name' is set to true, or bond issuer type to retrieve bonds.
            name (bool, optional): Determines if symbol reflects company name or ticker symbol.
            sec_type (str, optional): Valid Values: “STK”, “IND”, “BOND”. Declares underlying security type.
        """
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
    ) -> Result:  # pragma: no cover
        """
        Returns trading related rules for a specific contract and side.

        Parameters:
            conid (Number): Contract identifier for the interested contract.
            exchange (str, optional): Designate the exchange you wish to receive information for in relation to the contract.
            is_buy (bool, optional): Side of the market rules apply to. Set to true for Buy Orders, set to false for Sell Orders. Defaults to true or Buy side rules.
            modify_order (bool, optional): Used to find trading rules related to an existing order.
            order_id (int): Required for modify_order:true. Specify the order identifier used for tracking a given order.
        """
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
            sec_type: str,
            month: str,
            exchange: str = None,
            strike: str = None,
            right: str = None,
            issuer_id: str = None,
    ) -> Result:  # pragma: no cover
        """
        Provides Contract Details of Futures, Options, Warrants, Cash and CFDs based on conid.

        Parameters:
            conid (str): Contract identifier of the underlying. May also pass the final derivative conid directly.
            sec_type (str): Security type of the requested contract of interest.
            month (str): Required for Derivatives. Expiration month for the given derivative.
            exchange (str, optional): Designate the exchange you wish to receive information for in relation to the contract.
            strike (str): Required for Options and Futures Options. Set the strike price for the requested contract details.
            right (str): Required for Options. Set the right for the given contract. Value Format: “C” for Call or “P” for Put.
            issuer_id (str): Required for Bonds. Set the issuer_id for the given bond issuer type. Example Format: “e1234567”
        """

        params = params_dict(
            {
                'conid': conid,
                'sectype': sec_type,
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
            sec_type: str,
            month: str,
            exchange: str = None,
    ) -> Result:  # pragma: no cover
        """
        Query to receive a list of potential strikes supported for a given underlying.

        Parameters:
            conid (str): Contract Identifier number for the underlying.
            sec_type (str): Security type of the derivatives you are looking for. Value Format: “OPT” or “WAR”.
            month (str): Expiration month and year for the given underlying. Value Format: {3 character month}{2 character year}. Example: AUG23.
            exchange (str, optional): Exchange from which derivatives should be retrieved from. Default value is set to SMART.
        """
        params = params_dict(
            {
                'conid': conid,
                'sectype': sec_type,
                'month': month,
            },
            optional={'exchange': exchange}
        )

        return self.get(f'iserver/secdef/strikes', params)

    @ensure_list_arg('symbols')
    def search_future_by_symbol(self: 'IbkrClient', symbols: OneOrMany[str]) -> Result:  # pragma: no cover
        """
        Returns a list of non-expired future contracts for given symbol(s).

        Parameters:
            symbols (str): Indicate the symbol(s) of the underlier you are trying to retrieve futures on. Accepts list of string of symbols.
        """
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
    ) -> Result:  # pragma: no cover
        """
        Returns the trading schedule up to a month for the requested contract.

        Parameters:
            asset_class (str): Specify the security type of the given contract. Value Formats: Stock: STK, Option: OPT, Future: FUT, Contract For Difference: CFD, Warrant: WAR, Forex: SWP, Mutual Fund: FND, Bond: BND, Inter-Commodity Spreads: ICS.
            symbol (str): Specify the symbol for your contract.
            exchange (str, optional): Specify the primary exchange of your contract.
            exchange_filter (str, optional): Specify all exchanges you want to retrieve data from.
        """
        params = params_dict(
            {'assetClass': asset_class, 'symbol': symbol},
            optional={'exchange': exchange, 'exchangeFilter': exchange_filter}
        )

        return self.get(f'trsrv/secdef/schedule', params)
