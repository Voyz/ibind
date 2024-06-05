# Table of Contents

* [Result](#base.rest_client.Result)
* [IbkrClient](#client.ibkr_client.IbkrClient)
  * [\_\_init\_\_](#client.ibkr_client.IbkrClient.__init__)
* [AccountsMixin](#client.ibkr_client_mixins.accounts_mixin.AccountsMixin)
  * [account\_profit\_and\_loss](#client.ibkr_client_mixins.accounts_mixin.AccountsMixin.account_profit_and_loss)
  * [search\_dynamic\_account](#client.ibkr_client_mixins.accounts_mixin.AccountsMixin.search_dynamic_account)
  * [set\_dynamic\_account](#client.ibkr_client_mixins.accounts_mixin.AccountsMixin.set_dynamic_account)
  * [signatures\_and\_owners](#client.ibkr_client_mixins.accounts_mixin.AccountsMixin.signatures_and_owners)
  * [switch\_account](#client.ibkr_client_mixins.accounts_mixin.AccountsMixin.switch_account)
  * [receive\_brokerage\_accounts](#client.ibkr_client_mixins.accounts_mixin.AccountsMixin.receive_brokerage_accounts)
* [ContractMixin](#client.ibkr_client_mixins.contract_mixin.ContractMixin)
  * [security\_definition\_by\_conid](#client.ibkr_client_mixins.contract_mixin.ContractMixin.security_definition_by_conid)
  * [all\_conids\_by\_exchange](#client.ibkr_client_mixins.contract_mixin.ContractMixin.all_conids_by_exchange)
  * [contract\_information\_by\_conid](#client.ibkr_client_mixins.contract_mixin.ContractMixin.contract_information_by_conid)
  * [currency\_pairs](#client.ibkr_client_mixins.contract_mixin.ContractMixin.currency_pairs)
  * [currency\_exchange\_rate](#client.ibkr_client_mixins.contract_mixin.ContractMixin.currency_exchange_rate)
  * [info\_and\_rules\_by\_conid](#client.ibkr_client_mixins.contract_mixin.ContractMixin.info_and_rules_by_conid)
  * [algo\_params\_by\_conid](#client.ibkr_client_mixins.contract_mixin.ContractMixin.algo_params_by_conid)
  * [search\_bond\_filter\_information](#client.ibkr_client_mixins.contract_mixin.ContractMixin.search_bond_filter_information)
  * [search\_contract\_by\_symbol](#client.ibkr_client_mixins.contract_mixin.ContractMixin.search_contract_by_symbol)
  * [search\_contract\_rules](#client.ibkr_client_mixins.contract_mixin.ContractMixin.search_contract_rules)
  * [search\_secdef\_info\_by\_conid](#client.ibkr_client_mixins.contract_mixin.ContractMixin.search_secdef_info_by_conid)
  * [search\_strikes\_by\_conid](#client.ibkr_client_mixins.contract_mixin.ContractMixin.search_strikes_by_conid)
  * [security\_future\_by\_symbol](#client.ibkr_client_mixins.contract_mixin.ContractMixin.security_future_by_symbol)
  * [security\_stocks\_by\_symbol](#client.ibkr_client_mixins.contract_mixin.ContractMixin.security_stocks_by_symbol)
  * [stock\_conid\_by\_symbol](#client.ibkr_client_mixins.contract_mixin.ContractMixin.stock_conid_by_symbol)
  * [trading\_schedule\_by\_symbol](#client.ibkr_client_mixins.contract_mixin.ContractMixin.trading_schedule_by_symbol)
* [MarketdataMixin](#client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin)
  * [live\_marketdata\_snapshot](#client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.live_marketdata_snapshot)
  * [regulatory\_snapshot](#client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.regulatory_snapshot)
  * [marketdata\_history\_by\_conid](#client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.marketdata_history_by_conid)
  * [historical\_marketdata\_beta](#client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.historical_marketdata_beta)
  * [marketdata\_history\_by\_symbol](#client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.marketdata_history_by_symbol)
  * [marketdata\_history\_by\_symbols](#client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.marketdata_history_by_symbols)
  * [marketdata\_unsubscribe](#client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.marketdata_unsubscribe)
  * [marketdata\_unsubscribe\_all](#client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.marketdata_unsubscribe_all)
* [OrderMixin](#client.ibkr_client_mixins.order_mixin.OrderMixin)
  * [live\_orders](#client.ibkr_client_mixins.order_mixin.OrderMixin.live_orders)
  * [order\_status](#client.ibkr_client_mixins.order_mixin.OrderMixin.order_status)
  * [trades](#client.ibkr_client_mixins.order_mixin.OrderMixin.trades)
  * [place\_order](#client.ibkr_client_mixins.order_mixin.OrderMixin.place_order)
  * [reply](#client.ibkr_client_mixins.order_mixin.OrderMixin.reply)
  * [whatif\_order](#client.ibkr_client_mixins.order_mixin.OrderMixin.whatif_order)
  * [cancel\_order](#client.ibkr_client_mixins.order_mixin.OrderMixin.cancel_order)
  * [modify\_order](#client.ibkr_client_mixins.order_mixin.OrderMixin.modify_order)
  * [suppress\_messages](#client.ibkr_client_mixins.order_mixin.OrderMixin.suppress_messages)
  * [reset\_suppressed\_messages](#client.ibkr_client_mixins.order_mixin.OrderMixin.reset_suppressed_messages)
* [PortfolioMixin](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin)
  * [portfolio\_accounts](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.portfolio_accounts)
  * [portfolio\_subaccounts](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.portfolio_subaccounts)
  * [large\_portfolio\_subaccounts](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.large_portfolio_subaccounts)
  * [portfolio\_account\_information](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.portfolio_account_information)
  * [portfolio\_account\_allocation](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.portfolio_account_allocation)
  * [portfolio\_account\_allocations](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.portfolio_account_allocations)
  * [positions](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.positions)
  * [positions2](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.positions2)
  * [positions\_by\_conid](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.positions_by_conid)
  * [invalidate\_backend\_portfolio\_cache](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.invalidate_backend_portfolio_cache)
  * [portfolio\_summary](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.portfolio_summary)
  * [get\_ledger](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.get_ledger)
  * [position\_and\_contract\_info](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.position_and_contract_info)
  * [account\_performance](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.account_performance)
  * [transaction\_history](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.transaction_history)
* [ScannerMixin](#client.ibkr_client_mixins.scanner_mixin.ScannerMixin)
  * [scanner\_parameters](#client.ibkr_client_mixins.scanner_mixin.ScannerMixin.scanner_parameters)
  * [market\_scanner](#client.ibkr_client_mixins.scanner_mixin.ScannerMixin.market_scanner)
  * [hmds\_scanner\_parameters](#client.ibkr_client_mixins.scanner_mixin.ScannerMixin.hmds_scanner_parameters)
  * [hmds\_market\_scanner](#client.ibkr_client_mixins.scanner_mixin.ScannerMixin.hmds_market_scanner)
* [SessionMixin](#client.ibkr_client_mixins.session_mixin.SessionMixin)
  * [authentication\_status](#client.ibkr_client_mixins.session_mixin.SessionMixin.authentication_status)
  * [initialize\_brokerage\_session](#client.ibkr_client_mixins.session_mixin.SessionMixin.initialize_brokerage_session)
  * [logout](#client.ibkr_client_mixins.session_mixin.SessionMixin.logout)
  * [tickle](#client.ibkr_client_mixins.session_mixin.SessionMixin.tickle)
  * [reauthenticate](#client.ibkr_client_mixins.session_mixin.SessionMixin.reauthenticate)
  * [validate](#client.ibkr_client_mixins.session_mixin.SessionMixin.validate)
  * [check\_health](#client.ibkr_client_mixins.session_mixin.SessionMixin.check_health)
* [WatchlistMixin](#client.ibkr_client_mixins.watchlist_mixin.WatchlistMixin)
  * [create\_watchlist](#client.ibkr_client_mixins.watchlist_mixin.WatchlistMixin.create_watchlist)
  * [get\_all\_watchlists](#client.ibkr_client_mixins.watchlist_mixin.WatchlistMixin.get_all_watchlists)
  * [get\_watchlist\_information](#client.ibkr_client_mixins.watchlist_mixin.WatchlistMixin.get_watchlist_information)
  * [delete\_watchlist](#client.ibkr_client_mixins.watchlist_mixin.WatchlistMixin.delete_watchlist)

<a id="base.rest_client.Result"></a>

## Result

A class to encapsulate the result of an API request.

This class is used to store and handle data returned from an API call. It includes the response data and
the original request details.

Attributes:

- `data` _Optional[Union[list, dict]]_ - The data returned from the operation. Can be either a list or a dictionary.
- `request` _Optional[dict]_ - Details of the request that resulted in this data.

<a id="client.ibkr_client.IbkrClient"></a>

## IbkrClient

A client class for interfacing with the IBKR API, extending the RestClient class.

This subclass of RestClient is specifically designed for the IBKR API. It inherits
the foundational REST API interaction capabilities from RestClient and adds functionalities
particular to the IBKR API, such as specific endpoint handling.

The class provides methods to perform various operations with the IBKR API, such as
fetching stock data, submitting orders, and managing account information.

See: https://interactivebrokers.github.io/cpwebapi/endpoints

Notes:

  - All endpoint mappings are defined as class mixins, categorised similar to the IBKR REST API documentation. See appropriate mixins for more information.

<a id="client.ibkr_client.IbkrClient.__init__"></a>

### \_\_init\_\_

```python
def __init__(account_id: Optional[str] = var.IBIND_ACCOUNT_ID,
             url: str = var.IBIND_REST_URL,
             host: str = 'localhost',
             port: str = '5000',
             base_route: str = '/v1/api/',
             cacert: Union[str, os.PathLike, bool] = var.IBIND_CACERT,
             timeout: float = 10,
             max_retries: int = 3) -> None
```

Arguments:

- `account_id` _str_ - An identifier for the account.
- `url` _str_ - The base URL for the REST API.
- `host` _str, optional_ - Host for the IBKR REST API. Defaults to 'localhost'.
- `port` _str, optional_ - Port for the IBKR REST API. Defaults to '5000'
- `base_route` _str, optional_ - Base route for the IBKR REST API. Defaults to '/v1/api/'.
- `cacert` _Union[os.PathLike, bool], optional_ - Path to the CA certificate file for SSL verification,
  or False to disable SSL verification. Defaults to False.
- `timeout` _float, optional_ - Timeout in seconds for the API requests. Defaults to 10.
- `max_retries` _int, optional_ - Maximum number of retries for failed API requests. Defaults to 3.

<a id="client.ibkr_client_mixins.accounts_mixin.AccountsMixin"></a>

## AccountsMixin

https://ibkrcampus.com/ibkr-api-page/webapi-doc/#accounts

<a id="client.ibkr_client_mixins.accounts_mixin.AccountsMixin.account_profit_and_loss"></a>

### account\_profit\_and\_loss

```python
def account_profit_and_loss() -> Result
```

Returns an object containing PnL for the selected account and its models (if any).

<a id="client.ibkr_client_mixins.accounts_mixin.AccountsMixin.search_dynamic_account"></a>

### search\_dynamic\_account

```python
def search_dynamic_account(search_pattern: str) -> Result
```

Searches for broker accounts configured with the DYNACCT property using a specified pattern.

Arguments:

- `search_pattern` _str_ - The pattern used to describe credentials to search for. Valid Format: “DU” in order to query all paper accounts.
  

Notes:

  - Customers without the DYNACCT property will receive the following 503 message: "Details currently unavailable. Please try again later and contact client services if the issue persists."

<a id="client.ibkr_client_mixins.accounts_mixin.AccountsMixin.set_dynamic_account"></a>

### set\_dynamic\_account

```python
def set_dynamic_account(account_id: str) -> Result
```

Set the active dynamic account. Values retrieved from Search Dynamic Account.

Arguments:

- `account_id` _str_ - The account ID that should be set for future requests.
  

Notes:

  - If the account does not have the DYNACCT property, a 503 error message is returned.

<a id="client.ibkr_client_mixins.accounts_mixin.AccountsMixin.signatures_and_owners"></a>

### signatures\_and\_owners

```python
def signatures_and_owners(account_id: str = None) -> Result
```

Receive a list of all applicant names on the account and for which account and entity is represented.

Arguments:

- `account_id` _str_ - Pass the account identifier to receive information for. Valid Structure: “U1234567”.

<a id="client.ibkr_client_mixins.accounts_mixin.AccountsMixin.switch_account"></a>

### switch\_account

```python
def switch_account(account_id: str) -> Result
```

Switch the active account for how you request data.

Only available for financial advisors and multi-account structures.

Arguments:

- `acctId` _str_ - Identifier for the unique account to retrieve information from. Value Format: “DU1234567”.

<a id="client.ibkr_client_mixins.accounts_mixin.AccountsMixin.receive_brokerage_accounts"></a>

### receive\_brokerage\_accounts

```python
def receive_brokerage_accounts() -> Result
```

Returns a list of accounts the user has trading access to, their respective aliases, and the currently selected account. Note this endpoint must be called before modifying an order or querying open orders.

<a id="client.ibkr_client_mixins.contract_mixin.ContractMixin"></a>

## ContractMixin

https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#contract

<a id="client.ibkr_client_mixins.contract_mixin.ContractMixin.security_definition_by_conid"></a>

### security\_definition\_by\_conid

```python
@ensure_list_arg('conids')
def security_definition_by_conid(conids: OneOrMany[str]) -> Result
```

Returns a list of security definitions for the given conids.

Arguments:

- `conids` _OneOrMany[str]_ - One or many contract ID strings. Value Format: 1234.

<a id="client.ibkr_client_mixins.contract_mixin.ContractMixin.all_conids_by_exchange"></a>

### all\_conids\_by\_exchange

```python
def all_conids_by_exchange(exchange: str) -> Result
```

Send out a request to retrieve all contracts made available on a requested exchange. This returns all contracts that are tradable on the exchange, even those that are not using the exchange as their primary listing.

Note: This is only available for Stock contracts.

Arguments:

- `exchange` _str_ - Specify a single exchange to receive conids for.

<a id="client.ibkr_client_mixins.contract_mixin.ContractMixin.contract_information_by_conid"></a>

### contract\_information\_by\_conid

```python
def contract_information_by_conid(conid: str) -> Result
```

Requests full contract details for the given conid.

Arguments:

- `conid` _str_ - Contract ID for the desired contract information.

<a id="client.ibkr_client_mixins.contract_mixin.ContractMixin.currency_pairs"></a>

### currency\_pairs

```python
def currency_pairs(currency: str) -> Result
```

Obtains available currency pairs corresponding to the given target currency.

Arguments:

- `currency` _str_ - Specify the target currency you would like to receive official pairs of. Valid Structure: “USD”.

<a id="client.ibkr_client_mixins.contract_mixin.ContractMixin.currency_exchange_rate"></a>

### currency\_exchange\_rate

```python
def currency_exchange_rate(source: str, target: str) -> Result
```

Obtains the exchange rates of the currency pair.

Arguments:

- `source` _str_ - Specify the base currency to request data for. Valid Structure: “AUD”
- `target` _str_ - Specify the quote currency to request data for. Valid Structure: “USD”

<a id="client.ibkr_client_mixins.contract_mixin.ContractMixin.info_and_rules_by_conid"></a>

### info\_and\_rules\_by\_conid

```python
def info_and_rules_by_conid(conid: str, is_buy: bool) -> Result
```

Returns both contract info and rules from a single endpoint.

Arguments:

- `conid` _str_ - Contract identifier for the given contract.
- `is_buy` _bool, optional_ - Indicates whether you are searching for Buy or Sell order rules. Set to true for Buy Orders, set to false for Sell Orders.

<a id="client.ibkr_client_mixins.contract_mixin.ContractMixin.algo_params_by_conid"></a>

### algo\_params\_by\_conid

```python
def algo_params_by_conid(conid: str,
                         algos: List[str] = None,
                         add_description: str = None,
                         add_params: str = None) -> Result
```

Returns supported IB Algos for contract.

Arguments:

- `conid` _str_ - Contract identifier for the requested contract of interest.
- `algos` _str, optional_ - List of algo ids. Max of 8 algos ids can be specified. Case sensitive to algo id.
- `add_description` _str, optional_ - Whether or not to add algo descriptions to response. Set to 1 for yes, 0 for no.
- `add_params` _str, optional_ - Whether or not to show algo parameters. Set to 1 for yes, 0 for no.

<a id="client.ibkr_client_mixins.contract_mixin.ContractMixin.search_bond_filter_information"></a>

### search\_bond\_filter\_information

```python
def search_bond_filter_information(symbol: str, issuer_id: str) -> Result
```

Request a list of filters relating to a given Bond issuerID.

Arguments:

- `symbol` _str_ - This should always be set to “BOND”
- `issuer_id` _str_ - Specifies the issuerId value used to designate the bond issuer type.

<a id="client.ibkr_client_mixins.contract_mixin.ContractMixin.search_contract_by_symbol"></a>

### search\_contract\_by\_symbol

```python
def search_contract_by_symbol(symbol: str,
                              name: bool = None,
                              sec_type: str = None) -> Result
```

Search by underlying symbol or company name. Relays back what derivative contract(s) it has. This endpoint must be called before using /secdef/info.

Arguments:

- `symbol` _str_ - Underlying symbol of interest. May also pass company name if 'name' is set to true, or bond issuer type to retrieve bonds.
- `name` _bool, optional_ - Determines if symbol reflects company name or ticker symbol.
- `sec_type` _str, optional_ - Valid Values: “STK”, “IND”, “BOND”. Declares underlying security type.

<a id="client.ibkr_client_mixins.contract_mixin.ContractMixin.search_contract_rules"></a>

### search\_contract\_rules

```python
def search_contract_rules(conid: int,
                          exchange: str = None,
                          is_buy: bool = None,
                          modify_order: bool = None,
                          order_id: int = None) -> Result
```

Returns trading related rules for a specific contract and side.

Arguments:

- `conid` _Number_ - Contract identifier for the interested contract.
- `exchange` _str, optional_ - Designate the exchange you wish to receive information for in relation to the contract.
- `is_buy` _bool, optional_ - Side of the market rules apply to. Set to true for Buy Orders, set to false for Sell Orders. Defaults to true or Buy side rules.
- `modify_order` _bool, optional_ - Used to find trading rules related to an existing order.
- `order_id` _int_ - Required for modify_order:true. Specify the order identifier used for tracking a given order.

<a id="client.ibkr_client_mixins.contract_mixin.ContractMixin.search_secdef_info_by_conid"></a>

### search\_secdef\_info\_by\_conid

```python
def search_secdef_info_by_conid(conid: str,
                                sec_type: str,
                                month: str,
                                exchange: str = None,
                                strike: str = None,
                                right: str = None,
                                issuer_id: str = None) -> Result
```

Provides Contract Details of Futures, Options, Warrants, Cash and CFDs based on conid.

Arguments:

- `conid` _str_ - Contract identifier of the underlying. May also pass the final derivative conid directly.
- `sec_type` _str_ - Security type of the requested contract of interest.
- `month` _str_ - Required for Derivatives. Expiration month for the given derivative.
- `exchange` _str, optional_ - Designate the exchange you wish to receive information for in relation to the contract.
- `strike` _str_ - Required for Options and Futures Options. Set the strike price for the requested contract details.
- `right` _str_ - Required for Options. Set the right for the given contract. Value Format: “C” for Call or “P” for Put.
- `issuer_id` _str_ - Required for Bonds. Set the issuer_id for the given bond issuer type. Example Format: “e1234567”

<a id="client.ibkr_client_mixins.contract_mixin.ContractMixin.search_strikes_by_conid"></a>

### search\_strikes\_by\_conid

```python
def search_strikes_by_conid(conid: str,
                            sec_type: str,
                            month: str,
                            exchange: str = None) -> Result
```

Query to receive a list of potential strikes supported for a given underlying.

Arguments:

- `conid` _str_ - Contract Identifier number for the underlying.
- `sec_type` _str_ - Security type of the derivatives you are looking for. Value Format: “OPT” or “WAR”.
- `month` _str_ - Expiration month and year for the given underlying. Value Format: {3 character month}{2 character year}. Example: AUG23.
- `exchange` _str, optional_ - Exchange from which derivatives should be retrieved from. Default value is set to SMART.

<a id="client.ibkr_client_mixins.contract_mixin.ContractMixin.security_future_by_symbol"></a>

### security\_future\_by\_symbol

```python
@ensure_list_arg('symbols')
def security_future_by_symbol(symbols: OneOrMany[str]) -> Result
```

Returns a list of non-expired future contracts for given symbol(s).

Arguments:

- `symbols` _str_ - Indicate the symbol(s) of the underlier you are trying to retrieve futures on. Accepts list of string of symbols.

<a id="client.ibkr_client_mixins.contract_mixin.ContractMixin.security_stocks_by_symbol"></a>

### security\_stocks\_by\_symbol

```python
@ensure_list_arg('queries')
def security_stocks_by_symbol(queries: StockQueries,
                              default_filtering: bool = True) -> Result
```

Retrieves and filters stock information based on specified queries.

This function fetches stock data and applies filtering based on the provided queries,
each represented by a StockQuery object. Each query can specify conditions on stock symbol,
name matching, and additional criteria for instruments and contracts. The function processes
these queries to filter and return the relevant stock data.

Arguments:

- `queries` _List[StockQuery]_ - A list of StockQuery objects, each specifying filter conditions
  for the stocks to be retrieved. The StockQuery can include criteria
  like stock symbol, name matching, and specific conditions for
  instruments and contracts.
  

Returns:

- `support.rest_client.Result` - The result object containing filtered stock information based on the provided queries,
  in form of {symbol: stock_data} dictionary data.
  
  See:
- `StockQuery` - for details on how to construct queries for filtering stocks.

<a id="client.ibkr_client_mixins.contract_mixin.ContractMixin.stock_conid_by_symbol"></a>

### stock\_conid\_by\_symbol

```python
@ensure_list_arg('queries')
def stock_conid_by_symbol(queries: StockQueries,
                          default_filtering: bool = True,
                          return_type: str = 'dict') -> Result
```

Retrieves contract IDs (conids) for given stock queries, ensuring only one conid per query.

This function fetches conids for each stock query provided. It is essential that each query's
filtering criteria is specific enough to return exactly one instrument and one contract,
hence one conid per symbol. If the filtering returns multiple instruments or contracts,
a RuntimeError is raised to prevent ambiguity in conid selection.

Arguments:

- `queries` _List[StockQuery]_ - A list of StockQuery objects to specify filtering criteria for stocks.
- `default_filtering` _bool, optional_ - Indicates whether to apply default filtering of {isUS: True}. Defaults to True.
- `return_type` _str, optional_ - Specifies the return type ('dict' or 'list') of the conids. Defaults to 'dict'.
  

Returns:

- `support.rest_client.Result` - A Result object containing the conids, either as a dictionary with symbols as keys and
  conids as values or as a list of conids, depending on the return_type parameter.
  

Raises:

- `RuntimeError` - If the filtering criteria do not result in exactly one instrument and one contract
  per query, thereby leading to ambiguity in conid selection.
  
  See:
- `StockQuery` - for details on how to construct queries for filtering stocks.

<a id="client.ibkr_client_mixins.contract_mixin.ContractMixin.trading_schedule_by_symbol"></a>

### trading\_schedule\_by\_symbol

```python
def trading_schedule_by_symbol(asset_class: str,
                               symbol: str,
                               exchange: str = None,
                               exchange_filter: str = None) -> Result
```

Returns the trading schedule up to a month for the requested contract.

Arguments:

- `asset_class` _str_ - Specify the security type of the given contract. Value Formats: Stock: STK, Option: OPT, Future: FUT, Contract For Difference: CFD, Warrant: WAR, Forex: SWP, Mutual Fund: FND, Bond: BND, Inter-Commodity Spreads: ICS.
- `symbol` _str_ - Specify the symbol for your contract.
- `exchange` _str, optional_ - Specify the primary exchange of your contract.
- `exchange_filter` _str, optional_ - Specify all exchanges you want to retrieve data from.

<a id="client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin"></a>

## MarketdataMixin

https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#md

<a id="client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.live_marketdata_snapshot"></a>

### live\_marketdata\_snapshot

```python
@ensure_list_arg('conids', 'fields')
def live_marketdata_snapshot(conids: OneOrMany[str],
                             fields: OneOrMany[str]) -> Result
```

Get Market Data for the given conid(s).

A pre-flight request must be made prior to ever receiving data.

Arguments:

- `conids` _OneOrMany[str]_ - Contract identifier(s) for the contract of interest.
- `fields` _OneOrMany[str]_ - Specify a series of tick values to be returned.
  

Notes:

  - The endpoint /iserver/accounts must be called prior to /iserver/marketdata/snapshot.
  - For derivative contracts, the endpoint /iserver/secdef/search must be called first.

<a id="client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.regulatory_snapshot"></a>

### regulatory\_snapshot

```python
def regulatory_snapshot(conid: str) -> Result
```

Send a request for a regulatory snapshot. This will cost $0.01 USD per request unless you are subscribed to the direct exchange market data already.

WARNING: Each regulatory snapshot made will incur a fee of $0.01 USD to the account. This applies to both live and paper accounts.

Arguments:

- `conid` _str_ - Provide the contract identifier to retrieve market data for.
  

Notes:

  - If you are already paying for, or are subscribed to, a specific US Network subscription, your account will not be charged.
  - For stocks, there are individual exchange-specific market data subscriptions necessary to receive streaming quotes.

<a id="client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.marketdata_history_by_conid"></a>

### marketdata\_history\_by\_conid

```python
def marketdata_history_by_conid(
        conid: str,
        bar: str,
        exchange: str = None,
        period: str = None,
        outside_rth: bool = None,
        start_time: datetime.datetime = None) -> Result
```

Get historical market Data for given conid, length of data is controlled by 'period' and 'bar'.

Arguments:

- `conid` _str_ - Contract identifier for the ticker symbol of interest.
- `bar` _str_ - Individual bars of data to be returned. Possible values– 1min, 2min, 3min, 5min, 10min, 15min, 30min, 1h, 2h, 3h, 4h, 8h, 1d, 1w, 1m.
- `exchange` _str, optional_ - Returns the exchange you want to receive data from.
- `period` _str_ - Overall duration for which data should be returned. Default to 1w. Available time period– {1-30}min, {1-8}h, {1-1000}d, {1-792}w, {1-182}m, {1-15}y.
- `outside_rth` _bool, optional_ - Determine if you want data after regular trading hours.
- `start_time` _datetime.datetime, optional_ - Starting date of the request duration.
  

Notes:

  - There's a limit of 5 concurrent requests. Excessive requests will return a 'Too many requests' status 429 response.

<a id="client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.historical_marketdata_beta"></a>

### historical\_marketdata\_beta

```python
def historical_marketdata_beta(conid: str,
                               period: str,
                               bar: str,
                               outside_rth: bool = None,
                               start_time: datetime.datetime = None,
                               direction: str = None,
                               bar_type: str = None) -> Result
```

Using a direct connection to the market data farm, will provide a list of historical market data for given conid.

Arguments:

- `conid` _str_ - The contract identifier for which data should be requested.
- `period` _str_ - The duration for which data should be requested. Available Values: See HMDS Period Units.
- `bar` _str_ - The bar size for which bars should be returned. Available Values: See HMDS Bar Sizes.
- `outside_rth` _bool, optional_ - Define if data should be returned for trades outside regular trading hours.
- `start_time` _datetime.datetime, optional_ - Specify the value from where historical data should be taken. Value Format: UTC; YYYYMMDD-HH:mm:dd. Defaults to the current date and time.
- `direction` _str, optional_ - Specify the direction from which market data should be returned. Available Values: -1: time from the start_time to now; 1: time from now to the end of the period. Defaults to 1.
- `bar_type` _str, optional_ - Returns valid bar types for which data may be requested. Available Values: Last, Bid, Ask, Midpoint, FeeRate, Inventory. Defaults to Last for Stocks, Options, Futures, and Futures Options.
  

Notes:

  - The first time a user makes a request to the /hmds/history endpoints will result in a 404 error. This initial request instantiates the historical market data services allowing future requests to return data. Subsequent requests will return data as expected.

<a id="client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.marketdata_history_by_symbol"></a>

### marketdata\_history\_by\_symbol

```python
def marketdata_history_by_symbol(
        symbol: Union[str, StockQuery],
        bar: str,
        exchange: str = None,
        period: str = None,
        outside_rth: bool = None,
        start_time: datetime.datetime = None) -> Result
```

Get historical market Data for given symbol, length of data is controlled by 'period' and 'bar'.

Arguments:

- `symbol` _Union[str, StockQuery]_ - StockQuery or str symbol for the ticker of interest.
- `bar` _str_ - Individual bars of data to be returned. Possible values– 1min, 2min, 3min, 5min, 10min, 15min, 30min, 1h, 2h, 3h, 4h, 8h, 1d, 1w, 1m.
- `exchange` _str, optional_ - Returns the exchange you want to receive data from.
- `period` _str_ - Overall duration for which data should be returned. Default to 1w. Available time period– {1-30}min, {1-8}h, {1-1000}d, {1-792}w, {1-182}m, {1-15}y.
- `outside_rth` _bool, optional_ - Determine if you want data after regular trading hours.
- `start_time` _datetime.datetime, optional_ - Starting date of the request duration.

<a id="client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.marketdata_history_by_symbols"></a>

### marketdata\_history\_by\_symbols

```python
@ensure_list_arg('queries')
def marketdata_history_by_symbols(
        queries: StockQueries,
        period: str = "1min",
        bar: str = "1min",
        outside_rth: bool = True,
        start_time: datetime.datetime = None) -> dict
```

An extended version of the marketdata_history_by_symbol method.

For each StockQuery provided, it queries the marketdata history for the specified symbols in parallel. The results are then cleaned up and unified. Due to this grouping and post-processing, this method returns data directly without the Result dataclass.

Arguments:

- `queries` _List[StockQuery]_ - A list of StockQuery objects to specify filtering criteria for stocks.
- `exchange` _str, optional_ - Returns the exchange you want to receive data from.
- `period` _str_ - Overall duration for which data should be returned. Default to 1w. Available time period– {1-30}min, {1-8}h, {1-1000}d, {1-792}w, {1-182}m, {1-15}y.
- `bar` _str_ - Individual bars of data to be returned. Possible values– 1min, 2min, 3min, 5min, 10min, 15min, 30min, 1h, 2h, 3h, 4h, 8h, 1d, 1w, 1m.
- `outside_rth` _bool, optional_ - Determine if you want data after regular trading hours.
- `start_time` _datetime.datetime, optional_ - Starting date of the request duration.
  

Notes:

  - This method returns data directly without the `Result` dataclass.

<a id="client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.marketdata_unsubscribe"></a>

### marketdata\_unsubscribe

```python
@ensure_list_arg('conids')
def marketdata_unsubscribe(conids: OneOrMany[int]) -> List[Result]
```

Cancel market data for given conid(s).

Arguments:

- `conids` _OneOrMany[int]_ - Enter the contract identifier to cancel the market data feed. This can clear all standing market data feeds to invalidate your cache and start fresh.

<a id="client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.marketdata_unsubscribe_all"></a>

### marketdata\_unsubscribe\_all

```python
def marketdata_unsubscribe_all() -> Result
```

Cancel all market data request(s). To cancel market data for a specific conid, see /iserver/marketdata/{conid}/unsubscribe.

<a id="client.ibkr_client_mixins.order_mixin.OrderMixin"></a>

## OrderMixin

* https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#order-monitor
* https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#orders

<a id="client.ibkr_client_mixins.order_mixin.OrderMixin.live_orders"></a>

### live\_orders

```python
@ensure_list_arg('filters')
def live_orders(filters: OneOrMany[str] = None,
                force: bool = None,
                account_id: str = None) -> Result
```

Retrieves live orders with optional filtering. The filters, if provided, should be a list of strings. These filters are then converted and sent as a comma-separated string in the request to the API.

Arguments:

- `filters` _List[str], optional_ - A list of strings representing the filters to be applied. Defaults to None
- `force` _bool, optional_ - Force the system to clear saved information and make a fresh request for orders. Submission will appear as a blank array. Defaults to False.
- `account_id` _str_ - For linked accounts, allows users to view orders on sub-accounts as specified.
  
  Available filters:
  * Inactive:
  Order was received by the system but is no longer active because it was rejected or cancelled.
  * PendingSubmit:
  Order has been transmitted but have not received confirmation yet that order accepted by destination exchange or venue.
  * PreSubmitted:
  Simulated order transmitted but the order has yet to be elected. Order is held by IB system until election criteria are met.
  * Submitted:
  Order has been accepted by the system.
  * Filled:
  Order has been completely filled.
  * PendingCancel:
  Sent an order cancellation request but have not yet received confirmation order cancelled by destination exchange or venue.
  * Cancelled:
  The balance of your order has been confirmed canceled by the system.
  * WarnState:
  Order has a specific warning message such as for basket orders.
  * SortByTime:
  There is an initial sort by order state performed so active orders are always above inactive and filled then orders are sorted chronologically.
  

Notes:

  - This endpoint requires a pre-flight request. Orders is the list of live orders (cancelled, filled, submitted).

<a id="client.ibkr_client_mixins.order_mixin.OrderMixin.order_status"></a>

### order\_status

```python
def order_status(order_id: str) -> Result
```

Retrieve the given status of an individual order using the orderId returned by the order placement response or the orderId available in the live order response.

Arguments:

- `order_id` _str_ - Order identifier for the placed order. Returned by the order placement response or the order_id available in the live order response.

<a id="client.ibkr_client_mixins.order_mixin.OrderMixin.trades"></a>

### trades

```python
def trades(days: str = None, account_id: str = None) -> Result
```

Returns a list of trades for the currently selected account for current day and six previous days. It is advised to call this endpoint once per session.

Arguments:

- `days` _str_ - Specify the number of days to receive executions for, up to a maximum of 7 days. If unspecified, only the current day is returned.
- `account_id` _str_ - Include a specific account identifier or allocation group to retrieve trades for.

<a id="client.ibkr_client_mixins.order_mixin.OrderMixin.place_order"></a>

### place\_order

```python
def place_order(order_request: dict,
                answers: Answers,
                account_id: str = None) -> Result
```

When connected to an IServer Brokerage Session, this endpoint will allow you to submit orders.

Notes:

  - With the exception of OCA groups and bracket orders, the orders endpoint does not currently support the placement of unrelated orders in bulk.
  - Developers should not attempt to place another order until the previous order has been fully acknowledged, that is, when no further warnings are received deferring the client to the reply endpoint.
  

Arguments:

- `account_id` _str_ - The account ID for which account should place the order.
- `answers` _Answers_ - List of question-answer pairs for order submission process.
- `order_request` _dict_ - Used to the order content.
  
  Keep this in mind:
  https://interactivebrokers.github.io/tws-api/automated_considerations.html#order_placement

<a id="client.ibkr_client_mixins.order_mixin.OrderMixin.reply"></a>

### reply

```python
def reply(reply_id, confirmed: bool) -> Result
```

Confirm order precautions and warnings presented from placing orders.

Many of the warning notifications within the Client Portal API can be disabled.

Arguments:

- `reply_id` _str_ - Include the id value from the prior order request relating to the particular order's warning confirmation.
- `confirmed` _bool_ - Pass your confirmation to the reply to allow or cancel the order to go through. true will agree to the message transmit the order. false will decline the message and discard the order.

<a id="client.ibkr_client_mixins.order_mixin.OrderMixin.whatif_order"></a>

### whatif\_order

```python
def whatif_order(order_request: dict, account_id: str) -> Result
```

This endpoint allows you to preview order without actually submitting the order and you can get commission information in the response. Also supports bracket orders.

Clients must query /iserver/marketdata/snapshot for the instrument prior to requesting the /whatif endpoint.

The body content of the /whatif endpoint will follow the same structure as the standard /iserver/account/{accountId}/orders endpoint.

Arguments:

- `account_id` _str_ - The account ID for which account should place the order. Financial Advisors may specify.
- `order_request` _dict_ - Used to the order content.

<a id="client.ibkr_client_mixins.order_mixin.OrderMixin.cancel_order"></a>

### cancel\_order

```python
def cancel_order(order_id: str, account_id: str = None) -> Result
```

Cancels an open order.

Must call /iserver/accounts endpoint prior to cancelling an order.
Use /iservers/account/orders endpoint to review open-order(s) and get latest order status.

Arguments:

- `account_id` _str_ - The account ID for which account should place the order.
- `order_id` _str_ - The orderID for that should be modified. Can be retrieved from /iserver/account/orders. Submitting '-1' will cancel all open orders.

<a id="client.ibkr_client_mixins.order_mixin.OrderMixin.modify_order"></a>

### modify\_order

```python
def modify_order(order_id: str,
                 order_request: dict,
                 answers: Answers,
                 account_id: str = None) -> Result
```

Modifies an open order.

Must call /iserver/accounts endpoint prior to modifying an order.
Use /iservers/account/orders endpoint to review open-order(s).

Arguments:

- `order_id` _str_ - The orderID for that should be modified. Can be retrieved from /iserver/account/orders.
- `order_request` _dict_ - Used to the order content. The content should mirror the content of the original order.
- `answers` _Answers_ - List of question-answer pairs for order submission process.
- `account_id` _str_ - The account ID for which account should place the order.

<a id="client.ibkr_client_mixins.order_mixin.OrderMixin.suppress_messages"></a>

### suppress\_messages

```python
def suppress_messages(message_ids: List[str]) -> Result
```

Disables a messageId, or series of messageIds, that will no longer prompt the user.

Arguments:

- `message_ids` _List[str]_ - The identifier for each warning message to suppress. The array supports up to 51 messages sent in a single request. Any additional values will result in a system error. The majority of the message IDs are based on the TWS API Error Codes with a “o” prepended to the id.

<a id="client.ibkr_client_mixins.order_mixin.OrderMixin.reset_suppressed_messages"></a>

### reset\_suppressed\_messages

```python
def reset_suppressed_messages() -> Result
```

Resets all messages disabled by the Suppress Messages endpoint.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin"></a>

## PortfolioMixin

* https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#portfolio
* https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#pa

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.portfolio_accounts"></a>

### portfolio\_accounts

```python
def portfolio_accounts() -> Result
```

In non-tiered account structures, returns a list of accounts for which the user can view position and account information. This endpoint must be called prior to calling other /portfolio endpoints for those accounts.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.portfolio_subaccounts"></a>

### portfolio\_subaccounts

```python
def portfolio_subaccounts() -> Result
```

Used in tiered account structures (such as Financial Advisor and IBroker Accounts) to return a list of up to 100 sub-accounts for which the user can view position and account-related information. This endpoint must be called prior to calling other /portfolio endpoints for those sub-accounts.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.large_portfolio_subaccounts"></a>

### large\_portfolio\_subaccounts

```python
def large_portfolio_subaccounts(page: int = 0) -> Result
```

Used in tiered account structures (such as Financial Advisor and IBroker Accounts) to return a list of sub-accounts, paginated up to 20 accounts per page, for which the user can view position and account-related information. This endpoint must be called prior to calling other /portfolio endpoints for those sub-accounts.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.portfolio_account_information"></a>

### portfolio\_account\_information

```python
def portfolio_account_information(account_id: str = None) -> Result
```

Account information related to account Id. /portfolio/accounts or /portfolio/subaccounts must be called prior to this endpoint.

Arguments:

- `account_id` _str, optional_ - Specify the AccountID to receive portfolio information for.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.portfolio_account_allocation"></a>

### portfolio\_account\_allocation

```python
def portfolio_account_allocation(account_id: str = None) -> Result
```

Information about the account's portfolio allocation by Asset Class, Industry and Category. /portfolio/accounts or /portfolio/subaccounts must be called prior to this endpoint.

Arguments:

- `account_id` _str, optional_ - Specify the account ID for the request.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.portfolio_account_allocations"></a>

### portfolio\_account\_allocations

```python
@ensure_list_arg('account_ids')
def portfolio_account_allocations(account_ids: OneOrMany[str]) -> Result
```

Similar to /portfolio/{accountId}/allocation but returns a consolidated view of all the accounts returned by /portfolio/accounts.

Arguments:

- `account_ids` _OneOrMany[str]_ - Contains all account IDs as strings the user should receive data for.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.positions"></a>

### positions

```python
def positions(account_id: str = None,
              page: int = 0,
              model: str = None,
              sort: str = None,
              direction: str = None,
              period: str = None) -> Result
```

Returns a list of positions for the given account. The endpoint supports paging, each page will return up to 100 positions.

Arguments:

- `account_id` _str, optional_ - The account ID for which account should place the order.
- `page_id` _str, optional_ - The “page” of positions that should be returned. One page contains a maximum of 100 positions. Pagination starts at 0.
- `model` _str, optional_ - Code for the model portfolio to compare against.
- `sort` _str, optional_ - Declare the table to be sorted by which column.
- `direction` _str, optional_ - The order to sort by. 'a' means ascending 'd' means descending.
- `period` _str, optional_ - Period for pnl column. Value Format: 1D, 7D, 1M.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.positions2"></a>

### positions2

```python
def positions2(account_id: str = None,
               model: str = None,
               sort: str = None,
               direction: str = None) -> Result
```

Returns a list of positions for the given account.
/portfolio/accounts or /portfolio/subaccounts must be called prior to this endpoint.
This endpoint provides near-real time updates and removes caching otherwise found in the /portfolio/{accountId}/positions/{pageId} endpoint.

Arguments:

- `account_id` _str, optional_ - The account ID for which account should place the order.
- `model` _str, optional_ - Code for the model portfolio to compare against.
- `sort` _str, optional_ - Declare the table to be sorted by which column.
- `direction` _str, optional_ - The order to sort by. 'a' means ascending 'd' means descending.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.positions_by_conid"></a>

### positions\_by\_conid

```python
def positions_by_conid(account_id: str, conid: str) -> Result
```

Returns a list containing position details only for the specified conid.

Arguments:

- `account_id` _str_ - The account ID for which account should place the order.
- `conid` _str_ - The contract ID to receive position information on.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.invalidate_backend_portfolio_cache"></a>

### invalidate\_backend\_portfolio\_cache

```python
def invalidate_backend_portfolio_cache(account_id: str = None) -> Result
```

Invalidates the cached value for your portfolio’s positions and calls the /portfolio/{accountId}/positions/0 endpoint automatically.

Arguments:

- `account_id` _str_ - The account ID for which cache to invalidate.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.portfolio_summary"></a>

### portfolio\_summary

```python
def portfolio_summary(account_id: str = None) -> Result
```

Information regarding settled cash, cash balances, etc. in the account’s base currency and any other cash balances hold in other currencies. /portfolio/accounts or /portfolio/subaccounts must be called prior to this endpoint. The list of supported currencies is available at https://www.interactivebrokers.com/en/index.php?f=3185.

Arguments:

- `account_id` _str_ - Specify the account ID for which account you require ledger information on.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.get_ledger"></a>

### get\_ledger

```python
def get_ledger(account_id: str = None) -> Result
```

Information regarding settled cash, cash balances, etc. in the account’s base currency and any other cash balances hold in other currencies. /portfolio/accounts or /portfolio/subaccounts must be called prior to this endpoint. The list of supported currencies is available at https://www.interactivebrokers.com/en/index.php?f=3185.

Arguments:

- `account_id` _str_ - Specify the account ID for which account you require ledger information on.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.position_and_contract_info"></a>

### position\_and\_contract\_info

```python
def position_and_contract_info(conid: str) -> Result
```

Returns an object containing information about a given position along with its contract details.

Arguments:

- `conid` _str_ - The contract ID to receive position information on.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.account_performance"></a>

### account\_performance

```python
@ensure_list_arg('account_ids')
def account_performance(account_ids: OneOrMany[str], period: str) -> Result
```

Returns the performance (MTM) for the given accounts, if more than one account is passed, the result is consolidated.

Arguments:

- `account_ids` _OneOrMany[str]_ - Include each account ID to receive data for.
- `period` _str_ - Specify the period for which the account should be analyzed. Available Values: “1D”, “7D”, “MTD”, “1M”, “YTD”, “1Y”.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.transaction_history"></a>

### transaction\_history

```python
@ensure_list_arg('account_ids', 'conids')
def transaction_history(account_ids: OneOrMany[str],
                        conids: OneOrMany[str],
                        currency: str,
                        days: str = None) -> Result
```

Transaction history for a given number of conids and accounts. Types of transactions include dividend payments, buy and sell transactions, transfers.

Arguments:

- `account_ids` _OneOrMany[str]_ - Include each account ID to receive data for.
- `conids` _OneOrMany[str]_ - Include contract ID to receive data for. Only supports one contract id at a time.
- `currency` _str_ - Define the currency to display price amounts with. Defaults to USD.
- `days` _str, optional_ - Specify the number of days to receive transaction data for. Defaults to 90 days of transaction history if unspecified.

<a id="client.ibkr_client_mixins.scanner_mixin.ScannerMixin"></a>

## ScannerMixin

https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#scanner

<a id="client.ibkr_client_mixins.scanner_mixin.ScannerMixin.scanner_parameters"></a>

### scanner\_parameters

```python
def scanner_parameters() -> Result
```

Returns an xml file containing all available parameters to be sent for the Iserver scanner request.

<a id="client.ibkr_client_mixins.scanner_mixin.ScannerMixin.market_scanner"></a>

### market\_scanner

```python
def market_scanner(instrument: str,
                   type: str,
                   location: str,
                   filter: List[Dict[str, str]] = None) -> Result
```

Searches for contracts according to the filters specified in /iserver/scanner/params endpoint.
Users can receive a maximum of 50 contracts from 1 request.

Arguments:

- `instrument` _str_ - Instrument type as the target of the market scanner request. Found in the “instrument_list” section of the /iserver/scanner/params response.
- `type` _str_ - Scanner value the market scanner is sorted by. Based on the “scan_type_list” section of the /iserver/scanner/params response.
- `location` _str_ - Location value the market scanner is searching through. Based on the “location_tree” section of the /iserver/scanner/params response.
- `filter` _List[Dict[str, str]]_ - Contains any additional filters that should apply to response. Each filter object may include:
  - code (str): Code value of the filter. Based on the “code” value within the “filter_list” section of the /iserver/scanner/params response.
  - value (int): Value corresponding to the input for “code”.

<a id="client.ibkr_client_mixins.scanner_mixin.ScannerMixin.hmds_scanner_parameters"></a>

### hmds\_scanner\_parameters

```python
def hmds_scanner_parameters() -> Result
```

Query the parameter list for the HMDS market scanner.

<a id="client.ibkr_client_mixins.scanner_mixin.ScannerMixin.hmds_market_scanner"></a>

### hmds\_market\_scanner

```python
def hmds_market_scanner(instrument: str,
                        location: str,
                        scan_code: str,
                        sec_type: str,
                        filter: List[Dict[str, str]],
                        max_items: int = None) -> Result
```

Request a market scanner from our HMDS service.
Can return a maximum of 250 contracts.

Arguments:

- `instrument` _str_ - Specify the type of instrument for the request. Found under the “instrument_list” value of the /hmds/scanner/params request.
- `locations` _str_ - Specify the type of location for the request. Found under the “location_tree” value of the /hmds/scanner/params request.
- `scanCode` _str_ - Specify the scanner type for the request. Found under the “scan_type_list” value of the /hmds/scanner/params request.
- `secType` _str_ - Specify the type of security type for the request. Found under the “location_tree” value of the /hmds/scanner/params request.
- `filters` _List[Dict[str, str]]_ - Array of objects containing all filters upon the scanner request. While “filters” must be specified in the body, no content in the array needs to be passed.
- `maxItems` _int, optional_ - Specify how many items should be returned. Default and maximum set to 250.

<a id="client.ibkr_client_mixins.session_mixin.SessionMixin"></a>

## SessionMixin

https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#session

<a id="client.ibkr_client_mixins.session_mixin.SessionMixin.authentication_status"></a>

### authentication\_status

```python
def authentication_status() -> Result
```

Current Authentication status to the Brokerage system. Market Data and Trading is not possible if not authenticated, e.g. authenticated shows false.

<a id="client.ibkr_client_mixins.session_mixin.SessionMixin.initialize_brokerage_session"></a>

### initialize\_brokerage\_session

```python
def initialize_brokerage_session(publish: bool, compete: bool) -> Result
```

After retrieving the access token and subsequent Live Session Token, customers can initialize their brokerage session with the ssodh/init endpoint.
NOTE: This is essential for using all /iserver endpoints, including access to trading and market data.

Arguments:

- `publish` _Boolean_ - Determines if the request should be sent immediately. Users should always pass true. Otherwise, a ‘500’ response will be returned.
- `compete` _Boolean_ - Determines if other brokerage sessions should be disconnected to prioritize this connection.

<a id="client.ibkr_client_mixins.session_mixin.SessionMixin.logout"></a>

### logout

```python
def logout() -> Result
```

Logs the user out of the gateway session. Any further activity requires re-authentication.

<a id="client.ibkr_client_mixins.session_mixin.SessionMixin.tickle"></a>

### tickle

```python
def tickle() -> Result
```

If the gateway has not received any requests for several minutes an open session will automatically timeout. The tickle endpoint pings the server to prevent the session from ending. It is expected to call this endpoint approximately every 60 seconds to maintain the connection to the brokerage session.

<a id="client.ibkr_client_mixins.session_mixin.SessionMixin.reauthenticate"></a>

### reauthenticate

```python
def reauthenticate() -> Result
```

When using the CP Gateway, this endpoint provides a way to reauthenticate to the Brokerage system as long as there is a valid brokerage session.
All interest in reauthenticating the gateway session should be handled using the /iserver/auth/ssodh/init endpoint.

<a id="client.ibkr_client_mixins.session_mixin.SessionMixin.validate"></a>

### validate

```python
def validate() -> Result
```

Validates the current session for the SSO user.

<a id="client.ibkr_client_mixins.session_mixin.SessionMixin.check_health"></a>

### check\_health

```python
def check_health() -> bool
```

Verifies the health and authentication status of the IBKR Gateway server.

This method checks if the Gateway server is alive and whether the user is authenticated.
It also checks for any competing connections and the connection status.

Returns:

- `bool` - True if the Gateway server is authenticated, not competing, and connected, False otherwise.
  

Raises:

- `AttributeError` - If the Gateway health check request returns invalid data.
  

Notes:

  - This method returns a boolean directly without the `Result` dataclass.

<a id="client.ibkr_client_mixins.watchlist_mixin.WatchlistMixin"></a>

## WatchlistMixin

https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#watchlists

<a id="client.ibkr_client_mixins.watchlist_mixin.WatchlistMixin.create_watchlist"></a>

### create\_watchlist

```python
def create_watchlist(id: str, name: str,
                     rows: List[Dict[str, Union[str, int]]]) -> Result
```

Create a watchlist to monitor a series of contracts.

Arguments:

- `id` _str_ - Supply a unique identifier to track a given watchlist. Must supply a number.
- `name` _str_ - Supply the human readable name of a given watchlist. Displayed in TWS and Client Portal.
- `rows` _List[Dict[str, Union[str, int]]]_ - Provide details for each contract or blank space in the watchlist. Each object may include:
  - C (int): Provide the conid, or contract identifier, of the conid to add.
  - H (str): Can be used to add a blank row between contracts in the watchlist.

<a id="client.ibkr_client_mixins.watchlist_mixin.WatchlistMixin.get_all_watchlists"></a>

### get\_all\_watchlists

```python
def get_all_watchlists(sc: str = 'USER_WATCHLIST') -> Result
```

Retrieve a list of all available watchlists for the account.

Arguments:

- `SC` _str_ - Optional. Specify the scope of the request. Valid Values: USER_WATCHLIST.

<a id="client.ibkr_client_mixins.watchlist_mixin.WatchlistMixin.get_watchlist_information"></a>

### get\_watchlist\_information

```python
def get_watchlist_information(id: str) -> Result
```

Request the contracts listed in a particular watchlist.

Arguments:

- `id` _str_ - Set equal to the watchlist ID you would like data for.

<a id="client.ibkr_client_mixins.watchlist_mixin.WatchlistMixin.delete_watchlist"></a>

### delete\_watchlist

```python
def delete_watchlist(id: str) -> Result
```

Permanently delete a specific watchlist for all platforms.

Arguments:

- `id` _str_ - Include the watchlist ID you wish to delete.

