import json
import logging
from threading import Thread
from typing import Optional
from unittest import TestCase
from unittest.mock import MagicMock, patch, call

import requests

from ibind import Result
from ibind.client.ibkr_client import IbkrClient
from ibind.client.ibkr_ws_client import IbkrWsClient, IbkrSubscriptionProcessor, IbkrWsKey
from ibind.support.logs import project_logger
from test.integration.base.websocketapp_mock import create_wsa_mock, init_wsa_mock
from test_utils import RaiseLogsContext, SafeAssertLogs


class TestPreprocessRawMessage(TestCase):
    def setUp(self):
        self.url = 'wss://localhost:5000/v1/api/ws'

        self.ws_client = IbkrWsClient(
            url=self.url,
            ibkr_client=None,
            account_id=None,
            subscription_processor_class=lambda: None,
        )

    def test_preprocess_with_well_formed_message(self):
        raw_message = json.dumps({'topic': 'actABC', 'args': {'key': 'value'}})
        expected_result = (
            {'topic': 'actABC', 'args': {'key': 'value'}},  # message
            'actABC',  # topic
            {'key': 'value'},  # data
            'a',  # subscribed
            'ctABC',  # channel
        )
        self.assertEqual(self.ws_client._preprocess_raw_message(raw_message), expected_result)

    def test_preprocess_with_unsubscribed_message(self):
        raw_message = json.dumps({'message': 'Unsubscribed'})
        expected_result = ({'message': 'Unsubscribed'}, None, None, None, None)
        self.assertEqual(self.ws_client._preprocess_raw_message(raw_message), expected_result)


