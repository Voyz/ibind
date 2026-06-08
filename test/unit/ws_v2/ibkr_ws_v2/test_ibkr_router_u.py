import json
from unittest.mock import patch

import pytest

from ibind import events
from ibind.ibkr_ws_v2.ibkr_router import IbkrRouter, get_ibkr_topic_event, parse_raw_message
from test.test_utils import capture_logs


class TestGetIbkrTopicEvent:
    @capture_logs()
    def test_valid_topics(self):
        """get_ibkr_topic_event returns correct event types for valid topics."""
        ## Arrange / Act / Assert
        assert get_ibkr_topic_event('sd') == events.AccountSummary
        assert get_ibkr_topic_event('ld') == events.AccountLedger
        assert get_ibkr_topic_event('md') == events.MarketData
        assert get_ibkr_topic_event('mh') == events.MarketHistory
        assert get_ibkr_topic_event('bd') == events.PriceLadder
        assert get_ibkr_topic_event('or') == events.Orders
        assert get_ibkr_topic_event('pl') == events.Pnl
        assert get_ibkr_topic_event('tr') == events.Trades

    @capture_logs()
    def test_invalid_topic_raises_error(self):
        """get_ibkr_topic_event raises ValueError for unknown topics."""
        ## Arrange / Act / Assert
        with pytest.raises(ValueError, match="No Ibkr event associated with topic 'xx'"):
            get_ibkr_topic_event('xx')


class TestParseRawMessage:
    @capture_logs()
    def test_message_with_topic_and_args(self):
        """parse_raw_message extracts topic and args from valid message."""
        ## Arrange
        raw_message = json.dumps({'topic': 'md', 'args': {'key': 'value'}})

        ## Act
        message, topic, arguments = parse_raw_message(raw_message)

        ## Assert
        assert message == {'topic': 'md', 'args': {'key': 'value'}}
        assert topic == 'md'
        assert arguments == {'key': 'value'}

    @capture_logs()
    def test_message_without_topic(self):
        """parse_raw_message returns None for topic and arguments when missing."""
        ## Arrange
        raw_message = json.dumps({'data': 'value'})

        ## Act
        message, topic, arguments = parse_raw_message(raw_message)

        ## Assert
        assert message == {'data': 'value'}
        assert topic is None
        assert arguments is None

    @capture_logs()
    def test_message_with_topic_no_args(self):
        """parse_raw_message returns empty dict for args when missing."""
        ## Arrange
        raw_message = json.dumps({'topic': 'sts'})

        ## Act
        message, topic, arguments = parse_raw_message(raw_message)

        ## Assert
        assert message == {'topic': 'sts'}
        assert topic == 'sts'
        assert arguments == {}


class TestIbkrRouterPreprocessMarketData:
    @capture_logs()
    def test_empty_data_returns_empty_list(self):
        """route returns empty list when market data conid is missing."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'smd+265598'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert result == []

    @capture_logs()
    def test_unwrap_disabled_returns_raw_data(self):
        """route returns raw data when unwrap is disabled."""
        ## Arrange
        router = IbkrRouter(unwrap_market_data=False)
        raw_message = json.dumps({'topic': 'smd+12345', 'conid': '12345', '31': '100.5'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.MarketData)
        assert result.conid == '12345'
        assert result.data == {'topic': 'smd+12345', 'conid': '12345', '31': '100.5'}

    @capture_logs()
    def test_unwrap_enabled_translates_keys(self):
        """route translates numeric keys to readable names when unwrap is enabled."""
        ## Arrange
        router = IbkrRouter(unwrap_market_data=True)
        raw_message = json.dumps({'topic': 'smd+12345', 'conid': 12345, '31': '100.5', '84': '99.0'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.MarketData)
        assert result.conid == '12345'
        assert result.data == {'last_price': '100.5', 'bid_price': '99.0'}


class TestIbkrRouterPreprocessMarketHistory:
    @capture_logs()
    def test_new_server_id_emits_server_id_event(self):
        """route emits ServerId event for new server_id."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'smh+265598', 'serverId': 'srv123', 'data': 'value'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert len(result) == 2
        assert isinstance(result[0], events.ServerId)
        assert result[0].conid == '265598'
        assert result[0].server_id == 'srv123'
        assert result[0].target_event_type == events.MarketHistory
        assert isinstance(result[1], events.MarketHistory)
        assert result[1].conid == '265598'

    @capture_logs()
    def test_existing_server_id_no_duplicate_event(self):
        """route does not emit duplicate ServerId events."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'smh+265598', 'serverId': 'srv123', 'data': 'value'})
        router.route(raw_message)

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert len(result) == 1
        assert isinstance(result[0], events.MarketHistory)

    @capture_logs()
    def test_no_server_id_only_market_history(self):
        """route emits only MarketHistory when serverId is missing."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'smh+265598', 'data': 'value'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert len(result) == 1
        assert isinstance(result[0], events.MarketHistory)
        assert result[0].conid == '265598'


