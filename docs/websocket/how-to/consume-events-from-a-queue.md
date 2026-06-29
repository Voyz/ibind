# Consume events from a queue

`QueueSink` stores events in per-type thread-safe queues as they arrive. The application code reads from them at its own pace.

## Setup

Pass a `QueueSink` to the client at construction time:

```python
from ibind import QueueSink, IbkrWsClientV2, events

sink = QueueSink()
ws_client = IbkrWsClientV2(account_id='...', sinks=[sink])
ws_client.start()
```

## Getting a single event

`sink.get()` retrieves the next event for a given type. By default it is non-blocking - returns `None` immediately if the queue is empty:

```python
event = sink.get(events.MarketData)
if event is not None:
    print(event)
```

To block until an event arrives, pass `block=True`. Combine with `timeout` to avoid blocking indefinitely:

```python
event = sink.get(events.MarketData, block=True, timeout=10)
if event is not None:
    print(event)
```

`None` is returned both when the queue is empty (non-blocking) and when the timeout expires. Always check the return value before using it.

## Continuous consumption loop

A simple example for continuously consuming events:

```python
import time

while True:
    while not sink.empty(events.MarketData):
        event = sink.get(events.MarketData)
        if event is not None:
            process(event)
    time.sleep(0.1)
```

The inner loop drains everything currently queued before sleeping, so events do not build up between cycles.

## Shutdown-safe consumer loop

If your loop blocks on `sink.get()`, it may prevent up a graceful shutdown. Use a short `timeout` combined with a running flag to allow the loop to exit promptly:

```python
import threading

running = True

def consume():
    while running:
        event = sink.get(events.MarketData, block=True, timeout=1)
        if event is not None:
            process(event)

consumer_thread = threading.Thread(target=consume, daemon=True)
consumer_thread.start()

ws_client.start()
# ...

running = False
ws_client.shutdown()
consumer_thread.join()
```

The `timeout=1` means the loop wakes up at least once per second to check the flag regardless of whether any events arrived.

## Consuming multiple event types

Each event type has its own independent queue. Poll each one in turn:

```python
while True:
    event = sink.get(events.MarketData)
    if event is not None:
        handle_market_data(event)

    event = sink.get(events.Orders)
    if event is not None:
        handle_orders(event)

    time.sleep(0.05)
```

## Backwards compatibility with QueueAccessor

`new_queue_accessor()` exposes a backwards-compatible interface with `QueueAccessor` classes. It will be removed in future versions of IBind. Use `QueueSink` directly instead.

```python
accessor = sink.new_queue_accessor(events.MarketData)
```

`QueueAccessor` exposes the same `get(block, timeout)` and `empty()` interface. Useful when different components are responsible for consuming different event types.

## A note on queue size

`QueueSink` does not enforce a maximum size. If your consumer falls significantly behind the rate of incoming events, the queue will grow without bound.

[sinks]: ../core-concepts/sinks.md
[threading-model]: ../core-concepts/threading-model.md