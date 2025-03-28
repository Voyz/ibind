from threading import Thread
from typing import Optional
from unittest import TestCase
from unittest.mock import patch, MagicMock

from ibind.base.ws_client import WsClient
from ibind.support.py_utils import tname
from test.integration.base.websocketapp_mock import create_wsa_mock, init_wsa_mock
from test_utils import RaiseLogsContext, exact_log


class TestWsClient(TestCase):
    def setUp(self):
        self.url = 'wss://localhost:5000/v1/api/ws'
        self.max_reconnect_attempts = 4
        self.max_ping_interval = 38
        self.error_message = 'TEST_ERROR'

        self.ws_client = WsClient(
            subscription_processor=None,
            url=self.url,
            cacert=False,
            timeout=0.01,
            max_connection_attempts=self.max_reconnect_attempts,
            max_ping_interval=self.max_ping_interval,
        )

        self.wsa_mock = create_wsa_mock()

        self.thread_mock = MagicMock(spec=Thread)
        self.thread_mock.start.side_effect = lambda: self.ws_client._run_websocket(self.wsa_mock)

    def run_in_test_context(self, fn, expected_errors: list[str] = None):
        with patch('ibind.base.ws_client.WebSocketApp', side_effect=lambda *args, **kwargs: init_wsa_mock(self.wsa_mock, *args, **kwargs)), \
                patch('ibind.base.ws_client.Thread', return_value=self.thread_mock) as new_thread_mock, \
                self.assertLogs('ibind', level='DEBUG') as cm, \
                RaiseLogsContext(self, 'ibind', level='ERROR', expected_errors=expected_errors):  # fmt: skip
            self.new_thread_mock = new_thread_mock
            rv = fn()

        return cm, rv

    def start(self):
        success = self.ws_client.start()
        self.new_thread_mock.assert_called_with(target=self.ws_client._run_websocket, args=(self.wsa_mock,), name='ws_client_thread')
        return success

    def _logs_start_success_beginning(self):
        return [
            'WsClient: Starting',
            'WsClient: Trying to connect',
        ]

    def _logs_start_success_end(self):
        return [
            'WsClient: Creating new WebSocketApp',
            f'WsClient: Thread started ({tname()})',
            'WsClient: Connection open',
            f'WsClient: Thread stopped ({tname()})',
        ]

    def _logs_failed_attempt(self, attempt):
        s = [
            'WsClient: Creating new WebSocketApp',
            'WsClient: New WebSocketApp connection timeout',
            'WsClient: on_close',
            'WsClient: on_close event while disconnected',
        ]
        if attempt:
            s.append(f'WsClient: Connect reattempt {attempt}/{self.max_reconnect_attempts}')
        return s

    def _logs_shutdown_success(self):
        return [
            'WsClient: Shutting down',
            'WsClient: on_close',
            'WsClient: Connection closed',
            'WsClient: Gracefully stopped',
        ]

    def _logs_exception_starting(self, error_message, thread_mock):
        return [
            'WsClient: Creating new WebSocketApp',
            f'WsClient: Thread started ({tname()})',
            f'WsClient: Unexpected error while running WebSocketApp: {error_message}',
            'WsClient: Hard reset, restart=False, self._wsa is None=False',
            'WsClient: Forced restart',
            'WsClient: Reconnecting',
            f'WsClient: Thread already running: {thread_mock.name}-{thread_mock.ident}',
            f'WsClient: Thread stopped ({tname()})',
            'WsClient: Reconnecting',
            'WsClient: Trying to connect',
        ]

    def _logs_check_health_error(self, time_ago):
        return [
            f'WsClient: Last WebSocket ping happened  {time_ago} seconds ago, exceeding the max ping interval of {self.max_ping_interval}. Restarting.',
            'WsClient: Hard reset, restart=True, self._wsa is None=False',
            'WsClient: Hard reset is closing the WebSocketApp',
        ]

    def _logs_hard_restart_error(self):
        return [
            'WsClient: Hard reset close timeout',
            f'WsClient: Abandoning current WebSocketApp that cannot be closed: {self.wsa_mock}',
            'WsClient: Forced restart',
            'WsClient: Reconnecting',
            'WsClient: Trying to connect',
        ]

    def _verify_started(self):
        self.wsa_mock.run_forever.assert_called_with(
            sslopt=self.ws_client._sslopt, ping_interval=self.ws_client._ping_interval, ping_timeout=0.95 * self.ws_client._ping_interval
        )
        self.wsa_mock._on_open.assert_called_with(self.wsa_mock)

    def _verify_failed_starting(self):
        self.wsa_mock.run_forever.assert_not_called()
        self.wsa_mock._on_open.assert_not_called()
        self.wsa_mock.close.assert_called()

    def test_start_success(self):
        cm, success = self.run_in_test_context(self.start)

        self.assertTrue(success, 'Starting should succeed')
        self._verify_started()
        exact_log(self, cm, self._logs_start_success_beginning() + self._logs_start_success_end())

    def test_start_success_on_second_attempt(self):
        counter = [0]

        # ensure we fail to do anything on the first attempt, and succeed on the second
        def delayed_start():
            if counter[0] >= 1:
                self.ws_client._run_websocket(self.wsa_mock)
            counter[0] += 1

        self.thread_mock.start.side_effect = delayed_start

        expected_errors = ['WsClient: New WebSocketApp connection timeout']

        cm, success = self.run_in_test_context(self.start, expected_errors=expected_errors)

        self._verify_started()

        exact_log(self, cm, self._logs_start_success_beginning() + self._logs_failed_attempt(2) + self._logs_start_success_end())
        self.thread_mock.join.assert_called_with(60)
        # print("\n".join([r.msg for r in cm.records]))

    def test_start_reattempt_failure(self):
        self.thread_mock.start.side_effect = lambda: None

        expected_errors = ['WsClient: New WebSocketApp connection timeout']

        cm, success = self.run_in_test_context(self.start, expected_errors=expected_errors)

        self.assertFalse(success, 'Starting not succeed')

        self._verify_failed_starting()

        expected_logs = self._logs_start_success_beginning()
        for i in range(self.max_reconnect_attempts):
            if i < self.max_reconnect_attempts - 1:
                expected_logs += self._logs_failed_attempt(i + 2)
            else:
                expected_logs += self._logs_failed_attempt(None)
        expected_logs.append(f'WsClient: Connection failed after {self.max_reconnect_attempts} attempts')
        exact_log(self, cm, expected_logs)

        self.assertFalse(self.wsa_mock.keep_running)

    def test_open_exception(self):
        old_run_forever = self.wsa_mock.run_forever.side_effect

        def run():
            success = self.start()
            self.ws_client.shutdown()
            return success

        def run_forever_exception(wsa_mock: MagicMock, sslopt: dict = None, ping_interval: float = 0, ping_timeout: Optional[float] = None):
            self.wsa_mock.run_forever.side_effect = old_run_forever
            raise RuntimeError(self.error_message)

        self.wsa_mock.run_forever.side_effect = lambda *args, **kwargs: run_forever_exception(self.wsa_mock, *args, **kwargs)

        expected_errors = [f'WsClient: Unexpected error while running WebSocketApp: {self.error_message}']

        cm, success = self.run_in_test_context(run, expected_errors=expected_errors)

        exact_log(
            self,
            cm,
            self._logs_start_success_beginning()
            + self._logs_exception_starting(self.error_message, self.thread_mock)
            + self._logs_start_success_end()
            + self._logs_shutdown_success(),
        )

    def test_open_and_close(self):
        def run():
            success = self.start()
            self.ws_client.shutdown()
            return success

        cm, success = self.run_in_test_context(run)

        exact_log(self, cm, self._logs_start_success_beginning() + self._logs_start_success_end() + self._logs_shutdown_success())

    def test_send(self):
        def run():
            success = self.start()
            self.ws_client.send('test')
            self.ws_client.shutdown()
            return success

        self.ws_client._on_message = MagicMock()

        cm, success = self.run_in_test_context(run)

        self.ws_client._on_message.assert_called_once_with(self.wsa_mock, 'test')

        exact_log(self, cm, self._logs_start_success_beginning() + self._logs_start_success_end() + self._logs_shutdown_success())

    def test_send_without_start(self):
        def run():
            self.ws_client.send('test')
            self.ws_client.shutdown()

        self.ws_client._on_message = MagicMock()

        expected_errors = ['WsClient: Must be started before sending payloads']

        cm, success = self.run_in_test_context(run, expected_errors=expected_errors)

        exact_log(self, cm, expected_errors)

    def test_check_ping(self):
        start_time = [100]

        def fake_time():
            start_time[0] += 100
            return start_time[0]

        def run():
            self.ws_client.start()
            self.ws_client.check_ping()
            # we simulate that closing the WebSocketApp doesn't work since we have connectivity issues
            self.wsa_mock._on_close.side_effect = lambda x, y, z: None
            with patch('ibind.base.ws_client.time') as time_mock:
                time_mock.time.side_effect = fake_time
                self.wsa_mock.last_ping_tm = self.max_ping_interval
                self.ws_client.check_ping()
                self.assertTrue(self.ws_client.ready())
                self.ws_client.shutdown()

        self.ws_client._on_message = MagicMock()

        expected_errors = ['WsClient: Must be started before sending payloads', 'WsClient: Hard reset close timeout']

        cm, success = self.run_in_test_context(run, expected_errors=expected_errors)

        exact_log(
            self,
            cm,
            self._logs_start_success_beginning()
            + self._logs_start_success_end()
            + self._logs_check_health_error('162.00')
            +
            # self._logs_start_success_end() +
            self._logs_hard_restart_error()
            + self._logs_start_success_end()
            + self._logs_shutdown_success(),
        )
