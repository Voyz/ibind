import functools
import inspect
import logging
import os
import traceback
from pathlib import Path
from typing import List, TypeVar

from ibind.support.logs import get_logger_children
from ibind.support.py_utils import make_clean_stack, OneOrMany, UNDEFINED

_NAME_TO_LEVEL = logging.getLevelNamesMapping()

# --- New Functions and Types ---

def accepts_kwargs(func):
    """Returns True if func accepts **kwargs, else False."""
    sig = inspect.signature(func)
    for param in sig.parameters.values():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True
    return False

# --- Logging Utilities ---

class LoggingWatcher:
    """Helper class for capturing and asserting logs during testing."""

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
        """Assert that all expected messages appear in the captured logs."""
        found, missing_expected = self._process_logs(expected_messages, lambda x, y: x == y)
        if len(missing_expected) > 0:
            raise AssertionError(f"Expected exact log(s) not found:\n\t{'\n\t'.join(missing_expected)}\n\nActual logs:\n{self.format_logs()}\n")

    def partial_log(self, expected_messages: OneOrMany[str]):
        """Assert that each expected message is a substring of at least one captured log message."""
        found, missing_expected = self._process_logs(expected_messages, lambda x, y: x in y)
        if len(missing_expected) > 0:
            raise AssertionError(f"Expected partial log(s) not found:\n\t{'\n\t'.join(missing_expected)}\n\nActual logs:\n{self.format_logs()}\n")

    def log_excludes(self, expected_messages: OneOrMany[str]):
        """Assert that none of the expected messages appear in any captured log message."""
        found, _ = self._process_logs(expected_messages, lambda x, y: x in y)
        if found:
            raise AssertionError(f"Unexpected log(s) found:\n\t{'\n\t'.join(found)}\n\nCurrent logs:\n{self.format_logs()}\n")

    def format_logs(self):
        """Return a formatted string of all captured log messages."""
        return f"\n{self} captured {len(self.output)} logs:\n[\n\t{'\n\t'.join(self.output)}\n]"

    def count_occurrences(self, msg: str):
        """Count the number of occurrences of a message in the captured logs."""
        return sum(1 for log in self.output if msg in log)

    def print(self):
        """Print the formatted logs."""
        print(self.format_logs())

    def __str__(self):
        return f'LoggingWatcher({self.logger.name})'

class _CapturingHandler(logging.Handler):
    """A logging handler capturing all (raw and formatted) logging output."""
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
    LOGGING_FORMAT = "%(message)s"

    def __init__(
        self,
        logger='slog',
        level='DEBUG',
        logger_level: str = None,
        error_level='WARNING',
        no_logs=UNDEFINED,
        expected_errors=None,
        partial_match=False,
        attach_stack=True,
    ):
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
            extra['manual_trace'] = make_clean_stack(extra_filters=[os.path.join('support', 'slog.py')])[:-2]
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
        return self._logger.name if isinstance(self._logger, logging.Logger) else self._logger

    def acquire(self) -> LoggingWatcher:
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
    def decorator(test_func):
        @functools.wraps(test_func)
        def wrapper(*args, **kwargs):
            capture_log_context = CaptureLogsContext(**ctx_kwargs)
            logger_name = f'_cm_{capture_log_context.logger_name()}'
            fn_exc = None
            log_exc = None

            cm = capture_log_context.acquire()
            if accepts_kwargs(test_func):
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
    def __init__(self, target_module, time_sequence=None, start_time=0.0):
        self.target_module = target_module
        if time_sequence is not None:
            self.time_sequence = list(time_sequence)
            self.call_index = 0
        else:
            self.time_sequence = None
            self.current_time = start_time
        self.original_time_module = None

    def advance_time(self, seconds):
        if self.time_sequence is not None:
            raise ValueError("Cannot advance time when using time_sequence.")
        self.current_time += seconds

    def set_time(self, time_value):
        if self.time_sequence is not None:
            raise ValueError("Cannot set time when using time_sequence.")
        self.current_time = time_value

    def mock_time(self):
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
    return MockTimeController(target_module, time_sequence=time_sequence, start_time=start_time)
