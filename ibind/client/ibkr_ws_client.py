import json
import time
from collections import defaultdict
from enum import Enum
from typing import Union, Type, Dict

from websocket import WebSocketApp

from ibind import var
from ibind.base.queue_controller import QueueController, QueueAccessor
from ibind.base.subscription_controller import SubscriptionProcessor, SubscriptionController
from ibind.base.ws_client import WsClient
from ibind.client import ibkr_definitions
from ibind.client.ibkr_client import IbkrClient
from ibind.client.ibkr_utils import extract_conid
from ibind.support.logs import project_logger
from ibind.support.py_utils import TimeoutLock, UNDEFINED

_LOGGER = project_logger(__file__)


class IbkrWsKey(Enum):
    """
    Enumeration of key types for Interactive Brokers WebSocket channels.

    This Enum class represents various types of data or subscription channels for Interactive Brokers WebSocket API.

    Enum Members:
        TRADES: Represents the 'TRADES' subscription.
        MARKET_DATA: Represents the 'MARKET_DATA' subscription.
        MARKET_HISTORY: Represents the 'MARKET_HISTORY' subscription.
        ORDERS: Represents the 'ORDERS' subscription.
    """
    TRADES = 'TRADES'
    MARKET_DATA = 'MARKET_DATA'
    MARKET_HISTORY = 'MARKET_HISTORY'
    ORDERS = 'ORDERS'

    @classmethod
    def from_channel(cls, channel):
        """
         Converts a channel string to its corresponding IbkrWsKey enum member.

         Parameters:
             channel (str): The channel string to be converted.

         Returns:
             IbkrWsKey: The corresponding IbkrWsKey enum member.

         Raises:
             ValueError: If no enum member is associated with the provided channel.
         """
        channel_to_key = {
            'tr': IbkrWsKey.TRADES,
            'md': IbkrWsKey.MARKET_DATA,
            'mh': IbkrWsKey.MARKET_HISTORY,
            'or': IbkrWsKey.ORDERS,
        }
        if channel in channel_to_key:
            return channel_to_key[channel]
        raise ValueError(f"No enum member associated with channel '{channel}'")

    @property
    def channel(self):
        """
        Gets the channel string associated with the enum member.

        Returns:
            str: The channel string corresponding to the enum member.
        """
        return {
            IbkrWsKey.TRADES: 'tr',
            IbkrWsKey.MARKET_DATA: 'md',
            IbkrWsKey.MARKET_HISTORY: 'mh',
            IbkrWsKey.ORDERS: 'or',
        }[self]


class IbkrSubscriptionProcessor(SubscriptionProcessor):
    """
    A subscription processor for Interactive Brokers WebSocket channels. This class extends the SubscriptionProcessor.
    """

    def make_subscribe_payload(self, channel: str, data: dict = None) -> str:
        """
        Constructs a subscription payload for a specific channel with optional data.

        The payload format is a combination of a prefix 's', the channel identifier, and the JSON-serialized
        data if provided.

        Parameters:
            channel (str): The channel identifier to subscribe to.
            data (dict, optional): Additional data to be included in the subscription payload. Defaults to None.

        Returns:
            str: A formatted subscription payload for the Interactive Brokers WebSocket.

        Example:
            - With data: make_subscribe_payload('md', {'foo': 'bar'}) returns "smd+{"foo": "bar"}"
            - Without data: make_subscribe_payload('md') returns "smd"
        """
        payload = f"s{channel}"

        if data is not None or data == {}:
            payload += f"+{json.dumps(data)}"

        return payload

    def make_unsubscribe_payload(self, channel: str, data: dict = None) -> str:
        """
        Constructs an unsubscription payload for a specific channel with optional data.

        The payload format is a combination of a prefix 'u', the channel identifier, and the JSON-serialized
        data. If data is not provided, an empty dictionary is used.

        Parameters:
            channel (str): The channel identifier to unsubscribe from.
            data (dict, optional): Additional data to be included in the unsubscription payload. Defaults to None.

        Returns:
            str: A formatted unsubscription payload for the Interactive Brokers WebSocket.

        Example:
            - With data: make_unsubscribe_payload('md', {'foo': 'bar'}) returns "umd+{"foo": "bar"}"
            - Without data: make_unsubscribe_payload('md') returns "umd+{}"
        """
        data = {} if data is None else data
        return f'u{channel}+{json.dumps(data)}'


