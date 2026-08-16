import json
from typing import Tuple, List, Optional

from pydantic import Field

from ibind import events
from ibind.events import AccountLedger, MarketData, MarketHistory, Orders, PriceLadder, Pnl, Trades, Unsubscription, AccountSummary, IbkrTopicEvent
from ibind.support.py_utils import filter_none
from ibind.ws.ws_subscriptions import Subscription, SubscriptionResolver


def make_binding_key(event_type: type[IbkrTopicEvent], conid: str = None, account_id=None, exchange=None):
    """
    Create a binding key for an IBKR event type.

    The binding key format depends on the event type and required parameters.
    Market data events require conid, account-based events require account_id,
    and account-agnostic events use only the topic.

    Args:
        event_type (type[IbkrTopicEvent]): The event type class.
        conid (str, optional): Contract identifier for market data events.
        account_id (str, optional): Account ID for account-based events.
        exchange (str, optional): Exchange identifier (currently unused).

    Returns:
        str: A binding key combining topic and relevant parameters.

    Raises:
        ValueError: If the event type is not supported.
    """
    if event_type in [events.MarketData, events.MarketHistory]:
        return f'{event_type.topic}+{conid}'
    elif event_type in [events.AccountLedger, events.AccountSummary]:
        return f'{event_type.topic}+{account_id}'
    elif event_type in [events.PriceLadder]:
        return f'{event_type.topic}+{account_id}'
    elif event_type in [events.Orders, events.Pnl, events.Trades]:
        return event_type.topic
    else:
        raise ValueError(f'Unsupported event type: {event_type}')


class IbkrSubscriptionResolver(SubscriptionResolver):
    """
    Resolves subscription binding keys for IBKR events.

    Maps IBKR topic events and unsubscription requests to their corresponding
    binding keys, enabling the subscription controller to track and manage
    subscriptions by event type and relevant parameters (conid, account_id).
    """

    def __init__(self, account_id):
        self._account_id = account_id

    def _resolve_subscribing_event(self, event) -> str:
        event_type = type(event)
        if event_type in [events.MarketData, events.MarketHistory]:
            return make_binding_key(event_type, conid=event.conid)
        elif event_type in [events.AccountLedger, events.AccountSummary]:
            return make_binding_key(event_type, account_id=event.account_id)
        elif event_type in [events.PriceLadder]:
            return make_binding_key(event_type, account_id=event.account_id)
        elif event_type in [events.Orders, events.Pnl, events.Trades]:
            return make_binding_key(event_type)
        else:
            raise ValueError(f'Unsupported event: {event}')

    def _resolve_unsubscribing_event(self, event) -> str:
        return make_binding_key(event.target_event_type, event.conid, self._account_id)

    def resolve_binding_key(self, event) -> Tuple[bool, str] | Tuple[None, None]:
        if not (isinstance(event, IbkrTopicEvent) or isinstance(event, Unsubscription)):
            return None, None

        if isinstance(event, Unsubscription):
            return False, self._resolve_unsubscribing_event(event)
        else:
            return True, self._resolve_subscribing_event(event)


class IbkrSubscription(Subscription):
    """
    Base class for IBKR topic event subscriptions.

    Attributes:
        event_type (type[IbkrTopicEvent]): The IBKR event type this subscription handles.
    """

    event_type: type[IbkrTopicEvent]

    @property
    def topic(self) -> str:
        return self.event_type.topic


class AccountSummarySubscription(IbkrSubscription):
    """
    Subscribes to a stream of account summary messages for the specified account.

    Attributes:
        account_id (str): Required. The account ID whose account summary data will be subscribed.
        keys (List[str], optional): Pass specific account summary data keys to receive messages concerning only those keys.
        fields (List[str], optional): Pass specific account summary field names to filter responses to include only these fields.
    """

    event_type: type[IbkrTopicEvent] = AccountSummary
    account_id: str
    keys: Optional[List[str]] = None
    fields: Optional[List[str]] = None

    def subscribe_payload(self) -> str:
        data = filter_none(
            {
                'keys': self.keys,
                'fields': self.fields,
            }
        )
        data_str = json.dumps(data, separators=(',', ':')) if data else '{}'
        return f'ssd+{self.account_id}+{data_str}'

    def unsubscribe_payload(self) -> str:
        return f'usd+{self.account_id}'

    @property
    def confirms_subscribe(self) -> bool:
        return True

    @property
    def confirms_unsubscribe(self) -> bool:
        return True

    def binding_key(self):
        return make_binding_key(self.event_type, account_id=self.account_id)