class TestIbkrRouterPreprocessAccountLedger:
    @capture_logs()
    def test_multiple_entries_with_acct_code(self):
        """route creates events for ledger entries with acctCode."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({
            'topic': 'sld+123',
            'result': [
                {'acctCode': 'U123', 'balance': 1000},
                {'acctCode': 'U456', 'balance': 2000},
            ]
        })

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert len(result) == 2
        assert all(isinstance(e, events.AccountLedger) for e in result)
        assert result[0].account_id == 'U123'
        assert result[1].account_id == 'U456'

    @capture_logs()
    def test_entry_without_acct_code_skipped(self):
        """route skips ledger entries without acctCode."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({
            'topic': 'sld+123',
            'result': [
                {'acctCode': 'U123', 'balance': 1000},
                {'balance': 2000},
            ]
        })

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert len(result) == 1
        assert result[0].account_id == 'U123'


class TestIbkrRouterPreprocessAccountSummary:
    @capture_logs()
    def test_valid_summary_with_account_code(self):
        """route creates AccountSummary event."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({
            'topic': 'ssd+123',
            'result': [
                {'key': 'AccountCode', 'value': 'U123', 'timestamp': 1234567890},
                {'key': 'NetLiquidation', 'value': '50000', 'timestamp': 1234567890},
            ]
        })

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.AccountSummary)
        assert result.account_id == 'U123'
        assert result.data['NetLiquidation'] == {'value': '50000'}
        assert result.data['timestamp'] == 1234567890

    @capture_logs()
    def test_empty_entries_skipped(self):
        """route skips summary entries with no data after key/timestamp removal."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({
            'topic': 'ssd+123',
            'result': [
                {'key': 'AccountCode', 'value': 'U123', 'timestamp': 1234567890},
                {'key': 'EmptyKey', 'timestamp': 1234567890},
            ]
        })

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.AccountSummary)
        assert 'EmptyKey' not in result.data

    @capture_logs(expected_errors=['IbkrRouter(): Account code not found in account summary:'], partial_match=True)
    def test_missing_account_code_logs_error(self):
        """route logs error and returns empty list when AccountCode is missing."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({
            'topic': 'ssd+123',
            'result': [
                {'key': 'NetLiquidation', 'value': '50000', 'timestamp': 1234567890},
            ]
        })

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert result == []

    @capture_logs()
    def test_all_empty_entries_returns_empty_list(self):
        """route returns empty list when all summary entries are empty."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({
            'topic': 'ssd+123',
            'result': [
                {'key': 'EmptyKey1', 'timestamp': 1234567890},
                {'key': 'EmptyKey2', 'timestamp': 1234567890},
            ]
        })

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert result == []


