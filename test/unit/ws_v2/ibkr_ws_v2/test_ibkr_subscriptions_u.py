import json
from unittest.mock import MagicMock

import pytest

from ibind import WsState
from ibind.events import AccountLedger, MarketData, MarketHistory, Orders, PriceLadder, Pnl, Trades, AccountSummary, Unsubscription
from ibind.ibkr_ws_v2.ibkr_subscriptions import (
    make_binding_key,
    IbkrSubscriptionResolver,
    AccountSummarySubscription,
    AccountLedgerSubscription,
    MarketDataSubscription,
    MarketHistorySubscription,
    OrdersSubscription,
    PriceLadderSubscription,
    PnlSubscription,
    TradesSubscription,
)
from ibind.ws_v2.ws_subscriptions import BindingStatus, SubscriptionConflictError, SubscriptionController
from test.test_utils import capture_logs
from ibind.ibkr_ws_v2.ibkr_events import IbkrTopicEvent
from ibind.events import WsOpen


class TestMakeBindingKey:
    @pytest.mark.parametrize(
        'event_type,kwargs,expected',
        [
            (MarketData, {'conid': '12345'}, 'md+12345'),
            (MarketHistory, {'conid': '67890'}, 'mh+67890'),
            (AccountLedger, {'account_id': 'ACC123'}, 'ld+ACC123'),
            (AccountSummary, {'account_id': 'ACC456'}, 'sd+ACC456'),
            (PriceLadder, {'conid': '11111', 'account_id': 'ACC789'}, 'bd+ACC789'),
            (PriceLadder, {'conid': '11111', 'account_id': 'ACC789', 'exchange': 'NASDAQ'}, 'bd+ACC789'),
            (Orders, {}, 'or'),
            (Pnl, {}, 'pl'),
            (Trades, {}, 'tr'),
        ],
    )
    @capture_logs()
    def test_binding_key(self, event_type, kwargs, expected):
        """make_binding_key generates correct key for event type."""
        ## Act
        result = make_binding_key(event_type, **kwargs)

        ## Assert
        assert result == expected

    @capture_logs()
    def test_unsupported_event_type(self):
        """make_binding_key raises ValueError for unsupported event type."""

        ## Arrange
        class UnsupportedEvent:
            topic = 'unsupported'

        ## Act & Assert
        with pytest.raises(ValueError, match='Unsupported event type'):
            make_binding_key(UnsupportedEvent)


class TestIbkrSubscriptionResolver:
    @pytest.fixture
    def resolver(self):
        return IbkrSubscriptionResolver(account_id='TEST_ACCOUNT')

    @pytest.mark.parametrize(
        'event_factory,expected_binding_key',
        [
            (lambda: MarketData(conid='12345', data={}), 'md+12345'),
            (lambda: MarketHistory(conid='67890', data={}), 'mh+67890'),
            (lambda: AccountLedger(account_id='ACC123', data={}), 'ld+ACC123'),
            (lambda: AccountSummary(account_id='ACC456', data={}), 'sd+ACC456'),
            (lambda: PriceLadder(account_id='ACC789', conid='11111', exchange=None, data=[]), 'bd+ACC789'),
            (lambda: Orders(data={}), 'or'),
            (lambda: Pnl(data={}), 'pl'),
            (lambda: Trades(data={}), 'tr'),
        ],
    )
    @capture_logs()
    def test_resolve_event(self, resolver, event_factory, expected_binding_key):
        """IbkrSubscriptionResolver resolves event correctly."""
        ## Arrange
        event = event_factory()

        ## Act
        is_active, binding_key = resolver.resolve_binding_key(event)

        ## Assert
        assert is_active is True
        assert binding_key == expected_binding_key

    @capture_logs()
    def test_resolve_unsubscription_event(self, resolver):
        """IbkrSubscriptionResolver resolves Unsubscription event."""
        ## Arrange
        event = Unsubscription(target_event_type=MarketData, conid='12345')

        ## Act
        is_active, binding_key = resolver.resolve_binding_key(event)

        ## Assert
        assert is_active is False
        assert binding_key == 'md+12345'

    @capture_logs()
    def test_resolve_unsubscription_uses_resolver_account_id(self, resolver):
        """IbkrSubscriptionResolver uses resolver account_id for Unsubscription."""
        ## Arrange
        event = Unsubscription(target_event_type=AccountLedger, conid=None)

        ## Act
        is_active, binding_key = resolver.resolve_binding_key(event)

        ## Assert
        assert is_active is False
        assert binding_key == 'ld+TEST_ACCOUNT'

    @capture_logs()
    def test_resolve_non_ibkr_event(self, resolver):
        """IbkrSubscriptionResolver returns None for non-IBKR events."""
        ## Arrange
        event = WsOpen(previous_state=WsState.STARTING, current_state=WsState.OPEN)

        ## Act
        is_active, binding_key = resolver.resolve_binding_key(event)

        ## Assert
        assert is_active is None
        assert binding_key is None

    @capture_logs()
    def test_resolve_unsupported_event(self, resolver):
        """IbkrSubscriptionResolver raises ValueError for unsupported event."""
        ## Arrange

        class UnsupportedTopicEvent(IbkrTopicEvent):
            topic = 'unsupported'
            data: dict

        event = UnsupportedTopicEvent(data={})

        ## Act & Assert
        with pytest.raises(ValueError, match='Unsupported event'):
            resolver.resolve_binding_key(event)


