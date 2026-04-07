import functools
import inspect
import logging
import traceback
from typing import List, Union

from ibind.support.logs import get_logger_children
from ibind.support.py_utils import make_clean_stack, OneOrMany, UNDEFINED


def _accepts_kwargs(func):
    """
    Check if a function accepts **kwargs.

    Args:
        func: A callable to inspect.

    Returns:
        bool: True if the function accepts **kwargs, False otherwise.
    """
    sig = inspect.signature(func)
    for param in sig.parameters.values():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True
    return False


# --- Logging Utilities ---

class LoggingWatcher:
    """
    Captures and asserts on log messages during testing.
    """

    def __init__(self, logger):
        self.logger = logger
        self.records = []
        self.output = []

    def _process_logs(self, expected_messages: OneOrMany[str], comparison: callable = lambda x, y: x == y):
        if not isinstance(expected_messages, list):
            expected_messages = [expected_messages]

        if not self.output:
            return [], expected_messages

        messages = [msg for msg in self.output]
        missing_expected = expected_messages.copy()
        found = []
        for i, expected_msg in enumerate(expected_messages):
            for msg in messages:
                if comparison(expected_msg, msg):
                    found.append(msg)
                    missing_expected.remove(expected_msg)
                    break
        return found, missing_expected

    def exact_log(self, expected_messages: OneOrMany[str]):
        """
        Assert that all expected messages appear exactly in the captured logs.

        Args:
            expected_messages: A single message string or list of message strings to match.

        Raises:
            AssertionError: If any expected message is not found in the captured logs.
        """
        found, missing_expected = self._process_logs(expected_messages, lambda x, y: x == y)
        if len(missing_expected) > 0:
            missing_expected_str = '\n\t'.join(missing_expected)
            raise AssertionError(f"Expected exact log(s) not found:\n\t{missing_expected_str}\n\nActual logs:\n{self.format_logs()}\n")

    def partial_log(self, expected_messages: OneOrMany[str]):
        """
        Assert that each expected message is a substring of at least one captured log.

        Args:
            expected_messages: A single message string or list of message strings to match as substrings.

        Raises:
            AssertionError: If any expected message is not found as a substring in the captured logs.
        """
        found, missing_expected = self._process_logs(expected_messages, lambda x, y: x in y)
        if len(missing_expected) > 0:
            missing_expected_str = '\n\t'.join(missing_expected)
            raise AssertionError(f"Expected partial log(s) not found:\n\t{missing_expected_str}\n\nActual logs:\n{self.format_logs()}\n")

    def log_excludes(self, expected_messages: OneOrMany[str]):
        """
        Assert that none of the expected messages appear in any captured log.

        Args:
            expected_messages: A single message string or list of message strings to exclude.

        Raises:
            AssertionError: If any expected message is found in the captured logs.
        """
        found, _ = self._process_logs(expected_messages, lambda x, y: x in y)
        if found:
            found_str = '\n\t'.join(found)
            raise AssertionError(f"Unexpected log(s) found:\n\t{found_str}\n\nCurrent logs:\n{self.format_logs()}\n")

    def format_logs(self):
        """
        Return a formatted string of all captured log messages.

        Returns:
            str: A formatted string containing all captured logs.
        """
        output_str = '\n\t'.join(self.output)
        return f"\n{self} captured {len(self.output)} logs:\n[\n\t{output_str}\n]"

    def count_occurrences(self, msg: str):
        """
        Count occurrences of a message in the captured logs.

        Args:
            msg: The message substring to count.

        Returns:
            int: The number of logs containing the message substring.
        """
        return sum(1 for log in self.output if msg in log)

    def print(self):
        """
        Print the formatted logs to stdout.
        """
        print(self.format_logs())

    def __str__(self):
        return f'LoggingWatcher({self.logger.name})'


class _CapturingHandler(logging.Handler):
    """
    Internal logging handler that captures all logging output.
    """

    def __init__(self, logger):
        logging.Handler.__init__(self)
        self.watcher = LoggingWatcher(logger)

    def flush(self):
        pass

    def emit(self, record):
        self.watcher.records.append(record)
        msg = self.format(record)
        self.watcher.output.append(msg)


