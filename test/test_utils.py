import functools
import logging
import sys
import traceback
import types
import unittest
from unittest import TestCase
from unittest._log import _CapturingHandler, _AssertLogsContext

from ibind.support.py_utils import make_clean_stack


def raise_from_context(cm, level='WARNING'):
    for record in cm.records:
        if record.levelno >= getattr(logging, level):
            raise RuntimeError(record.message)


def verify_log(test_case:TestCase, cm, expected_messages, comparison:callable= lambda x, y: x == y):
    messages = [record.msg for record in cm.records]
    missing_expected = expected_messages.copy()
    for i, expected_msg in enumerate(expected_messages):
        for msg in messages:
            if comparison(expected_msg, msg):
                missing_expected.remove(expected_msg)
                break

    if missing_expected:
        test_case.fail("Expected log(s) not found:\n\t{}".format('\n\t'.join(missing_expected)))


def verify_log_simple(test_self, cm, expected_messages):
    for i, msg in enumerate(expected_messages):
        test_self.assertEqual(msg, cm.records[i].msg)

def exact_log(test_case, cm, expected_messages):
    test_case.assertEqual(expected_messages, [record.msg for record in cm.records])


class SafeAssertLogs(_AssertLogsContext):
    """
    The self.assertLogs context manager, that sets log level on the handler instead of logger.

    Original docstring:
    A context manager used to implement TestCase.assertLogs().
    """
    def __init__(self, *args, logger_level:str=None, **kwargs):
        if sys.version_info < (3, 10, 0) and 'no_logs' in kwargs:
            del kwargs['no_logs']

        super().__init__(*args, **kwargs)
        self.logger_level = logger_level

    def __enter__(self, include_original_handlers:bool=False):
        if isinstance(self.logger_name, logging.Logger):
            logger = self.logger = self.logger_name
        else:
            logger = self.logger = logging.getLogger(self.logger_name)
        formatter = logging.Formatter(self.LOGGING_FORMAT)
        handler = _CapturingHandler()
        handler.setFormatter(formatter)
        self.watcher = handler.watcher
        self.old_handlers = logger.handlers[:]
        self.old_level = logger.level
        self.old_propagate = logger.propagate
        logger.handlers = [handler]
        handler.setLevel(self.level)  # this one line is different, originally was `logger.setLevel`
        logger.propagate = False
        if self.logger_level is not None:
            logger.setLevel(getattr(logging, self.logger_level))

        if include_original_handlers:
            logger.handlers += self.old_handlers
            logger.propagate = True
        return handler.watcher

def get_logger_children(main_logger) -> list[logging.Logger]:
    """
    Gets child loggers. Added as a support compat for Python version 3.11 and below.
    Source: https://github.com/python/cpython/blob/3.12/Lib/logging/__init__.py#L1831
    """

    def _hierlevel(logger):
        if logger is logger.manager.root:
            return 0
        return 1 + logger.name.count('.')

    d = main_logger.manager.loggerDict
    # exclude PlaceHolders - the last check is to ensure that lower-level
    # descendants aren't returned - if there are placeholders, a logger's
    # parent field might point to a grandparent or ancestor thereof.
    return [item for item in d.values()
            if isinstance(item, logging.Logger) and item.parent is main_logger and
            _hierlevel(item) == 1 + _hierlevel(item.parent)]


