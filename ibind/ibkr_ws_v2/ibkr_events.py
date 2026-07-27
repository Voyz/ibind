from typing import ClassVar

from pydantic import Field

from ibind.events import WsEvent


class GenericIbkrEvent(WsEvent):
    """
    Fallback event for IBKR messages that could not be mapped to a specific event type.

    Produced when a message carries an unrecognised topic-less payload, or when a known
    topic has no dedicated handler.

    Attributes:
        message (dict | None): The full raw message as received from IBKR.
        topic (str | None): The message topic, if one was present. Default: None.
        data (dict | None): The message arguments, if any were extracted. Default: None.
    """

    message: dict | None
    topic: str | None = None
    data: dict | None = None


# ===================
# ==  Unsolicited  ==
# ===================


class IbkrError(WsEvent):
    """
    An error reported by IBKR.

    Attributes:
        data (dict): The raw error payload from IBKR.
    """

    data: dict


class WaitingForSession(WsEvent):
    """Signals that the client is waiting for an active IBKR brokerage session to be established."""

    ...


class Notification(WsEvent):
    """
    An unsolicited IBKR notification (topic `ntf`), emitted once per notification.

    Attributes:
        data (dict): The notification payload.
    """

    data: dict


class Bulletin(WsEvent):
    """
    An unsolicited IBKR bulletin message (topic `blt`).

    Attributes:
        data (dict): The bulletin payload.
    """

    data: dict


class AccountUpdate(WsEvent):
    """
    Details of the current account (topic `act`).

    Attributes:
        data (dict): The account update payload.
    """

    data: dict


class System(WsEvent):
    """
    A system-level message such as a connection or heartbeat confirmation (topics `system` and `tic`).

    Attributes:
        data (dict): The system message payload.
    """

    data: dict


class AuthenticationStatus(WsEvent):
    """
    A change to the session's authentication status (topic `sts`).

    Attributes:
        data (dict): The raw status payload.
        authenticated (bool | None): Whether the session is authenticated, or None when not reported.
        competing (bool | None): Whether another session is competing for the same account, or None
            when not reported.
    """

    data: dict
    authenticated: bool | None
    competing: bool | None


# ===================
# ==  Topic-based  ==
# ===================


class IbkrTopicEvent(WsEvent):
    """
    Base class for solicited, topic-based IBKR events.

    Attributes:
        topic (ClassVar[str]): The IBKR topic code the subclass corresponds to.
    """

    topic: ClassVar[str]


class AccountSummary(IbkrTopicEvent):
    """
    Account summary data (topic `sd`).

    Attributes:
        account_id (str): The account the summary belongs to.
        data (dict): The account summary payload.
    """

    topic: ClassVar[str] = 'sd'
    account_id: str
    data: dict


class AccountLedger(IbkrTopicEvent):
    """
    Account ledger data (topic `ld`).

    Attributes:
        account_id (str): The account the ledger entry belongs to.
        data (dict): The ledger payload.
    """

    topic: ClassVar[str] = 'ld'
    account_id: str
    data: dict


class MarketData(IbkrTopicEvent):
    """
    A market data update for a contract (topic `md`).

    IBKR only sends fields that changed, so `data` may contain a subset of the subscribed fields;
    absent fields are unchanged.

    Attributes:
        conid (str): The contract identifier the update applies to.
        data (dict): The changed market data fields. Default: empty dict.
    """

    topic: ClassVar[str] = 'md'
    conid: str
    data: dict = Field(default_factory=dict)


class MarketHistory(IbkrTopicEvent):
    """
    Historical OHLC bar data for a contract (topic `mh`).

    Attributes:
        conid (str): The contract identifier the bars apply to.
        data (dict): The historical bar payload.
    """

    topic: ClassVar[str] = 'mh'
    conid: str
    data: dict


class Orders(IbkrTopicEvent):
    """
    Live order updates (topic `or`).

    Attributes:
        data (dict): The order update payload.
    """

    topic: ClassVar[str] = 'or'
    data: dict


class PriceLadder(IbkrTopicEvent):
    """
    BookTrader price ladder data (topic `bd`).

    Attributes:
        account_id (str): The account the ladder is requested for.
        conid (str): The contract identifier the ladder applies to.
        exchange (str | None): The exchange echoed by IBKR, when present.
        data (list[dict]): The price ladder rows.
    """

    topic: ClassVar[str] = 'bd'
    account_id: str
    conid: str
    exchange: str | None = None
    data: list[dict]


class Pnl(IbkrTopicEvent):
    """
    Live profit and loss information (topic `pl`).

    Attributes:
        data (dict): The profit and loss payload.
    """

    topic: ClassVar[str] = 'pl'
    data: dict


class Trades(IbkrTopicEvent):
    """
    A reported trade execution (topic `tr`).

    Attributes:
        data (dict): The trade payload.
    """

    topic: ClassVar[str] = 'tr'
    data: dict


# ===============
# ==  Derived  ==
# ===============
class ServerId(WsEvent):
    """
    Derived event capturing the server ID that IBKR assigns to a subscription.

    Produced when a `serverId` is first seen for a topic, recording its mapping to a contract so the
    subscription can later be unsubscribed by that server ID. Currently used for `MarketHistory`.

    Attributes:
        target_event_type (type[IbkrTopicEvent]): The topic event the server ID belongs to.
        conid (str): The contract identifier mapped to the server ID.
        server_id (str): The server ID assigned by IBKR.
    """

    target_event_type: type[IbkrTopicEvent]
    conid: str
    server_id: str


class Unsubscription(WsEvent):
    """
    Derived event confirming that a subscription has been cancelled.

    Attributes:
        target_event_type (type[IbkrTopicEvent]): The topic event that was unsubscribed.
        conid (str | None): The contract identifier when the subscription was contract-specific,
            otherwise None. Default: None.
    """

    target_event_type: type[IbkrTopicEvent]
    conid: str | None = None
