# Advanced REST

Majority of the IBKR endpoints' mapping is implemented by performing a simple REST request. For example:

```python
class SessionMixin():
    def authentication_status(self: 'IbkrClient') -> Result:
        return self.post('iserver/auth/status')

    ...
```

In several cases, `IbkrClient` implements additional logic to allow more sophisticated interaction with the IBKR endpoints.

The advanced API topics are:

* [security_stocks_by_symbol](#security_stocks_by_symbol) (contract mixin)
* [stock_conid_by_symbol](#stock_conid_by_symbol) (contract mixin)
* [marketdata_history_by_symbol](#marketdata_history_by_symbol) (marketdata mixin)
* [marketdata_history_by_symbols](#marketdata_history_by_symbols) (marketdata mixin)
* [marketdata_unsubscribe](#marketdata_unsubscribe) (marketdata mixin)
* [place_order](#place_order) (order mixin)
* [modify_order](#modify_order) (order mixin)
* [check_health](#check_health) (session mixin)
* [pre-flight requests](#pre-flight-requests)

## <a name="security_stocks_by_symbol"></a> security_stocks_by_symbol

IBKR provides access to multiple exchanges, markets and instruments for most symbols. As a result, when searching for a stock by symbol using the `trsrv/stocks` endpoint, the API will frequently return more than one contract.

```python

{
    "AAPL": [
        {
            "assetClass": "STK",
            "chineseName": "&#x82F9;&#x679C;&#x516C;&#x53F8;",
            "contracts": [
                {"conid": 265598, "exchange": "NASDAQ", "isUS": True},
                {"conid": 38708077, "exchange": "MEXI", "isUS": False},
                {"conid": 273982664, "exchange": "EBS", "isUS": False},
            ],
            "name": "APPLE INC",
        },
        {
            "assetClass": "STK",
            "chineseName": None,
            "contracts": [{"conid": 493546048, "exchange": "LSEETF", "isUS": False}],
            "name": "LS 1X AAPL",
        },
        {
            "assetClass": "STK",
            "chineseName": "&#x82F9;&#x679C;&#x516C;&#x53F8;",
            "contracts": [{"conid": 532640894, "exchange": "AEQLIT", "isUS": False}],
            "name": "APPLE INC-CDR",
        },
    ]
}
```

To facilitate specifying which security we want to operate on, the `security_stocks_by_symbol` provides a filtering mechanism. To use it, each stock that you'd want to search for can be expressed as an instance of the `StockQuery` dataclass:

```python
@dataclass
class StockQuery():
    symbol: str
    name_match: Optional[str] = field(default=None)  # ie. filter for instrument name
    instrument_conditions: Optional[dict] = field(default=None)  # ie. filters for instrument fields
    contract_conditions: Optional[dict] = field(default=None)  # ie. filters for contract fields
```

When using the `StockQuery`, apart from specifying the `symbol` to search for, we can provide additional filters that will be used to narrow down our stock search query, eg.:

```python
from ibind import IbkrClient, StockQuery

ibkr_client = IbkrClient()
queries = [StockQuery('AAPL', contract_conditions={'exchange': 'MEXI'})]
stocks = ibkr_client.security_stocks_by_symbol(queries, default_filtering=False)
```

This will call the `trsrv/stocks` endpoint and filter the result to contracts whose exchange is equal to `MEXI`:

```python
{
    "AAPL": [
        {
            "assetClass": "STK",
            "chineseName": "&#x82F9;&#x679C;&#x516C;&#x53F8;",
            "contracts": [{"conid": 38708077, "exchange": "MEXI", "isUS": False}],
            "name": "APPLE INC",
        }
    ]
}
```

Note:

* A `isUS=True` contract condition is applied to all calls of this method by default. Disable by setting `security_stocks_by_symbol(..., default_filtering=False)`.
* You can call this method with `str` arguments instead of `StockQuery`. These will be interpreted as `StockQuery` arguments with no filtering.
* You can call this method with one or many arguments, eg. `security_stocks_by_symbol('AAPL')` or `security_stocks_by_symbol(['AAPL', 'GOOG'])`
* You can mix `str` and `StockQuery` arguments, eg.: `security_stocks_by_symbol(['AAPL', StockQuery('GOOG')])`
* Same rules apply to all other methods using `StockQuery` parameters.

See example ["rest_03_stock_querying"][rest_03_stock_querying] which demonstrates various usages of StockQuery.

## <a name="stock_conid_by_symbol"></a> stock_conid_by_symbol

Most of the IBKR endpoints require us to specify securities' numerical contract IDs (usually shortened to _conid_) rather than symbols.

```python
ibkr_client.contract_information_by_conid('AAPL')  # INVALID
ibkr_client.contract_information_by_conid(265598)  # VALID
```

`stock_conid_by_symbol` method facilitates acquiring conids for stock symbols using the same filtering functionality as the [`security_stocks_by_symbol`](#security_stocks_by_symbol).

* Importantly, this method will raise a `RuntimeError` unless all of the filtered stocks return exactly one instrument and one contract.
* As a result, exactly one conid can be acquired for each symbol, prompting the users to tweak the `StockQuery` arguments until this is true.
* This ensures that there is no ambiguity when searching for conids.

Note:

* This "one-instrument and one-contract" limitation is not present in the `security_stocks_by_symbol` method.

See example ["rest_03_stock_querying"][rest_03_stock_querying] for querying conid from a symbol.

Eg.:

```python
from ibind import IbkrClient, StockQuery

stock_queries = [
    StockQuery('AAPL', contract_conditions={'exchange': 'MEXI'}),
    'HUBS',
    StockQuery('GOOG', name_match='ALPHABET INC - CDR')
]
conids = ibkr_client.stock_conid_by_symbol(stock_queries, default_filtering=False).data
print(conids)

# outputs:
{'AAPL': 38708077, 'GOOG': 532638805, 'HUBS': 169544810}
```

## <a name="marketdata_history_by_symbol"></a> marketdata_history_by_symbol

`marketdata_history_by_symbol` is a small wrapper around the simple `marketdata_history_by_conid` method.

It utilises the [`stock_conid_by_symbol`](#stock_conid_by_symbol) to query stock conids automatically before calling the `marketdata_history_by_conid`.

## <a name="marketdata_history_by_symbols"></a> marketdata_history_by_symbols

`marketdata_history_by_symbols` is an extended version of the [`marketdata_history_by_symbol`](#marketdata_history_by_symbol) method.

For each `StockQuery` provided, it queries the marketdata history for the specified symbols in parallel. The results are then cleaned up and unified. Due to this grouping and post-processing, this method returns data directly without the `Result` dataclass.

```python
ibkr_client.marketdata_history_by_symbols('AAPL', period='1min', bar='1min', outside_rth=True)

# outputs:
{
    "AAPL": [
        {
            "open": 169.15,
            "high": 169.15,
            "low": 169.15,
            "close": 169.15,
            "volume": 0,
            "date": datetime.datetime(2024, 4, 25, 19, 56),
        },
    ]
}
```

```python
ibkr_client.marketdata_history_by_symbols(['AAPL', 'MSFT'], period='1min', bar='1min', outside_rth=True)

# outputs:
{
    "AAPL": [
        {
            "open": 169.15,
            "high": 169.15,
            "low": 169.15,
            "close": 169.15,
            "volume": 0,
            "date": datetime.datetime(2024, 4, 25, 19, 56),
        },
    ],
    "MSFT": [
        {
            "open": 400.75,
            "high": 400.75,
            "low": 400.75,
            "close": 400.75,
            "volume": 0,
            "date": datetime.datetime(2024, 4, 25, 19, 56),
        },
    ]
}
```

Both of these requests took approximately the same amount of time to execute, due to parallel execution.

This method imposes a limit of 5 parallel requests per second due to IBKR rate limiting.

See example ["rest_05_marketdata_history"][rest_05_marketdata_history] for various example of Market Data History queries and the execution time differences between these.

## <a name="marketdata_unsubscribe"></a> marketdata_unsubscribe

The `/iserver/marketdata/unsubscribe` endpoint allows for only one conid to be unsubscribed from at a time.

`marketdata_unsubscribe` method utilises parallel execution to unsubscribe from multiple marketdata history conids at the same time.

## <a name="place_order"></a> place_order

From [placing order docs][place-order-docs]:
> In some cases the response to an order submission request might not deliver an acknowledgment. Instead, it might contain an "order reply message" - essentially a notice — which must be confirmed via a second request before our order ticket can go to work.

When placing an order using `place_order` method, you are to provide a dictionary of question-answer pairs. The method will then perform a back-and-forth message exchange with IBKR servers to reply to the questions and complete the order submission process automatically.

```python
from ibind import IbkrClient, QuestionType

answers = {
    QuestionType.PRICE_PERCENTAGE_CONSTRAINT: True,
    QuestionType.ORDER_VALUE_LIMIT: True,
    "Unforeseen new question": True,
}

ibkr_client = IbkrClient()
ibkr_client.place_order(..., answers, ...)
```

Observe that:

* Questions-answer pairs are expected to be made of `QuestionType` enum and a boolean.
* You can provide a `str` instead of `QuestionType` as key in order to answer questions that have not been previously observed.
* You may chose to use `str` in every case, although `QuestionType` enum is preferred.

Note:

* If a question is found without an answer or the answer to the question is negative, an exception is raised.
* Only one place order request - either single order request or bracket orders request - can be carried out at a time. This limitation is dictated by the fact that for each order request a synchronous question-answer exchange needs to happen between the client and IBKR servers. Submitting multiple order requests would cause multiple exchanges to happen, causing the servers to error out.

----

Additionally, `make_order_request` utility function is provided to facilitate creating the `order_request` dictionary. It ensures all necessary fields are specified when placing an order using `place_order` method.

```python
import datetime
from ibind import IbkrClient, make_order_request

conid = '265598'  # AAPL
side = 'BUY'
size = 1
order_type = 'MARKET'
price = 100
order_tag = f'my_order-{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}'

order_request = make_order_request(
    conid=conid,
    side=side,
    quantity=size,
    order_type=order_type,
    price=price,
    acct_id=account_id,
    coid=order_tag
)

ibkr_client = IbkrClient()
ibkr_client.place_order(order_request, ...)
```

See example ["rest_04_place_order"][rest_04_place_order] which demonstrates creating an order_request and placing an order.

## <a name="modify_order"></a> modify_order

`modify_order` method follows the same question-handling logic as [`place_order`](#place-order).

## <a name="check_health"></a> check_health

`check_health` method is a wrapper around the `tickle` method, providing additional interpretation to its response.

The outcomes of `check_health` are:

* `True` - all good. We can call the Gateway and verify that it has a non-competing, authenticated session.
* `False` - something is wrong. We either cannot call the Gateway (in which case an additional log is produced) or the session is either competing, disconnected or unauthenticated.
* `AttributeError` - `tickle` endpoint returned unexpected data.

It is encouraged to call `check_health` in a loop to ensure a healthy connection. This is particularly important when using OAuth.

When it returns `False` the appropriate course of action depends on your setup:

* IBeam - do nothing, wait for it to reauthenticate.
* OAuth - call `stop()` and `init_oauth()` to reauthenticate.
* CP Gateway - reauthenticate manually.

An example health checking function that should be called repeatedly (eg. in a loop):

```python
# run this in a loop
def handle_health_status(client: IbkrClient, use_oauth: bool = False) -> bool:
    healthy = client.check_health()
    if healthy:
        _LOGGER.info(f'IBKR connection in good health: {client.check_health()}')
        return True

    _LOGGER.info(f'IBKR connection in bad health: {client.check_health()}')
    if not use_oauth:
        # Wait for a reconnect either from IBeam or manually.
        return False
        try:
            client.stop_tickler()
        except Exception as e:
            _LOGGER.error(f'Error stopping tickler.')

        try:
            client.oauth_init(maintain_oauth=True, init_brokerage_session=True)
        except Exception as e:
            _LOGGER.error(f'Error reauthenticating with OAuth.')
    return False
```

## <a name="pre-flight-requests"></a> Pre-Flight Requests

A number of endpoints indicate that some type of pre-flight is required. A pre-flight request is an additional request that is required to be carried out before the actual request can be made.

For example, the [`live_orders`][live-orders-docs] endpoint documentation states:

> This endpoint requires a pre-flight request.

While [Receive Brokerage Accounts][get-brokerage-accounts-docs] docs state:

> Note this endpoint must be called before modifying an order or querying open orders.


This indicates that to retrieve live orders we should call:

```python
client.receive_brokerage_accounts()
client.live_orders()
```

While it was considered to make IBind handle pre-flight requests automatically, it was decided to refrain from doing so in most cases for two reasons:

1. To increase transparency, making the user aware of the amount of requests being made, in order to avoid exceeding rate limits.
2. To encourage users to learn about the pre-flight requests and their behaviour. Some endpoints require to be called several times to return correct data. IBind shouldn't provide false sense of _"taking care of it"_ by stating that it handles pre-flights automatically, encouraging users to blindly trust that all requests that needed to be made have been made.

Each pre-flight should be handled individually by your system. You can use the following code snippet as an inspiration for how repeated pre-flights could be implemented:

```python
_DEFAULT_LIVE_ORDERS_FILTERS = ['submitted', 'pre_submitted', 'pending_submit']


# use filters=[] to disable filters
def get_live_orders(client: IbkrClient, filters: [str] = None):
    if filters is None:
        filters = _DEFAULT_LIVE_ORDERS_FILTERS

    # this first request with force=True should ensure we get live data and not stale cached one.
    client.receive_brokerage_accounts()
    client.live_orders(filters, force=True)
    ibkr_orders = client.live_orders(filters)

    attempt = 0

    # if there is no data, continue getting live orders
    while ibkr_orders.data.get('snapshot', False) is False:
        if attempt >= 20:
            raise RuntimeError(f'Failed to get live orders after {attempt} attempts.')

        ibkr_orders = client.live_orders(filters)
        attempt += 1
        time.sleep(0.25)

    return ibkr_orders
```

### <a name="list-of-pre-flights"></a> List Of Pre-Flights

Based on the IBKR documentation at the time of writing this, we've identified the following pre-flights. Please create an issue if you think this list should be modified.

* Search Algo Params by Contract ID
    * Call twice [needs confirmation]
* Live Market Data Snapshot
    * Call several times. There are cases where some fields are never returned. Run this field several times to observe which fields are returned.
* Live Orders
    * Call Receive Brokerage Accounts first
    * Optionally, call this endpoint twice, first with force=True
* Live Orders WebSocket
    * Call Live Orders.
    * Note that if you call Live Orders with filters while this WebSocket is active, it will also start to return filtered data. [needs confirmation]
* Cancel Order
    * Call Receive Brokerage Accounts [needs confirmation]
* Modify Order
    * Call Receive Brokerage Accounts [needs confirmation]
* Search SecDef information by conid
    * Call Search Contract by Symbol [needs confirmation]
* Order Status
    * Switch Account (for multi-account structures such as Financial Advisors or linked-account structures only) [needs confirmation]

----

#### Next

Learn about the [IbkrWsClient][ibkr-ws-client-docs].

[place-order-docs]: https://ibkrcampus.com/ibkr-api-page/webapi-doc/#order-reply-messages

[ibkr-ws-client-docs]: ../websocket/overview.md

[live-orders-docs]: https://www.interactivebrokers.com/campus/ibkr-api-page/cpapi-v1/#live-orders

[get-brokerage-accounts-docs]: https://www.interactivebrokers.com/campus/ibkr-api-page/cpapi-v1/#get-brokerage-accounts

[rest_03_stock_querying]: https://github.com/Voyz/ibind/blob/master/examples/rest_03_stock_querying.py

[rest_04_place_order]: https://github.com/Voyz/ibind/blob/master/examples/rest_04_place_order.py

[rest_05_marketdata_history]: https://github.com/Voyz/ibind/blob/master/examples/rest_05_marketdata_history.py
