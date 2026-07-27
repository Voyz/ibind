# Migrating from IbkrWsClient to IbkrWsClientV2

`IbkrWsClientV2` replaces `IbkrWsClient` with a redesigned interface. The core responsibilities are the same - connecting to IBKR WebSocket, managing subscriptions, and delivering incoming data - but the model for subscriptions and event consumption has changed significantly.

## Imports

**Before:**
```python
from ibind import IbkrWsClient, IbkrWsKey
```

**After:**
```python
from ibind import IbkrWsClientV2, QueueSink, events
from ibind.subscriptions import MarketDataSubscription, OrdersSubscription  # etc.
```

## Initialisation

The constructor is leaner. Most of the old parameters either no longer exist or are handled internally.

**Before:**
```python
client = IbkrWsClient(
    account_id='...',
    host='127.0.0.1',
    port='5000',
    start=True,
    subscription_retries=5,
    subscription_timeout=2,
    restart_on_close=True,
    restart_on_critical=True,
)
```

**After:**
```python
sink = QueueSink()
client = IbkrWsClientV2(account_id='...', sink=sink)
client.start()
```

The `start=True` convenience flag no longer exists. Call `start()` explicitly.

## Subscriptions

The old client subscribed using raw string channel identifiers with manually assembled payloads. The new client uses typed Subscription model instances.

**Before:**
```python
client.subscribe('md+265598', data={'fields': ['31', '84', '86']})
client.subscribe('or')

client.unsubscribe('md+265598', data={})
```

**After:**
```python
from ibind import snapshot_keys_to_ids
from ibind.subscriptions import MarketDataSubscription, OrdersSubscription

subscription = MarketDataSubscription(
    conid='265598',
    fields=snapshot_keys_to_ids(['last_price', 'bid_price', 'ask_price']),
)
handle = client.subscribe(subscription)

client.subscribe(OrdersSubscription())

client.unsubscribe(subscription)
```

`subscribe()` is now non-blocking and returns a `SubscriptionHandle`. In the old client it was blocking, waiting for subscription confirmation before returning. In v2, use `handle.wait(timeout)` if you need to block until the subscription is confirmed active.

## Consuming events

This is the most significant change. The old client used `IbkrWsKey`-keyed queues and returned raw dicts. The new client delivers typed `WsEvent` instances through sinks.

**Before:**
```python
# blocking get
message = client.get(IbkrWsKey.MARKET_DATA, block=True, timeout=10)
# message is a raw dict

# poll loop
while not client.empty(IbkrWsKey.MARKET_DATA):
    msg = client.get(IbkrWsKey.MARKET_DATA)

# queue accessor
accessor = client.new_queue_accessor(IbkrWsKey.MARKET_DATA)
msg = accessor.get(block=True)
```

**After:**
```python
# blocking get
event = sink.get(events.MarketData, block=True, timeout=10)
# event is a typed MarketData instance

# poll loop
while not sink.empty(events.MarketData):
    event = sink.get(events.MarketData)

# queue accessor
accessor = sink.new_queue_accessor(events.MarketData)
event = accessor.get(block=True)
```

Field access changes accordingly. In the old client, market data arrived as a flat dict (eg. `message['last_price']`). In v2 the same fields are accessible as `event.data['last_price']` - the field remapping behaviour is the same by default, since `IbkrRouter` also defaults to `unwrap_market_data=True`.

## Callback-based consumption

The old client had no callback mechanism. In v2, use `CallbackSink`:

```python
from ibind import CallbackSink

sink = CallbackSink()
sink.on(events.MarketData, lambda event: print(event))
client = IbkrWsClientV2(account_id='...', sink=sink)
```

## Lifecycle

**Before:**
```python
client.start()
client.shutdown()
client.hard_reset(restart=True)
```

**After:**
```python
client.start()
client.shutdown()
client.hard_reset()            # always performs a full stop and restart
client.reset_websocket_app()   # new: resets only the underlying WebSocketApp
```

`hard_reset()` in v2 no longer accepts a `restart` argument - it always performs a full stop and start cycle.

## Unsolicited messages

The old client required passing `unsolicited_channels_to_be_queued` at construction time for unsolicited messages to be queued. In v2, all unsolicited messages are delivered as typed events to sinks by default - no extra configuration neccessary.

Authentication status changes arrive as `events.AuthenticationStatus`, account updates as `events.AccountUpdate`, notifications as `events.Notification`, and so on. See [Events][events] for the full list.

## New lifecycle events

V2 introduces lifecycle events that have no equivalent in the old client. These are emitted by the runtime itself and describe the connection state:

- `events.WsOpen` - connection opened
- `events.WsAuthenticated` - connection authenticated
- `events.WsReady` - connection ready for subscriptions
- `events.WsDegraded` - connection degraded
- `events.WsClose` - connection closed
- `events.WsError` - WebSocket error
- `events.WsStarting` / `events.WsStopping` / `events.WsStopped` - runtime lifecycle

These are useful for reacting to connection state changes without polling `is_authenticated()` or `is_running()`.

## Other changes

A few things from the old client have moved or no longer exist:

- `log_raw_messages` - no longer a client constructor argument. Pass `IbkrRouter(log_raw_messages=True)` to the `router` argument instead.
- `unwrap_market_data` - no longer a client constructor argument. Pass `IbkrRouter(unwrap_market_data=False)` to the `router` argument to disable field remapping.

[events]: ../core-concepts/events.md
[subscriptions]: ../core-concepts/subscriptions.md
[sinks]: ../core-concepts/sinks.md