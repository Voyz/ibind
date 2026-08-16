# Table of Contents

* [ibkr\_ws\_client\_v2](#ibkr_ws_v2.ibkr_ws_client_v2)
  * [IbkrWsClientV2](#ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2)
    * [\_\_init\_\_](#ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.__init__)
    * [start](#ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.start)
    * [shutdown](#ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.shutdown)
    * [hard\_reset](#ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.hard_reset)
    * [reset\_websocket\_app](#ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.reset_websocket_app)
    * [subscribe](#ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.subscribe)
    * [unsubscribe](#ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.unsubscribe)
    * [get\_binding\_status](#ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.get_binding_status)
    * [get\_server\_id](#ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.get_server_id)
    * [wait\_all](#ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.wait_all)
    * [is\_running](#ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.is_running)
    * [get\_state](#ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.get_state)
    * [is\_authenticated](#ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.is_authenticated)
    * [is\_subscription\_active](#ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.is_subscription_active)
    * [tic](#ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.tic)
* [ws\_subscriptions](#ws_v2.ws_subscriptions)
  * [Subscription](#ws_v2.ws_subscriptions.Subscription)
    * [topic](#ws_v2.ws_subscriptions.Subscription.topic)
    * [subscribe\_payload](#ws_v2.ws_subscriptions.Subscription.subscribe_payload)
    * [unsubscribe\_payload](#ws_v2.ws_subscriptions.Subscription.unsubscribe_payload)
    * [confirms\_subscribe](#ws_v2.ws_subscriptions.Subscription.confirms_subscribe)
    * [confirms\_unsubscribe](#ws_v2.ws_subscriptions.Subscription.confirms_unsubscribe)
    * [binding\_key](#ws_v2.ws_subscriptions.Subscription.binding_key)
  * [BindingStatus](#ws_v2.ws_subscriptions.BindingStatus)
    * [ACTIVE](#ws_v2.ws_subscriptions.BindingStatus.ACTIVE)
    * [UNSUBSCRIBED](#ws_v2.ws_subscriptions.BindingStatus.UNSUBSCRIBED)
  * [SubscriptionUpdated](#ws_v2.ws_subscriptions.SubscriptionUpdated)
  * [Binding](#ws_v2.ws_subscriptions.Binding)
    * [done](#ws_v2.ws_subscriptions.Binding.done)
    * [reset](#ws_v2.ws_subscriptions.Binding.reset)
  * [SubscriptionHandle](#ws_v2.ws_subscriptions.SubscriptionHandle)
    * [binding\_key](#ws_v2.ws_subscriptions.SubscriptionHandle.binding_key)
    * [status](#ws_v2.ws_subscriptions.SubscriptionHandle.status)
    * [active](#ws_v2.ws_subscriptions.SubscriptionHandle.active)
    * [unsubscribed](#ws_v2.ws_subscriptions.SubscriptionHandle.unsubscribed)
    * [done](#ws_v2.ws_subscriptions.SubscriptionHandle.done)
    * [wait](#ws_v2.ws_subscriptions.SubscriptionHandle.wait)
    * [unsubscribe](#ws_v2.ws_subscriptions.SubscriptionHandle.unsubscribe)

<a id="ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2"></a>

## IbkrWsClientV2

WebSocket client for Interactive Brokers market data and account updates.

Manages subscriptions to IBKR WebSocket topics, handles authentication,
and routes incoming events to registered sinks. Supports both OAuth and
Gateway-based authentication.

<a id="ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.__init__"></a>

### \_\_init\_\_

```python
def __init__(account_id: str = var.IBIND_ACCOUNT_ID,
             url: str = var.IBIND_WS_URL,
             host: str = '127.0.0.1',
             port: str = '5000',
             base_route: str = '/v1/api/ws',
             ibkr_client: IbkrClient = None,
             use_oauth: bool = var.IBIND_USE_OAUTH,
             access_token: str = var.IBIND_OAUTH1A_ACCESS_TOKEN,
             cacert: Union[str, bool] = var.IBIND_CACERT,
             cycle_interval: float = _DEFAULT_CYCLE_INTERVAL,
             sink: EventSink = None,
             router: Router = None,
             subscription_resolver: SubscriptionResolver = None,
             synchronous_output_events: bool = False)
```

Initialize the IBKR WebSocket client.

Arguments:

- `account_id` _str_ - IBKR account ID. Default: None.
- `url` _str_ - WebSocket server URL. Default: None.
- `host` _str_ - Server host for local connections. Default: '127.0.0.1'.
- `port` _str_ - Server port. Default: '5000'.
- `base_route` _str_ - API base route. Default: '/v1/api/ws'.
- `ibkr_client` _IbkrClient, optional_ - REST client for authentication. If None, creates new instance.
- `use_oauth` _bool_ - Whether to use OAuth authentication. Default: False.
- `access_token` _str_ - OAuth access token. Default: None.
- `cacert` _Union[str, bool]_ - CA certificate for SSL verification. Default: False.
- `cycle_interval` _float_ - Event loop cycle interval in seconds. Default: 0.25.
- `sink` _EventSink, optional_ - Event sink for output events. Default: NoopSink.
- `router` _Router, optional_ - Event router. Default: IbkrRouter.
- `subscription_resolver` _SubscriptionResolver, optional_ - Subscription resolver. Default: IbkrSubscriptionResolver.
- `synchronous_output_events` _bool_ - If True, emit events synchronously from runtime thread. Default: False.

<a id="ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.start"></a>

### start

```python
def start() -> bool
```

Start the WebSocket client.

Returns:

- `bool` - True if start was successful, False otherwise.

<a id="ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.shutdown"></a>

### shutdown

```python
def shutdown() -> bool
```

Shutdown the WebSocket client.

Returns:

- `bool` - True if shutdown was successful, False otherwise.

<a id="ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.hard_reset"></a>

### hard\_reset

```python
def hard_reset() -> bool
```

Perform a hard reset of the WebSocket client, stopping and restarting the runtime.

Returns:

- `bool` - True if reset completed successfully, False if stop failed.

<a id="ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.reset_websocket_app"></a>

### reset\_websocket\_app

```python
def reset_websocket_app()
```

Reset the underlying WebSocketApp.

<a id="ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.subscribe"></a>

### subscribe

```python
def subscribe(subscription: Subscription) -> SubscriptionHandle
```

Subscribe to a WebSocket topic.

Arguments:

- `subscription` _Subscription_ - Subscription object specifying the topic and parameters.
  

Returns:

- `SubscriptionHandle` - Handle to track subscription status and wait for completion.
  

Notes:

  - This method is non-blocking and idempotent.

<a id="ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.unsubscribe"></a>

### unsubscribe

```python
def unsubscribe(subscription: Subscription) -> SubscriptionHandle
```

Unsubscribe from a WebSocket topic.

Arguments:

- `subscription` _Subscription_ - Subscription object to unsubscribe from.
  

Returns:

- `SubscriptionHandle` - Handle to track unsubscription status.
  

Notes:

  - This method is non-blocking and idempotent.

<a id="ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.get_binding_status"></a>

### get\_binding\_status

```python
def get_binding_status(binding_key: str) -> BindingStatus
```

Get the status of a subscription binding.

Arguments:

- `binding_key` _str_ - Unique identifier for the subscription binding.
  

Returns:

- `BindingStatus` - Current status of the binding.

<a id="ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.get_server_id"></a>

### get\_server\_id

```python
def get_server_id(event_type: Type[IbkrTopicEvent], conid: str) -> str
```

Get the server ID for a given event type and contract ID.

This is primarily used for Market History subscriptions.

Arguments:

- `event_type` _Type[IbkrTopicEvent]_ - The event type to look up.
- `conid` _str_ - Contract ID.
  

Returns:

- `str` - The server ID associated with the event type and contract ID.

<a id="ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.wait_all"></a>

### wait\_all

```python
@ensure_list_arg('subscription_handles')
def wait_all(subscription_handles: OneOrMany[SubscriptionHandle],
             timeout_each: float | None = None) -> List[SubscriptionHandle]
```

Wait for multiple subscription handles to complete.

Returns an empty list if all handles completed successfully.

Arguments:

- `subscription_handles` _OneOrMany[SubscriptionHandle]_ - Single handle or list of handles to wait for.
- `timeout_each` _float | None_ - Maximum time to wait for each handle in seconds.
  If None, waits indefinitely for each handle.
  

Returns:

- `List[SubscriptionHandle]` - Handles that failed to complete within their
  individual timeout.

<a id="ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.is_running"></a>

### is\_running

```python
def is_running() -> bool
```

Check if the WebSocket runtime is running.

Returns:

- `bool` - True if runtime is running, False otherwise.

<a id="ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.get_state"></a>

### get\_state

```python
def get_state() -> WsState
```

Get the current state of the WebSocket client.

Returns:

- `WsState` - Current runtime state.

<a id="ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.is_authenticated"></a>

### is\_authenticated

```python
def is_authenticated() -> bool
```

Check if the WebSocket connection is authenticated.

Returns:

- `bool` - True if authenticated, False otherwise.

<a id="ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.is_subscription_active"></a>

### is\_subscription\_active

```python
def is_subscription_active(binding_key: str) -> Optional[bool]
```

Check if a subscription binding is currently active.

Arguments:

- `binding_key` _str_ - Unique identifier for the subscription binding.
  

Returns:

- `Optional[bool]` - True if active, False if inactive, None if binding not found.

<a id="ibkr_ws_v2.ibkr_ws_client_v2.IbkrWsClientV2.tic"></a>

### tic

```python
def tic()
```

Sends a tic request to the IBKR WebSocket server and waits for the response.

This method sends a 'tic' message to the server and waits for the server to update
the internal tic message with a new timestamp. It uses the 'lastAccessed' field
to detect when a fresh response has been received.

Returns:

- `dict` - The tic message dictionary containing server response data, or None if
  the send operation failed or the response timed out.

<a id="ws_v2.ws_subscriptions.Subscription"></a>

## Subscription

Base class for WebSocket subscriptions.

Immutable model defining subscription behaviour including payload generation,
confirmation requirements, and expiry settings. Subclasses implement specific
subscription types by overriding abstract methods.

Attributes:

- `expiry_seconds` _int | None_ - Time in seconds before subscription expires and
  requires renewal. None means no expiry. Default: None.

<a id="ws_v2.ws_subscriptions.Subscription.topic"></a>

### topic

```python
@property
def topic() -> str
```

Get the subscription topic identifier.

<a id="ws_v2.ws_subscriptions.Subscription.subscribe_payload"></a>

### subscribe\_payload

```python
def subscribe_payload() -> str
```

Generate the payload string to send for subscribing.

<a id="ws_v2.ws_subscriptions.Subscription.unsubscribe_payload"></a>

### unsubscribe\_payload

```python
def unsubscribe_payload() -> str
```

Generate the payload string to send for unsubscribing.

<a id="ws_v2.ws_subscriptions.Subscription.confirms_subscribe"></a>

### confirms\_subscribe

```python
@property
def confirms_subscribe() -> bool
```

Whether the server sends confirmation when subscription succeeds.

<a id="ws_v2.ws_subscriptions.Subscription.confirms_unsubscribe"></a>

### confirms\_unsubscribe

```python
@property
def confirms_unsubscribe() -> bool
```

Whether the server sends confirmation when unsubscription succeeds.

<a id="ws_v2.ws_subscriptions.Subscription.binding_key"></a>

### binding\_key

```python
def binding_key()
```

Get the unique key identifying this subscription binding.

<a id="ws_v2.ws_subscriptions.BindingStatus"></a>

## BindingStatus

Status of a subscription binding.

Tracks the lifecycle state of a subscription from initial registration through
activation, failure, or unsubscription.

<a id="ws_v2.ws_subscriptions.BindingStatus.ACTIVE"></a>

#### ACTIVE

subscription successful

<a id="ws_v2.ws_subscriptions.BindingStatus.UNSUBSCRIBED"></a>

#### UNSUBSCRIBED

unsubscription successful

<a id="ws_v2.ws_subscriptions.SubscriptionUpdated"></a>

## SubscriptionUpdated

Emitted when subscription status changes.

Attributes:

- `subscription` _Subscription_ - The subscription that changed.
- `binding_key` _str_ - The binding key of the subscription.
- `status` _BindingStatus_ - The new status of the subscription.
- `previous_status` _BindingStatus_ - The previous status of the subscription.

<a id="ws_v2.ws_subscriptions.Binding"></a>

## Binding

Internal state tracking for a subscription binding.

Maintains the desired intent (subscribe or unsubscribe), current status,
and retry state for subscription operations.

Attributes:

- `subscription` _Subscription_ - The subscription being tracked.
- `intent` _Literal[BindingStatus.ACTIVE, BindingStatus.UNSUBSCRIBED]_ - Desired state.
- `status` _BindingStatus_ - Current state. Default: BindingStatus.NEW.
- `attempts` _int_ - Number of attempts made. Default: 0.
- `last_attempt` _float_ - Timestamp of last attempt. Default: 0.

<a id="ws_v2.ws_subscriptions.Binding.done"></a>

### done

```python
@property
def done() -> bool
```

Whether the binding has reached its intended state.

<a id="ws_v2.ws_subscriptions.Binding.reset"></a>

### reset

```python
def reset()
```

Reset retry state to allow new attempts.

<a id="ws_v2.ws_subscriptions.SubscriptionHandle"></a>

## SubscriptionHandle

Handle for interacting with a subscription.

Provides methods to query subscription state, wait for completion, and unsubscribe.
Returned by subscribe/unsubscribe operations.

<a id="ws_v2.ws_subscriptions.SubscriptionHandle.binding_key"></a>

### binding\_key

```python
@property
def binding_key() -> str
```

Get the unique key identifying this subscription.

<a id="ws_v2.ws_subscriptions.SubscriptionHandle.status"></a>

### status

```python
@property
def status() -> BindingStatus
```

Get the current status of this subscription.

<a id="ws_v2.ws_subscriptions.SubscriptionHandle.active"></a>

### active

```python
@property
def active() -> bool
```

Whether the subscription is currently active.

<a id="ws_v2.ws_subscriptions.SubscriptionHandle.unsubscribed"></a>

### unsubscribed

```python
@property
def unsubscribed() -> bool
```

Whether the subscription has been unsubscribed.

<a id="ws_v2.ws_subscriptions.SubscriptionHandle.done"></a>

### done

```python
@property
def done() -> bool
```

Whether the subscription has reached its intended state.

<a id="ws_v2.ws_subscriptions.SubscriptionHandle.wait"></a>

### wait

```python
def wait(timeout: float | None = None) -> bool
```

Wait for the subscription to reach its intended state.

Arguments:

- `timeout` _float | None_ - Maximum time to wait in seconds, or indefinitely if None. Default: None.
  

Returns:

- `bool` - True if subscription reached intended state, False if timed out or failed.

<a id="ws_v2.ws_subscriptions.SubscriptionHandle.unsubscribe"></a>

### unsubscribe

```python
def unsubscribe() -> 'SubscriptionHandle'
```

Unsubscribe from this subscription.

Returns:

- `SubscriptionHandle` - This handle for chaining.
