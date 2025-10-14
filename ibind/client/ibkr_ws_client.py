import json
import time
from collections import defaultdict
from enum import Enum
from typing import Union, Type, Dict, List

from websocket import WebSocketApp

from ibind import var
from ibind.base.queue_controller import QueueController, QueueAccessor
from ibind.base.subscription_controller import SubscriptionProcessor
from ibind.base.ws_client import WsClient
from ibind.client import ibkr_definitions
from ibind.client.ibkr_client import IbkrClient
from ibind.client.ibkr_utils import extract_conid
from ibind.support.errors import ExternalBrokerError
from ibind.support.logs import project_logger
from ibind.support.py_utils import TimeoutLock, UNDEFINED, wait_until

_LOGGER = project_logger(__file__)


class IbkrWsKey(Enum):
    """
    https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#websockets

    Enumeration of key types for IBKR WebSocket channels.

    This Enum class represents various types of data or subscription channels for IBKR WebSocket API.

    Subscriptions Enums:
        * ACCOUNT_SUMMARY: Represents the 'ACCOUNT_SUMMARY' subscription. (S) (U)
        * ACCOUNT_LEDGER: Represents the 'ACCOUNT_LEDGER' subscription. (S) (U)
        * MARKET_DATA: Represents the 'MARKET_DATA' subscription. (S)
        * MARKET_HISTORY: Represents the 'MARKET_HISTORY' subscription. (S) (U)
        * PRICE_LADDER: Represents the 'PRICE_LADDER' subscription.
        * ORDERS: Represents the 'ORDERS' subscription.
        * PNL: Represents the 'PNL' subscription. (S)
        * TRADES: Represents the 'TRADES' subscription. (S)

    Unsolicited Enums:
        * ACCOUNT_UPDATES: Represents the 'ACCOUNT_UPDATES' unsolicited message.
        * AUTHENTICATION: Represents the 'AUTHENTICATION' unsolicited message.
        * BULLETINS: Represents the 'BULLETINS' unsolicited message.
        * ERROR: Represents the 'ERROR' unsolicited message.
        * SYSTEM: Represents the 'SYSTEM' unsolicited message.
        * NOTIFICATIONS: Represents the 'NOTIFICATIONS' unsolicited message.

    (S) marker indicates that the channel confirms its subscription, while (U) marker indicates that it confirms its unsubscription.
    """

    # subscription-based
    ACCOUNT_SUMMARY = 'ACCOUNT_SUMMARY'
    ACCOUNT_LEDGER = 'ACCOUNT_LEDGER'
    MARKET_DATA = 'MARKET_DATA'
    MARKET_HISTORY = 'MARKET_HISTORY'
    PRICE_LADDER = 'PRICE_LADDER'
    ORDERS = 'ORDERS'
    PNL = 'PNL'
    TRADES = 'TRADES'

    # unsolicited
    ACCOUNT_UPDATES = 'ACCOUNT_UPDATES'
    AUTHENTICATION_STATUS = 'AUTHENTICATION_STATUS'
    BULLETINS = 'BULLETINS'
    ERROR = 'ERROR'
    SYSTEM = 'SYSTEM'
    NOTIFICATIONS = 'NOTIFICATIONS'

    @classmethod
    def from_channel(cls, channel):
        """
        Converts a solicited channel string to its corresponding IbkrWsKey enum member.

        Parameters:
            channel (str): The channel string to be converted.

        Returns:
            IbkrWsKey: The corresponding IbkrWsKey enum member.

        Raises:
            ValueError: If no enum member is associated with the provided channel.
        """
        channel_to_key = {
            'sd': IbkrWsKey.ACCOUNT_SUMMARY,
            'ld': IbkrWsKey.ACCOUNT_LEDGER,
            'md': IbkrWsKey.MARKET_DATA,
            'mh': IbkrWsKey.MARKET_HISTORY,
            'bd': IbkrWsKey.PRICE_LADDER,
            'or': IbkrWsKey.ORDERS,
            'pl': IbkrWsKey.PNL,
            'tr': IbkrWsKey.TRADES,
        }
        if channel in channel_to_key:
            return channel_to_key[channel]
        raise ValueError(f"No enum member associated with channel '{channel}'")

    @property
    def channel(self):
        """
        Gets the solicited channel string associated with the enum member.

        Returns:
            str: The channel string corresponding to the enum member.
        """
        return {
            IbkrWsKey.ACCOUNT_SUMMARY: 'sd',
            IbkrWsKey.ACCOUNT_LEDGER: 'ld',
            IbkrWsKey.MARKET_DATA: 'md',
            IbkrWsKey.MARKET_HISTORY: 'mh',
            IbkrWsKey.PRICE_LADDER: 'bd',
            IbkrWsKey.ORDERS: 'or',
            IbkrWsKey.PNL: 'pl',
            IbkrWsKey.TRADES: 'tr',
        }[self]

    @property
    def confirms_subscribing(self):
        return {
            IbkrWsKey.ACCOUNT_SUMMARY: True,
            IbkrWsKey.ACCOUNT_LEDGER: True,
            IbkrWsKey.MARKET_DATA: True,
            IbkrWsKey.MARKET_HISTORY: True,
            IbkrWsKey.PRICE_LADDER: False,
            IbkrWsKey.ORDERS: False,
            IbkrWsKey.PNL: True,
            IbkrWsKey.TRADES: True,
        }[self]

    @property
    def confirms_unsubscribing(self):
        return {
            IbkrWsKey.ACCOUNT_SUMMARY: True,
            IbkrWsKey.ACCOUNT_LEDGER: True,
            IbkrWsKey.MARKET_DATA: False,
            IbkrWsKey.MARKET_HISTORY: True,
            IbkrWsKey.PRICE_LADDER: False,
            IbkrWsKey.ORDERS: False,
            IbkrWsKey.PNL: False,
            IbkrWsKey.TRADES: False,
        }[self]