class TestIbkrRouterPreprocessOrders:
    @capture_logs()
    def test_removes_color_fields(self):
        """route removes bgColor and fgColor from order data."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({
            'topic': 'sor+123',
            'args': [
                {'orderId': 1, 'bgColor': '#fff', 'fgColor': '#000'},
                {'orderId': 2, 'bgColor': '#aaa'},
            ]
        })

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.Orders)
        assert 'bgColor' not in result.data['args'][0]
        assert 'fgColor' not in result.data['args'][0]
        assert 'bgColor' not in result.data['args'][1]

    @capture_logs()
    def test_no_args_field(self):
        """route handles order data without args field."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'sor+123', 'orderId': 1})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.Orders)
        assert result.data == {'topic': 'sor+123', 'orderId': 1}


class TestIbkrRouterHandleSubscribedMessage:
    @capture_logs(expected_errors=['IbkrRouter(): Unhandled subscribed message:'], partial_match=True)
    def test_unhandled_event_type_logs_error(self):
        """route logs error for unhandled event types in _handle_subscribed_message."""
        ## Arrange
        router = IbkrRouter()

        ## Act
        with patch('ibind.ibkr_ws_v2.ibkr_router.get_ibkr_topic_event') as mock_get_event:
            mock_get_event.return_value = type('UnhandledEvent', (), {})
            result = router._handle_subscribed_message('sxx+123', {'data': 'test'})

        ## Assert
        assert result is None

    @capture_logs()
    def test_account_summary_topic(self):
        """route handles account summary topic correctly."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({
            'topic': 'ssd+123',
            'result': [
                {'key': 'AccountCode', 'value': 'U123', 'timestamp': 1234567890},
            ]
        })

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.AccountSummary)

    @capture_logs()
    def test_account_ledger_topic(self):
        """route handles account ledger topic correctly."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'sld+123', 'result': [{'acctCode': 'U123', 'balance': 1000}]})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert len(result) == 1
        assert isinstance(result[0], events.AccountLedger)

    @capture_logs()
    def test_market_data_topic(self):
        """route handles market data topic correctly."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'smd+265598', 'conid': 265598})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.MarketData)

    @capture_logs()
    def test_market_history_topic(self):
        """route handles market history topic correctly."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'smh+265598', 'serverId': 'srv123'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert len(result) == 2
        assert isinstance(result[0], events.ServerId)
        assert isinstance(result[1], events.MarketHistory)

    @capture_logs()
    def test_orders_topic(self):
        """route handles orders topic correctly."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'sor+123', 'args': [{'orderId': 1}]})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.Orders)

    @capture_logs()
    def test_pnl_topic(self):
        """route handles pnl topic correctly."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'spl+123', 'pnl': 1000})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.Pnl)

    @capture_logs()
    def test_trades_topic(self):
        """route handles trades topic correctly."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'str+123', 'trade': 'data'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.Trades)

    @capture_logs(expected_errors=['IbkrRouter(): topic "sxx+123" subscribed but lacking a handler.'], partial_match=True)
    def test_unknown_topic_creates_generic_event(self):
        """route creates GenericIbkrEvent for unknown subscribed topics."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'sxx+123', 'data': 'value'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.GenericIbkrEvent)

    def test_price_ladder_topic_unhandled(self):
        """route raises error for PriceLadder (missing required fields)."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'sbd+123', 'data': 'value'})

        ## Act / Assert
        with pytest.raises(Exception):
            router.route(raw_message)


class TestIbkrRouterHandleAccountUpdate:
    @capture_logs()
    def test_creates_account_update_event(self):
        """route creates AccountUpdate event."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'act', 'args': {'account': 'U123'}})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.AccountUpdate)
        assert result.data == {'account': 'U123'}


