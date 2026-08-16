# Table of Contents

* [marketdata\_mixin](#client.ibkr_client_mixins.marketdata_mixin)
  * [MarketdataMixin](#client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin)
    * [live\_marketdata\_snapshot](#client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.live_marketdata_snapshot)
    * [live\_marketdata\_snapshot\_by\_symbol](#client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.live_marketdata_snapshot_by_symbol)
    * [regulatory\_snapshot](#client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.regulatory_snapshot)
    * [marketdata\_history\_by\_conid](#client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.marketdata_history_by_conid)
    * [historical\_marketdata\_beta](#client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.historical_marketdata_beta)
    * [marketdata\_history\_by\_symbol](#client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.marketdata_history_by_symbol)
    * [marketdata\_history\_by\_conids](#client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.marketdata_history_by_conids)
    * [marketdata\_history\_by\_symbols](#client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.marketdata_history_by_symbols)
    * [marketdata\_unsubscribe](#client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.marketdata_unsubscribe)
    * [marketdata\_unsubscribe\_all](#client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.marketdata_unsubscribe_all)

<a id="client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin"></a>

## MarketdataMixin

https://www.interactivebrokers.com/docs/web-api/v1/endpoints/market-data

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

<a id="client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.live_marketdata_snapshot_by_symbol"></a>

### live\_marketdata\_snapshot\_by\_symbol

```python
def live_marketdata_snapshot_by_symbol(queries: StockQueries,
                                       fields: OneOrMany[str]) -> dict
```

Get Market Data for the given symbols(s).

A pre-flight request must be made prior to ever receiving data.

Arguments:

- `queries` _List[StockQuery]_ - A list of StockQuery objects to specify filtering criteria for stocks.
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
- `bar` _str_ - Individual bars of data to be returned. Possible values� 1min, 2min, 3min, 5min, 10min, 15min, 30min, 1h, 2h, 3h, 4h, 8h, 1d, 1w, 1m.
- `exchange` _str, optional_ - Returns the exchange you want to receive data from.
- `period` _str_ - Overall duration for which data should be returned. Default to 1w. Available time period� {1-30}min, {1-8}h, {1-1000}d, {1-792}w, {1-182}m, {1-15}y.
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
- `bar` _str_ - Individual bars of data to be returned. Possible values� 1min, 2min, 3min, 5min, 10min, 15min, 30min, 1h, 2h, 3h, 4h, 8h, 1d, 1w, 1m.
- `exchange` _str, optional_ - Returns the exchange you want to receive data from.
- `period` _str_ - Overall duration for which data should be returned. Default to 1w. Available time period� {1-30}min, {1-8}h, {1-1000}d, {1-792}w, {1-182}m, {1-15}y.
- `outside_rth` _bool, optional_ - Determine if you want data after regular trading hours.
- `start_time` _datetime.datetime, optional_ - Starting date of the request duration.

<a id="client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.marketdata_history_by_conids"></a>

### marketdata\_history\_by\_conids

```python
def marketdata_history_by_conids(conids: Union[List[str], Dict[Hashable, str]],
                                 period: str = '1min',
                                 bar: str = '1min',
                                 outside_rth: bool = True,
                                 start_time: datetime.datetime = None,
                                 raise_on_error: bool = False,
                                 run_in_parallel: bool = True) -> dict
```

An extended version of the marketdata_history_by_conid method.

For each conid provided, it queries the marketdata history for the specified symbols. The results are then cleaned up and unified. Due to this grouping and post-processing, this method returns data directly without the Result dataclass.

Arguments:

- `conids` _Union[List[str], Dict[Hashable, str]]_ - A list of conids to get market data for.
- `exchange` _str, optional_ - Returns the exchange you want to receive data from.
- `period` _str_ - Overall duration for which data should be returned. Default to 1w. Available time period� {1-30}min, {1-8}h, {1-1000}d, {1-792}w, {1-182}m, {1-15}y.
- `bar` _str_ - Individual bars of data to be returned. Possible values� 1min, 2min, 3min, 5min, 10min, 15min, 30min, 1h, 2h, 3h, 4h, 8h, 1d, 1w, 1m.
- `outside_rth` _bool, optional_ - Determine if you want data after regular trading hours.
- `start_time` _datetime.datetime, optional_ - Starting date of the request duration.
- `raise_on_error` _bool, optional_ - If True, raise an exception if an error occurs during the request. Defaults to False.
- `run_in_parallel` _bool, optional_ - If True, send requests in parallel to speed up the response. Defaults to True.
  

Notes:

  - This method returns data directly without the `Result` dataclass.

<a id="client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.marketdata_history_by_symbols"></a>

### marketdata\_history\_by\_symbols

```python
@ensure_list_arg('queries')
def marketdata_history_by_symbols(queries: StockQueries,
                                  period: str = '1min',
                                  bar: str = '1min',
                                  outside_rth: bool = True,
                                  start_time: datetime.datetime = None,
                                  raise_on_error: bool = False,
                                  run_in_parallel: bool = True) -> dict
```

An extended version of the marketdata_history_by_conids method.

For each StockQuery provided, it queries the marketdata history for the specified symbols. The results are then cleaned up and unified. Due to this grouping and post-processing, this method returns data directly without the Result dataclass.

Arguments:

- `queries` _List[StockQuery]_ - A list of StockQuery objects to specify filtering criteria for stocks.
- `exchange` _str, optional_ - Returns the exchange you want to receive data from.
- `period` _str_ - Overall duration for which data should be returned. Default to 1w. Available time period� {1-30}min, {1-8}h, {1-1000}d, {1-792}w, {1-182}m, {1-15}y.
- `bar` _str_ - Individual bars of data to be returned. Possible values� 1min, 2min, 3min, 5min, 10min, 15min, 30min, 1h, 2h, 3h, 4h, 8h, 1d, 1w, 1m.
- `outside_rth` _bool, optional_ - Determine if you want data after regular trading hours.
- `start_time` _datetime.datetime, optional_ - Starting date of the request duration.
- `raise_on_error` _bool, optional_ - If True, raise an exception if an error occurs during the request. Defaults to False.
- `run_in_parallel` _bool, optional_ - If True, send requests in parallel to speed up the response. Defaults to True.
  

Notes:

  - This method returns data directly without the `Result` dataclass.

<a id="client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.marketdata_unsubscribe"></a>

### marketdata\_unsubscribe

```python
@ensure_list_arg('conids')
def marketdata_unsubscribe(conids: OneOrMany[str]) -> List[Result]
```

Cancel market data for given conid(s).

Arguments:

- `conids` _OneOrMany[str]_ - Enter the contract identifier to cancel the market data feed. This can clear all standing market data feeds to invalidate your cache and start fresh.

<a id="client.ibkr_client_mixins.marketdata_mixin.MarketdataMixin.marketdata_unsubscribe_all"></a>

### marketdata\_unsubscribe\_all

```python
def marketdata_unsubscribe_all() -> Result
```

Cancel all market data request(s). To cancel market data for a specific conid, see /iserver/marketdata/{conid}/unsubscribe.
