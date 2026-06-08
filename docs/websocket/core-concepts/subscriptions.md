# Subscription Interface

Interacting with the IBKR WebSocket interface requires sending string payloads to express intents of subscribing to and unsubscribing from topics.

IBind solves the intricacies of this communication, exposing an elegant model-based interface to the user, while handling the quirks of specific topics behind the scenes.

We define a 'subscription' (noun) as a single communication channel through which IBKR will stream messages, that can be uniquely identified and later unsubscribed from. A 'subscription' (verb) is an action of sending the appropriate payload through the WebSocket.

For brevity, this document will speak primarily of topic subscription, given that most concepts apply in the same way for unsubscribing.

## Topics are typed classes

Topics are represented by typed Pydantic models. Each class accepts arguments expected by its topic.  

For some topics, IBKR usually sends a message that can validate that the subscription was successful. In such cases, the WebSocket client will repeatedly send the payload until such signal is received or all attempts are spent, marking the subscription attempt as failed. For remaining topics the subscription is assumed as active immediately after sending the payload.

Full list of Subscription models can be found later in this document.


## Subscribing and unsubscribing

There are two primary functions to interact with the WebSocket interface:

- `client.subscribe()`
- `client.unsubscribe()`

In both cases passing an instance of Subscription model representing the topic in question, optionally populated with the relevant parameters.

```python
# Example subscription call
orders_sub = OrdersSubscription(filter='Submitted')
client.subscribe(orders_sub)

time.sleep(5)

client.unsubscribe(orders_sub)
```

## Bindings represent the subscriptions

The WebSocket client represents each WebSocket topic connection as a `Binding` object. It stores the target Subscription model and user's intent for that subscription - either ACTIVE (on subscription) or UNSUBSCRIBED (on unsubscription). 

Additionally, bindings hold the current state of the subscription as `BindingStatus` enum:
- `NEW` - freshly registered
- `ACTIVE` - successfully subscribed (either confirmed or assumed) 
- `FAILED` - didn't receive expected subscription confirmation 
- `DEGRADED` - externally marked as stale, usually due to connectivity issues observed by the WebSocket client
- `UNSUBSCRIBED` - successfully unsubscribed (either confirmed or assumed)
- `EXPIRED` - exceeded specified time since last subscription payload was sent, triggering a prompt resubscription

Changes in a binding's BindingStatus reflect its state and that of its corresponding subscription.

## Binding key identifies unique subscriptions

IBKR does not treat each individual subscription call as a separate subscription, instead classifying subscriptions in various ways depending on the topic. For example, all 'orders' topic subscription calls are unified under a single subscription, irrespectively of arguments passed. Contrarily, each 'market data' topic subscription call with unique `conid` argument will create a separate subscription which needs to be handled separately.

As a result, for some topics there could be a separate binding instance for each unique subscription + arguments combination. Such uniquness is expressed through Subscription's binding key, which can be acquired by calling `subscription.binding_key()`.

For example, the following two MarketDataSubscriptions would result in two separate binding keys, hence resulting in two bindings being created:

```python
>>> MarketDataSubscriptions(conid='123', fields=[...]).binding_key()
md+123
>>> MarketDataSubscriptions(conid='456', fields=[...]).binding_key()
md+456
```

While two OrdersSubscriptions would still be represented as a single binding:

```python
>>> OrdersSubscription().binding_key()
or
>>> OrdersSubscription(filter='Submitted').binding_key()
or
```

The binding key is used to query information about a binding, using the following methods:

- `get_binding_status(binding_key)` - Get the status of a subscription binding, returns a BindingStatus if binding is found, or None otherwise.
- `is_subscription_active(binding_key)` - Check if a subscription binding is currently active, returns a bool.



## Interface is asynchronous and idempotent

Upon calling either `subscribe()` or `unsubscribe()` the client registers an intent (ACTIVE and UNSUBSCRIBED accordingly) for the binding related to the subscription model passed. These methods are non-blocking - calling either returns immediately. They are also idempotent - repeated calls produce no further side effects, with the exception to resetting a FAILED status back to NEW for failed bindings.

The WebSocket client regularly scans current bindings and reconciles them until their BindingStatus is equal to the intent. Reconciliation involves resending payloads and validating the status if confirmation is expected from the server. This also ensures that topics are automatically resubscribed to after connectivity drops.

An `events.SubscriptionUpdated` event is emitted each time a status of a binding changes, containing an instance of the Subscription model, its binding key and the new status.

## Subscription handles

