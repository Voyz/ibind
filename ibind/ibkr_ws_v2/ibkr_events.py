from enum import Enum

from pydantic import Field

from ws_v2.events import WsEvent


class IbkrWsKey(Enum):
    # generic
    GENERIC = 'GENERIC'
    UNSUBSCRIPTION = 'UNSUBSCRIPTION'
    SERVER_ID = 'SERVER_ID'

    # unsolicited
    ACCOUNT_UPDATE = 'ACCOUNT_UPDATE'
    AUTHENTICATION_STATUS = 'AUTHENTICATION_STATUS'
    BULLETIN = 'BULLETIN'
    ERROR = 'ERROR'
    SYSTEM = 'SYSTEM'
    NOTIFICATION = 'NOTIFICATION'

    # subscription-based
    ACCOUNT_SUMMARY = 'ACCOUNT_SUMMARY'
    ACCOUNT_LEDGER = 'ACCOUNT_LEDGER'
    MARKET_DATA = 'MARKET_DATA'
    MARKET_HISTORY = 'MARKET_HISTORY'
    PRICE_LADDER = 'PRICE_LADDER'
    ORDERS = 'ORDERS'
    PNL = 'PNL'
    TRADES = 'TRADES'

    # internal
    CLIENT_INTERNAL = 'CLIENT_INTERNAL'

    @classmethod
    def from_topic(cls, topic):
        topic_to_key = {
            'sd': IbkrWsKey.ACCOUNT_SUMMARY,
            'ld': IbkrWsKey.ACCOUNT_LEDGER,
            'md': IbkrWsKey.MARKET_DATA,
            'mh': IbkrWsKey.MARKET_HISTORY,
            'bd': IbkrWsKey.PRICE_LADDER,
            'or': IbkrWsKey.ORDERS,
            'pl': IbkrWsKey.PNL,
            'tr': IbkrWsKey.TRADES,
        }
        if topic in topic_to_key:
            return topic_to_key[topic]
        raise ValueError(f"No enum member associated with topic '{topic}'")

    @property
    def topic(self):
        """
        Gets the solicited topic string associated with the enum member.

        Returns:
            str: The topic string corresponding to the enum member.
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

    def __str__(self):
        return self.value


class GenericIbkrEvent(WsEvent):
    key: str = IbkrWsKey.GENERIC
    message: dict | None
    topic: str | None = None
    data: dict | None = None


# ===================
# ==  Unsolicited  ==
# ===================

class IbkrError(WsEvent):
    key: IbkrWsKey = IbkrWsKey.ERROR
    message: str


class WaitingForSession(WsEvent):
    key: IbkrWsKey = IbkrWsKey.GENERIC


class Notification(WsEvent):
    key: IbkrWsKey = IbkrWsKey.NOTIFICATION
    message: str


class Bulletin(WsEvent):
    key: IbkrWsKey = IbkrWsKey.BULLETIN
    message: str


class AccountUpdate(WsEvent):
    key: IbkrWsKey = IbkrWsKey.ACCOUNT_UPDATE
    data: dict


class System(WsEvent):
    key: IbkrWsKey = IbkrWsKey.SYSTEM
    data: dict


class AuthenticationStatus(WsEvent):
    key: IbkrWsKey = IbkrWsKey.AUTHENTICATION_STATUS
    data: dict
    authenticated: bool | None
    competing: bool | None


# ==========================
# ==  Subscription-based  ==
# ==========================

class Unsubscription(WsEvent):
    key: IbkrWsKey = IbkrWsKey.UNSUBSCRIPTION
    target_key: IbkrWsKey
    conid: str | None = None


class AccountSummary(WsEvent):
    key: IbkrWsKey = IbkrWsKey.ACCOUNT_SUMMARY
    account_id: str
    data: dict


class AccountLedger(WsEvent):
    key: IbkrWsKey = IbkrWsKey.ACCOUNT_LEDGER
    account_id: str
    data: dict


class MarketData(WsEvent):
    key: IbkrWsKey = IbkrWsKey.MARKET_DATA
    conid: str
    data: dict = Field(default_factory=dict)


class MarketHistory(WsEvent):
    key: IbkrWsKey = IbkrWsKey.MARKET_HISTORY
    conid: str
    data: dict


class ServerId(WsEvent):
    key: IbkrWsKey = IbkrWsKey.SERVER_ID
    conid: str
    server_id: str
    target_key: IbkrWsKey


class Orders(WsEvent):
    key: IbkrWsKey = IbkrWsKey.ORDERS
    data: dict


class PriceLadder(WsEvent):
    key: IbkrWsKey = IbkrWsKey.PRICE_LADDER
    account_id: str
    conid: str
    exchange: str
    data: dict


class Pnl(WsEvent):
    key: IbkrWsKey = IbkrWsKey.PNL
    data: dict


class Trades(WsEvent):
    key: IbkrWsKey = IbkrWsKey.TRADES
    data: dict