class AccountLedgerSubscription(IbkrSubscription):
    """
    Subscribes to a stream of account ledger messages for the specified account, with contents sorted by currency.

    Attributes:
        account_id (str): Required. The account ID whose ledger data will be subscribed.
        keys (List[str], optional): Pass specific ledger currency keys to receive messages with data only for those currencies.
        fields (List[str], optional): Pass specific ledger field names to receive messages only those data points.
    """

    event_type: type[IbkrTopicEvent] = AccountLedger
    account_id: str
    keys: Optional[List[str]] = None
    fields: Optional[List[str]] = None

    def subscribe_payload(self) -> str:
        data = filter_none(
            {
                'keys': self.keys,
                'fields': self.fields,
            }
        )
        data_str = json.dumps(data, separators=(',', ':')) if data else '{}'
        return f'sld+{self.account_id}+{data_str}'

    def unsubscribe_payload(self) -> str:
        return f'uld+{self.account_id}'

    @property
    def confirms_subscribe(self) -> bool:
        return True

    @property
    def confirms_unsubscribe(self) -> bool:
        return True

    def binding_key(self):
        return make_binding_key(self.event_type, account_id=self.account_id)


class MarketDataSubscription(IbkrSubscription):
    """
    Subscribes the user to watchlist market data. Streaming, top-of-the-book, level one, market data is available for all instruments.

    Market data streams will terminate after 15 minutes. Users must send a new request for market data after 10 minutes to continue retrieving data for the instrument.

    Attributes:
        conid (str): Required. A single contract identifier. Contracts requested use SMART routing by default.
        fields (List[str]): Optional. Pass an array of field IDs to receive messages concerning only those fields.
    """

    event_type: type[IbkrTopicEvent] = MarketData
    conid: str
    fields: List[str]

    # IBKR specifies: "Market data streams will terminate after 10 minutes. Users must send a new request for market data after 9 minutes to continue retrieving data for the instrument."
    expiry_seconds: int | None = 60 * 9  # 9 minutes expiry

    def subscribe_payload(self) -> str:
        fields_str = json.dumps({'fields': list(self.fields)}, separators=(',', ':'))
        return f'smd+{self.conid}+{fields_str}'

    def unsubscribe_payload(self) -> str:
        return f'umd+{self.conid}+{{}}'

    @property
    def confirms_subscribe(self) -> bool:
        return True

    @property
    def confirms_unsubscribe(self) -> bool:
        return False

    def binding_key(self):
        return make_binding_key(self.event_type, conid=self.conid)


class MarketHistorySubscription(IbkrSubscription):
    """
    Subscribes the user to historical bar data. Streaming, top-of-the-book, level one, historical data is available for all instruments.

    Only a maximum of 5 concurrent historical data requests are available at a time. Historical data will only respond once, though customers will still need to unsubscribe from the endpoint.

    Attributes:
        conid (str): Required. A single contract identifier. Contracts requested use SMART routing by default.
        exchange (str, optional): Requested exchange to receive data.
        period (str, optional): Total duration for which bars will be requested.
        bar (str, optional): Interval of time to receive data.
        outside_rth (bool, optional): Determines if you want data outside regular trading hours (true) or only during market hours (false).
        source (str, optional): The value determining what type of data to show.
        format (str, optional): The format in which bars are returned.
    """

    event_type: type[IbkrTopicEvent] = MarketHistory
    conid: str
    exchange: str = None
    period: str = None
    bar: str = None
    outside_rth: bool = None
    source: str = None
    format: str = None
    server_id: list = Field(default_factory=list)  # uses list to allow writing despite frozen model

    def subscribe_payload(self) -> str:
        data = {
            'exchange': self.exchange,
            'period': self.period,
            'bar': self.bar,
            'outside_rth': self.outside_rth,
            'source': self.source,
            'format': self.format,
        }
        data = filter_none(data)
        return f'smh+{self.conid}+{json.dumps(data, separators=(",", ":"))}'

    def unsubscribe_payload(self) -> str:
        server_id = self.get_server_id()
        if server_id is None:
            raise RuntimeError(
                f'{self}: Unsubscribing from market history for conid={self.conid!r} without server_id. MarketHistorySubscription must have server_id set before unsubscribing.'
            )
        return f'umh+{server_id}'

    @property
    def confirms_subscribe(self) -> bool:
        return True

    @property
    def confirms_unsubscribe(self) -> bool:
        return True

    def set_server_id(self, server_id):
        if self.has_server_id():
            raise ValueError('Server ID already set')
        self.server_id.append(server_id)

    def clear_server_id(self):
        """Clear the server ID, typically needed after reconnect."""
        self.server_id.clear()

    def has_server_id(self) -> bool:
        return len(self.server_id) > 0

    def get_server_id(self):
        return self.server_id[0] if self.has_server_id() else None

    def binding_key(self):
        return make_binding_key(self.event_type, conid=self.conid)