Both `subscribe()` and `unsubscribe()` return an instance of SubscriptionHandle object, facilitating interaction with the binding related to this call. 

Subscription handles provide methods for querying binding status and checking whether binding is done (ie. its status is equal to its intent).

A handle can also be waited for by either calling `handle.wait(timeout)` or `client.wait_all([handle, ...])`), blocking the current thread until the binding is done.

## Subscription Models

### AccountSummarySubscription
Topic: 'account summary'  
Confirms subscription: True  
Confirms unsubscription: True  

Arguments:   
- `account_id` (str): The account ID whose account summary data will be subscribed.
- `keys` (List[str], optional): Pass specific account summary data keys to receive messages concerning only those keys. Passing no named keys when opening the subscription will deliver account summary messages containing values for the selected account. Example Values: "AccruedCash-S", "ExcessLiquidity-S"
- `fields` (List[str], optional): Pass specific account summary field names to filter responses to include only these fields for the requested keys. Passing no named fields when opening the subscription will deliver all available data points for the specified account summary keys. Example Values: "currency", "monetaryValue"

### AccountLedgerSubscription
Topic: 'account ledger'  
Confirms subscription: True  
Confirms unsubscription: True  

Arguments:   
- `account_id` (str): The account ID whose account summary data will be subscribed.
- `keys` (List[str], optional): Pass specific ledger currency keys to receive messages with data only for those currencies. Passing no named keys when opening the subscription will deliver ledger messages containing values for all currencies in the selected account. Example Values: "LedgerListEUR", "LedgerListUSD", "LedgerListBASE" (for the account’s base currency)
- `fields` (List[str], optional): Pass specific ledger field names to receive messages only those data points for the currencies specified in the keys argument. Passing no named fields when opening the subscription will deliver all available data points for the specified currencies. Example Values: "cashBalance", "exchangeRate"

### MarketDataSubscription
Topic: 'market data'  
Confirms subscription: True  
Confirms unsubscription: False  

Arguments:   
- `conid` (str): a single contract identifier.
- `fields` (List[str], optional): Pass an array of field IDs.

### MarketHistorySubscription
Topic: 'market history'  
Confirms subscription: True  
Confirms unsubscription: True  

Arguments:   
- `conid` (str): A single contract identifier.
- `exchange` (str): Requested exchange to receive data.
- `period` (str): Total duration for which bars will be requested.
- `bar` (str): Interval of time to receive data.
- `outside_rth` (bool): Determines if you want data outside regular trading hours (true) or only during market hours (false).
- `source` (str): The value determining what type of data to show.
- `format` (str): The format in which bars are returned.

**Note on market history unsubscription:**

Contrarily to other topics, the 'market history' topic requires unsubscribing by passing server ID specified in the incoming market data messages to be passed in the unsubscription payload. 

The WebSocket client stores the server IDs and can handle this unsubscription quirk automatically. For that purpose, the MarketHistorySubscription contains  `server_id` field which is populated by the client upon receiving the first message.

This functionality relies on using a MarketHistorySubscription instance with `unsubscribe()` that has been previously passed to `subscribe()`. Should a fresh MarketHistorySubscription instance be used, the `server_id` should be set prior to passing it to `unsubscribe()`. If an instance without `server_id` is received, the unsubscribe method will attempt to match it against its current server ID records using `conid` as a lookup key, however a warning will be issued.

### OrdersSubscription
Topic: 'orders'  
Confirms subscription: False  
Confirms unsubscription: False  

Arguments:   
- `filter` (str, optional): Exclusive Order Status Value to return.

**Note on order updates:**

The data received through the 'orders' channel is affected by the calls to Live Orders endpoint. See [FIXME: link to order-update-caveats.md] for more.

### PriceLadderSubscription
Topic: 'price ladder'  
Confirms subscription: False  
Confirms unsubscription: False  

Arguments:   
- `conid` (str): A single contract identifier.
- `account_id` (str): A single AccountId.
- `exchange` (str, optional): Provide a routing exchange identifier. 

### PnlSubscription
Topic: 'pnl'  
Confirms subscription: True  
Confirms unsubscription: False  

Arguments:   
- None

### TradesSubscription
Topic: 'trades'  
Confirms subscription: True  
Confirms unsubscription: False  

Arguments:   
- `realtime_updates_only` (bool | None, optional): Decide whether you want to display any historical executions, or only the executions available in real time. Set to false by default.
- `days` (int | None, optional): Returns the number of days of executions for data to be returned. Set to 1 by default.