class CaptureLogsContext:
    """
    Context manager for capturing and validating log output during tests.
    """
    LOGGING_FORMAT = "%(message)s"

    def __init__(
        self,
        logger: str = 'ibind',
        level: str = 'DEBUG',
        logger_level: str = None,
        error_level: str = 'WARNING',
        no_logs: Union[bool, object] = UNDEFINED,
        expected_errors: List[str] = None,
        partial_match: bool = False,
        attach_stack: bool = True,
    ):
        """
        Initialize a log capture context.

        Args:
            logger (str): Logger name to capture. Defaults to 'ibind'.
            level (str): Logging level to capture. Defaults to 'DEBUG'.
            logger_level (str): Optional logger-specific level override.
            error_level (str): Logging level threshold for unexpected logs. Defaults to 'WARNING'.
            no_logs (bool): If True, assert no logs are produced. If False, assert logs are produced.
                Defaults to UNDEFINED (no assertion).
            expected_errors (list): List of expected error messages to match.
            partial_match (bool): If True, match expected errors as substrings. Defaults to False.
            attach_stack (bool): If True, attach stack traces to logs. Defaults to True.
        """
        self._logger = logger
        self.level = getattr(logging, level) if isinstance(level, str) else level
        self.logger_level = getattr(logging, logger_level) if isinstance(logger_level, str) else logger_level
        self.no_logs = no_logs
        self.expected_errors = expected_errors or []
        self.partial_match = partial_match
        self.comparison = (lambda x, y: x in y) if partial_match else (lambda x, y: x == y)
        self.attach_stack = attach_stack
        self.error_level = getattr(logging, error_level) if isinstance(error_level, str) else (error_level if error_level is not None else self.level)
        if not isinstance(self.expected_errors, list):
            self.expected_errors = [self.expected_errors]

    def _monkey_patch_log(self, logger):
        original_log = logger._log

        def new_log(level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
            if extra is None:
                extra = {}
            extra['manual_trace'] = make_clean_stack()[:-2]

            return original_log(level, msg, args, exc_info, extra, stack_info, stacklevel)

        logger.__old_log_method__ = original_log
        logger._log = new_log

    def _monkey_patch_loggers(self, loggers):
        for logger in loggers:
            self._monkey_patch_log(logger)

    def _restore_loggers(self, loggers):
        for logger in loggers:
            if hasattr(logger, '__old_log_method__'):
                logger._log = logger.__old_log_method__

    def logger_name(self):
        """
        Get the logger name.

        Returns:
            str: The name of the logger.
        """
        return self._logger.name if isinstance(self._logger, logging.Logger) else self._logger

    def acquire(self) -> LoggingWatcher:
        """
        Acquire and configure the logger for capturing.

        Returns:
            LoggingWatcher: A watcher object for asserting on captured logs.
        """
        self.logger = logging.getLogger(self.logger_name())
        self.old_handlers = self.logger.handlers[:]
        self.old_level = self.logger.level
        self.old_propagate = self.logger.propagate

        formatter = logging.Formatter(self.LOGGING_FORMAT, datefmt='%H:%M:%S')
        handler = _CapturingHandler(self.logger)
        handler.setFormatter(formatter)
        self.watcher = handler.watcher
        self.logger.handlers = [handler]
        handler.setLevel(self.level)
        self.logger.propagate = False
        if self.logger_level is not None:
            self.logger.setLevel(self.logger_level)

        if self.attach_stack:
            loggers_to_patch = [self.logger] + get_logger_children(self.logger)
            self._monkey_patch_loggers(loggers_to_patch)
            self._loggers_to_patch = loggers_to_patch
        else:
            self._loggers_to_patch = []

        return self.watcher

    def _raise_unexpected_log(self, record):
        if hasattr(record, 'manual_trace'):
            raise RuntimeError(f'\n{"".join(traceback.format_list(record.manual_trace))}Logger {self.logger} logged an unexpected message:\n{record.msg}')
        raise RuntimeError(f'\n...\nFile "{record.pathname}", line {record.lineno} in {record.funcName}\n{record.msg}')

    def _process_exit_logs(self):
        records = self.watcher.records
        if self.no_logs is not UNDEFINED and self.no_logs:
            if records:
                self._raise_unexpected_log(records[0])
            return True

        if self.no_logs is not UNDEFINED and not records:
            raise AssertionError(f"no logs of level {logging.getLevelName(self.level)} or higher triggered on {self.logger.name}")

        for record in records:
            if record.levelno < self.error_level:
                continue
            if any(self.comparison(expected, record.msg) for expected in self.expected_errors):
                continue
            self._raise_unexpected_log(record)

        if self.partial_match:
            self.watcher.partial_log(self.expected_errors)
        else:
            self.watcher.exact_log(self.expected_errors)

    def release(self, exc_type=None, exc_val=None, exc_tb=None):
        """
        Release and restore the logger to its original state.

        Args:
            exc_type: Exception type if an exception occurred.
            exc_val: Exception value if an exception occurred.
            exc_tb: Exception traceback if an exception occurred.

        Returns:
            bool: True if no exception occurred, False otherwise.
        """
        self.logger.handlers = self.old_handlers
        self.logger.propagate = self.old_propagate
        self.logger.setLevel(self.old_level)
        if self._loggers_to_patch:
            self._restore_loggers(self._loggers_to_patch)
        self._process_exit_logs()
        return exc_type is None

    def __enter__(self) -> LoggingWatcher:
        return self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.release(exc_type, exc_val, exc_tb)


def capture_logs(**ctx_kwargs):
    """
    Decorator to capture and validate logs in a test function.

    Args:
        **ctx_kwargs: Keyword arguments passed to CaptureLogsContext.
            Common options: logger, level, error_level, expected_errors, partial_match.

    Returns:
        callable: A decorator that wraps a test function to capture logs.

    Example:
        @capture_logs(logger='myapp', expected_errors=['Error occurred'])
        def test_something():
            # test code that logs
            pass
    """

    def decorator(test_func):
        @functools.wraps(test_func)
        def wrapper(*args, **kwargs):
            capture_log_context = CaptureLogsContext(**ctx_kwargs)
            logger_name = f'_cm_{capture_log_context.logger_name()}'
            fn_exc = None
            log_exc = None

            cm = capture_log_context.acquire()
            if _accepts_kwargs(test_func):
                kwargs[logger_name] = cm

            try:
                rv = test_func(*args, **kwargs)
            except Exception as e:
                rv = None
                fn_exc = e

            try:
                capture_log_context.release()
            except Exception as e2:
                log_exc = e2

            if fn_exc is not None:
                if log_exc is not None:
                    print('Unexpected log found in test:')
                    traceback.print_exception(log_exc)
                raise fn_exc
            elif log_exc is not None:
                raise log_exc

            return rv

        return wrapper

    return decorator


# --- Time Mocking Utilities ---

class MockTimeController:
    """
    Mock time module for testing time-dependent code.
    """

    def __init__(self, target_module, time_sequence=None, start_time=0.0):
        """
        Initialize a mock time controller.

        Args:
            target_module (str): Module name to inject the mock time into (eg. 'mymodule.submodule').
            time_sequence (list): Optional sequence of time values to return on successive calls.
                If provided, time_sequence takes precedence over start_time.
            start_time (float): Initial time value. Defaults to 0.0. Ignored if time_sequence is provided.
        """
        self.target_module = target_module
        if time_sequence is not None:
            self.time_sequence = list(time_sequence)
            self.call_index = 0
        else:
            self.time_sequence = None
            self.current_time = start_time
        self.original_time_module = None

    def advance_time(self, seconds):
        """
        Advance the mock time by the specified number of seconds.

        Args:
            seconds (float): Number of seconds to advance.

        Raises:
            ValueError: If using time_sequence mode.
        """
        if self.time_sequence is not None:
            raise ValueError("Cannot advance time when using time_sequence.")
        self.current_time += seconds

    def set_time(self, time_value):
        """
        Set the mock time to a specific value.

        Args:
            time_value (float): The time value to set.

        Raises:
            ValueError: If using time_sequence mode.
        """
        if self.time_sequence is not None:
            raise ValueError("Cannot set time when using time_sequence.")
        self.current_time = time_value

    def mock_time(self):
        """
        Get the current mock time value.

        Returns:
            float: The current time value. If using time_sequence, returns the next value in the sequence.
        """
        if self.time_sequence is not None:
            if self.call_index < len(self.time_sequence):
                time_value = self.time_sequence[self.call_index]
                self.call_index += 1
                return time_value
            else:
                return self.time_sequence[-1]
        else:
            return self.current_time

    def __enter__(self):
        target_module_obj = __import__(self.target_module, fromlist=[''])
        self.original_time_module = target_module_obj.time

        class MockTimeModule:
            def __init__(self, original_module, mock_time_func):
                self.original_module = original_module
                self.time = mock_time_func

            def __getattr__(self, name):
                return getattr(self.original_module, name)

        target_module_obj.time = MockTimeModule(self.original_time_module, self.mock_time)
        self.target_module_obj = target_module_obj
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.target_module_obj.time = self.original_time_module


def mock_module_time(target_module, time_sequence=None, start_time=0.0):
    """
    Create a mock time controller for a target module.

    Args:
        target_module (str): Module name to inject the mock time into.
        time_sequence (list): Optional sequence of time values to return on successive calls.
        start_time (float): Initial time value. Defaults to 0.0.

    Returns:
        MockTimeController: A context manager for mocking time in the target module.

    Example:
        with mock_module_time('mymodule', time_sequence=[1.0, 2.0, 3.0]):
            # time.time() in mymodule will return 1.0, then 2.0, then 3.0
            pass
    """
    return MockTimeController(target_module, time_sequence=time_sequence, start_time=start_time)