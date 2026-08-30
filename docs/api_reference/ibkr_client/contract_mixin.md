# Table of Contents

* [contract\_mixin](#client.ibkr_client_mixins.contract_mixin)
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

<a id="client.ibkr_client_mixins.contract_mixin.ContractMixin"></a>

## ContractMixin

https://www.interactivebrokers.com/docs/web-api/v1/endpoints/contract

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

- `currency` _str_ - Specify the target currency you would like to receive official pairs of. Valid Structure: �USD�.

<a id="client.ibkr_client_mixins.contract_mixin.ContractMixin.currency_exchange_rate"></a>

### currency\_exchange\_rate

```python
def currency_exchange_rate(source: str, target: str) -> Result
```

Obtains the exchange rates of the currency pair.

Arguments:

- `source` _str_ - Specify the base currency to request data for. Valid Structure: �AUD�
- `target` _str_ - Specify the quote currency to request data for. Valid Structure: �USD�

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

- `symbol` _str_ - This should always be set to �BOND�
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
- `sec_type` _str, optional_ - Valid Values: �STK�, �IND�, �BOND�. Declares underlying security type.

<a id="client.ibkr_client_mixins.contract_mixin.ContractMixin.search_contract_rules"></a>

### search\_contract\_rules

```python
def search_contract_rules(conid: str,
                          exchange: str = None,
                          is_buy: bool = None,
                          modify_order: bool = None,
                          order_id: int = None) -> Result
```

Returns trading related rules for a specific contract and side.

Arguments:

- `conid` _str_ - Contract identifier for the interested contract.
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
- `right` _str_ - Required for Options. Set the right for the given contract. Value Format: �C� for Call or �P� for Put.
- `issuer_id` _str_ - Required for Bonds. Set the issuer_id for the given bond issuer type. Example Format: �e1234567�

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
- `sec_type` _str_ - Security type of the derivatives you are looking for. Value Format: �OPT� or �WAR�.
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
                              default_filtering: bool = None) -> Result
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
- `default_filtering` _bool, optional_ - Indicates whether to apply override the default filtering of {isUS: True}. Defaults to None, which applies the global default filtering.
  
  

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
                          default_filtering: bool = None,
                          return_type: str = 'dict') -> Result
```

Retrieves contract IDs (conids) for given stock queries, ensuring only one conid per query.

This function fetches conids for each stock query provided. It is essential that each query's
filtering criteria is specific enough to return exactly one instrument and one contract,
hence one conid per symbol. If the filtering returns multiple instruments or contracts,
a RuntimeError is raised to prevent ambiguity in conid selection.

Arguments:

- `queries` _List[StockQuery]_ - A list of StockQuery objects to specify filtering criteria for stocks.
- `default_filtering` _bool, optional_ - Indicates whether to apply override the default filtering of {isUS: True}. Defaults to None, which applies the global default filtering.
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
