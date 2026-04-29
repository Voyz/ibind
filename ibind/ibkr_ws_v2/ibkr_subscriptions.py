import json
from typing import Literal, Any

from ibkr_ws_v2.ibkr_events import IbkrWsKey, AccountSummary, AccountLedger, MarketData, MarketHistory, Orders, PriceLadder, Pnl, Trades
from ws_v2.events import WsEvent
from ws_v2.subscription_controller import Subscription


def ibkr_payload(op: Literal['s', 'u'], topic: str, target: str | None = None, data: dict[str, Any] | None = None) -> str:
    payload = f"{op}{topic}"
    if target is not None:
        payload += f"+{target}"
    if data is not None:
        payload += f"+{json.dumps(data, separators=(',', ':'))}"
    return payload


class AccountSummarySubscription(Subscription):
    @property
    def key(self) -> IbkrWsKey:
        return IbkrWsKey.ACCOUNT_SUMMARY

    @property
    def topic(self) -> str:
        return ''

    def subscribe_payload(self) -> str:
        ...

    def unsubscribe_payload(self) -> str:
        ...

    def confirms_subscribe(self) -> bool:
        return True

    def confirms_unsubscribe(self) -> bool:
        return True


class AccountLedgerSubscription(Subscription):
    account_id: str
    @property
    def key(self) -> IbkrWsKey:
        return IbkrWsKey.ACCOUNT_LEDGER

    @property
    def topic(self) -> str:
        return 'ld'

    def subscribe_payload(self) -> str:
        return ibkr_payload("s", "ld", self.account_id)


    def unsubscribe_payload(self) -> str:
        return ibkr_payload("u", "ld", self.account_id)


    def confirms_subscribe(self) -> bool:
        return True

    def confirms_unsubscribe(self) -> bool:
        return True

    def make_hash(self):
        return self.topic + "+" + self.account_id

class MarketDataSubscription(Subscription):
    conid: str
    fields: tuple[str, ...] = ("31", "84", "86")

    @property
    def key(self) -> IbkrWsKey:
        return IbkrWsKey.MARKET_DATA

    @property
    def topic(self) -> str:
        return "md"

    def subscribe_payload(self) -> str:
        return ibkr_payload("s", "md", self.conid, {"fields": list(self.fields)})

    def unsubscribe_payload(self) -> str:
        return ibkr_payload("u", "md", self.conid, {})

    @property
    def confirms_subscribe(self) -> bool:
        return True

    @property
    def confirms_unsubscribe(self) -> bool:
        return False

    def make_hash(self):
        return self.topic + "+" + self.conid


class MarketHistorySubscription(Subscription):
    conid: str

    @property
    def key(self) -> IbkrWsKey:
        return IbkrWsKey.MARKET_HISTORY

    @property
    def topic(self) -> str:
        return ''

    def subscribe_payload(self) -> str:
        ...

    def unsubscribe_payload(self) -> str:
        ...

    def confirms_subscribe(self) -> bool:
        return True

    def confirms_unsubscribe(self) -> bool:
        return True


class OrdersSubscription(Subscription):
    @property
    def key(self) -> IbkrWsKey:
        return IbkrWsKey.ORDERS

    @property
    def topic(self) -> str:
        return "or"

    def subscribe_payload(self) -> str:
        return ibkr_payload("s", "or")

    def unsubscribe_payload(self) -> str:
        return ibkr_payload("u", "or", data={})

    @property
    def confirms_subscribe(self) -> bool:
        return False

    @property
    def confirms_unsubscribe(self) -> bool:
        return False


class PriceLadderSubscription(Subscription):
    @property
    def key(self) -> IbkrWsKey:
        return IbkrWsKey.PRICE_LADDER

    @property
    def topic(self) -> str:
        return ''

    def subscribe_payload(self) -> str:
        ...

    def unsubscribe_payload(self) -> str:
        ...

    def confirms_subscribe(self) -> bool:
        return False

    def confirms_unsubscribe(self) -> bool:
        return False


class PnlSubscription(Subscription):
    @property
    def key(self) -> IbkrWsKey:
        return IbkrWsKey.PNL

    @property
    def topic(self) -> str:
        return ''

    def subscribe_payload(self) -> str:
        ...

    def unsubscribe_payload(self) -> str:
        ...

    def confirms_subscribe(self) -> bool:
        return True

    def confirms_unsubscribe(self) -> bool:
        return False


class TradesSubscription(Subscription):
    @property
    def key(self) -> IbkrWsKey:
        return IbkrWsKey.TRADES

    @property
    def topic(self) -> str:
        return ''

    def subscribe_payload(self) -> str:
        ...

    def unsubscribe_payload(self) -> str:
        ...

    def confirms_subscribe(self) -> bool:
        return True

    def confirms_unsubscribe(self) -> bool:
        return False

def event_to_subscription(event:WsEvent):
    if isinstance(event, AccountSummary):
        return AccountSummarySubscription()
    elif isinstance(event, AccountLedger):
        return AccountLedgerSubscription(account_id=event.account_id)
    elif isinstance(event, MarketData):
        return MarketDataSubscription(conid=event.conid)
    elif isinstance(event, MarketHistory):
        return MarketHistorySubscription(conid=event.conid)
    elif isinstance(event, Orders):
        return OrdersSubscription()
    elif isinstance(event, PriceLadder):
        return PriceLadderSubscription()
    elif isinstance(event, Pnl):
        return PnlSubscription()
    elif isinstance(event, Trades):
        return TradesSubscription()
    else:
        raise ValueError(f'Unsupported event: {event}')