class OrdersSubscription(IbkrSubscription):
    """
    Subscribes the user to live order updates.

    Attributes:
        filter (str, optional): Pass an exclusive Order Status Value to return.
    """

    event_type: type[IbkrTopicEvent] = Orders
    filter: str = None

    def subscribe_payload(self) -> str:
        # filter is constrained to IBKR order status values (simple strings without special chars)
        filter_str = f'{{"filters": ["{self.filter}"]}}' if self.filter is not None else '{}'
        return f'sor+{filter_str}'

    def unsubscribe_payload(self) -> str:
        return 'uor+{}'

    @property
    def confirms_subscribe(self) -> bool:
        return False

    @property
    def confirms_unsubscribe(self) -> bool:
        return False

    def binding_key(self):
        return make_binding_key(self.event_type)


class PriceLadderSubscription(IbkrSubscription):
    """
    Subscribes the user to BookTrader price ladder data. Streaming BookTrader data requires users to maintain a L2, Depth of Book, market data subscription.

    Attributes:
        account_id (str): Required. A single AccountId.
        conid (str): Required. A single contract identifier.
        exchange (str, optional): Provide a routing exchange identifier. If no exchange is specified, all available deep exchanges are assumed.
    """

    event_type: type[IbkrTopicEvent] = PriceLadder
    conid: str
    account_id: str
    exchange: str | None = None

    def subscribe_payload(self) -> str:
        return f'sbd+{self.account_id}+{self.conid}' + (f'+{self.exchange}' if self.exchange is not None else '')

    def unsubscribe_payload(self) -> str:
        return f'ubd+{self.account_id}'

    @property
    def confirms_subscribe(self) -> bool:
        return False

    @property
    def confirms_unsubscribe(self) -> bool:
        return False

    def binding_key(self):
        return make_binding_key(self.event_type, conid=self.conid, account_id=self.account_id, exchange=self.exchange)


class PnlSubscription(IbkrSubscription):
    """
    Subscribes the user to live profit and loss information.
    """

    event_type: type[IbkrTopicEvent] = Pnl

    def subscribe_payload(self) -> str:
        return 'spl'

    def unsubscribe_payload(self) -> str:
        return 'upl'

    @property
    def confirms_subscribe(self) -> bool:
        return True

    @property
    def confirms_unsubscribe(self) -> bool:
        return False

    def binding_key(self):
        return make_binding_key(self.event_type)


class TradesSubscription(IbkrSubscription):
    """
    Subscribes the user to trades data. This will return all executions data while streamed.

    Attributes:
        realtime_updates_only (bool, optional): Decide whether you want to display any historical executions, or only the executions available in real time. Default: False.
        days (int, optional): Returns the number of days of executions for data to be returned. Default: 1.
    """

    event_type: type[IbkrTopicEvent] = Trades
    realtime_updates_only: bool | None = None
    days: int | None = None

    def subscribe_payload(self) -> str:
        extra = {}
        if self.realtime_updates_only is not None:
            extra['realtime_updates_only'] = self.realtime_updates_only
        if self.days is not None:
            extra['days'] = self.days
        extra_str = json.dumps(extra, separators=(',', ':'))
        return f'str+{extra_str}'

    def unsubscribe_payload(self) -> str:
        return 'utr'

    @property
    def confirms_subscribe(self) -> bool:
        return True

    @property
    def confirms_unsubscribe(self) -> bool:
        return False

    def binding_key(self):
        return make_binding_key(self.event_type)
