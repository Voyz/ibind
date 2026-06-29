# Old Queues vs New Sinks and Events

In the Websocket client v1, the only way to access data was through QueueAccessor interface. Additionally, the client exposed an internal QueueAccessor through `client.get()` and `client.empty()` methods.

In v2, sinks are separate objects you create and pass to the client at construction time. The client emits typed `WsEvent` instances into those sinks. Application code receives data using `EventSink` protocol, without locking the user into a specific consumption implementation.

`QueueSink` is a built-in sink that provides an analogous interface to the old QueueAccessor.

## IbkrWsKey to event type mapping

In v1 messages were identified with `IbkrWsKey` enum. Every `IbkrWsKey` has a direct equivalent event type:

| IbkrWsKey | Event type |
|---|---|
| `IbkrWsKey.ACCOUNT_SUMMARY` | `events.AccountSummary` |
| `IbkrWsKey.ACCOUNT_LEDGER` | `events.AccountLedger` |
| `IbkrWsKey.MARKET_DATA` | `events.MarketData` |
| `IbkrWsKey.MARKET_HISTORY` | `events.MarketHistory` |
| `IbkrWsKey.PRICE_LADDER` | `events.PriceLadder` |
| `IbkrWsKey.ORDERS` | `events.Orders` |
| `IbkrWsKey.PNL` | `events.Pnl` |
| `IbkrWsKey.TRADES` | `events.Trades` |
| `IbkrWsKey.ACCOUNT_UPDATES` | `events.AccountUpdate` |
| `IbkrWsKey.AUTHENTICATION_STATUS` | `events.AuthenticationStatus` |
| `IbkrWsKey.BULLETINS` | `events.Bulletin` |
| `IbkrWsKey.ERROR` | `events.IbkrError` |
| `IbkrWsKey.SYSTEM` | `events.System` |
| `IbkrWsKey.NOTIFICATIONS` | `events.Notification` |

Event types are used to identify the queue when acquiring data from the QueueSink.

## Replacing client.get() and client.empty()

**Before:**
```python
# poll
while not client.empty(IbkrWsKey.MARKET_DATA):
    msg = client.get(IbkrWsKey.MARKET_DATA)

# blocking get
msg = client.get(IbkrWsKey.ORDERS, block=True, timeout=5)
```

**After:**
```python
sink = QueueSink()
# ... pass to client at construction ...

# poll
while not sink.empty(events.MarketData):
    event = sink.get(events.MarketData)

# blocking get
event = sink.get(events.Orders, block=True, timeout=5)
```

## Replacing new_queue_accessor()

**Before:**
```python
accessor = client.new_queue_accessor(IbkrWsKey.TRADES)
msg = accessor.get()
```

**After:**
```python
accessor = sink.new_queue_accessor(events.Trades)
event = accessor.get()
```

Note: `QueueAccessor` is kept for backwards compatibility and will be removed in a future version. Use `QueueSink` directly where possible.


[events]: ../core-concepts/events.md
[sinks]: ../core-concepts/sinks.md