# Threading Model

The WebSocket client runs across multiple concurrent threads. Understanding which thread executes what is important when working with sinks, callbacks, and lifecycle methods.

## Execution Contexts

There are four execution contexts:

- Caller thread - the thread calling `start()`, `shutdown()`, `subscribe()` from the application code and reading from sinks. This would be the thread interacting with IBind.
- Transport thread - the internal thread managing the raw WebSocket connection.
- Runtime thread - the internal thread processing incoming messages and emitting events.
- AsyncSink thread - the background thread forwarding events from an internal queue to user-configured sinks.


## Caller Thread

The caller thread is the application code interacting with IBind - typically the main thread or a dedicated control thread.

`start()` is blocking. It waits until the connection is authenticated or a timeout is reached before returning.

`shutdown()` is also blocking. It must not be called from the runtime thread (see below). It waits for all internal threads to stop before returning.

`subscribe()` and `unsubscribe()` are non-blocking and thread-safe. They can be called at any time after `start()`.


## Transport Thread

The transport thread runs the `WebSocketApp` loop, maintaining the WebSocket connection. It receives raw WebSocket callbacks (open, close, message, error, reconnect) and converts them into internal `TransportEvent`s, which are placed into a queue for the runtime thread to process.

The transport thread does not emit `WsEvent`s and does not interact with user sinks directly.

## Runtime Thread

The runtime thread is the main event processing loop. On each cycle it:

1. Ensures the transport thread is alive, recreating it if necessary.
2. Drains the transport event queue, sorting events by the time they were received.
3. Routes each message through the router, producing `WsEvent`s.
4. Emits each event to the configured sinks.
5. Reconciles subscription bindings.
6. Runs health checks, and resets the WebSocket connection if they fail.

By default, the runtime thread emits each event to an internal `AsyncSink` queue and returns immediately. The actual delivery to user-configured sinks happens on the AsyncSink thread (see below). This functionality can be disabled by setting `synchronous_output_events=True` on the client constructor, which will cause the runtime thread to emit events directly to user sinks. See [Sinks](./sinks.md) for more on sink implementations.

The runtime thread sleeps between cycles for a configurable interval (`cycle_interval`). When the transport thread receives a new message, it wakes the runtime thread immediately to minimise latency.

## AsyncSink Thread

By default, the client wraps all user-configured sinks in an internal `AsyncSink` before passing them to the runtime. This creates a dedicated `async_sink_thread` that sits between the runtime and user code.

The flow is:

1. Runtime thread produces a `WsEvent` and calls `AsyncSink.emit(event)`.
2. `AsyncSink` places the event into its internal queue and returns immediately.
3. `async_sink_thread` drains the queue and calls the user sink's `emit(event)` for each event.

This means user code - callbacks, queue writes, custom sink logic - runs on the `async_sink_thread`, not on the runtime thread. The runtime is free to continue processing new messages, maintaining subscriptions and running health checks regardless of how long user code takes.

The `AsyncSink` and its thread are managed automatically. They are started when the client starts and stopped when it shuts down.

If you set `synchronous_output_events=True` on the client constructor, the internal `AsyncSink` is not created. Events are emitted directly from the runtime thread to user sinks, meaning slow or blocking user code will stall the runtime.

[sinks]: ./sinks.md
[events]: ./events.md
[runtime-and-lifecycle]: ./runtime-and-lifecycle.md
