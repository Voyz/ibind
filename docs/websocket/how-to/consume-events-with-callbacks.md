# Consume events with callbacks

`CallbackSink` lets you register functions to be called whenever a specific event type is received.

## Registering a callback

```python
from ibind import CallbackSink, IbkrWsClientV2, events

def on_market_data(event: events.MarketData):
    print(event)

sink = CallbackSink()
sink.on(events.MarketData, on_market_data)

ws_client = IbkrWsClientV2(account_id='...', sinks=[sink])
ws_client.start()
```

`sink.on(event_type, callback)` takes the event class (not an instance) and a callable accepting a single argument of that type. It can be called at any time - before or after `start()`.

## Multiple callbacks for the same type

More than one callback can be registered for the same event type. They are invoked in the order they were registered:

```python
sink.on(events.MarketData, update_cache)
sink.on(events.MarketData, log_tick)
```

Registering the same function twice for the same type has no effect.

## Multiple event types

Each event type is independent. Register as many as needed:

```python
sink.on(events.MarketData, on_market_data)
sink.on(events.Orders, on_orders)
sink.on(events.WsAuthenticated, on_ready)
sink.on(events.WsDegraded, on_degraded)
```

## Callback execution

By default, callbacks are invoked from a dedicated background thread, separate from the WebSocket client's internal runtime. This means a slow callback does not delay incoming message processing or subscription reconciliation.

If you set `synchronous_output_events=True` on the client constructor, callbacks are invoked directly from the runtime thread. In that case, blocking inside a callback will stall all subsequent event processing, health checks and subscription management until the callback returns.

Unless you have a specific reason for synchronous delivery, the default is preferable.


## Avoid Calling Shutdown

`shutdown()` must not be called from within a callback. Depending on the execution context, doing so may raise a `RuntimeError` or deadlock. If a shutdown is needed in response to an event, defer it to a separate thread or communicate its intent to the main application thread:

```python
import threading

def on_degraded(event: events.WsDegraded):
    threading.Thread(target=ws_client.shutdown, daemon=True).start()

sink.on(events.WsDegraded, on_degraded)
```


[sinks]: ../core-concepts/sinks.md
[threading-model]: ../core-concepts/threading-model.md