class IbkrSubscriptionProcessor(SubscriptionProcessor):
    """
    A subscription processor for IBKR WebSocket channels. This class extends the SubscriptionProcessor.
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
            str: A formatted subscription payload for the IBKR WebSocket.

        Example:
            - With data: make_subscribe_payload('md', {'foo': 'bar'}) returns "smd+{"foo": "bar"}"
            - Without data: make_subscribe_payload('md') returns "smd"
        """
        payload = f's{channel}'

        if data is not None or data == {}:
            payload += f'+{json.dumps(data)}'

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
            str: A formatted unsubscription payload for the IBKR WebSocket.

        Example:
            - With data: make_unsubscribe_payload('md', {'foo': 'bar'}) returns "umd+{"foo": "bar"}"
            - Without data: make_unsubscribe_payload('md') returns "umd+{}"
        """
        data = {} if data is None else data
        return f'u{channel}+{json.dumps(data)}'


class IbkrWsClient(WsClient):
    """
    A WebSocket client for IBKR, extending WsClient.

    This class handles WebSocket communications specific to IBKR, managing subscriptions,
    message processing, and maintaining the health of the WebSocket connection.

    See: https://interactivebrokers.github.io/cpwebapi/websockets
    """

    def __init__(
        self,
        account_id: str = var.IBIND_ACCOUNT_ID,
        url: str = var.IBIND_WS_URL,
        host: str = '127.0.0.1',
        port: str = '5000',
        base_route: str = '/v1/api/ws',
        ibkr_client: IbkrClient = None,
        subscription_processor_class: Type[SubscriptionProcessor] = IbkrSubscriptionProcessor,
        queue_controller_class: Type[QueueController] = QueueController[IbkrWsKey],
        log_raw_messages: bool = var.IBIND_WS_LOG_RAW_MESSAGES,
        unsolicited_channels_to_be_queued: List[IbkrWsKey] = None,
        unwrap_market_data: bool = True,
        start: bool = False,
        use_oauth: bool = var.IBIND_USE_OAUTH,
        access_token: str = var.IBIND_OAUTH1A_ACCESS_TOKEN,
        # inherited
        ping_interval: int = var.IBIND_WS_PING_INTERVAL,
        max_ping_interval: int = var.IBIND_WS_MAX_PING_INTERVAL,
        timeout: float = var.IBIND_WS_TIMEOUT,
        restart_on_close: bool = True,
        restart_on_critical: bool = True,
        max_connection_attempts: int = 10,
        cacert: Union[str, bool] = var.IBIND_CACERT,
        recreate_subscriptions_on_reconnect: bool = True,
        # subscription controller
        subscription_retries: int = var.IBIND_WS_SUBSCRIPTION_RETRIES,
        subscription_timeout: float = var.IBIND_WS_SUBSCRIPTION_TIMEOUT,
    ) -> None:
        """
        Initializes the IbkrWsClient, an IBKR WebSocket client.

        Sets up the client with necessary configurations for connecting to and interacting with the IBKR WebSocket.

        Parameters:
            url (str, optional): URL for the IBKR WebSocket.
            host (str, optional): Host for the IBKR WebSocket API. Defaults to 'localhost'.
            port (str, optional): Port for the IBKR WebSocket API. Defaults to '5000'
            base_route (str, optional): Base route for the IBKR WebSocket API. Defaults to '/v1/api/ws'.
            account_id (str, optional): Account ID for subscription management.
            ibkr_client (IbkrClient, optional): An instance of the IbkrClient for related operations.
            subscription_processor_class (Type[SubscriptionProcessor]): The class to process subscription payloads.
            queue_controller_class (Type[QueueController[IbkrWsKey]], optional): The class to manage message queues. Defaults to QueueController[IbkrWsKey].
            unsolicited_channels_to_be_queued (List[IbkrWsKey], optional): List of unsolicited channels to be queued. Defaults to None.
            unwrap_market_data (bool, optional): Whether Market Data messages' data should be remapped to readable keys. Defaults to True.
            start (bool, optional): Flag to start the client immediately after initialization. Defaults to False.
            use_oauth (bool, optional): Whether to use OAuth authentication. Defaults to False.
            access_token (str, optional): OAuth access token generated in the self-service portal. Defaults to None.

            Inherited parameters from WsClient:

            timeout (float, optional): Timeout for waiting on operations like connection and shutdown. Defaults to _DEFAULT_TIMEOUT.
            restart_on_close (bool, optional): Flag to restart the connection if it closes unexpectedly. Defaults to True.
            restart_on_critical (bool, optional): Flag to restart the connection on critical errors. Defaults to True.
            ping_interval (int, optional): Interval in seconds for sending pings to keep the connection alive. Defaults to _DEFAULT_PING_INTERVAL.
            max_ping_interval (int, optional): Maximum interval in seconds to wait for a ping response. Defaults to _DEFAULT_MAX_PING_INTERVAL.
            max_connection_attempts (int, optional): Maximum number of attempts for connecting to the WebSocket. Defaults to 10.
            cacert (Union[str, bool], optional): Path to the CA certificate file for SSL verification, or False to disable SSL verification. Defaults to False.
            recreate_subscriptions_on_reconnect (bool, optional): Flag to recreate subscriptions on reconnect. Defaults to True.
            subscription_retries (int, optional): Number of retries for subscription requests. Defaults to 5.
            subscription_timeout (float, optional): Timeout for subscription requests. Defaults to 2.
        """

        self._account_id = account_id

        url = var.IBIND_OAUTH1A_WS_URL if url is None and use_oauth else url

        if url is None:
            url = f'wss://{host}:{port}{base_route}'

        if use_oauth:
            if access_token is None:
                raise ValueError(
                    'OAuth access token not found. Please set IBIND_OAUTH1A_ACCESS_TOKEN environment variable or provide it as `access_token` argument.'
                )
            url += f'?oauth_token={access_token}'

        if ibkr_client is None:
            ibkr_client = IbkrClient(account_id=account_id, host=host, port=port, cacert=cacert, use_oauth=use_oauth)

        self._ibkr_client = ibkr_client

        self._queue_controller = queue_controller_class()
        self._subscription_processor = subscription_processor_class()

        self._log_raw_messages = log_raw_messages
        self._unsolicited_channels_to_be_queued = unsolicited_channels_to_be_queued if unsolicited_channels_to_be_queued is not None else []
        self._unwrap_market_data = unwrap_market_data
        self._use_oauth = use_oauth

        super().__init__(
            subscription_processor=self._subscription_processor,
            url=url,
            timeout=timeout,
            restart_on_close=restart_on_close,
            restart_on_critical=restart_on_critical,
            ping_interval=ping_interval,
            max_ping_interval=max_ping_interval,
            max_connection_attempts=max_connection_attempts,
            cacert=cacert,
            subscription_retries=subscription_retries,
            subscription_timeout=subscription_timeout,
            recreate_subscriptions_on_reconnect=recreate_subscriptions_on_reconnect
        )

        self._operational_lock = TimeoutLock(60)

        self._queue_controller.register_queues(list(IbkrWsKey))

        self._last_heartbeat = 0
        self._server_id_conid_pairs: Dict[IbkrWsKey, Dict[str, int]] = defaultdict(dict)
        self._queue_accessors: Dict[IbkrWsKey, QueueAccessor] = {}
        self._tic_message = {}

        if start:
            self.start()

    def _get_cookie(self):
        try:
            status = self._ibkr_client.tickle()
        except ExternalBrokerError:
            _LOGGER.warning('Acquiring session cookie failed, connection to the Gateway may be broken.')
            return None
        session_id = status.data['session']
        if self._use_oauth:
            return f'api={session_id}'
        payload = {'session': session_id}
        return f'api={json.dumps(payload)}'

    def _get_header(self):
        return {'User-Agent': 'ClientPortalGW/1'} if self._use_oauth else None

    def _on_reconnect(self):
        self._last_heartbeat = 0
        super()._on_reconnect()

    def _preprocess_market_data_message(self, message: dict):
        """
        API will only return fields that were updated. If you are not receiving certain fields in the response - means that they remain unchanged.
        """
        if 'conid' not in message:  # pragma: no cover
            # sometimes the ticker message is just an empty update, we ignore it
            return

        if not self._unwrap_market_data:
            return {message['conid']: message}

        result = {'conid': message['conid'], '_updated': message['_updated'], 'topic': message['topic']}
        for key, value in message.items():
            if key in ibkr_definitions.snapshot_by_id:
                result[ibkr_definitions.snapshot_by_id[key]] = value
        return {message['conid']: result}

    def _preprocess_market_history_message(self, message: dict):
        mh_server_id_conid_pairs = self._server_id_conid_pairs[IbkrWsKey.MARKET_HISTORY]
        if 'serverId' in message and message['serverId'] not in mh_server_id_conid_pairs:
            mh_server_id_conid_pairs[message['serverId']] = extract_conid(message)

        return message

    def _handle_subscribed_message(self, channel: str, message: dict):
        try:
            ibkr_ws_key = IbkrWsKey.from_channel(channel[:2])
        except ValueError:
            # ValueError means we don't support this channel
            return False

        if ibkr_ws_key == IbkrWsKey.MARKET_DATA:
            message = self._preprocess_market_data_message(message)
        elif ibkr_ws_key == IbkrWsKey.MARKET_HISTORY:
            message = self._preprocess_market_history_message(message)

        self._queue_controller.put_to_queue(ibkr_ws_key, message)

        return True

    def _handle_unsolicited_message(self, ibkr_ws_key: IbkrWsKey, message: dict):
        if ibkr_ws_key in self._unsolicited_channels_to_be_queued:
            self._queue_controller.put_to_queue(ibkr_ws_key, message)

    def _handle_account_update(self, message, data):
        self._handle_unsolicited_message(IbkrWsKey.ACCOUNT_UPDATES, message)
        if 'accounts' in data and self._account_id not in data['accounts']:
            _LOGGER.error(f'{self}: Account ID mismatch: expected={self._account_id}, received={data["accounts"]}')
        elif 'acctProps' in data:  # expected account update that we ignore
            pass
        else:
            _LOGGER.info(f'{self}: Account message: {data}')
            return

    def _handle_authentication_status(self, message, data):
        self._handle_unsolicited_message(IbkrWsKey.AUTHENTICATION_STATUS, data)

        if 'authenticated' in data:
            if data.get('authenticated') is False:
                _LOGGER.error(f'{self}: Status unauthenticated: {data}')
            self.set_authenticated(data.get('authenticated'))
        elif 'competing' in data:
            if data.get('competing') is False:
                pass
            _LOGGER.error(f'{self}: Status competing: {data}')
        elif (  # expected status updates that we ignore
                data == {'message': ''} or
                data.get('fail', '') == '' or
                'serverName' in data or
                'serverVersion' in data or
                'username' in data
        ):
            pass
        else:
            _LOGGER.info(f'{self}: Status message: {data}')

    def _handle_bulletin(self, message):  # pragma: no cover
        self._handle_unsolicited_message(IbkrWsKey.BULLETINS, message)

    def _handle_error(self, message):
        self._handle_unsolicited_message(IbkrWsKey.ERROR, message)
        _LOGGER.error(f'{self}: on_message error: {message}')

    def _handle_notification(self, data):  # pragma: no cover
        self._handle_unsolicited_message(IbkrWsKey.NOTIFICATIONS, data)
        for notification in data:
            _LOGGER.info(f'{self}: IBKR notification: {notification}')

    def _handle_market_history_unsubscribe(self, data):
        server_id = data['message'].split('Unsubscribed ')[-1]
        mh_server_id_conid_pairs = self._server_id_conid_pairs[IbkrWsKey.MARKET_HISTORY]
        if server_id in mh_server_id_conid_pairs:
            conid = mh_server_id_conid_pairs[server_id]
            _LOGGER.info(f'{self}: Received unsubscribing confirmation for server_id={server_id!r}/conid={conid!r}.')
            if conid is None:
                _LOGGER.warning(f'{self}: Unknown conid={conid!r}. Cannot mark the subscription as unsubscribed.')
                return

            self.modify_subscription(f'mh+{conid}', status=False)
        else:
            _LOGGER.warning(
                f'{self}: Received unsubscribing confirmation for unknown server_id={server_id!r}. Existing server_ids: {mh_server_id_conid_pairs}'
            )

    def _handle_message_without_topic(self, message: dict):
        if 'message' in message:
            if 'Unsubscribed' in message['message']:
                self._handle_market_history_unsubscribe(message)
                return
            elif message['message'] == 'waiting for session':
                _LOGGER.info(f'{self}: Waiting for an active IBKR session.')
                return
        elif 'result' in message:
            if message['result'] == 'unsubscribed from summary':
                return self.modify_subscription(f'sd+{self._account_id}', status=False)
            elif message['result'] == 'unsubscribed from ledger':
                return self.modify_subscription(f'ld+{self._account_id}', status=False)

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

    def _on_message(self, wsa: WebSocketApp, raw_message: str) -> None:
        if self._log_raw_messages:
            _LOGGER.debug(f'{self}: Raw message: {raw_message}')
        message, topic, data, subscribed, channel = self._preprocess_raw_message(raw_message)

        if 'error' in message:
            self._handle_error(message)

        elif topic is None:
            # in general most message should carry a topic, other than for few exceptions
            self._handle_message_without_topic(message)

        elif topic == 'tic':
            self._tic_message = message

        elif topic == 'system':
            if 'hb' in message:
                self._last_heartbeat = message['hb']

        elif topic == 'act':
            self._handle_account_update(message, data)

        elif topic == 'blt':
            self._handle_bulletin(message)

        elif topic == 'ntf':
            self._handle_notification(data)

        elif topic == 'sts':
            self._handle_authentication_status(message, data)

        elif topic == 'error':
            _LOGGER.error(f'{self}: Error message:  {message}')

        elif self.has_subscription(channel):
            if not self.is_subscription_active(channel):
                self.modify_subscription(channel, status=True)

            if not self._handle_subscribed_message(channel, message):
                _LOGGER.error(f'{self}: Channel "{channel}" subscribed but lacking a handler. Message: {message}')

        elif self._handle_subscribed_message(channel, message):
            _LOGGER.warning(f'{self}: Handled a channel "{channel}" message that is missing a subscription. Message: {message}')
        else:
            _LOGGER.error(f'{self}: Topic "{topic}" unrecognised. Message: {message}')

    def check_health(self) -> bool:
        """
        Checks the overall health of the IbkrWsClient and its WebSocket connection.

        Verifies the health of the WebSocket connection by checking ping responses and heartbeat messages
        from IBKR. If the connection is found to be unhealthy, a hard reset is initiated.

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
            _LOGGER.warning(
                f'{self}: Last IBKR heartbeat happened {diff:.2f} seconds ago, exceeding the max ping interval of {self._max_ping_interval}. Restarting.'
            )
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
        return self._server_id_conid_pairs[key]

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
        needs_confirmation: bool = None,
        subscription_processor: SubscriptionProcessor = None,
    ) -> bool:  # pragma: no cover
        """
        Subscribes to a specific channel in the IBKR WebSocket.

        Initiates a subscription to a given channel, optionally including additional data in the subscription
        request. The method delegates the subscription logic to the SubscriptionController.

        From docs: "To receive all orders for the current day the endpoint /iserver/account/orders can be used. It is advised to query all orders for the current day first before subscribing to live orders."

        Parameters:
            channel (str): The channel to subscribe to.
            data (dict, optional): Additional data to be included in the subscription request. Defaults to None.
            needs_confirmation (bool, optional): Specifies whether the subscription requires confirmation. If not specified it will be derived from the channel type. Defaults to None.
            subscription_processor (SubscriptionProcessor, optional): The subscription processor to use instead of the
                                                                      default one if provided. Defaults to None.

        Returns:
            bool: True if the subscription was successful, False otherwise.
        """
        if channel[:2] == 'or':
            if not wait_until(self._ibkr_client.check_health, 'IbkrClient not healthy before subscribing to orders', timeout=15, sleep=3):
                return False
            self._ibkr_client.receive_brokerage_accounts()
            time.sleep(0.25)
            self._ibkr_client.live_orders(force=True)
            self._ibkr_client.live_orders()

        if needs_confirmation is None:
            needs_confirmation = IbkrWsKey.from_channel(channel[:2]).confirms_subscribing

        return super().subscribe(channel, data, needs_confirmation, subscription_processor)

    def unsubscribe(
        self,
        channel: str,
        data: dict = None,
        needs_confirmation: bool = None,
        subscription_processor: SubscriptionProcessor = None,
    ) -> bool:  # pragma: no cover
        """
        Unsubscribes from a specified channel.

        Attempts to unsubscribe from a given channel using the WsClient. The method manages the
        unsubscription logic, including sending the unsubscription payload and handling retries and timeouts.
        The subscription status is updated accordingly within the class.

        Parameters:
            channel (str): The name of the channel to unsubscribe from.
            data (dict, optional): Additional data to be included in the unsubscription request. Defaults to None.
            needs_confirmation (bool, optional): Specifies whether the subscription requires confirmation. If not specified it will be derived from the channel type. Defaults to None.
            subscription_processor (SubscriptionProcessor, optional): The subscription processor to use instead of the
                                                                      default one if provided. Defaults to None.

        Returns:
            bool: True if the unsubscription was successful, False otherwise.
        """
        if needs_confirmation is None:
            needs_confirmation = IbkrWsKey.from_channel(channel[:2]).confirms_unsubscribing

        return super().unsubscribe(channel, data, needs_confirmation, subscription_processor)

    def _queue_accessor(self, ibkr_ws_key: IbkrWsKey):  # pragma: no cover
        try:
            return self._queue_accessors[ibkr_ws_key]
        except KeyError:
            self._queue_accessors[ibkr_ws_key] = self.new_queue_accessor(ibkr_ws_key)
            return self._queue_accessors[ibkr_ws_key]

    def get(self, ibkr_ws_key: IbkrWsKey, block: bool = False, timeout=None):  # pragma: no cover
        """
        Facilitates access to data queues by exposing the `get` method of internally-stored QueueAccessor objects.

        Parameters:
            ibkr_ws_key (IbkrWsKey): The IbkrWsKey of the queue to access.
            block (bool, optional): Whether to block if the queue is empty. Defaults to False.
            timeout (Optional[float]): The maximum time in seconds to block waiting for an item.
                                       A value of None indicates an indefinite wait. Only effective if 'block' is True.

        Returns:
            The item retrieved from the queue, or None if the queue is empty and 'block' is False.

        Note:
            - This method is provided for convenience and should not be used in production code. A new QueueAccessor object should be acquired instead using `new_queue_accessor`.
        """
        return self._queue_accessor(ibkr_ws_key).get(block=block, timeout=timeout)

    def empty(self, ibkr_ws_key: IbkrWsKey):  # pragma: no cover
        """
        Facilitates access to data queues by exposing the `empty` method of internally-stored QueueAccessor objects.

        Parameters:
            ibkr_ws_key (IbkrWsKey): The IbkrWsKey of the queue to access.

        Returns:
             bool: True if the queue is empty, False otherwise.

        Note:
            - This method is provided for convenience and should not be used in production code. A new QueueAccessor object should be acquired instead using `new_queue_accessor`.
        """
        return self._queue_accessor(ibkr_ws_key).empty()

    def tic(self):
        """
        Sends a tic request to the IBKR WebSocket server and waits for the response.

        This method sends a 'tic' message to the server and waits for the server to update
        the internal tic message with a new timestamp. It uses the 'lastAccessed' field
        to detect when a fresh response has been received.

        Returns:
            dict: The tic message dictionary containing server response data, or None if
                  the send operation failed or the response timed out.
        """
        ts = self._tic_message.get('lastAccessed', 0)
        ret = self.send('tic')

        if not ret:
            return None

        def ts_changed():
            return self._tic_message.get('lastAccessed', 0) != ts

        if not wait_until(ts_changed, f'tic timeout, ts={ts}', timeout=5):
            return None

        return self._tic_message