import time
import unittest
from unittest.mock import MagicMock, patch

from ibind.support.py_utils import ensure_list_arg, execute_in_parallel, execute_with_key, wait_until


class TestEnsureListArgU(unittest.TestCase):

    @ensure_list_arg('arg')
    def sample_function(self, arg):
        return arg

    def test_ensure_list_arg_with_list(self):
        input_arg = [1, 2, 3]
        self.assertEqual(self.sample_function(input_arg), input_arg)

    def test_ensure_list_arg_with_non_list(self):
        input_arg = 1
        self.assertEqual(self.sample_function(input_arg), [input_arg])

    def test_ensure_list_arg_with_keyword_arg_list(self):
        input_arg = [1, 2, 3]
        self.assertEqual(self.sample_function(arg=input_arg), input_arg)

    def test_ensure_list_arg_with_keyword_arg_non_list(self):
        input_arg = 1
        self.assertEqual(self.sample_function(arg=input_arg), [input_arg])

    def test_ensure_list_arg_with_missing_arg(self):
        with self.assertRaises(TypeError):
            self.sample_function()


class TestExecuteInParallelU(unittest.TestCase):

    def _func(self, v1, v2):
        if v1 == 1:
            time.sleep(self.delay)
            return 'result1'
        elif v2 == 2:
            return 'result2'
        else:
            return 'unknown'

    def setUp(self):
        self.delay = 0
        self.func = MagicMock(side_effect=self._func)
        self.func.__name__ = 'TEST_FUNCTION'
        self.requests_dict = {
            'req1': {'args': [1, 0], 'kwargs': {}},
            'req2': {'args': [0], 'kwargs': {'v2': 2}}
        }
        self.requests_list = [{'args': [1, 0], 'kwargs': {}}, {'args': [0], 'kwargs': {'v2': 2}}]

    def test_execute_in_parallel_with_dict(self):
        results = execute_in_parallel(self.func, self.requests_dict)
        self.assertEqual(results, {'req1': 'result1', 'req2': 'result2'})
        self.assertEqual(self.func.call_count, 2)

    def test_execute_in_parallel_with_list(self):
        self.delay = 0.1
        results = execute_in_parallel(self.func, self.requests_list)
        self.assertEqual(results, ['result1', 'result2'])
        self.assertEqual(self.func.call_count, 2)

    def test_execute_with_key_success(self):
        result = execute_with_key('key', self.func, 1, v2=2)
        self.func.assert_called_with(1, v2=2)
        self.assertEqual(result, ('key', 'result1'))

    def test_execute_with_key_exception(self):
        self.func.side_effect = Exception("error")
        result = execute_with_key('key', self.func, 1, v2=2)
        self.assertIsInstance(result[1], Exception)

    def test_execute_in_parallel_rate_limiting(self):
        start_time = time.time()

        # Simulate a slow function to test rate limiting
        def slow_func():
            time.sleep(0.05)
            return "slow_result"

        requests = {i: {'args': [], 'kwargs': {}} for i in range(20)}  # 10 requests
        max_per_second = 10  # Limit to 5 requests per second
        results = execute_in_parallel(slow_func, requests, max_per_second=max_per_second)

        duration = time.time() - start_time
        self.assertGreaterEqual(duration, 1.05)  # Should take at least 1.1 seconds to complete all requests
        self.assertEqual(len(results), 20)


class TestWaitUntilU(unittest.TestCase):

    def test_wait_until_condition_met(self):
        condition = MagicMock(return_value=True)
        self.assertTrue(wait_until(condition))
        condition.assert_called()

    def test_wait_until_condition_not_met(self):
        condition = MagicMock(return_value=False)
        self.assertFalse(wait_until(condition, timeout=0.1))
        condition.assert_called()

    @patch('ibind.support.py_utils._LOGGER.error')
    def test_wait_until_timeout_message(self, mock_logger_error):
        condition = MagicMock(return_value=False)
        timeout_message = "Condition not met within timeout"
        self.assertFalse(wait_until(condition, timeout_message=timeout_message, timeout=0.1))
        mock_logger_error.assert_called_with(timeout_message)

    def test_wait_until_timeout(self):
        start_time = time.time()
        condition = MagicMock(return_value=False)
        timeout = 0.1
        self.assertFalse(wait_until(condition, timeout=timeout))
        duration = time.time() - start_time
        self.assertAlmostEqual(duration, timeout, delta=0.02)