class TestIbkrRouterHandleAuthenticationStatus:
    @capture_logs()
    def test_authenticated_status(self):
        """route creates event for authenticated status."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'sts', 'args': {'authenticated': True}})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.AuthenticationStatus)
        assert result.authenticated is True

    @capture_logs()
    def test_competing_status(self):
        """route creates event for competing status."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'sts', 'args': {'competing': True}})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.AuthenticationStatus)
        assert result.competing is True

    @capture_logs()
    def test_ignored_status_messages(self):
        """route ignores expected status updates."""
        ## Arrange
        router = IbkrRouter()

        ## Act / Assert
        assert router.route(json.dumps({'topic': 'sts', 'args': {'message': ''}})) == []
        assert router.route(json.dumps({'topic': 'sts', 'args': {'fail': ''}})) == []
        assert router.route(json.dumps({'topic': 'sts', 'args': {'serverName': 'srv1'}})) == []
        assert router.route(json.dumps({'topic': 'sts', 'args': {'serverVersion': '1.0'}})) == []
        assert router.route(json.dumps({'topic': 'sts', 'args': {'username': 'user'}})) == []


class TestIbkrRouterHandleBulletin:
    @capture_logs()
    def test_creates_bulletin_event(self):
        """route creates Bulletin event."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'blt', 'bulletin': 'message'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.Bulletin)
        assert result.data == {'topic': 'blt', 'bulletin': 'message'}


class TestIbkrRouterHandleError:
    @capture_logs(expected_errors=["IbkrRouter(): on_message error: {'error': 'test error'}"])
    def test_logs_error_and_creates_event(self):
        """route logs error and creates IbkrError event."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'error': 'test error'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.IbkrError)
        assert result.data == {'error': 'test error'}


class TestIbkrRouterHandleNotification:
    @capture_logs()
    def test_creates_notification_events(self):
        """route creates Notification events for each notification."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'ntf', 'args': [{'id': 1, 'msg': 'notif1'}, {'id': 2, 'msg': 'notif2'}]})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert len(result) == 2
        assert all(isinstance(e, events.Notification) for e in result)
        assert result[0].data == {'id': 1, 'msg': 'notif1'}
        assert result[1].data == {'id': 2, 'msg': 'notif2'}


class TestIbkrRouterHandleMarketHistoryUnsubscribe:
    @capture_logs(error_level='INFO', expected_errors=['Received unsubscribing confirmation'], partial_match=True)
    def test_known_server_id_creates_unsubscription_event(self):
        """route creates Unsubscription event for known server_id."""
        ## Arrange
        router = IbkrRouter()
        router._server_id_conid_pairs[events.MarketHistory]['srv123'] = '265598'
        raw_message = json.dumps({'message': 'Unsubscribed srv123'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.Unsubscription)
        assert result.target_event_type == events.MarketHistory
        assert result.conid == '265598'

    @capture_logs(expected_errors=['IbkrRouter(): Unknown conid=None. Cannot mark the subscription as unsubscribed.'], partial_match=True)
    def test_known_server_id_none_conid_logs_warning(self):
        """route logs warning when conid is None."""
        ## Arrange
        router = IbkrRouter()
        router._server_id_conid_pairs[events.MarketHistory]['srv123'] = None
        raw_message = json.dumps({'message': 'Unsubscribed srv123'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert result == []

    @capture_logs(expected_errors=["IbkrRouter(): Received unsubscribing confirmation for unknown server_id='srv999'. Existing server_ids: {}"])
    def test_unknown_server_id_logs_warning(self):
        """route logs warning for unknown server_id."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'message': 'Unsubscribed srv999'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert result == []


class TestIbkrRouterHandleMessageWithoutTopic:
    @capture_logs(error_level='INFO', expected_errors=['Waiting for an active IBKR session'], partial_match=True)
    def test_waiting_for_session_message(self):
        """route creates WaitingForSession event."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'message': 'waiting for session'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.WaitingForSession)

    @capture_logs()
    def test_unsubscribed_summary_message(self):
        """route creates Unsubscription event for summary."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'result': 'unsubscribed from summary'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.Unsubscription)
        assert result.target_event_type == events.AccountSummary

    @capture_logs()
    def test_unsubscribed_ledger_message(self):
        """route creates Unsubscription event for ledger."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'result': 'unsubscribed from ledger'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.Unsubscription)
        assert result.target_event_type == events.AccountLedger

    @capture_logs(error_level='INFO', expected_errors=['Received unsubscribing confirmation'], partial_match=True)
    def test_unsubscribed_market_history_message(self):
        """route delegates to market history unsubscribe handler."""
        ## Arrange
        router = IbkrRouter()
        router._server_id_conid_pairs[events.MarketHistory]['srv123'] = '265598'
        raw_message = json.dumps({'message': 'Unsubscribed srv123'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.Unsubscription)

    @capture_logs(expected_errors=["IbkrRouter(): Unrecognised message without a topic: {'unknown': 'data'}"])
    def test_unrecognised_message_creates_generic_event(self):
        """route creates GenericIbkrEvent for unrecognised messages."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'unknown': 'data'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.GenericIbkrEvent)
        assert result.message == {'unknown': 'data'}


