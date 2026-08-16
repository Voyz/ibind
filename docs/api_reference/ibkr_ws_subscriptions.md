# Table of Contents

* [ibkr\_subscriptions](#ibkr_ws.ibkr_subscriptions)
  * [AccountSummarySubscription](#ibkr_ws.ibkr_subscriptions.AccountSummarySubscription)
  * [AccountLedgerSubscription](#ibkr_ws.ibkr_subscriptions.AccountLedgerSubscription)
  * [MarketDataSubscription](#ibkr_ws.ibkr_subscriptions.MarketDataSubscription)
  * [MarketHistorySubscription](#ibkr_ws.ibkr_subscriptions.MarketHistorySubscription)
  * [OrdersSubscription](#ibkr_ws.ibkr_subscriptions.OrdersSubscription)
  * [PriceLadderSubscription](#ibkr_ws.ibkr_subscriptions.PriceLadderSubscription)
  * [PnlSubscription](#ibkr_ws.ibkr_subscriptions.PnlSubscription)
  * [TradesSubscription](#ibkr_ws.ibkr_subscriptions.TradesSubscription)

<a id="ibkr_ws.ibkr_subscriptions.AccountSummarySubscription"></a>

## AccountSummarySubscription

Subscribes to a stream of account summary messages for the specified account.

Attributes:

- `account_id` _str_ - Required. The account ID whose account summary data will be subscribed.
- `keys` _List[str], optional_ - Pass specific account summary data keys to receive messages concerning only those keys.
- `fields` _List[str], optional_ - Pass specific account summary field names to filter responses to include only these fields.

<a id="ibkr_ws.ibkr_subscriptions.AccountLedgerSubscription"></a>

## AccountLedgerSubscription

Subscribes to a stream of account ledger messages for the specified account, with contents sorted by currency.

Attributes:

- `account_id` _str_ - Required. The account ID whose ledger data will be subscribed.
- `keys` _List[str], optional_ - Pass specific ledger currency keys to receive messages with data only for those currencies.
- `fields` _List[str], optional_ - Pass specific ledger field names to receive messages only those data points.

<a id="ibkr_ws.ibkr_subscriptions.MarketDataSubscription"></a>

## MarketDataSubscription

Subscribes the user to watchlist market data. Streaming, top-of-the-book, level one, market data is available for all instruments.

Market data streams will terminate after 15 minutes. Users must send a new request for market data after 10 minutes to continue retrieving data for the instrument.

Attributes:

- `conid` _str_ - Required. A single contract identifier. Contracts requested use SMART routing by default.
- `fields` _List[str]_ - Optional. Pass an array of field IDs to receive messages concerning only those fields.

<a id="ibkr_ws.ibkr_subscriptions.MarketHistorySubscription"></a>

## MarketHistorySubscription

Subscribes the user to historical bar data. Streaming, top-of-the-book, level one, historical data is available for all instruments.

Only a maximum of 5 concurrent historical data requests are available at a time. Historical data will only respond once, though customers will still need to unsubscribe from the endpoint.

Attributes:

- `conid` _str_ - Required. A single contract identifier. Contracts requested use SMART routing by default.
- `exchange` _str, optional_ - Requested exchange to receive data.
- `period` _str, optional_ - Total duration for which bars will be requested.
- `bar` _str, optional_ - Interval of time to receive data.
- `outside_rth` _bool, optional_ - Determines if you want data outside regular trading hours (true) or only during market hours (false).
- `source` _str, optional_ - The value determining what type of data to show.
- `format` _str, optional_ - The format in which bars are returned.

<a id="ibkr_ws.ibkr_subscriptions.OrdersSubscription"></a>

## OrdersSubscription

Subscribes the user to live order updates.

Attributes:

- `filter` _str, optional_ - Pass an exclusive Order Status Value to return.

<a id="ibkr_ws.ibkr_subscriptions.PriceLadderSubscription"></a>

## PriceLadderSubscription

Subscribes the user to BookTrader price ladder data. Streaming BookTrader data requires users to maintain a L2, Depth of Book, market data subscription.

Attributes:

- `account_id` _str_ - Required. A single AccountId.
- `conid` _str_ - Required. A single contract identifier.
- `exchange` _str, optional_ - Provide a routing exchange identifier. If no exchange is specified, all available deep exchanges are assumed.

<a id="ibkr_ws.ibkr_subscriptions.PnlSubscription"></a>

## PnlSubscription

Subscribes the user to live profit and loss information.

<a id="ibkr_ws.ibkr_subscriptions.TradesSubscription"></a>

## TradesSubscription

Subscribes the user to trades data. This will return all executions data while streamed.

Attributes:

- `realtime_updates_only` _bool, optional_ - Decide whether you want to display any historical executions, or only the executions available in real time. Default: False.
- `days` _int, optional_ - Returns the number of days of executions for data to be returned. Default: 1.
