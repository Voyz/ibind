import json
from typing import Tuple

from pydantic import Field

from ibkr_ws_v2.ibkr_events import IbkrWsKey, AccountLedger, MarketData, MarketHistory, Orders, PriceLadder, Pnl, Trades, Unsubscription, AccountSummary
from support.py_utils import filter_none
from ws_v2.subscriptions import Subscription, SubscriptionResolver


def make_binding_key(
    key: IbkrWsKey,
    conid: str = None,
    account_id=None,
    exchange=None
):
    if key in [IbkrWsKey.MARKET_DATA, IbkrWsKey.MARKET_HISTORY]:
        return f"{key.topic}+{conid}"
    elif key in [IbkrWsKey.ACCOUNT_LEDGER, IbkrWsKey.ACCOUNT_SUMMARY]:
        return f"{key.topic}+{account_id}"
    elif key in [IbkrWsKey.PRICE_LADDER]:
        return f"{key.topic}+{account_id}+{conid}" + (f"+{exchange}" if exchange is not None else '')
    elif key in [IbkrWsKey.ORDERS, IbkrWsKey.PNL, IbkrWsKey.TRADES]:
        return key.topic
    else:
        raise ValueError(f'Unsupported key: {key}')


class IbkrSubscriptionResolver(SubscriptionResolver):
    _register = [
        MarketData,
        AccountSummary,
        AccountLedger,
        MarketHistory,
        Orders,
        PriceLadder,
        Pnl,
        Trades,
        Unsubscription
    ]

    def __init__(self, account_id):
        self._account_id = account_id

    def _resolve_subscribing_event(self, event) -> str:
        if event.key in [IbkrWsKey.MARKET_DATA, IbkrWsKey.MARKET_HISTORY]:
            return make_binding_key(event.key, conid=event.conid)
        elif event.key in [IbkrWsKey.ACCOUNT_LEDGER, IbkrWsKey.ACCOUNT_SUMMARY]:
            return make_binding_key(event.key, account_id=event.account_id)
        elif event.key in [IbkrWsKey.PRICE_LADDER]:
            return make_binding_key(event.key, conid=event.conid, account_id=event.account_id, exchange=event.exchange)
        elif event.key in [IbkrWsKey.ORDERS, IbkrWsKey.PNL, IbkrWsKey.TRADES]:
            return make_binding_key(event.key)
        else:
            raise ValueError(f'Unsupported event: {event}')

    def _resolve_unsubscribing_event(self, event) -> str:
        return make_binding_key(event.target_key, event.conid, self._account_id)

    def resolve_binding_key(self, event) -> Tuple[bool, str] | Tuple[None, None]:
        if type(event) not in self._register:
            return None, None

        if isinstance(event, Unsubscription):
            return False, self._resolve_unsubscribing_event(event)
        else:
            return True, self._resolve_subscribing_event(event)


class IbkrSubscription(Subscription):
    key: IbkrWsKey

    @property
    def topic(self) -> str:
        return self.key.topic


class AccountSummarySubscription(IbkrSubscription):
    key: IbkrWsKey = IbkrWsKey.ACCOUNT_SUMMARY
    account_id: str

    def subscribe_payload(self) -> str:
        return f'ssd+{self.account_id}'

    def unsubscribe_payload(self) -> str:
        return f'usd+{self.account_id}'

    @property
    def confirms_subscribe(self) -> bool:
        return True

    @property
    def confirms_unsubscribe(self) -> bool:
        return True

    def binding_key(self):
        return make_binding_key(self.key, account_id=self.account_id)


class AccountLedgerSubscription(IbkrSubscription):
    key: IbkrWsKey = IbkrWsKey.ACCOUNT_LEDGER
    account_id: str

    def subscribe_payload(self) -> str:
        return f'sld+{self.account_id}'

    def unsubscribe_payload(self) -> str:
        return f'uld+{self.account_id}'

    @property
    def confirms_subscribe(self) -> bool:
        return True

    @property
    def confirms_unsubscribe(self) -> bool:
        return True

    def binding_key(self):
        return make_binding_key(self.key, account_id=self.account_id)


class MarketDataSubscription(IbkrSubscription):
    key: IbkrWsKey = IbkrWsKey.MARKET_DATA
    conid: str
    fields: tuple[str, ...]

    def subscribe_payload(self) -> str:
        fields_str = json.dumps({"fields": list(self.fields)}, separators=(',', ':'))
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
        return make_binding_key(self.key, conid=self.conid)


class MarketHistorySubscription(IbkrSubscription):
    key: IbkrWsKey = IbkrWsKey.MARKET_HISTORY
    conid: str
    exchange: str = None
    period: str = None
    bar: str = None
    outside_rth: bool = None
    source: str = None
    format: str = None
    server_id: list = Field(default_factory=list) # uses list to allow writing despite frozen model

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
        return f'smh+{self.conid}+{json.dumps(data, separators=(',', ':'))}'

    def unsubscribe_payload(self) -> str:
        server_id = self.get_server_id()
        if server_id is None:
            raise RuntimeError(f'{self}: Unsubscribing from market history for conid={self.conid!r} without server_id. MarketHistorySubscription must have server_id set before unsubscribing.')
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

    def has_server_id(self) -> bool:
        return len(self.server_id) > 0

    def get_server_id(self):
        return self.server_id[0]

    def binding_key(self):
        return make_binding_key(self.key, conid=self.conid)


class OrdersSubscription(IbkrSubscription):
    key: IbkrWsKey = IbkrWsKey.ORDERS
    filter: str = None

    def subscribe_payload(self) -> str:
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
        return make_binding_key(self.key)


class PriceLadderSubscription(IbkrSubscription):
    key: IbkrWsKey = IbkrWsKey.PRICE_LADDER
    conid: str
    account_id: str
    exchange: str

    def subscribe_payload(self) -> str:
        return f'sbd+{self.account_id}+{self.conid}+{self.exchange}'

    def unsubscribe_payload(self) -> str:
        return f'ubd+{self.account_id}'

    @property
    def confirms_subscribe(self) -> bool:
        return False

    @property
    def confirms_unsubscribe(self) -> bool:
        return False

    def binding_key(self):
        return make_binding_key(self.key, conid=self.conid, account_id=self.account_id, exchange=self.exchange)


class PnlSubscription(IbkrSubscription):
    key: IbkrWsKey = IbkrWsKey.PNL

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
        return make_binding_key(self.key)


class TradesSubscription(IbkrSubscription):
    key: IbkrWsKey = IbkrWsKey.TRADES
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
        return make_binding_key(self.key)