class RaiseLogsContext:
    """
    Captures log messages at or above a specified level and raises unexpected ones as exceptions.

    This context manager monitors log messages from a specified logger. Any log messages
    at or above the given logging level are recorded. If a message is not explicitly
    expected, a `RuntimeError` is raised, including the stack trace of the log call. It ensures
    loggers are restored to their original state after use.

    Note:
        - When used in conjunction with `self.assertLogs` or `SafeAssertLogs`, ensure this context manager is defined last to properly assert log expectations.

    Args:
        test_case (TestCase): The test case instance, typically from `unittest.TestCase`.
        logger_name (str | None): The name of the logger to monitor. Defaults to the root logger.
        level (str): The logging level threshold (e.g., 'ERROR', 'WARNING'). Logs at or above this level are captured.
        expected_errors (list[str] | None): A list of log messages that are expected and should not trigger an exception.
        comparison (Callable[[str, str], bool]): A function to compare expected errors with log messages.
            Defaults to an exact string match (`lambda x, y: x == y`).

    Example Usage:
        >>> with RaiseLogsContext(self, logger_name="my_logger", level="WARNING", expected_errors=["My expected warning"]):
        ...     logging.getLogger("my_logger").warning("My expected warning")  # No error
        ...     logging.getLogger("my_logger").error("Unexpected issue")  # Raises RuntimeError
    """

    def __init__(self,
                 test_case:TestCase,
                 logger_name=None,
                 level='ERROR',
                 expected_errors:[str]=None,
                 comparison: callable = lambda x, y: x == y,
                 ):
        self._test_case = test_case
        self._logger_name = logger_name
        self._level = level
        self._level_no = getattr(logging, level)
        if expected_errors is None:
            expected_errors = []
        self._expected_errors = expected_errors
        self._comparison = comparison

    def monkey_patch_log(self, original_method):
        """Wraps a logger method to attach a manually captured stack trace to log records."""

        def new_method(msg, *args, **kwargs):
            # Store the manually captured stack trace in the log record
            stack = make_clean_stack()
            if 'extra' not in kwargs:
                kwargs['extra'] = {}
            kwargs['extra']['manual_trace'] = stack

            # Call the original logging method with the modified arguments
            return original_method(msg, *args, **kwargs)

        return new_method

    def monkey_patch_loggers(self, loggers):
        """Monkey-patches loggers to attach a stack trace to warning and error messages."""
        for logger in loggers:
            if self._level_no <= logging.ERROR:
                logger.__old_error_method__ = logger.error
                logger.error = self.monkey_patch_log(logger.error)

            if self._level_no <= logging.WARNING:
                logger.__old_warning_method__ = logger.warning
                logger.warning = self.monkey_patch_log(logger.warning)

    def restore_loggers(self, loggers):
        """Restores the original error and warning logging methods after patching."""
        for logger in loggers:
            if self._level_no <= logging.ERROR:
                logger.error = logger.__old_error_method__  # Restore the original error method

            if self._level_no <= logging.WARNING:
                logger.warning = logger.__old_warning_method__  # Restore the original warning method

    def __enter__(self):
        """
        Initializes the logging context by patching loggers and setting up a log watcher.

        This method ensures that logs at the specified level are captured and asserts
        that unexpected log messages are raised as errors.
        """

        self._logger = logging.getLogger(self._logger_name)
        loggers_to_be_patched = [self._logger] + get_logger_children(self._logger)
        self.monkey_patch_loggers(loggers_to_be_patched) # Apply monkey-patching to attach stack traces to logged messages

        # Initialize SafeAssertLogs, a helper to capture and assert log records
        self._context_manager = SafeAssertLogs(
            self._test_case, self._logger, level=self._level, no_logs=False
        )

        # Enter the SafeAssertLogs context, starting log capture and returning the watcher
        self._watcher = self._context_manager.__enter__(include_original_handlers=True)
        return self._watcher

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Restores original logger methods and verifies captured log messages.

        This method is called when exiting the context manager. It ensures that:
        - Monkey-patched loggers are restored to their original state.
        - If an exception occurred inside the `with` block, it is propagated normally.
        - If no exception occurred, all captured log messages are checked against expected errors.
        - Unexpected log messages result in a `RuntimeError`.
        """

        # Restore original logging methods that were monkey-patched
        loggers_to_be_patched = [self._logger] + get_logger_children(self._logger)
        self.restore_loggers(loggers_to_be_patched)

        # If an exception occurred inside the 'with' block, return False to let Python re-raise it
        if exc_type is not None:
            return False

        # If no logs were captured return True to indicate that no errors were encountered and that the context exited cleanly
        if len(self._watcher.records) == 0:
            return True

        for record in self._watcher.records:
            found = False

            # Check if the log message matches any of the expected error messages
            for expected_error in self._expected_errors:
                if self._comparison(expected_error, record.msg):
                    found = True
                    break

            # If the message is expected, move on to the next record
            if found:
                continue

            # If the log record has a manually stored traceback, raise an error with that traceback
            if hasattr(record, 'manual_trace'):
                raise RuntimeError(
                    f'\n' + ''.join(traceback.format_list(record.manual_trace)) +
                    f'Logger {self._logger} logged an unexpected message:\n{record.msg}'
                )

            # Otherwise, raise an error using the log record's location
            raise RuntimeError(
                f'\n...\nFile "{record.pathname}", line {record.lineno} in {record.funcName}\n{record.msg}'
            )


def raise_logs(level='ERROR', logger_name=None):
    def _wrapper(fn):
        @functools.wraps(fn)
        def wrapper(self, *args, **kwargs):
            with RaiseLogsContext(self, level=level, logger_name=logger_name):
                return fn(self, *args, **kwargs)

        return wrapper

    return _wrapper


def decorate_methods(decorator, starts_with=""):
    class DecorateMethods(type):
        """ Decorate all methods of the class with the decorator provided """

        def __new__(cls, name, bases, attrs, **kwargs):
            exclude = kwargs.get('exclude', [])

            for attr_name, attr_value in attrs.items():

                if isinstance(attr_value, types.FunctionType) and \
                        attr_name.startswith(starts_with) and \
                        attr_name not in exclude and \
                        not hasattr(attr_value, '__exclude_decorator__') and \
                        not attr_name.startswith('__'):
                    attrs[attr_name] = decorator(attr_value)

            return super(DecorateMethods, cls).__new__(cls, name, bases, attrs)

    return DecorateMethods


class TestCaseWithRaiseLogs(unittest.TestCase, metaclass=decorate_methods(raise_logs(logger_name='ibind'), starts_with='test')):
    ...


def exclude_decorator(fn):
    fn.__exclude_decorator__ = True
    return fn
