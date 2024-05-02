# Table of Contents

* [IbkrWsKey](#client.ibkr_ws_client.IbkrWsKey)
  * [from\_channel](#client.ibkr_ws_client.IbkrWsKey.from_channel)
  * [channel](#client.ibkr_ws_client.IbkrWsKey.channel)
* [IbkrSubscriptionProcessor](#client.ibkr_ws_client.IbkrSubscriptionProcessor)
  * [make\_subscribe\_payload](#client.ibkr_ws_client.IbkrSubscriptionProcessor.make_subscribe_payload)
  * [make\_unsubscribe\_payload](#client.ibkr_ws_client.IbkrSubscriptionProcessor.make_unsubscribe_payload)
* [IbkrWsClient](#client.ibkr_ws_client.IbkrWsClient)
  * [\_\_init\_\_](#client.ibkr_ws_client.IbkrWsClient.__init__)
  * [check\_health](#client.ibkr_ws_client.IbkrWsClient.check_health)
  * [server\_ids](#client.ibkr_ws_client.IbkrWsClient.server_ids)
  * [new\_queue\_accessor](#client.ibkr_ws_client.IbkrWsClient.new_queue_accessor)
  * [subscribe](#client.ibkr_ws_client.IbkrWsClient.subscribe)
  * [unsubscribe](#base.subscription_controller.SubscriptionController.unsubscribe)
  * [modify\_subscription](#base.subscription_controller.SubscriptionController.modify_subscription)
  * [recreate\_subscriptions](#base.subscription_controller.SubscriptionController.recreate_subscriptions)
  * [hard\_reset](#base.ws_client.WsClient.hard_reset)
  * [disconnect](#base.ws_client.WsClient.disconnect)
  * [start](#base.ws_client.WsClient.start)
  * [shutdown](#base.ws_client.WsClient.shutdown)
  * [check\_ping](#base.ws_client.WsClient.check_ping)

<a id="base.queue_controller.QueueAccessor"></a>

## QueueAccessor

Provides access to a queue with an associated key.

This class encapsulates a queue and provides methods to interact with it, such as retrieving items
and checking if the queue is empty. It is generic and can be associated with a key of any type.

Constructor Parameters:
queue (Queue): The queue to be accessed.
key (T): The key associated with this queue accessor.

<a id="client.ibkr_ws_client.IbkrWsKey"></a>

## IbkrWsKey

https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#websockets

Enumeration of key types for Interactive Brokers WebSocket channels.

This Enum class represents various types of data or subscription channels for Interactive Brokers WebSocket API.

Subscriptions Enums:
* ACCOUNT_SUMMARY: Represents the 'ACCOUNT_SUMMARY' subscription.
* ACCOUNT_LEDGER: Represents the 'ACCOUNT_LEDGER' subscription.
* MARKET_DATA: Represents the 'MARKET_DATA' subscription.
* MARKET_HISTORY: Represents the 'MARKET_HISTORY' subscription.
* PRICE_LADDER: Represents the 'PRICE_LADDER' subscription.
* ORDERS: Represents the 'ORDERS' subscription.
* PNL: Represents the 'PNL' subscription.
* TRADES: Represents the 'TRADES' subscription.

Unsolicited Enums:
* ACCOUNT_UPDATES: Represents the 'ACCOUNT_UPDATES' unsolicited message.
* AUTHENTICATION: Represents the 'AUTHENTICATION' unsolicited message.
* BULLETINS: Represents the 'BULLETINS' unsolicited message.
* ERROR: Represents the 'ERROR' unsolicited message.
* SYSTEM: Represents the 'SYSTEM' unsolicited message.
* NOTIFICATIONS: Represents the 'NOTIFICATIONS' unsolicited message.

<a id="client.ibkr_ws_client.IbkrWsKey.from_channel"></a>

### from\_channel

```python
@classmethod
def from_channel(cls, channel)
```

Converts a channel string to its corresponding IbkrWsKey enum member.

Arguments:

- `channel` _str_ - The channel string to be converted.
  

Returns:

- `IbkrWsKey` - The corresponding IbkrWsKey enum member.
  

Raises:

- `ValueError` - If no enum member is associated with the provided channel.

<a id="client.ibkr_ws_client.IbkrWsKey.channel"></a>

### channel

```python
@property
def channel()
```

Gets the channel string associated with the enum member.

Returns:

- `str` - The channel string corresponding to the enum member.

<a id="client.ibkr_ws_client.IbkrSubscriptionProcessor"></a>

## IbkrSubscriptionProcessor

A subscription processor for Interactive Brokers WebSocket channels. This class extends the SubscriptionProcessor.

<a id="client.ibkr_ws_client.IbkrSubscriptionProcessor.make_subscribe_payload"></a>

### make\_subscribe\_payload

```python
def make_subscribe_payload(channel: str, data: dict = None) -> str
```

Constructs a subscription payload for a specific channel with optional data.

The payload format is a combination of a prefix 's', the channel identifier, and the JSON-serialized
data if provided.

Arguments:

- `channel` _str_ - The channel identifier to subscribe to.
- `data` _dict, optional_ - Additional data to be included in the subscription payload. Defaults to None.
  

Returns:

- `str` - A formatted subscription payload for the Interactive Brokers WebSocket.
  

**Example**:

  - With data: make_subscribe_payload('md', {'foo': 'bar'}) returns "smd+{"foo": "bar"}"
  - Without data: make_subscribe_payload('md') returns "smd"

<a id="client.ibkr_ws_client.IbkrSubscriptionProcessor.make_unsubscribe_payload"></a>

### make\_unsubscribe\_payload

```python
def make_unsubscribe_payload(channel: str, data: dict = None) -> str
```

Constructs an unsubscription payload for a specific channel with optional data.

The payload format is a combination of a prefix 'u', the channel identifier, and the JSON-serialized
data. If data is not provided, an empty dictionary is used.

Arguments:

- `channel` _str_ - The channel identifier to unsubscribe from.
- `data` _dict, optional_ - Additional data to be included in the unsubscription payload. Defaults to None.
  

Returns:

- `str` - A formatted unsubscription payload for the Interactive Brokers WebSocket.
  

**Example**:

  - With data: make_unsubscribe_payload('md', {'foo': 'bar'}) returns "umd+{"foo": "bar"}"
  - Without data: make_unsubscribe_payload('md') returns "umd+{}"

<a id="client.ibkr_ws_client.IbkrWsClient"></a>

## IbkrWsClient

A WebSocket client for Interactive Brokers, extending WsClient.

This class handles WebSocket communications specific to Interactive Brokers, managing subscriptions,
message processing, and maintaining the health of the WebSocket connection.

See: https://interactivebrokers.github.io/cpwebapi/websockets

<a id="client.ibkr_ws_client.IbkrWsClient.__init__"></a>

### \_\_init\_\_

```python
def __init__(
        ibkr_client: IbkrClient,
        account_id: str = var.IBIND_ACCOUNT_ID,
        url: str = var.IBIND_WS_URL,
        host: str = 'localhost',
        port: str = '5000',
        base_route: str = '/v1/api/ws',
        SubscriptionProcessorClass: Type[
            SubscriptionProcessor] = IbkrSubscriptionProcessor,
        QueueControllerClass: Type[QueueController] = QueueController[
            IbkrWsKey],
        log_raw_messages: bool = var.IBIND_WS_LOG_RAW_MESSAGES,
        unsolicited_channels_to_be_queued: List[IbkrWsKey] = None,
        ping_interval: int = var.IBIND_WS_PING_INTERVAL,
        max_ping_interval: int = var.IBIND_WS_MAX_PING_INTERVAL,
        timeout: float = var.IBIND_WS_TIMEOUT,
        restart_on_close: bool = True,
        restart_on_critical: bool = True,
        max_connection_attempts: int = 10,
        cacert: Union[str, bool] = var.IBIND_CACERT,
        subscription_retries: int = var.IBIND_WS_SUBSCRIPTION_RETRIES,
        subscription_timeout: float = var.IBIND_WS_SUBSCRIPTION_TIMEOUT
) -> None
```

Initializes the IbkrWsClient, an Interactive Brokers WebSocket client.

Sets up the client with necessary configurations for connecting to and interacting with the Interactive Brokers WebSocket.

Arguments:

- `url` _str_ - URL for the Interactive Brokers WebSocket.
- `ibkr_client` _IbkrClient_ - An instance of the IbkrClient for related operations.
- `account_id` _str_ - Account ID for subscription management.
- `SubscriptionProcessorClass` _Type[SubscriptionProcessor]_ - The class to process subscription payloads.
- `QueueControllerClass` _Type[QueueController[IbkrWsKey]], optional_ - The class to manage message queues. Defaults to QueueController[IbkrWsKey].
- `unsolicited_channels_to_be_queued` _List[IbkrWsKey], optional_ - List of unsolicited channels to be queued. Defaults to None.
  
  
  Inherited parameters from WsClient:
  
- `timeout` _float, optional_ - Timeout for waiting on operations like connection and shutdown. Defaults to _DEFAULT_TIMEOUT.
- `restart_on_close` _bool, optional_ - Flag to restart the connection if it closes unexpectedly. Defaults to True.
- `restart_on_critical` _bool, optional_ - Flag to restart the connection on critical errors. Defaults to True.
- `ping_interval` _int, optional_ - Interval in seconds for sending pings to keep the connection alive. Defaults to _DEFAULT_PING_INTERVAL.
- `max_ping_interval` _int, optional_ - Maximum interval in seconds to wait for a ping response. Defaults to _DEFAULT_MAX_PING_INTERVAL.
- `max_connection_attempts` _int, optional_ - Maximum number of attempts for connecting to the WebSocket. Defaults to 10.
- `cacert` _Union[str, bool], optional_ - Path to the CA certificate file for SSL verification, or False to disable SSL verification. Defaults to False.
- `subscription_retries` _int, optional_ - Number of retries for subscription requests. Defaults to 5.
- `subscription_timeout` _float, optional_ - Timeout for subscription requests. Defaults to 2.

<a id="client.ibkr_ws_client.IbkrWsClient.check_health"></a>

### check\_health

```python
def check_health() -> bool
```

Checks the overall health of the IbkrWsClient and its WebSocket connection.

Verifies the health of the WebSocket connection by checking ping responses and heartbeat messages
from Interactive Brokers. If the connection is found to be unhealthy, a hard reset is initiated.

Returns:

- `bool` - True if the WebSocket connection is healthy, False otherwise.

<a id="client.ibkr_ws_client.IbkrWsClient.server_ids"></a>

### server\_ids

```python
def server_ids(key: IbkrWsKey)
```

Retrieves the server IDs associated with a specific IbkrWsKey.

Each type of data subscription (identified by IbkrWsKey) may have an associated server ID. This method
returns the server IDs for the given subscription type.

Arguments:

- `key` _IbkrWsKey_ - The key representing the subscription type.
  

Returns:

  Optional[Dict[str, int]: The server IDs associated with the given key, or None if no server IDs are available.

<a id="client.ibkr_ws_client.IbkrWsClient.new_queue_accessor"></a>

### new\_queue\_accessor

```python
def new_queue_accessor(key: IbkrWsKey) -> QueueAccessor[IbkrWsKey]
```

Creates a new queue accessor for a specified IbkrWsKey.

Utilizes the internal queue controller to create an accessor for a queue associated with a specific
IbkrWsKey. This accessor facilitates interaction with the queue for that particular type of subscription.

Arguments:

- `key` _IbkrWsKey_ - The key representing the subscription type for which the queue accessor is created.
  

Returns:

- `QueueAccessor[IbkrWsKey]` - A queue accessor for the specified key.

<a id="client.ibkr_ws_client.IbkrWsClient.subscribe"></a>

### subscribe

```python
def subscribe(channel: str,
              data: dict = None,
              needs_confirmation: bool = True,
              subscription_processor: SubscriptionProcessor = None) -> bool
```

Subscribes to a specific channel in the Interactive Brokers WebSocket.

Initiates a subscription to a given channel, optionally including additional data in the subscription
request. The method delegates the subscription logic to the SubscriptionController.

From docs: "To receive all orders for the current day the endpoint /iserver/account/orders can be used. It is advised to query all orders for the current day first before subscribing to live orders."

Arguments:

- `channel` _str_ - The channel to subscribe to.
- `data` _dict, optional_ - Additional data to be included in the subscription request. Defaults to None.
- `needs_confirmation` _bool, optional_ - Specifies whether the subscription requires confirmation from the server. Defaults to True.
- `subscription_processor` _SubscriptionProcessor, optional_ - The subscription processor to use instead of the
  default one if provided. Defaults to None.
  

Returns:

- `bool` - True if the subscription was successful, False otherwise.


### unsubscribe

```python
def unsubscribe(channel: str,
                data: dict = None,
                needs_confirmation: bool = False,
                subscription_processor: SubscriptionProcessor = None) -> bool
```

Unsubscribes from a specified channel.

Attempts to unsubscribe from a given channel using the WsClient. The method manages the
unsubscription logic, including sending the unsubscription payload and handling retries and timeouts.
The subscription status is updated accordingly within the class.

Arguments:

- `channel` _str_ - The name of the channel to unsubscribe from.
- `data` _dict, optional_ - Additional data to be included in the unsubscription request. Defaults to None.
- `needs_confirmation` _bool, optional_ - Specifies whether the unsubscription requires confirmation.
  Defaults to False.
- `subscription_processor` _SubscriptionProcessor, optional_ - The subscription processor to use instead of the
  default one if provided. Defaults to None.


Returns:

- `bool` - True if the unsubscription was successful, False otherwise.


Notes:

- If 'needs_confirmation' is False, the method sends the unsubscription request and assumes success.
- If 'needs_confirmation' is True, the method waits for confirmation before marking the unsubscription as successful.

<a id="base.subscription_controller.SubscriptionController.modify_subscription"></a>

### modify\_subscription

```python
def modify_subscription(
        channel: str,
        status: bool = UNDEFINED,
        data: dict = UNDEFINED,
        needs_confirmation: bool = UNDEFINED,
        subscription_processor: SubscriptionProcessor = UNDEFINED)
```

Modifies an existing subscription.

Updates the properties of an existing subscription. If a property is set to UNDEFINED, it remains unchanged.

Arguments:

- `channel` _str_ - The channel whose subscription is to be modified.
- `status` _bool, optional_ - The new status of the subscription. Set as UNDEFINED to leave unchanged.
- `data` _dict, optional_ - The new data associated with the subscription. Set as UNDEFINED to leave unchanged.
- `needs_confirmation` _bool, optional_ - Specifies whether the subscription requires confirmation.
  Set as UNDEFINED to leave unchanged.
- `subscription_processor` _SubscriptionProcessor, optional_ - The subscription processor to use instead of the
  default one if provided. Defaults to None.


Raises:

- `KeyError` - If the specified channel does not have an existing subscription.

<a id="base.subscription_controller.SubscriptionController.recreate_subscriptions"></a>

### recreate\_subscriptions

```python
def recreate_subscriptions()
```

Re-subscribes to all currently stored subscriptions.

Iterates over all currently stored subscriptions and attempts to re-subscribe to each. Useful in scenarios
where a connection reset or similar event necessitates re-establishing subscriptions.


<a id="base.ws_client.WsClient.hard_reset"></a>

### hard\_reset

```python
def hard_reset(restart: bool = False) -> None
```

Performs a hard reset of the WebSocket connection.

This method forcefully closes the current WebSocketApp connection and optionally restarts it. It is
used to handle scenarios where the connection is unresponsive or encounters a critical error.

Arguments:

- `restart` _bool, optional_ - Specifies whether to restart the WebSocketApp connection after resetting.
  Defaults to False.


Notes:

- Closes the current WebSocketApp connection, if any, and clears related resources.
- If the WebSocketApp is unresponsive or cannot be closed, it will be abandoned and the connection will be reset.
- If 'restart' is True, the method attempts to re-establish a new WebSocketApp connection after resetting.

<a id="base.ws_client.WsClient.disconnect"></a>

### disconnect

```python
def disconnect()
```

Disconnects the WebSocketApp connection.

This method closes the active WebSocketApp connection if it exists. If the WebSocketApp is not
currently connected, it sets the connected status to False.

<a id="base.ws_client.WsClient.start"></a>

### start

```python
def start() -> bool
```

Starts the WsClient and establishes the WebSocketApp connection.

This method sets the WsClient to running state and attempts to establish a WebSocketApp connection.
It returns the success status of the connection attempt.

Returns:

- `bool` - True if the WebSocketApp connection was successfully established, False otherwise.


Notes:

- The success of the connection is determined by the ability to establish and maintain the WebSocketApp connection.

<a id="base.ws_client.WsClient.shutdown"></a>

### shutdown

```python
def shutdown()
```

Shuts down the WsClient and its WebSocketApp connection.

This method stops the WsClient and closes the active WebSocketApp connection, if any.
It ensures that all resources are cleanly released.

Notes:

- The method sets the WsClient to a non-running state and closes the WebSocketApp connection.
- If the WebSocketApp connection is active, it is disconnected.

<a id="base.ws_client.WsClient.check_ping"></a>

### check\_ping

```python
def check_ping() -> bool
```

Checks the last ping response time of the WebSocketApp connection.

Verifies whether the last ping response from the WebSocketApp was within the acceptable time interval
defined by 'max_ping_interval' parameter. If the last ping response exceeds this interval, a hard reset of the connection is triggered.

Returns:

- `bool` - True if the last ping was within the acceptable interval or if the WebSocketApp is not connected,
  False if the ping interval was exceeded and a hard reset was initiated.


Notes:

- A ping interval exceeding 'max_ping_interval' indicates potential issues with the WebsocketApp connection.