class TestIbkrRouterRoute:
    @capture_logs(error_level='INFO')
    def test_logs_raw_message_when_enabled(self):
        """route logs raw message when log_raw_messages is enabled."""
        ## Arrange
        router = IbkrRouter(log_raw_messages=True)
        raw_message = json.dumps({'topic': 'system', 'data': 'value'})

        ## Act
        router.route(raw_message)

        ## Assert

    @capture_logs(expected_errors=['IbkrRouter(): on_message error:'], partial_match=True)
    def test_error_in_data(self):
        """route handles error in data."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'error': 'test error'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.IbkrError)

    @capture_logs(error_level='INFO', expected_errors=['Waiting for an active IBKR session'], partial_match=True)
    def test_message_without_topic(self):
        """route handles message without topic."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'message': 'waiting for session'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.WaitingForSession)

    @capture_logs()
    def test_tic_topic(self):
        """route handles tic topic."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'tic', 'data': 'value'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.System)

    @capture_logs()
    def test_system_topic(self):
        """route handles system topic."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'system', 'data': 'value'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.System)

    @capture_logs()
    def test_act_topic(self):
        """route handles act topic."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'act', 'args': {'account': 'U123'}})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.AccountUpdate)

    @capture_logs()
    def test_blt_topic(self):
        """route handles blt topic."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'blt', 'data': 'bulletin'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.Bulletin)

    @capture_logs()
    def test_ntf_topic(self):
        """route handles ntf topic."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'ntf', 'args': [{'id': 1}]})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert len(result) == 1
        assert isinstance(result[0], events.Notification)

    @capture_logs()
    def test_sts_topic(self):
        """route handles sts topic."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'sts', 'args': {'authenticated': True}})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.AuthenticationStatus)

    @capture_logs(expected_errors=['IbkrRouter(): on_message error:'], partial_match=True)
    def test_error_topic(self):
        """route handles error topic."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'error', 'error': 'test'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.IbkrError)

    @capture_logs(expected_errors=['IbkrRouter(): on_message error:'], partial_match=True)
    def test_error_topic_with_args(self):
        """route handles error topic with args."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'error', 'args': {'code': 500}, 'error': 'test error'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.IbkrError)

    @capture_logs(expected_errors=['IbkrRouter(): on_message error:'], partial_match=True)
    def test_error_topic_without_error_field(self):
        """route handles error topic without error field in data."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'error', 'args': {'message': 'something went wrong'}})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.IbkrError)

    @capture_logs()
    def test_subscribed_message_topic(self):
        """route handles subscribed message topics."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'smd+265598', 'conid': 265598})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.MarketData)

    @capture_logs(expected_errors=['IbkrRouter(): topic "sxx+123" subscribed but lacking a handler.'], partial_match=True)
    def test_unknown_subscribed_topic_creates_generic_event(self):
        """route creates GenericIbkrEvent for unknown subscribed topics."""
        ## Arrange
        router = IbkrRouter()
        raw_message = json.dumps({'topic': 'sxx+123'})

        ## Act
        result = router.route(raw_message)

        ## Assert
        assert isinstance(result, events.GenericIbkrEvent)
        assert result.topic == 'sxx+123'
