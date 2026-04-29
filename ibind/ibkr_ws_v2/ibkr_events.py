from enum import Enum
from typing import Any

from pydantic import Field

from ws_v2.events import WsEvent


class IbkrWsKey(Enum):
    # generic
    UNCLASSIFIED = 'UNCLASSIFIED'
    GENERIC = 'GENERIC'
    UNSUBSCRIPTION = 'UNSUBSCRIPTION'

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
    def from_channel(cls, channel):
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


class GenericIbkrEvent(WsEvent):
    key: str = IbkrWsKey.UNCLASSIFIED
    message: dict | None
    topic: str | None = None
    data: dict | None = None
    subscribed: str | None = None
    channel: str | None = None


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
    conid: int | None = None


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
    fields: dict[str, Any] = Field(default_factory=dict)


class MarketHistory(WsEvent):
    key: IbkrWsKey = IbkrWsKey.MARKET_HISTORY
    conid: str
    data: dict


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