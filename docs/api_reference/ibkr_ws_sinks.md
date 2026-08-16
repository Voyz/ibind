# Table of Contents

* [ws\_sinks](#ws_v2.ws_sinks)
  * [EventSink](#ws_v2.ws_sinks.EventSink)
  * [LogSink](#ws_v2.ws_sinks.LogSink)
  * [NoopSink](#ws_v2.ws_sinks.NoopSink)
  * [CallbackSink](#ws_v2.ws_sinks.CallbackSink)
    * [on](#ws_v2.ws_sinks.CallbackSink.on)
    * [has\_callback](#ws_v2.ws_sinks.CallbackSink.has_callback)
    * [emit](#ws_v2.ws_sinks.CallbackSink.emit)
  * [QueueSink](#ws_v2.ws_sinks.QueueSink)
    * [\_\_init\_\_](#ws_v2.ws_sinks.QueueSink.__init__)
    * [new\_queue\_accessor](#ws_v2.ws_sinks.QueueSink.new_queue_accessor)
    * [get](#ws_v2.ws_sinks.QueueSink.get)
    * [empty](#ws_v2.ws_sinks.QueueSink.empty)
    * [emit](#ws_v2.ws_sinks.QueueSink.emit)
  * [CompositeSink](#ws_v2.ws_sinks.CompositeSink)
    * [\_\_init\_\_](#ws_v2.ws_sinks.CompositeSink.__init__)
    * [emit](#ws_v2.ws_sinks.CompositeSink.emit)
  * [AsyncSink](#ws_v2.ws_sinks.AsyncSink)
    * [\_\_init\_\_](#ws_v2.ws_sinks.AsyncSink.__init__)
    * [start](#ws_v2.ws_sinks.AsyncSink.start)
    * [stop](#ws_v2.ws_sinks.AsyncSink.stop)
    * [emit](#ws_v2.ws_sinks.AsyncSink.emit)

<a id="ws_v2.ws_sinks.EventSink"></a>

## EventSink

Protocol for objects that can receive and process WebSocket events.

<a id="ws_v2.ws_sinks.LogSink"></a>

## LogSink

Sink that logs events using the project logger.

<a id="ws_v2.ws_sinks.NoopSink"></a>

## NoopSink

Sink that discards all events without processing.

<a id="ws_v2.ws_sinks.CallbackSink"></a>

## CallbackSink

Sink that invokes registered callbacks for specific event types.

Callbacks are registered per event type and invoked when matching events are emitted.
Exceptions from callbacks are logged but do not propagate.

<a id="ws_v2.ws_sinks.CallbackSink.on"></a>

### on

```python
def on(event_type: type[WsEvent], callback: Callable[[T], None]) -> None
```

Register a callback for a specific event type.

Arguments:

- `event_type` _type[WsEvent]_ - The event type to listen for.
- `callback` _Callable_ - Function to invoke when events of this type are emitted.

<a id="ws_v2.ws_sinks.CallbackSink.has_callback"></a>

### has\_callback

```python
def has_callback(event_type: type[WsEvent], callback: Callable[[T],
                                                               None]) -> bool
```

Check if a callback is registered for a specific event type.

Arguments:

- `event_type` _type[WsEvent]_ - The event type to check.
- `callback` _Callable_ - The callback to look for.
  

Returns:

- `bool` - True if the callback is registered, False otherwise.

<a id="ws_v2.ws_sinks.CallbackSink.emit"></a>

### emit

```python
def emit(event: WsEvent) -> None
```

Emit an event to all registered callbacks for its type.

Arguments:

- `event` _WsEvent_ - The event to emit.

<a id="ws_v2.ws_sinks.QueueSink"></a>

## QueueSink

Sink that stores events in separate queues per event type.

Maintains a dictionary of queues, one for each event type. Events can be
retrieved synchronously or asynchronously via queue accessors.

When queues reach maxsize, events are dropped according to the drop_oldest policy.

<a id="ws_v2.ws_sinks.QueueSink.__init__"></a>

### \_\_init\_\_

```python
def __init__(maxsize: int = var.IBIND_WS_MAX_QUEUE_SIZE,
             drop_oldest: bool = var.IBIND_WS_DROP_OLDEST)
```

Create a queue sink.

Arguments:

- `maxsize` _int, optional_ - Maximum queue size per event type. 0 = unbounded. Default: var.IBIND_WS_MAX_QUEUE_SIZE.
- `drop_oldest` _bool, optional_ - Whether to drop oldest events when full.
  If False, drops newest events. Default: var.IBIND_WS_DROP_OLDEST (True).

<a id="ws_v2.ws_sinks.QueueSink.new_queue_accessor"></a>

### new\_queue\_accessor

```python
def new_queue_accessor(event_type: type[WsEvent]) -> QueueAccessor
```

Create a queue accessor for a specific event type.

Arguments:

- `event_type` _type[WsEvent]_ - The event type to access.
  

Returns:

- `QueueAccessor` - Accessor for the queue associated with this event type.

<a id="ws_v2.ws_sinks.QueueSink.get"></a>

### get

```python
def get(event_type: type[WsEvent],
        block: bool = False,
        timeout: float = None) -> Any
```

Retrieve an event from the queue for a specific event type.

Arguments:

- `event_type` _type[WsEvent]_ - The event type to retrieve.
- `block` _bool, optional_ - Whether to block until an event is available. Default: False.
- `timeout` _float, optional_ - Maximum time to block in seconds. Default: None.
  

Returns:

  WsEvent | None: The retrieved event, or None if the queue is empty and block=False.

<a id="ws_v2.ws_sinks.QueueSink.empty"></a>

### empty

```python
def empty(event_type: type[WsEvent]) -> bool
```

Check if the queue for a specific event type is empty.

Arguments:

- `event_type` _type[WsEvent]_ - The event type to check.
  

Returns:

- `bool` - True if the queue is empty, False otherwise.

<a id="ws_v2.ws_sinks.QueueSink.emit"></a>

### emit

```python
def emit(event: WsEvent) -> None
```

Emit an event by adding it to the queue for its type.

Arguments:

- `event` _WsEvent_ - The event to emit.

<a id="ws_v2.ws_sinks.CompositeSink"></a>

## CompositeSink

Sink that forwards events to multiple child sinks.

Exceptions from individual sinks are logged but do not prevent other sinks
from receiving the event.

<a id="ws_v2.ws_sinks.CompositeSink.__init__"></a>

### \_\_init\_\_

```python
def __init__(*sinks: EventSink)
```

Create a composite sink.

Arguments:

- `*sinks` _EventSink_ - One or more sinks to forward events to.

<a id="ws_v2.ws_sinks.CompositeSink.emit"></a>

### emit

```python
def emit(event: WsEvent) -> None
```

Emit an event to all registered sinks.

Arguments:

- `event` _WsEvent_ - The event to emit.

<a id="ws_v2.ws_sinks.AsyncSink"></a>

## AsyncSink

Sink that forwards events to another sink asynchronously via a background thread.

Events are queued and processed in a separate thread. When the queue is full,
events are dropped according to the drop_oldest policy.

<a id="ws_v2.ws_sinks.AsyncSink.__init__"></a>

### \_\_init\_\_

```python
def __init__(sink: EventSink,
             maxsize: int = var.IBIND_WS_MAX_QUEUE_SIZE,
             drop_oldest: bool = var.IBIND_WS_DROP_OLDEST,
             stop_timeout: float = 5,
             cycle_interval: float = 0.25)
```

Create an asynchronous sink.

Arguments:

- `sink` _EventSink_ - The sink to forward events to.
- `maxsize` _int, optional_ - Maximum queue size. Default: var.IBIND_WS_MAX_QUEUE_SIZE.
- `drop_oldest` _bool, optional_ - Whether to drop oldest events when full.
  If False, drops newest events. Default: var.IBIND_WS_DROP_OLDEST (True).
- `stop_timeout` _float, optional_ - Maximum time to wait for thread to stop in seconds. Default: 5.
- `cycle_interval` _float, optional_ - Interval between queue processing cycles in seconds. Default: 0.25.

<a id="ws_v2.ws_sinks.AsyncSink.start"></a>

### start

```python
def start()
```

Start the background thread for processing events.

<a id="ws_v2.ws_sinks.AsyncSink.stop"></a>

### stop

```python
def stop() -> bool
```

Stop the background thread and discard remaining events.

Returns:

- `bool` - True if the thread stopped successfully, False if it timed out.
  

Raises:

- `RuntimeError` - If called from within the async sink thread.

<a id="ws_v2.ws_sinks.AsyncSink.emit"></a>

### emit

```python
def emit(event: WsEvent) -> None
```

Queue an event for asynchronous processing.

Arguments:

- `event` _WsEvent_ - The event to emit.
