# Sinks

Sinks are event consumers receiving events emitted by the WebSocket client. Every event is passed to all sinks provided to the client.

Sinks are passed to the client at construction time:

```python
sink = QueueSink()
ws_client = IbkrWsClientV2(account_id='...', sinks=[sink])
```


## EventSink is a Protocol

Any object implementing the `EventSink` protocol can be used as a sink. The protocol defines a single method:

```python
def emit(self, event: WsEvent) -> None:
    ...
```

There is no base class to inherit from. Any object with a matching `emit` method is a valid sink.

## Built-in Sinks

IBind provides several built-in sink implementations:

- `CallbackSink` - invokes registered callbacks per event type.
- `QueueSink` - stores events in per-type thread-safe queues.
- `CompositeSink` - forwards events to multiple child sinks.
- `LogSink` - logs every event using the project logger.
- `NoopSink` - silently discards all events.

## CallbackSink

`CallbackSink` allows registering one or more callbacks per event type. When an event is emitted, all callbacks registered for that type are invoked in the order they were registered.

```python
from ibind import CallbackSink, events

def on_market_data(event: events.MarketData):
    print(event)

sink = CallbackSink()
sink.on(events.MarketData, on_market_data)
```

By default, callbacks are invoked in sequence they're received, from a dedicated event propagation `async_sink_thread`. This is to ensure that a slow callback will not delay the runtime and lifecycle management functionalities of the client. If you'd like to receive events directly from the runtime thread instead, pass, `synchronous_output_events=True` to the Websocket client constructor.

Exceptions raised inside callbacks are caught and logged but do not propagate - a failing callback will not prevent remaining callbacks from being invoked.

### Methods

`on(event_type, callback)` - registers a callback for a specific event type. Registering the same callback for the same type twice has no effect. Different callbacks can be registered for the same event type.

The `event_type` argument should be the class type of the event, not an instance, eg. `events.Orders`. The callback should accept a single argument of the same type.

`has_callback(event_type, callback)` - Check if a callback is registered for a given event type. Returns a bool.

Callbacks can be registered at any point - before or after passing the sink to the client. The method is thread-safe.

## QueueSink

`QueueSink` stores events in separate thread-safe queues, one per event type. Events can be retrieved at any point after being emitted.

```python
from ibind import QueueSink, events

sink = QueueSink()

# ...

event = sink.get(events.MarketData, block=True, timeout=10)
```

### Methods

`get(event_type, block=False, timeout=None)` - retrieves the next event from the queue for the given type. With `block=True`, will wait up to `timeout` seconds for an event to arrive. Returns `None` if the queue is empty and blocking is disabled or timed out.

`empty(event_type)` - Check if the queue for a given event type is empty. Returns a bool.

`new_queue_accessor(event_type)` - Return a `QueueAccessor` for a given event type. Useful for passing read-only queue access to a separate component. The QueueAccessor functionality is provided as backward compatibility and will be removed in future versions.

A typical consumption pattern:

```python
while True:
    while not sink.empty(events.MarketData):
        event = sink.get(events.MarketData)
        # handle event
    time.sleep(0.1)
```

Note that `QueueSink` does not enforce a maximum queue size. If events are produced faster than they are consumed, the queue will grow without bound.

## CompositeSink

`CompositeSink` forwards every event to all of its child sinks. This is useful when events need to be consumed in more than one way simultaneously.

```python
from ibind import CompositeSink, CallbackSink, QueueSink

callback_sink = CallbackSink()
queue_sink = QueueSink()

composite = CompositeSink(callback_sink, queue_sink)
ws_client = IbkrWsClientV2(account_id='...', sinks=[composite])
```

Exceptions raised within a child sink are caught and logged, so a failure in one sink does not prevent the others from recieving the event.

## LogSink and NoopSink

Two minimal utility sinks are provided:

- `LogSink` - logs every event at INFO level using the project logger. Useful for observing what events are being generated during development or debugging.
- `NoopSink` - discards all events silently. Useful when a sink is required structurally but no event consumption is needed.

## Custom Sinks

Any class with an `emit(event: WsEvent) -> None` method satisfies the protocol and can be used as a sink:

```python
class MySink:
    def emit(self, event: WsEvent) -> None:
        # custom handling
        ...

ws_client = IbkrWsClientV2(account_id='...', sinks=[MySink()])
```

[events]: ./events.md
[subscriptions]: ./subscriptions.md