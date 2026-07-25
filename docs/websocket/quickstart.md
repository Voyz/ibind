# WebSocket Client Quickstart

This guide shows the smallest useful WebSocket workflow: start the client, subscribe to market data, consume an event, and shut down cleanly.

The exact contract ID used below is only an example. Replace it with a valid IBKR `conid` for the instrument you want to subscribe to.

## Prerequisites

Before using the WebSocket client, make sure that:

- IBKR Client Portal Gateway is running or that you have your OAuth credentials
- you know the IBKR account ID and contract ID you want to use

For local Client Portal Gateway usage, IBind normally connects to the local Gateway URL at port 5000. If your setup uses custom host, port, certificates, or OAuth, configure those before starting the WebSocket client.

## Minimal example

```python
from ibind import QueueSink, IbkrWsClientV2, MarketDataSubscription, snapshot_keys_to_ids, events

# Enables queue-based consumption
sink = QueueSink()

# Initialise the client
ws_client = IbkrWsClientV2(account_id='[YOUR_ACCOUNT_ID]', sinks=[sink])

# Start the client
ws_client.start()

# Create the subscription intent object
subscription = MarketDataSubscription(
    conids=['265598'], # AAPL
    fields=snapshot_keys_to_ids(['last_price', 'bid_price', 'ask_price']), # convert fields to numeric representation
)

# Register the intent with the client
handle = ws_client.subscribe(subscription)

# Wait for the first event
event = sink.get(events.MarketData, block=True, timeout=30)
print(event)
    
# Shutdown gracefully
ws_client.shutdown()
```

## Explanation

1. `QueueSink` will be used to store events into thread-safe queues, available for consumption by your code later.
2. `ws_client.start` starts the WebSocket runtime. It starts necessary threads, opens the WebSocket connection and prepares the client to send subscriptions.
3. `MarketDataSubscription` creates an intent to subscribe to Market Data topic for `conid='265598'` (ticker AAPL), using `snapshot_keys_to_ids` to convert human-readable fields into their numerical representation expected by IBKR.
4. `ws_client.subscribe` registers the subscription intent with the client. The runtime thread will pick it up on its next cycle and fulfill the subscription by sending the appropriate payload to IBKR. Once first data begins to arrive, the subscription will be marked as active. A `SubscriptionHandle` is returned and can be waited on using `.wait()` to ensure the subscription is active before proceeding.
5. `sink.get` blocks for up to 30 seconds for the first event to arrive. The `event.MarketData` event type passed specifies which queue we want to acquire the data from.
6. `ws_client.shutdown` stops the runtime and closes the underlying WebSocket connection.

## Consuming multiple events

```python
while True:
    while not sink.empty(events.MarketData):
        event = sink.get(events.MarketData)
        print(event)

    time.sleep(0.5)
```

In production code, replace `print(event)` with your own event handling logic. For example, you may update an in-memory market data cache, request a strategy to run with the new data, or store selected events for debugging.


## Callback example

```python
from ibind import CallbackSink, IbkrWsClientV2, MarketDataSubscription, snapshot_keys_to_ids, events

def on_market_data(event: events.MarketData):
    print(event)

sink = CallbackSink()
sink.on(events.MarketData, on_market_data) # can be called before or after passing the sink to the client
    
ws_client = IbkrWsClientV2(account_id='[YOUR_ACCOUNT_ID]', sinks=[sink])
ws_client.start()

subscription = MarketDataSubscription(
    conids=['265598'],
    fields=snapshot_keys_to_ids(['last_price', 'bid_price', 'ask_price']),
)

ws_client.subscribe(subscription)
...

```

Callbacks are invoked in order they're added to the sink and in the order in which the events are received. Invocation is synchronously carried out from a single dedicated thread. This means later callbacks will not run until earlier ones complete. Use QueueSink with dedicated reading threads if your application requires events to be consumed independently of each other.

If your application code is consuming events slower than they're received from IBKR, the WebSocket client will start dropping them after a certain number is reached to avoid out of memory errors. For more see [Sinks](./core-concepts/sinks.md).

## Checking Lifecycle and Subscription States 


```python
from ibind import CallbackSink, IbkrWsClientV2, events

def on_authenticated(event: events.WsAuthenticated):
    print('WebSocket client ready')

def on_degraded(event: events.WsDegraded):
    print('Warning: WebSocket connection degraded')

def on_stopped(event: events.WsStopped):
    print('WebSocket client stopped')

sink = CallbackSink()
sink.on(events.WsAuthenticated, on_authenticated)
sink.on(events.WsDegraded, on_degraded)
sink.on(events.WsStopped, on_stopped)
    
ws_client = IbkrWsClientV2(account_id='[YOUR_ACCOUNT_ID]', sinks=[sink])

ws_client.start()
# Should print 'WebSocket client ready'

time.sleep(5)

ws_client.shutdown()
# Should print 'WebSocket client stopped'
```

A range of lifecycle events allows your application respond to changes in connection state. See [Runtime and Lifecycle](./core-concepts/runtime-and-lifecycle.md).

Likewise you can react to changes in subscription statuses:

```python
def on_subscription_updated(event: events.SubscriptionUpdated):
    print(f'{event.subscription} status changed to {event.status})
    
sink.on(events.SubscriptionUpdated, on_subscription_updated)
```

For more, see [Subscription Interface](./core-concepts/subscriptions.md).