class IbkrWsClient(WsClient):
    """
    A WebSocket client for Interactive Brokers, extending WsClient.

    This class handles WebSocket communications specific to Interactive Brokers, managing subscriptions,
    message processing, and maintaining the health of the WebSocket connection.

    See: https://interactivebrokers.github.io/cpwebapi/websockets
    """

    def __init__(
            self,
            ibkr_client: IbkrClient,
            account_id: str = var.IBKR_ACCOUNT_ID,
            url: str = var.IBKR_WS_URL,
            SubscriptionProcessorClass: Type[SubscriptionProcessor] = IbkrSubscriptionProcessor,
            QueueControllerClass: Type[QueueController] = QueueController[IbkrWsKey],
            SubscriptionControllerClass: Type[SubscriptionController] = SubscriptionController,
            log_raw_messages: bool = var.IBKR_WS_LOG_RAW_MESSAGES,
            # subscription controller
            subscription_retries: int = var.IBKR_WS_SUBSCRIPTION_RETRIES,
            subscription_timeout: float = var.IBKR_WS_SUBSCRIPTION_TIMEOUT,
            # inherited
            ping_interval: int = var.IBKR_WS_PING_INTERVAL,
            max_ping_interval: int = var.IBKR_WS_MAX_PING_INTERVAL,
            timeout: float = var.IBKR_WS_TIMEOUT,
            restart_on_close: bool = True,
            restart_on_critical: bool = True,
            max_connection_attempts: int = 10,
            cacert: Union[str, bool] = var.IBKR_CACERT,
    ) -> None:
        """
        Initializes the IbkrWsClient, an Interactive Brokers WebSocket client.

        Sets up the client with necessary configurations for connecting to and interacting with the Interactive Brokers WebSocket.

        Parameters:
            url (str): URL for the Interactive Brokers WebSocket.
            ibkr_client (IbkrClient): An instance of the IbkrClient for related operations.
            account_id (str): Account ID for subscription management.
            SubscriptionProcessorClass (Type[SubscriptionProcessor]): The class to process subscription payloads.
            QueueControllerClass (Type[QueueController[IbkrWsKey]], optional): The class to manage message queues. Defaults to QueueController[IbkrWsKey].
            SubscriptionControllerClass (Type[SubscriptionController], optional): The class to control subscriptions. Defaults to SubscriptionController.


            # Subscription controller parameters:

            subscription_retries (int, optional): Number of retries for subscription requests. Defaults to IBKR_WS_SUBSCRIPTION_RETRIES.
            subscription_timeout (float, optional): Timeout for subscription requests. Defaults to IBKR_WS_SUBSCRIPTION_TIMEOUT.


            # Inherited parameters from WsClient:

            ping_interval, max_ping_interval, timeout, restart_on_close, restart_on_critical, max_connection_attempts, cacert
        """
        self._ibkr_client = ibkr_client
        self._account_id = account_id

        self._queue_controller = QueueControllerClass()
        self._subscription_processor = SubscriptionProcessorClass()
        self._subscription_controller = SubscriptionControllerClass(
            subscription_processor=self._subscription_processor,
            ws_client=self,
            subscription_retries=subscription_retries,
            subscription_timeout=subscription_timeout
        )
        self._log_raw_messages = log_raw_messages

        super().__init__(
            url=url,
            timeout=timeout,
            restart_on_close=restart_on_close,
            restart_on_critical=restart_on_critical,
            ping_interval=ping_interval,
            max_ping_interval=max_ping_interval,
            max_connection_attempts=max_connection_attempts,
            cacert=cacert,
        )

        self._operational_lock = TimeoutLock(60)

        self._queue_controller.register_queues(list(IbkrWsKey))

        self._logged_in = False
        self._last_heartbeat = 0
        self.server_id_conid_pairs: Dict[IbkrWsKey, Dict[str, int]] = defaultdict(dict)

    def _login(self):
        status = self._ibkr_client.tickle()
        session_id = status.data['session']
        payload = {'session': session_id}
        self.send_json(payload)

    def on_reconnect(self):
        self._logged_in = False
        self._subscription_controller.recreate_subscriptions()

    def _handle_trades_message(self, message: dict) -> None:
        self._queue_controller.put_to_queue(IbkrWsKey.from_channel('tr'), message['args'])

    def _handle_market_data_message(self, message: dict) -> None:
        """
        API will only return fields that were updated. If you are not receiving certain fields in the response - means that they remain unchanged.
        """
        if 'conid' not in message:  # pragma: no cover
            # sometimes the ticker message is just an empty update, we ignore it
            return

        result = {'conid': message['conid'], '_updated': message['_updated'], 'topic': message['topic']}
        for key, value in message.items():
            if key in ibkr_definitions.snapshot_by_id:
                result[ibkr_definitions.snapshot_by_id[key]] = value
        self._queue_controller.put_to_queue(IbkrWsKey.from_channel('md'), {message['conid']: result})

    def _handle_market_history_message(self, message: dict) -> None:
        mh_server_id_conid_pairs = self.server_id_conid_pairs[IbkrWsKey.MARKET_HISTORY]
        if 'serverId' in message and message['serverId'] not in mh_server_id_conid_pairs:
            mh_server_id_conid_pairs[message['serverId']] = extract_conid(message)

        self._queue_controller.put_to_queue(IbkrWsKey.from_channel('mh'), message)

    def _handle_orders_message(self, message: dict) -> None:
        self._queue_controller.put_to_queue(IbkrWsKey.from_channel('or'), message['args'])

    def _handle_subscribed_message(self, channel: str, message: dict):
        if channel.startswith('md'):  # market data
            self._handle_market_data_message(message)
        elif channel.startswith('or'):  # orders
            self._handle_orders_message(message)
        elif channel.startswith('tr'):  # trades
            self._handle_trades_message(message)
        elif channel.startswith('mh'):  # market history
            self._handle_market_history_message(message)
        else:
            return False

        return True

    def _handle_account(self, message, data):
        if 'accounts' not in data:
            _LOGGER.error(f'{self}: Unknown account response: {message}')
            return

        if self._account_id not in data['accounts']:
            _LOGGER.error(f'{self}: Account ID mismatch: expected={self._account_id}, received={data["accounts"]}')

    def _handle_bulletin(self, message):  # pragma: no cover
        ...

    def _handle_notification(self, data):  # pragma: no cover
        for notification in data:
            _LOGGER.info(f'{self}: IBKR notification: {notification}')

    def _handle_status(self, message, data):
        if 'authenticated' not in data:
            _LOGGER.info(f'{self}: Unknown status response: {message}')
            return

        if data.get('authenticated') == False:
            _LOGGER.error(f'{self}: Status unauthenticated: {data}')
            self._login()
        else:
            self._logged_in = True

    def _handle_error(self, message):
        _LOGGER.error(f'{self}: on_message error: {message}')

    def _handle_market_history_unsubscribe(self, data):
        server_id = data['message'].split('Unsubscribed ')[-1]
        mh_server_id_conid_pairs = self.server_id_conid_pairs[IbkrWsKey.MARKET_HISTORY]
        if server_id in mh_server_id_conid_pairs:
            conid = mh_server_id_conid_pairs[server_id]
            _LOGGER.info(f'{self}: Received unsubscribing confirmation for server_id={server_id!r}/conid={conid!r}.')
            if conid is None:
                _LOGGER.warning(f'{self}: Unknown conid={conid!r}. Cannot mark the subscription as unsubscribed.')
                return

            self._subscription_controller.modify_subscription(f'mh+{conid}', status=False)
        else:
            _LOGGER.warning(f'{self}: Received unsubscribing confirmation for unknown server_id={server_id!r}. Existing server_ids: {mh_server_id_conid_pairs}')

    def _handle_message_without_topic(self, message: dict):
        if 'message' in message:
            if 'Unsubscribed' in message['message']:
                self._handle_market_history_unsubscribe(message)
                return
            elif message['message'] == 'waiting for session':
                _LOGGER.info(f'{self}: Waiting for an active IBKR session.')
                return

        _LOGGER.error(f'{self}: Unrecognised message without a topic: {message}')

    def _preprocess_raw_message(self, raw_message: str):
        message = json.loads(raw_message)
        # print(message)
        topic = message.get('topic', UNDEFINED)

        if topic is UNDEFINED:
            return message, None, None, None, None

        data = message.get('args', {})

        # subscribed is the indicator of whether it was a subscription or unsubscription, defined by the first letter
        # channel is the actual channel we received the information about
        subscribed, channel = topic[0], topic[1:]

        return message, topic, data, subscribed, channel

    def on_message(self, wsa: WebSocketApp, raw_message: str) -> None:
        if self._log_raw_messages:
            _LOGGER.debug(f'{self}: Raw message: {raw_message}')
        message, topic, data, subscribed, channel = self._preprocess_raw_message(raw_message)

        if 'error' in message:
            self._handle_error(message)

        elif topic is None:
            # in general most message should carry a topic, other than for few exceptions
            self._handle_message_without_topic(message)

        elif topic == 'system':
            if 'hb' in message:
                self._last_heartbeat = message['hb']

        elif topic == 'act':
            self._handle_account(message, data)

        elif topic == 'blt':
            self._handle_bulletin(message)

        elif topic == 'ntf':
            self._handle_notification(data)

        elif topic == 'sts':
            self._handle_status(message, data)

        elif topic == 'error':
            _LOGGER.error(f'{self}: Error message:  {message}')

        elif self._subscription_controller.has_subscription(channel):
            if not self._subscription_controller.is_subscription_active(channel):
                self._subscription_controller.modify_subscription(channel, status=True)

            if not self._handle_subscribed_message(channel, message):
                _LOGGER.error(f'{self}: Channel "{channel}" subscribed but lacking a handler. Message: {message}')

        else:
            if self._handle_subscribed_message(channel, message):
                _LOGGER.warning(f'{self}: Handled a channel "{channel}" message that is missing a subscription. Message: {message}')
            else:
                _LOGGER.error(f'{self}: Topic "{topic}" unrecognised. Message: {message}')

    def on_close(self, wsa: WebSocketApp, close_status_code, close_msg):
        self._subscription_controller.invalidate_subscriptions()

    def check_health(self) -> bool:
        """
        Checks the overall health of the IbkrWsClient and its WebSocket connection.

        Verifies the health of the WebSocket connection by checking ping responses and heartbeat messages
        from Interactive Brokers. If the connection is found to be unhealthy, a hard reset is initiated.

        Returns:
            bool: True if the WebSocket connection is healthy, False otherwise.
        """
        if self._wsa is None:
            return True

        if not self.check_ping():
            return False

        if self._last_heartbeat == 0:
            return True

        diff = abs(time.time() - self._last_heartbeat / 1000)
        if diff > self._max_ping_interval:
            _LOGGER.warning(f'{self}: Last IBKR heartbeat happened {diff:.2f} seconds ago, exceeding the max ping interval of {self._max_ping_interval}. Restarting.')
            self.hard_reset(restart=True)
            return False

        return True

    def server_ids(self, key: IbkrWsKey):  # pragma: no cover
        """
        Retrieves the server IDs associated with a specific IbkrWsKey.

        Each type of data subscription (identified by IbkrWsKey) may have an associated server ID. This method
        returns the server IDs for the given subscription type.

        Parameters:
            key (IbkrWsKey): The key representing the subscription type.

        Returns:
            Optional[Dict[str, int]: The server IDs associated with the given key, or None if no server IDs are available.
        """
        return self.server_id_conid_pairs[key]

    def new_queue_accessor(self, key: IbkrWsKey) -> QueueAccessor[IbkrWsKey]:  # pragma: no cover
        """
        Creates a new queue accessor for a specified IbkrWsKey.

        Utilizes the internal queue controller to create an accessor for a queue associated with a specific
        IbkrWsKey. This accessor facilitates interaction with the queue for that particular type of subscription.

        Parameters:
            key (IbkrWsKey): The key representing the subscription type for which the queue accessor is created.

        Returns:
            QueueAccessor[IbkrWsKey]: A queue accessor for the specified key.
        """
        return self._queue_controller.new_queue_accessor(key)

    def subscribe(
            self,
            channel: str,
            data: dict = None,
            needs_confirmation: bool = True,
            subscription_processor: SubscriptionProcessor = None,
    ) -> bool:  # pragma: no cover
        """
        Subscribes to a specific channel in the Interactive Brokers WebSocket.

        Initiates a subscription to a given channel, optionally including additional data in the subscription
        request. The method delegates the subscription logic to the SubscriptionController.

        Parameters:
            channel (str): The channel to subscribe to.
            data (dict, optional): Additional data to be included in the subscription request. Defaults to None.
            needs_confirmation (bool, optional): Specifies whether the subscription requires confirmation from the server. Defaults to True.
            subscription_processor (SubscriptionProcessor, optional): The subscription processor to use instead of the
                                                                      default one if provided. Defaults to None.

        Returns:
            bool: True if the subscription was successful, False otherwise.
        """
        if channel == 'or':
            if not self._ibkr_client.check_health():
                return False
            self._ibkr_client.get_live_orders(force=True)
            self._ibkr_client.get_live_orders()
        return self._subscription_controller.subscribe(channel, data, needs_confirmation, subscription_processor)

    def unsubscribe(
            self,
            channel: str,
            data: dict = None,
            needs_confirmation: bool = False,
            subscription_processor: SubscriptionProcessor = None,
    ) -> bool:  # pragma: no cover
        """
        Unsubscribes from a specific channel in the Interactive Brokers WebSocket.

        Initiates an unsubscription request for a given channel, optionally including additional data. Interactive Brokers
        WebSocket typically does not send unsubscription confirmations, hence by default confirmation is not expected, and we assume it always succeeds.

        Parameters:
            channel (str): The channel to unsubscribe from.
            data (dict, optional): Additional data to be included in the unsubscription request. Defaults to None.
            needs_confirmation (bool, optional): Specifies whether the unsubscription requires confirmation from the server. Defaults to False.
            subscription_processor (SubscriptionProcessor, optional): The subscription processor to use instead of the
                                                                      default one if provided. Defaults to None.

        Returns:
            bool: True allways, as we currently don't need a confirmation.
        """
        return self._subscription_controller.unsubscribe(channel, data, needs_confirmation, subscription_processor)

    def modify_subscription(
            self,
            channel: str,
            status: bool = UNDEFINED,
            data: dict = UNDEFINED,
            needs_confirmation: bool = UNDEFINED
    ):  # pragma: no cover

        """
        Modifies an existing subscription.

        Updates the properties of an existing subscription. If a property is set to UNDEFINED, it remains unchanged.

        Parameters:
            channel (str): The channel whose subscription is to be modified.
            status (bool, optional): The new status of the subscription. Set as UNDEFINED to leave unchanged.
            data (dict, optional): The new data associated with the subscription. Set as UNDEFINED to leave unchanged.
            needs_confirmation (bool, optional): Specifies whether the subscription requires confirmation.
                                                 Set as UNDEFINED to leave unchanged.
            subscription_processor (SubscriptionProcessor, optional): The subscription processor to use instead of the
                                                                      default one if provided. Defaults to None.

        Raises:
            KeyError: If the specified channel does not have an existing subscription.
        """
        return self._subscription_controller.modify_subscription(channel, status, data, needs_confirmation)

    def is_subscription_active(self, channel: str) -> bool:  # pragma: no cover
        return self._subscription_controller.is_subscription_active(channel)

    def has_active_subscriptions(self) -> bool:  # pragma: no cover
        return self._subscription_controller.has_active_subscriptions()
