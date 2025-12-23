import time
from unittest.mock import MagicMock

import pytest

from ibind.support.py_utils import ensure_list_arg, execute_in_parallel, execute_with_key, wait_until


@ensure_list_arg('arg')
def sample_function(arg):
    return arg


def test_ensure_list_arg_with_list():
    """Wraps list args without altering the list."""
    # Arrange
    input_arg = [1, 2, 3]

    # Act
    result = sample_function(input_arg)

    # Assert
    assert result == input_arg


def test_ensure_list_arg_with_non_list():
    """Wraps a non-list arg into a single-item list."""
    # Arrange
    input_arg = 1

    # Act
    result = sample_function(input_arg)

    # Assert
    assert result == [input_arg]


def test_ensure_list_arg_with_keyword_arg_list():
    """Preserves list input when passed as a keyword arg."""
    # Arrange
    input_arg = [1, 2, 3]

    # Act
    result = sample_function(arg=input_arg)

    # Assert
    assert result == input_arg


def test_ensure_list_arg_with_keyword_arg_non_list():
    """Wraps a non-list keyword arg into a single-item list."""
    # Arrange
    input_arg = 1

    # Act
    result = sample_function(arg=input_arg)

    # Assert
    assert result == [input_arg]


def test_ensure_list_arg_with_missing_arg():
    """Raises TypeError when the decorated arg is missing."""
    # Arrange
    
    # Act / Assert
    with pytest.raises(TypeError):
        sample_function()


@pytest.fixture
def parallel_setup():
    state = {'delay': 0}

    def _func(v1, v2):
        if v1 == 1:
            time.sleep(state['delay'])
            return 'result1'
        elif v2 == 2:
            return 'result2'
        else:
            return 'unknown'

    func = MagicMock(side_effect=_func)
    func.__name__ = 'TEST_FUNCTION'
    requests_dict = {'req1': {'args': [1, 0], 'kwargs': {}}, 'req2': {'args': [0], 'kwargs': {'v2': 2}}}
    requests_list = [{'args': [1, 0], 'kwargs': {}}, {'args': [0], 'kwargs': {'v2': 2}}]

    return {
        'state': state,
        'func': func,
        'requests_dict': requests_dict,
        'requests_list': requests_list,
    }


def test_execute_in_parallel_with_dict(parallel_setup):
    """Executes requests in parallel when passed a dict of requests."""
    # Arrange
    func = parallel_setup['func']
    requests = parallel_setup['requests_dict']

    # Act
    results = execute_in_parallel(func, requests)

    # Assert
    assert results == {'req1': 'result1', 'req2': 'result2'}
    assert func.call_count == 2


def test_execute_in_parallel_with_list(parallel_setup):
    """Executes requests in parallel when passed a list of requests."""
    # Arrange
    func = parallel_setup['func']
    requests = parallel_setup['requests_list']
    parallel_setup['state']['delay'] = 0.1

    # Act
    results = execute_in_parallel(func, requests)

    # Assert
    assert results == ['result1', 'result2']
    assert func.call_count == 2


def test_execute_with_key_success(parallel_setup):
    """Returns (key, result) when the wrapped function succeeds."""
    # Arrange
    func = parallel_setup['func']

    # Act
    result = execute_with_key('key', func, 1, v2=2)

    # Assert
    func.assert_called_with(1, v2=2)
    assert result == ('key', 'result1')


def test_execute_with_key_exception(parallel_setup):
    """Returns (key, exception) when the wrapped function raises."""
    # Arrange
    func = parallel_setup['func']
    func.side_effect = Exception('error')

    # Act
    result = execute_with_key('key', func, 1, v2=2)

    # Assert
    assert isinstance(result[1], Exception)


def test_execute_in_parallel_rate_limiting():
    """Applies max_per_second rate limiting across parallel executions."""
    # Arrange
    start_time = time.time()

    # Simulate a slow function to test rate limiting
    def slow_func():
        time.sleep(0.05)
        return 'slow_result'

    requests = {i: {'args': [], 'kwargs': {}} for i in range(20)}  # 10 requests
    max_per_second = 10  # Limit to 5 requests per second

    # Act
    results = execute_in_parallel(slow_func, requests, max_per_second=max_per_second)

    # Assert
    duration = time.time() - start_time
    assert duration >= 1.05  # Should take at least 1.1 seconds to complete all requests
    assert len(results) == 20


def test_wait_until_condition_met():
    """Returns True immediately when the condition is already met."""
    # Arrange
    condition = MagicMock(return_value=True)

    # Act
    result = wait_until(condition)

    # Assert
    assert result is True
    condition.assert_called()


def test_wait_until_condition_not_met():
    """Returns False when the condition is not met before timeout."""
    # Arrange
    condition = MagicMock(return_value=False)

    # Act
    result = wait_until(condition, timeout=0.1)

    # Assert
    assert result is False
    condition.assert_called()


def test_wait_until_timeout_message(mocker):
    """Logs the timeout_message when the deadline is reached."""
    # Arrange
    mock_logger_error = mocker.patch('ibind.support.py_utils._LOGGER.error')
    condition = MagicMock(return_value=False)
    timeout_message = 'Condition not met within timeout'

    # Act
    result = wait_until(condition, timeout_message=timeout_message, timeout=0.1)

    # Assert
    assert result is False
    mock_logger_error.assert_called_with(timeout_message)


def test_wait_until_timeout():
    """Waits roughly the specified timeout duration before returning False."""
    # Arrange
    start_time = time.time()
    condition = MagicMock(return_value=False)
    timeout = 0.1

    # Act
    result = wait_until(condition, timeout=timeout)

    # Assert
    assert result is False
    duration = time.time() - start_time
    assert duration == pytest.approx(timeout, abs=0.02)