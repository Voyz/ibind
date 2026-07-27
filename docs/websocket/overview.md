# WebSocket Client Overview

The IBind WebSocket client provides a high-level interface to the IBKR WebSocket API.

It facilitates streaming live updates such as market data, order updates, account updates, PnLs or trades, without needing to manually manage WebSocket lifecycle, payloads, or subscription states.

The WebSocket client is responsible for:

* Maintaining the WebSocket connection
* Subscribing and unsubscribing from topics
* Tracking user subscription intents
* Handling the topic-specific outgoing payloads
* Parsing incoming raw messages into typed events
* Routing events into user-configured sinks
* Monitoring connection's health and recovering from connection anomalies
* Shutting down gracefully and unsubscribing

It does not replace the REST client (`IbkrClient`), and some WebSocket functionalities may require REST pre-flights, session checks or OAuth initialisation (if used).

## Implementation Overview

The WebSocket client encompasses 5 concepts:

* IbkrWsClient - the core interface, managing lifecycle and event forwarding
* [Events](./core-concepts/events.md) - Pydantic models encapsulating parsed incoming messages and connection state changes
* [Subscriptions](./core-concepts/subscriptions.md) - Typed representation of topics available for subscription
* [Sinks](./core-concepts/sinks.md) - User-defined event consumers, providing high degree of customizability
* [Routers](./core-concepts/router.md) - Parsing incoming messages into events

The client is implemented using two layers:

- Transport - the low-level WebSocket-facing interface, bridging between the client and the server
- Runtime - the main orchestrator and API layer

The message flow is:

```text
IBKR WebSocket
    ↓
Transport
    ↓
Runtime
    ↓
Router event parsing + subscription reconciliation
    ↓
Sinks
    ↓
User application
```

## Subscription Model is Idempotent

Calling either `subscribe(subscription)` or `unsubscribe(subscription)` passing a Subscription object registers an intent to subscribe or unsubscribe with the client. Such intent is then autonomously managed and fulfilled.

This interface is idempotent and non-blocking - a subscription handle is returned, facilitating state checks and waiting on intent being fulfilled.

The client handles converting the Subscription models into appropriate payloads to communicate with IBKR servers.


## Events Represent WebSocket Data

Incoming WebSocket messages are converted into events before they are propagated to user code. Known message types are parsed into events using a router - which can be overridden for bespoke message parsing -, while unknown types are collated into a single generic event type.

Typical events may include:

- WebSocket connection state changes
- Subscription status changes
- Market data events
- Order updates
- Trade events
- Errors
- Account updates

For exact types of events see [Events](./core-concepts/events.md)

## Sinks Consume Events

User application receives events through simple consumers called sinks. Implementing a consumer protocol, these allow for custom event propagation according to specific needs. 

Two main sink types are implemented by default:

- CallbackSink - registering event callbacks that will be invoked upon event consumption.
- QueueSink - putting events into thread-safe queues with read-only interface.

Additionally, two utility sinks are provided for convenience:
- LogSink - logging all events, useful for debugging.
- CompositeSink - combining several sinks together.

Any custom object implementing the sink protocol can be used instead.

For more on sinks, see [Sinks](./core-concepts/sinks.md)

## Connection Lifecycle

The WebSocket client has an explicit lifecycle:

```python
client = IbkrWsClientV2(...)
client.start()
# subscribe and consume events
client.shutdown()
```

After creating an instance, the client can be started (initialising the internal threads, enabling subscriptions and event propagation) and later shut down (closing the connection gracefully, flushing remaining events and stopping threads).

The client has a number of health checks and recovery mechanisms, attempting to provide continuous connectivity and high uptime. IBKR does not provide information on events' replay after downtime, hence user application should assume possible dropped WebSocket events and synchronise through REST API after connection issues where necessary.

## IBKR-specific behaviour

IBKR WebSocket behaviour is not fully uniform across topics. Some confirm subscription, some confirm unsubscription - for others subscription state is assumed after sending the appropriate payload. Some send partial updates. Some require REST pre-flight calls before subscribing. Some messages contain server-side identifiers that need to be tracked internally.

IBind handles these quirks where practical, but it does not pretend the IBKR WebSocket API is simpler than it is. Broker-specific behaviour is documented separately under [IBKR-Specific Behaviour](./ibkr-specific-behaviour/) so users can distinguish IBind design from IBKR quirks.

## When to use the WebSocket client

Use the WebSocket client when your application needs streaming updates from IBKR, such as:

- live market data
- order status changes
- trade updates
- account or portfolio updates
- PnL updates

Use the REST client when your application needs synchronous, request/response functionality, such as:

- searching contracts
- placing orders
- checking current authentication status
- fetching account metadata
- retrieving snapshots or one-off data

In many real systems, you use both: REST for setup and actions, WebSocket for ongoing state updates.

## Where to go next

Start with the WebSocket quickstart if you want a working example. Read Core Concepts if you need to understand the runtime model. Use the How-to Guides for task-specific workflows such as subscribing to market data or consuming events with callbacks. Use IBKR-Specific Behaviour when something looks strange but may be caused by broker-side quirks rather than IBind itself.