class TestAccountSummarySubscription:
    @pytest.fixture
    def sub(self):
        return AccountSummarySubscription(account_id='ACC123')

    @capture_logs()
    def test_subscribe_payload(self, sub):
        """AccountSummarySubscription generates correct subscribe payload."""
        assert sub.subscribe_payload() == 'ssd+ACC123'

    @capture_logs()
    def test_unsubscribe_payload(self, sub):
        """AccountSummarySubscription generates correct unsubscribe payload."""
        assert sub.unsubscribe_payload() == 'usd+ACC123'

    @capture_logs()
    def test_topic(self, sub):
        """AccountSummarySubscription has correct topic."""
        assert sub.topic == 'sd'

    @capture_logs()
    def test_confirms_subscribe(self, sub):
        """AccountSummarySubscription confirms subscribe."""
        assert sub.confirms_subscribe is True

    @capture_logs()
    def test_confirms_unsubscribe(self, sub):
        """AccountSummarySubscription confirms unsubscribe."""
        assert sub.confirms_unsubscribe is True

    @capture_logs()
    def test_binding_key(self, sub):
        """AccountSummarySubscription generates correct binding key."""
        assert sub.binding_key() == 'sd+ACC123'


class TestAccountLedgerSubscription:
    @pytest.fixture
    def sub(self):
        return AccountLedgerSubscription(account_id='ACC456')

    @capture_logs()
    def test_subscribe_payload(self, sub):
        """AccountLedgerSubscription generates correct subscribe payload."""
        assert sub.subscribe_payload() == 'sld+ACC456'

    @capture_logs()
    def test_unsubscribe_payload(self, sub):
        """AccountLedgerSubscription generates correct unsubscribe payload."""
        assert sub.unsubscribe_payload() == 'uld+ACC456'

    @capture_logs()
    def test_topic(self, sub):
        """AccountLedgerSubscription has correct topic."""
        assert sub.topic == 'ld'

    @capture_logs()
    def test_confirms_subscribe(self, sub):
        """AccountLedgerSubscription confirms subscribe."""
        assert sub.confirms_subscribe is True

    @capture_logs()
    def test_confirms_unsubscribe(self, sub):
        """AccountLedgerSubscription confirms unsubscribe."""
        assert sub.confirms_unsubscribe is True

    @capture_logs()
    def test_binding_key(self, sub):
        """AccountLedgerSubscription generates correct binding key."""
        assert sub.binding_key() == 'ld+ACC456'


