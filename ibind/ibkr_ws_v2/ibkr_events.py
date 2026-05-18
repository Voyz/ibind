from typing import ClassVar

from pydantic import Field

from ibind.events import WsEvent


class GenericIbkrEvent(WsEvent):
    message: dict | None
    topic: str | None = None
    data: dict | None = None


# ===================
# ==  Unsolicited  ==
# ===================


class IbkrError(WsEvent):
    data: dict


class WaitingForSession(WsEvent): ...


class Notification(WsEvent):
    data: dict


class Bulletin(WsEvent):
    data: dict


class AccountUpdate(WsEvent):
    data: dict


class System(WsEvent):
    data: dict


class AuthenticationStatus(WsEvent):
    data: dict
    authenticated: bool | None
    competing: bool | None


# ===================
# ==  Topic-based  ==
# ===================


class IbkrTopicEvent(WsEvent):
    topic: ClassVar[str]


class AccountSummary(IbkrTopicEvent):
    topic: ClassVar[str] = 'sd'
    account_id: str
    data: dict


class AccountLedger(IbkrTopicEvent):
    topic: ClassVar[str] = 'ld'
    account_id: str
    data: dict


class MarketData(IbkrTopicEvent):
    topic: ClassVar[str] = 'md'
    conid: str
    data: dict = Field(default_factory=dict)


class MarketHistory(IbkrTopicEvent):
    topic: ClassVar[str] = 'mh'
    conid: str
    data: dict


class Orders(IbkrTopicEvent):
    topic: ClassVar[str] = 'or'
    data: dict


class PriceLadder(IbkrTopicEvent):
    topic: ClassVar[str] = 'bd'
    account_id: str
    conid: str
    exchange: str
    data: dict


class Pnl(IbkrTopicEvent):
    topic: ClassVar[str] = 'pl'
    data: dict


class Trades(IbkrTopicEvent):
    topic: ClassVar[str] = 'tr'
    data: dict


# ===============
# ==  Derived  ==
# ===============
class ServerId(WsEvent):
    target_event_type: type[IbkrTopicEvent]
    conid: str
    server_id: str


class Unsubscription(WsEvent):
    target_event_type: type[IbkrTopicEvent]
    conid: str | None = None
