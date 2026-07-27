# Router

The router is responsible for translating raw WebSocket messages into typed [WsEvent](./events.md) instances. Every message received from the WebSocket passes through the router before it reaches the user-configured sinks.

The router sits at the boundary between the runtime and the event sinks. Its job is to parse raw message strings and return one or more events.

## IbkrRouter

`IbkrRouter` is the default router used by Websocket client. It implements the full IBKR WebSocket message format, mapping topic prefixes to typed events:

| Topic | Event |
|---|---|
| `md` | `events.MarketData` |
| `mh` | `events.MarketHistory` |
| `or` | `events.Orders` |
| `sd` | `events.AccountSummary` |
| `ld` | `events.AccountLedger` |
| `pl` | `events.Pnl` |
| `tr` | `events.Trades` |
| `bd` | `events.PriceLadder` |
| `sts` | `events.AuthenticationStatus` |
| `act` | `events.AccountUpdate` |
| `ntf` | `events.Notification` |
| `blt` | `events.Bulletin` |

Unrecognised messages are emitted as `GenericIbkrEvent`. Messages that carry an `error` field are emitted as `IbkrError`.

### Configuration

`IbkrRouter` accepts two optional constructor arguments:

`log_raw_messages` (bool, default `False`) - when enabled, logs each raw message string at DEBUG level before processing. Useful for troubleshooting unexpected message formats.

`unwrap_market_data` (bool, default `True`) - when enabled, remaps numeric IBKR field IDs in market data messages to their readable equivalents before storing them in `event.data`. When disabled, the raw numeric keys are preserved.

To pass a configured router to the client:

```python
from ibind import IbkrWsClientV2
from ibind.ibkr_ws_v2.ibkr_router import IbkrRouter

router = IbkrRouter(log_raw_messages=True, unwrap_market_data=False)
client = IbkrWsClientV2(account_id='...', router=router)
```

## Custom Router

Any object implementing the `Router` protocol can be passed as the `router` argument. The protocol defines a single method:

```python
def route(self, raw_message: str) -> OneOrMany[WsEvent]:
    ...
```

`route()` receives the raw message string and should return a single `WsEvent`, a list of `WsEvent`s, or an empty list to skip the message entirely.

A custom router is useful when connecting to a non-standard backend, adding support for additional message types, or overriding how specific topics are parsed. In most cases `IbkrRouter` is sufficient and does not need replacing.

```python
from ibind.ws_v2._ws_events import Router
from ibind.events import WsEvent

class MyRouter:
    def route(self, raw_message: str) -> list[WsEvent]:
        # parse raw_message and return typed events
        ...

client = IbkrWsClientV2(account_id='...', router=MyRouter())
```

[events]: ./events.md
[sinks]: ./sinks.md