class TestMarketDataSubscription:
    @pytest.fixture
    def sub(self):
        return MarketDataSubscription(conid='12345', fields=['31'])

    @capture_logs()
    def test_subscribe_payload(self):
        """MarketDataSubscription generates correct subscribe payload."""
        sub = MarketDataSubscription(conid='12345', fields=['31', '84', '86'])
        assert sub.subscribe_payload() == 'smd+12345+{"fields":["31","84","86"]}'

    @capture_logs()
    def test_unsubscribe_payload(self, sub):
        """MarketDataSubscription generates correct unsubscribe payload."""
        assert sub.unsubscribe_payload() == 'umd+12345+{}'

    @capture_logs()
    def test_topic(self, sub):
        """MarketDataSubscription has correct topic."""
        assert sub.topic == 'md'

    @capture_logs()
    def test_confirms_subscribe(self, sub):
        """MarketDataSubscription confirms subscribe."""
        assert sub.confirms_subscribe is True

    @capture_logs()
    def test_confirms_unsubscribe(self, sub):
        """MarketDataSubscription does not confirm unsubscribe."""
        assert sub.confirms_unsubscribe is False

    @capture_logs()
    def test_binding_key(self, sub):
        """MarketDataSubscription generates correct binding key."""
        assert sub.binding_key() == 'md+12345'


class TestMarketHistorySubscription:
    @pytest.fixture
    def sub(self):
        return MarketHistorySubscription(conid='67890')

    @capture_logs()
    def test_subscribe_payload_minimal(self, sub):
        """MarketHistorySubscription generates correct subscribe payload with minimal params."""
        assert sub.subscribe_payload() == 'smh+67890+{}'

    @capture_logs()
    def test_subscribe_payload_full(self):
        """MarketHistorySubscription generates correct subscribe payload with all params."""
        sub = MarketHistorySubscription(conid='67890', exchange='NASDAQ', period='1d', bar='5min', outside_rth=True, source='trades', format='json')
        result = sub.subscribe_payload()
        payload_data = json.loads(result.split('+', 2)[2])
        assert result.startswith('smh+67890+')
        assert payload_data == {'exchange': 'NASDAQ', 'period': '1d', 'bar': '5min', 'outside_rth': True, 'source': 'trades', 'format': 'json'}

    @capture_logs()
    def test_unsubscribe_payload_with_server_id(self, sub):
        """MarketHistorySubscription generates correct unsubscribe payload with server_id."""
        sub.set_server_id('server_123')
        assert sub.unsubscribe_payload() == 'umh+server_123'

    @capture_logs()
    def test_unsubscribe_payload_without_server_id_raises(self, sub):
        """MarketHistorySubscription raises RuntimeError when unsubscribing without server_id."""
        with pytest.raises((RuntimeError, IndexError)):
            sub.unsubscribe_payload()

    @capture_logs()
    def test_topic(self, sub):
        """MarketHistorySubscription has correct topic."""
        assert sub.topic == 'mh'

    @capture_logs()
    def test_confirms_subscribe(self, sub):
        """MarketHistorySubscription confirms subscribe."""
        assert sub.confirms_subscribe is True

    @capture_logs()
    def test_confirms_unsubscribe(self, sub):
        """MarketHistorySubscription confirms unsubscribe."""
        assert sub.confirms_unsubscribe is True

    @capture_logs()
    def test_set_server_id(self, sub):
        """MarketHistorySubscription sets server_id correctly."""
        sub.set_server_id('server_456')
        assert sub.has_server_id() is True
        assert sub.get_server_id() == 'server_456'

    @capture_logs()
    def test_set_server_id_twice_raises(self, sub):
        """MarketHistorySubscription raises ValueError when setting server_id twice."""
        sub.set_server_id('server_123')
        with pytest.raises(ValueError, match='Server ID already set'):
            sub.set_server_id('server_456')

    @capture_logs()
    def test_has_server_id_false_initially(self, sub):
        """MarketHistorySubscription has_server_id returns False initially."""
        assert sub.has_server_id() is False

    @capture_logs()
    def test_get_server_id_without_setting(self, sub):
        """MarketHistorySubscription get_server_id returns None when not set."""
        assert sub.get_server_id() is None

    @capture_logs()
    def test_binding_key(self, sub):
        """MarketHistorySubscription generates correct binding key."""
        assert sub.binding_key() == 'mh+67890'


