from typing import ClassVar

from pydantic import Field

from ws_v2.events import WsEvent


# class IbkrWsKey(Enum):
#     # generic
#     GENERIC = 'GENERIC'
#     UNSUBSCRIPTION = 'UNSUBSCRIPTION'
#     SERVER_ID = 'SERVER_ID'
#     WAITING_FOR_SESSION = 'WAITING_FOR_SESSION'
#
#     # unsolicited
#     ACCOUNT_UPDATE = 'ACCOUNT_UPDATE'
#     AUTHENTICATION_STATUS = 'AUTHENTICATION_STATUS'
#     BULLETIN = 'BULLETIN'
#     ERROR = 'ERROR'
#     SYSTEM = 'SYSTEM'
#     NOTIFICATION = 'NOTIFICATION'
#
#     # subscription-based
#     ACCOUNT_SUMMARY = 'ACCOUNT_SUMMARY'
#     ACCOUNT_LEDGER = 'ACCOUNT_LEDGER'
#     MARKET_DATA = 'MARKET_DATA'
#     MARKET_HISTORY = 'MARKET_HISTORY'
#     PRICE_LADDER = 'PRICE_LADDER'
#     ORDERS = 'ORDERS'
#     PNL = 'PNL'
#     TRADES = 'TRADES'
#
#     # internal
#     LIFECYCLE = 'LIFECYCLE'
#
#     @classmethod
#     def from_topic(cls, topic):
#         topic_to_key = {
#             'sd': IbkrWsKey.ACCOUNT_SUMMARY,
#             'ld': IbkrWsKey.ACCOUNT_LEDGER,
#             'md': IbkrWsKey.MARKET_DATA,
#             'mh': IbkrWsKey.MARKET_HISTORY,
#             'bd': IbkrWsKey.PRICE_LADDER,
#             'or': IbkrWsKey.ORDERS,
#             'pl': IbkrWsKey.PNL,
#             'tr': IbkrWsKey.TRADES,
#         }
#         if topic in topic_to_key:
#             return topic_to_key[topic]
#         raise ValueError(f"No enum member associated with topic '{topic}'")
#
#     @property
#     def topic(self):
#         """
#         Gets the solicited topic string associated with the enum member.
#
#         Returns:
#             str: The topic string corresponding to the enum member.
#         """
#         return {
#             IbkrWsKey.ACCOUNT_SUMMARY: 'sd',
#             IbkrWsKey.ACCOUNT_LEDGER: 'ld',
#             IbkrWsKey.MARKET_DATA: 'md',
#             IbkrWsKey.MARKET_HISTORY: 'mh',
#             IbkrWsKey.PRICE_LADDER: 'bd',
#             IbkrWsKey.ORDERS: 'or',
#             IbkrWsKey.PNL: 'pl',
#             IbkrWsKey.TRADES: 'tr',
#         }[self]
#
#     def __str__(self):
#         return self.value


class GenericIbkrEvent(WsEvent):
    message: dict | None
    topic: str | None = None
    data: dict | None = None


# ===================
# ==  Unsolicited  ==
# ===================

class IbkrError(WsEvent):
    message: str


class WaitingForSession(WsEvent):
    ...


class Notification(WsEvent):
    message: str


class Bulletin(WsEvent):
    message: str


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
    target_event_type: type['IbkrTopicEvent']
    conid: str
    server_id: str


class Unsubscription(WsEvent):
    target_event_type: type['IbkrTopicEvent']
    conid: str | None = None


def get_ibkr_topic_event(topic: str):
    topic_to_event_type = {
        'sd': AccountSummary,
        'ld': AccountLedger,
        'md': MarketData,
        'mh': MarketHistory,
        'bd': PriceLadder,
        'or': Orders,
        'pl': Pnl,
        'tr': Trades,
    }
    if topic in topic_to_event_type:
        return topic_to_event_type[topic]
    raise ValueError(f"No Ibkr event associated with topic '{topic}'")