class TestIbkrWsClient(TestCase):
    # Assuming IbkrWsClient is the class containing preprocess_raw_message

    def setUp(self):
        # Assuming similar initialization parameters as in WsClient
        self.url = 'wss://localhost:5000/v1/api/ws'
        self.max_reconnect_attempts = 4
        self.max_ping_interval = 38

        self.url_rest = 'https://localhost:5000'
        self.account_id = 'TEST_ACCOUNT_ID'
        self.timeout = 8
        self.max_retries = 4
        self.subscription_retries = 3
        self.client = MagicMock(
            spec=IbkrClient(
                url=self.url_rest,
                account_id=self.account_id,
                timeout=self.timeout,
                max_retries=self.max_retries,
            )
        )

        self.client.tickle.return_value.data = {'session': 'TEST_COOKIE'}

        self.SubscriptionProcessorClass = IbkrSubscriptionProcessor

        # Initialize the IbkrWsClient
        self.ws_client = IbkrWsClient(
            url=self.url,
            ibkr_client=self.client,
            account_id=self.account_id,
            subscription_processor_class=self.SubscriptionProcessorClass,
            subscription_retries=self.subscription_retries,
            subscription_timeout=0.01,
            cacert=False,
            timeout=0.01,
            max_connection_attempts=self.max_reconnect_attempts,
            max_ping_interval=self.max_ping_interval,
        )

        self.wsa_mock = create_wsa_mock()
        self.thread_mock = MagicMock(spec=Thread)
        self.thread_mock.start.side_effect = lambda: self.ws_client._run_websocket(self.wsa_mock)

        self.conid = 265598
        self.update_time = 5678765456

    def run_in_test_context(self, fn, expected_errors: list[str] = None, expect_logs: bool = True):
        with patch('ibind.base.ws_client.WebSocketApp', side_effect=lambda *args, **kwargs: init_wsa_mock(self.wsa_mock, *args, **kwargs)), \
                patch('ibind.base.ws_client.Thread', return_value=self.thread_mock) as new_thread_mock, \
                SafeAssertLogs(self, 'ibind', level='DEBUG', logger_level='DEBUG', no_logs=not expect_logs) as cm, \
                RaiseLogsContext(self, 'ibind', level='WARNING', expected_errors=expected_errors):  # fmt: skip
            ws_client_logger = project_logger('ws_client')
            old_level = ws_client_logger.getEffectiveLevel()
            ws_client_logger.setLevel(logging.WARNING)

            self.new_thread_mock = new_thread_mock
            try:
                rv = fn()
            except:
                raise
            finally:
                ws_client_logger.setLevel(old_level)

        return cm, rv

    def _send_payload(self, payload: dict, expected_errors: list[str] = None, expect_logs: bool = True):
        def run():
            success = self.ws_client.start()
            raw_payload = json.dumps(payload)
            self.ws_client.send(raw_payload)
            self.ws_client.shutdown()
            return success

        return self.run_in_test_context(run, expected_errors=expected_errors, expect_logs=expect_logs)

    def _subscribe(self, request: dict, response: Optional[dict], expected_errors: list[str] = None, expect_logs: bool = True):
        def run():
            def override_on_message(wsa_mock: MagicMock, message: str):
                if response is None:
                    return
                raw_message = json.dumps(response)
                wsa_mock.__on_message__(wsa_mock, raw_message)

            self.ws_client.start()
            self.wsa_mock._on_message.side_effect = override_on_message
            rv = self.ws_client.subscribe(
                **{'channel': request.get('channel'), 'data': request.get('data'), 'needs_confirmation': request.get('needs_confirmation')}
            )
            self.ws_client.unsubscribe(
                **{'channel': request.get('channel'), 'data': request.get('data'), 'needs_confirmation': request.get('confirms_unsubscription')}
            )
            self.ws_client.shutdown()
            return rv

        return self.run_in_test_context(run, expected_errors=expected_errors, expect_logs=expect_logs)

    def test_on_message_system_heartbeat(self):
        hb = 12345678
        cm, success = self._send_payload({'topic': 'system', 'hb': hb}, expect_logs=False)
        # print("\n".join([r.msg for r in cm.records]))
        self.assertEqual(self.ws_client._last_heartbeat, hb)

    def test_on_message_act_account_mismatch(self):
        message_data = {'topic': 'act', 'args': {'accounts': ['OTHER_ACCOUNT_ID']}}
        expected_errors = ["IbkrWsClient: Account ID mismatch: expected=TEST_ACCOUNT_ID, received=['OTHER_ACCOUNT_ID']"]

        cm, success = self._send_payload(message_data, expected_errors=expected_errors)
        self.assertEqual(expected_errors, [r.msg for r in cm.records])

    def test_on_message_blt(self):
        bulletin_message = {'topic': 'blt', 'args': {'bulletin_key': 'some_info'}}

        with patch.object(self.ws_client, '_handle_bulletin', MagicMock()) as mock_handle_bulletin:
            cm, success = self._send_payload(bulletin_message, expect_logs=False)
            mock_handle_bulletin.assert_called_once_with(bulletin_message)

    def test_on_message_sts_unauthenticated(self):
        message_data = {'topic': 'sts', 'args': {'authenticated': False}}
        session_id = 6545676

        expected_errors = ["IbkrWsClient: Status unauthenticated: {'authenticated': False}", 'IbkrWsClient: Not authenticated, closing WebSocketApp']

        response_mock = MagicMock(spec=requests.Response)
        response_mock.status_code = 200
        response_mock.json.return_value = {'session': session_id, 'data_to_be_ignored': '1234'}

        self.client.tickle.return_value = Result(data=response_mock.json.return_value)

        with patch('ibind.base.rest_client.requests') as requests_mock:
            requests_mock.request.return_value = response_mock
            cm, success = self._send_payload(message_data, expected_errors=expected_errors)

        self.assertEqual(expected_errors, [r.msg for r in cm.records])
        self.assertFalse(self.ws_client._authenticated)

    def test_on_message_sts_authenticated(self):
        message_data = {'topic': 'sts', 'args': {'authenticated': True}}
        cm, success = self._send_payload(message_data, expect_logs=False)

    def test_on_message_error(self):
        message_data = {'topic': 'error', 'args': {'error_key': 'error_details'}}
        expected_errors = [f'IbkrWsClient: Error message:  {message_data}']

        cm, success = self._send_payload(message_data, expected_errors=expected_errors)
        self.assertEqual(expected_errors, [r.msg for r in cm.records])

    def test_on_message_no_topic_handler(self):
        message_data = {'topic': 'unrecognized_topic', 'args': {'some_key': 'some_value'}}
        expected_errors = [f'IbkrWsClient: Topic "{message_data["topic"]}" unrecognised. Message: {message_data}']

        cm, success = self._send_payload(message_data, expected_errors=expected_errors)
        self.assertEqual(expected_errors, [r.msg for r in cm.records])

    def test_on_message_handled_without_subscription(self):
        message_data = {'topic': 'some_topic', 'args': {'channel': 'XYZ', 'data': 'info'}}
        expected_errors = [
            f'IbkrWsClient: Handled a channel "{message_data["topic"][1:]}" message that is missing a subscription. Message: {message_data}'
        ]

        with patch.object(self.ws_client, '_handle_subscribed_message', return_value=True):
            cm, success = self._send_payload(message_data, expected_errors=expected_errors)

        self.assertEqual(expected_errors, [r.msg for r in cm.records])

    def _logs_subscriptions(self, full_channel, data=None, needs_confirmation_sub: bool = False, needs_confirmation_unsub: bool = True):
        return [
            f'IbkrWsClient: Subscribed: s{full_channel}{"" if data is None else f"+{json.dumps(data)}"}{"" if not needs_confirmation_sub else " without confirmation."}',
            f'IbkrWsClient: Unsubscribed: u{full_channel}+{json.dumps(data if data is not None else {})}{"" if not needs_confirmation_unsub else " without confirmation."}',
        ]

    def test_on_message_market_data_channel_handling(self):
        queue = self.ws_client.new_queue_accessor(IbkrWsKey.MARKET_DATA)
        full_channel = f'{queue.key.channel}+{self.conid}'
        request = {'channel': f'{full_channel}', 'data': {'fields': ['55', '71', '84', '86', '88', '85', '87', '7295', '7296', '70']}}
        response = {
            'topic': f's{full_channel}',
            'conid': self.conid,
            '_updated': self.update_time,
            55: 'AAPL',
            70: '195.34',
            71: '193.67',
            87: '24.2M',
            7295: '194.10',
            84: '195.25',
            86: '195.26',
            88: '3,500',
            85: '500',
            6508: '&serviceID1=122&serviceID2=123&serviceID3=203&serviceID4=775&serviceID5=204&serviceID6=206&serviceID7=108&serviceID8=109',
        }

        self.assertTrue(queue.empty(), 'Queue should be empty')

        with patch.object(self.ws_client, 'has_subscription', return_value=True):
            cm, success = self._subscribe(request, response)
            self.assertTrue(success)

        self.assertEqual(self._logs_subscriptions(full_channel, request['data']), [r.msg for r in cm.records])

        self.assertEqual(
            {
                self.conid: {
                    '_updated': self.update_time,
                    'conid': self.conid,
                    'topic': f'smd+{self.conid}',
                    'ask_price': '195.26',
                    'ask_size': '500',
                    'bid_price': '195.25',
                    'bid_size': '3,500',
                    'high': '195.34',
                    'low': '193.67',
                    'open': '194.10',
                    'service_params': '&serviceID1=122&serviceID2=123&serviceID3=203&serviceID4=775&serviceID5=204&serviceID6=206&serviceID7=108&serviceID8=109',
                    'symbol': 'AAPL',
                    'volume': '24.2M',
                }
            },
            queue.get(),
        )

    def test_on_message_market_history_channel_handling(self):
        queue = self.ws_client.new_queue_accessor(IbkrWsKey.MARKET_HISTORY)
        server_id = 87567
        full_channel = f'{queue.key.channel}+{self.conid}'
        request = {
            'channel': f'{full_channel}',
            'data': {'period': '1min', 'bar': '1min', 'outsideRTH': True, 'source': 'trades', 'format': '%o/%c/%h/%l'},
            'confirms_unsubscription': False,
        }
        response = {'topic': f's{full_channel}', 'serverId': server_id, '_updated': self.update_time, 'conid': self.conid, 'foo': 'bar'}

        self.assertTrue(queue.empty(), 'Queue should be empty')

        with patch.object(self.ws_client, 'has_subscription', return_value=True):
            cm, success = self._subscribe(request, response)
            self.assertTrue(success)

        self.assertEqual(self._logs_subscriptions(full_channel, request['data']), [r.msg for r in cm.records])

        self.assertEqual(response, queue.get())
        self.assertIn(server_id, self.ws_client.server_ids(IbkrWsKey.MARKET_HISTORY))

    def test_on_message_trade_channel_handling(self):
        queue = self.ws_client.new_queue_accessor(IbkrWsKey.TRADES)
        full_channel = f'{queue.key.channel}+{self.conid}'
        request = {'channel': f'{full_channel}'}
        response = {'topic': f's{full_channel}', '_updated': self.update_time, 'conid': self.conid, 'args': [{'foo': 'bar'}]}

        self.assertTrue(queue.empty(), 'Queue should be empty')

        with patch.object(self.ws_client, 'has_subscription', return_value=True):
            cm, success = self._subscribe(request, response)
            self.assertTrue(success)

        self.assertEqual(self._logs_subscriptions(full_channel), [r.msg for r in cm.records])
        self.assertEqual(response, queue.get())

    def test_on_message_orders_channel_handling(self):
        queue = self.ws_client.new_queue_accessor(IbkrWsKey.ORDERS)

        full_channel = f'{queue.key.channel}+{self.conid}'
        request = {'channel': f'{full_channel}'}
        response = {'topic': f's{full_channel}', '_updated': self.update_time, 'conid': self.conid, 'args': [{'foo': 'bar'}]}

        self.assertTrue(queue.empty(), 'Queue should be empty')

        with patch.object(self.ws_client, 'has_subscription', return_value=True):
            cm, success = self._subscribe(request, response)
            self.assertTrue(success)

        self.assertEqual(self._logs_subscriptions(full_channel, None, True, True), [r.msg for r in cm.records])
        self.assertEqual(response, queue.get())

    def test_subscription_without_confirmation(self):
        channel = 'fake'
        full_channel = f'{channel}+{self.conid}'
        request = {'channel': f'{full_channel}', 'needs_confirmation': False, 'confirms_unsubscription': False}
        response = None

        expected_errors = [f'IbkrWsClient: Channel subscription timeout: s{full_channel} after {self.subscription_retries} attempts.']

        with patch.object(self.ws_client, 'has_subscription', return_value=True):
            cm, success = self._subscribe(request, response, expected_errors=expected_errors)
            self.assertTrue(success)

        self.assertEqual(
            [
                f'IbkrWsClient: Subscribed: s{full_channel} without confirmation.',
                f'IbkrWsClient: Unsubscribed: u{full_channel}+{{}} without confirmation.',
            ],
            [r.msg for r in cm.records],
        )

    def test_check_health(self):
        start_time = [100]
        has_active_connection_counter = [0]

        # control time
        def fake_time():
            start_time[0] += 100
            return start_time[0]

        # simulate that we don't have ws connection first
        def has_active_connection():
            has_active_connection_counter[0] += 1
            if has_active_connection_counter[0] <= 2:
                return False
            return True

        # prepare a fake subscription
        queue = self.ws_client.new_queue_accessor(IbkrWsKey.TRADES)
        full_channel = f'{queue.key.channel}+{self.conid}'
        request = {'channel': f'{full_channel}', 'data': {'foo': 'bar'}}
        response = {'topic': f's{full_channel}', '_updated': self.update_time, 'conid': self.conid, 'args': [{'foo': 'bar'}]}

        def run():
            # ensures each time WebSocketApp's mock is created, we override its on_message method
            def override_init_wsa_mock(wsa_mock: MagicMock, *args, **kwargs):
                wsa_mock = init_wsa_mock(wsa_mock, *args, **kwargs)
                wsa_mock._on_message.side_effect = lambda wsa_mock, message: wsa_mock.__on_message__(wsa_mock, json.dumps(response))
                return wsa_mock

            self.ws_client.start()
            self.ws_client.check_health()
            self.wsa_mock._on_message.side_effect = lambda wsa_mock, message: wsa_mock.__on_message__(wsa_mock, json.dumps(response))

            # create the original subscription
            self.ws_client.subscribe(**request)

            # we simulate that closing the WebSocket doesn't work since we have connectivity issues
            # self.wsa_mock.on_close.side_effect = lambda x, y, z: None

            # override time.time, ignore check_ping and take control of has_active_connection
            with patch('ibind.client.ibkr_ws_client.time') as time_mock, \
                    patch.object(self.ws_client, 'check_ping', return_value=True), \
                    patch('ibind.base.ws_client.WebSocketApp', side_effect=lambda *args, **kwargs: override_init_wsa_mock(self.wsa_mock, *args, **kwargs)), \
                    patch.object(self.ws_client, '_has_active_connection', side_effect=has_active_connection) as has_active_connection_mock:  # fmt: skip
                time_mock.time.side_effect = fake_time
                self.ws_client._last_heartbeat = self.max_ping_interval * 1000

                # this should try to close the connection, fail to do so, abandon the WebSocketApp's mock,
                # then recreate a new mock and recreate the connections
                self.ws_client.check_health()

                self.assertTrue(self.ws_client.ready())
                self.assertEqual([call()] * 6, has_active_connection_mock.call_args_list)
                self.ws_client.shutdown()

        expected_errors = [
            f'IbkrWsClient: Last IBKR heartbeat happened 162.00 seconds ago, exceeding the max ping interval of {self.max_ping_interval}. Restarting.',
            # 'IbkrWsClient: Hard reset close timeout',
            # f'IbkrWsClient: Abandoning current WebSocketApp that cannot be closed: {self.wsa_mock}'
        ]

        cm, success = self.run_in_test_context(run, expected_errors=expected_errors)

        channel_subscribed_log = f'IbkrWsClient: Subscribed: s{full_channel}+{json.dumps(request["data"])}'

        self.assertEqual(
            [channel_subscribed_log]
            + expected_errors
            + [
                f'IbkrWsClient: Invalidated subscription: {full_channel}',
                f"IbkrWsClient: Recreating 1/1 subscriptions: {{'{full_channel}': {{'status': False, 'data': {request['data']}, 'needs_confirmation': True, 'subscription_processor': None}}}}",
                channel_subscribed_log,
                f'IbkrWsClient: Invalidated subscription: {full_channel}',
            ],
            [r.msg for r in cm.records],
        )