class TestOrdersSubscription:
    @pytest.fixture
    def sub(self):
        return OrdersSubscription()

    @capture_logs()
    def test_subscribe_payload_without_filter(self, sub):
        """OrdersSubscription generates correct subscribe payload without filter."""
        assert sub.subscribe_payload() == 'sor+{}'

    @capture_logs()
    def test_subscribe_payload_with_filter(self):
        """OrdersSubscription generates correct subscribe payload with filter."""
        sub = OrdersSubscription(filter='inactive')
        assert sub.subscribe_payload() == 'sor+{"filters": ["inactive"]}'

    @capture_logs()
    def test_unsubscribe_payload(self, sub):
        """OrdersSubscription generates correct unsubscribe payload."""
        assert sub.unsubscribe_payload() == 'uor+{}'

    @capture_logs()
    def test_topic(self, sub):
        """OrdersSubscription has correct topic."""
        assert sub.topic == 'or'

    @capture_logs()
    def test_confirms_subscribe(self, sub):
        """OrdersSubscription does not confirm subscribe."""
        assert sub.confirms_subscribe is False

    @capture_logs()
    def test_confirms_unsubscribe(self, sub):
        """OrdersSubscription does not confirm unsubscribe."""
        assert sub.confirms_unsubscribe is False

    @capture_logs()
    def test_binding_key(self, sub):
        """OrdersSubscription generates correct binding key."""
        assert sub.binding_key() == 'or'


class TestPriceLadderSubscription:
    @pytest.fixture
    def sub(self):
        return PriceLadderSubscription(conid='11111', account_id='ACC789', exchange='NASDAQ')

    @capture_logs()
    def test_subscribe_payload(self, sub):
        """PriceLadderSubscription generates correct subscribe payload."""
        assert sub.subscribe_payload() == 'sbd+ACC789+11111+NASDAQ'


    @capture_logs()
    def test_subscribe_payload_without_exchange(self):
        """PriceLadderSubscription omits the optional exchange cleanly."""
        sub = PriceLadderSubscription(conid='11111', account_id='ACC789')
        assert sub.subscribe_payload() == 'sbd+ACC789+11111'

    @capture_logs()
    def test_unsubscribe_payload(self, sub):
        """PriceLadderSubscription generates correct unsubscribe payload."""
        assert sub.unsubscribe_payload() == 'ubd+ACC789'

    @capture_logs()
    def test_topic(self, sub):
        """PriceLadderSubscription has correct topic."""
        assert sub.topic == 'bd'

    @capture_logs()
    def test_confirms_subscribe(self, sub):
        """PriceLadderSubscription does not confirm subscribe."""
        assert sub.confirms_subscribe is False

    @capture_logs()
    def test_confirms_unsubscribe(self, sub):
        """PriceLadderSubscription does not confirm unsubscribe."""
        assert sub.confirms_unsubscribe is False

    @capture_logs()
    def test_binding_key(self, sub):
        """PriceLadderSubscription generates correct binding key."""
        assert sub.binding_key() == 'bd+ACC789'

    @capture_logs()
    def test_different_sources_for_same_account_share_binding(self):
        """Only one Price Ladder source can be active for an account."""
        first = PriceLadderSubscription(conid='11111', account_id='ACC789', exchange='NASDAQ')
        second = PriceLadderSubscription(conid='22222', account_id='ACC789', exchange='NYSE')
        assert first.binding_key() == second.binding_key() == 'bd+ACC789'

    @capture_logs()
    def test_different_source_for_active_account_raises_conflict(self):
        """Changing ladder source requires first unsubscribing the account binding."""
        controller = SubscriptionController(
            send_payload=MagicMock(return_value=True),
            emitter=MagicMock(),
            subscription_resolver=IbkrSubscriptionResolver(account_id='ACC789'),
        )
        first = PriceLadderSubscription(conid='11111', account_id='ACC789', exchange='NASDAQ')
        second = PriceLadderSubscription(conid='22222', account_id='ACC789', exchange='NYSE')
        controller.subscribe(first)
        controller._bindings[first.binding_key()].status = BindingStatus.ACTIVE

        with pytest.raises(SubscriptionConflictError, match='must be unsubscribed first'):
            controller.subscribe(second)



class TestPnlSubscription:
    @pytest.fixture
    def sub(self):
        return PnlSubscription()

    @capture_logs()
    def test_subscribe_payload(self, sub):
        """PnlSubscription generates correct subscribe payload."""
        assert sub.subscribe_payload() == 'spl'

    @capture_logs()
    def test_unsubscribe_payload(self, sub):
        """PnlSubscription generates correct unsubscribe payload."""
        assert sub.unsubscribe_payload() == 'upl'

    @capture_logs()
    def test_topic(self, sub):
        """PnlSubscription has correct topic."""
        assert sub.topic == 'pl'

    @capture_logs()
    def test_confirms_subscribe(self, sub):
        """PnlSubscription confirms subscribe."""
        assert sub.confirms_subscribe is True

    @capture_logs()
    def test_confirms_unsubscribe(self, sub):
        """PnlSubscription does not confirm unsubscribe."""
        assert sub.confirms_unsubscribe is False

    @capture_logs()
    def test_binding_key(self, sub):
        """PnlSubscription generates correct binding key."""
        assert sub.binding_key() == 'pl'


class TestTradesSubscription:
    @pytest.fixture
    def sub(self):
        return TradesSubscription()

    @capture_logs()
    def test_subscribe_payload_minimal(self, sub):
        """TradesSubscription generates correct subscribe payload with minimal params."""
        assert sub.subscribe_payload() == 'str+{}'

    @capture_logs()
    def test_subscribe_payload_with_realtime_updates_only(self):
        """TradesSubscription generates correct subscribe payload with realtime_updates_only."""
        sub = TradesSubscription(realtime_updates_only=True)
        assert sub.subscribe_payload() == 'str+{"realtime_updates_only":true}'

    @capture_logs()
    def test_subscribe_payload_with_days(self):
        """TradesSubscription generates correct subscribe payload with days."""
        sub = TradesSubscription(days=7)
        assert sub.subscribe_payload() == 'str+{"days":7}'

    @capture_logs()
    def test_subscribe_payload_with_both_params(self):
        """TradesSubscription generates correct subscribe payload with both params."""
        sub = TradesSubscription(realtime_updates_only=False, days=14)
        result = sub.subscribe_payload()
        payload_data = json.loads(result.split('+', 1)[1])
        assert result.startswith('str+')
        assert payload_data == {'realtime_updates_only': False, 'days': 14}

    @capture_logs()
    def test_unsubscribe_payload(self, sub):
        """TradesSubscription generates correct unsubscribe payload."""
        assert sub.unsubscribe_payload() == 'utr'

    @capture_logs()
    def test_topic(self, sub):
        """TradesSubscription has correct topic."""
        assert sub.topic == 'tr'

    @capture_logs()
    def test_confirms_subscribe(self, sub):
        """TradesSubscription confirms subscribe."""
        assert sub.confirms_subscribe is True

    @capture_logs()
    def test_confirms_unsubscribe(self, sub):
        """TradesSubscription does not confirm unsubscribe."""
        assert sub.confirms_unsubscribe is False

    @capture_logs()
    def test_binding_key(self, sub):
        """TradesSubscription generates correct binding key."""
        assert sub.binding_key() == 'tr'
