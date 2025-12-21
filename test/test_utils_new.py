import functools
import importlib
import inspect
import logging
import os
import traceback
from pathlib import Path

from support.slog import get_logger_children, PrettyFormatter
from utils.context_utils import make_clean_stack, accepts_kwargs
from utils.py_utils import UNDEFINED, OneOrMany

_NAME_TO_LEVEL = logging.getLevelNamesMapping()




class LoggingWatcher:
    """
    Helper class for capturing and asserting logs during testing.

    Attributes:
        logger: The logger instance being watched.
        records: List to store log records.
        output: List to store log output messages.

    """

    def __init__(self, logger):
        """
        Initialize the LoggingWatcher.

        Args:
            logger: The logger instance to watch.
        """
        self.logger = logger
        self.records = []
        self.output = []

    def _process_logs(self, expected_messages: OneOrMany[str], comparison: callable = lambda x, y: x == y):
        """
        Assert that all expected messages appear in the captured logs, using the given comparison function.

        Args:
            expected_messages (OneOrMany[str]): Message(s) expected in the logs.
            comparison (callable): Function to compare expected and actual messages (default: exact match).

        Raises:
            AssertionError: If any expected message is not found in the logs according to the comparison.
        """

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
        Assert that all expected messages appear in the captured logs.

        Args:
            expected_messages (OneOrMany[str]): Message(s) expected in the logs.
        """
        found, missing_expected = self._process_logs(expected_messages, lambda x, y: x == y)

        if len(missing_expected) > 0:
            raise AssertionError("Expected exact log(s) not found:\n\t{}\n\nActual logs:\n{}\n".format('\n\t'.join(missing_expected), self.format_logs()))

    def partial_log(self, expected_messages: OneOrMany[str]):
        """
        Assert that each expected message is a substring of at least one captured log message.

        Args:
            expected_messages (OneOrMany[str]): Message(s) expected to be partially present in the logs.
        """
        found, missing_expected = self._process_logs(expected_messages, lambda x, y: x in y)

        if len(missing_expected) > 0:
            raise AssertionError("Expected partial log(s) not found:\n\t{}\n\nActual logs:\n{}\n".format('\n\t'.join(missing_expected), self.format_logs()))

    def log_excludes(self, expected_messages: OneOrMany[str]):
        """
        Assert that none of the expected messages appear in any captured log message.

        Args:
            expected_messages (OneOrMany[str]): Message(s) that must not be present in the logs.
        """
        found, missing_expected = self._process_logs(expected_messages, lambda x, y: x in y)
        if found:
            raise AssertionError("Unexpected log(s) found:\n\t{}\n\nCurrent logs:\n{}\n".format('\n\t'.join(found), self.format_logs()))

    def format_logs(self):
        """
        Return a formatted string of all captured log messages.

        Returns:
            str: Formatted log output.
        """
        return f"\n{self} captured {len(self.output)} logs:\n[\n\t{'\n\t'.join(self.output)}\n]"

    def count_occurrences(self, msg: str):
        """
        Count the number of occurrences of a message in the captured logs.

        Args:
            msg (str): Message to count occurrences of.

        Returns:
            int: Number of occurrences of the message.
        """
        return sum(1 for log in self.output if msg in log)

    def print(self):
        """
        Print the formatted logs.
        """
        print(self.format_logs())

    def __str__(self):
        return f'LoggingWatcher({self.logger.name})'


class _CapturingHandler(logging.Handler):
    """
    A logging handler capturing all (raw and formatted) logging output.
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
    Flexible context manager for log assertion and raising on unexpected logs.

    - If no_logs is True: asserts that no logs are emitted at or above the specified level.
    - If no_logs is False: asserts that logs are emitted, and all logs must match expected_errors (if provided), otherwise raises.
    """
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

        # for warning/error logs we specify the minimum level separate from the main logger
        self.error_level = getattr(logging, error_level) if isinstance(error_level, str) else (error_level if error_level is not None else self.level)

        if not isinstance(self.expected_errors, list):
            self.expected_errors = [self.expected_errors]

    def _monkey_patch_log(self, logger):
        original_log = logger._log

        def new_log(level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
            # Attach cleaned stack trace
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
        if isinstance(self._logger, logging.Logger):
            return self._logger.name
        else:
            return self._logger

    def acquire(self) -> LoggingWatcher:
        if isinstance(self._logger, logging.Logger):
            self.logger = self._logger
        else:
            self.logger = logging.getLogger(self._logger)
        self.old_handlers = self.logger.handlers[:]
        self.old_level = self.logger.level
        self.old_propagate = self.logger.propagate

        formatter = PrettyFormatter(self.LOGGING_FORMAT, datefmt='%H:%M:%S', use_tags=False, print_ctx=False)
        handler = _CapturingHandler(self.logger)
        handler.setFormatter(formatter)
        self.watcher = handler.watcher
        self.logger.handlers = [handler]
        handler.setLevel(self.level)
        self.logger.propagate = False
        if self.logger_level is not None:
            self.logger.setLevel(self.logger_level)

        # Monkey-patch for stack traces
        if self.attach_stack:
            loggers_to_patch = [self.logger] + get_logger_children(self.logger)
            self._monkey_patch_loggers(loggers_to_patch)
            self._loggers_to_patch = loggers_to_patch
        else:
            self._loggers_to_patch = []

        return self.watcher



    def _raise_unexpected_log(self, record):
        if hasattr(record, 'manual_trace'):
            raise RuntimeError(
                '\n' + ''.join(traceback.format_list(record.manual_trace))
                + f'Logger {self.logger} logged an unexpected message:\n{record.msg}'
            )

        # Fallback to at least log the line at which the log was created
        raise RuntimeError(
            f'\n...\nFile "{record.pathname}", line {record.lineno} in {record.funcName}\n{record.msg}'
        )

    def _process_exit_logs(self):
        records = self.watcher.records

        # 1. If no_logs: fail if any logs found
        if self.no_logs is not UNDEFINED and self.no_logs:
            if records:
                self._raise_unexpected_log(records[0])
            return True

        # 2. If logs are expected: fail if no logs found
        if self.no_logs is not UNDEFINED and not records:
            raise AssertionError(
                f"no logs of level {logging.getLevelName(self.level)} or higher triggered on {self.logger.name}"
            )

        # 3. Check all logs against expected_errors, but only for logs at or above error_level
        for record in records:
            if record.levelno < self.error_level:
                continue

            # find and skip expected errors
            found = any(self.comparison(expected, record.msg) for expected in self.expected_errors)
            if found:
                continue

            # raise any unexpected logs
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

        if exc_type is not None:
            # raise exc_type(exc_val)
            return False  # propagate exceptions

        return True  # suppress exceptions if no error


    def __enter__(self) -> LoggingWatcher:
        return self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.release(exc_type, exc_val, exc_tb)


def capture_logs(**ctx_kwargs):
    """
    Wrapper around CaptureLogsContext to make it easier to use as a decorator for the whole test function.
    """

    def decorator(test_func):
        @functools.wraps(test_func)
        def wrapper(*args, **kwargs):
            capture_log_context = CaptureLogsContext(**ctx_kwargs)
            logger_name = f'_cm_{capture_log_context.logger_name()}'
            fn_exc = None
            log_exc = None
            # try:
            # with capture_log_context as cm:
                # for key, val in kwargs.items():
                #     # Dict containing LoggingWatcher(s)
                #     if inspect.isgenerator(val):
                #         val = next(val)
                #         kwargs[key] = val
                #
                #     if isinstance(val, dict) and logger_name in val and isinstance(val[logger_name], LoggingWatcher):
                #         capture_log_context.watcher.output.extend(val[logger_name].output)
                #         capture_log_context.watcher.records.extend(val[logger_name].records)
                #         del val[logger_name]

                # Pass the context manager to the test if kwargs are accepted
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
                    print(f'Unexpected log found in test:')
                    traceback.print_exception(log_exc)
                raise fn_exc
            elif log_exc is not None:
                raise log_exc

            return rv
            # except Exception as e:
            #     raise
                    # fn_exc = e
            # if fn_exc is not None:
            #     raise RuntimeError() from fn_exc


        return wrapper

    return decorator


def make_data_dir():
    current_frame = inspect.currentframe()
    current_frame = current_frame.f_back
    return Path(current_frame.f_code.co_filename).parent / 'data'


class MockTimeController:
    """
    A utility class to control time.time() calls within specific modules for testing.

    This allows tests to manually control the passage of time in specific modules,
    preventing tests from hanging on timeout conditions while not affecting other modules.
    """

    def __init__(self, target_module, time_sequence=None, start_time=0.0):
        """
        Initialize the mock time controller.

        Args:
            target_module (str): Module path to patch (eg., 'utils.py_utils')
            time_sequence (list): List of time values to return on successive calls to time.time()
            start_time (float): Starting time value if time_sequence is not provided
        """
        self.target_module = target_module
        if time_sequence is not None:
            self.time_sequence = list(time_sequence)  # Make a copy
            self.call_index = 0
        else:
            self.time_sequence = None
            self.current_time = start_time
        self.original_time_module = None

    def advance_time(self, seconds):
        """Advance the mocked time by the specified number of seconds."""
        if self.time_sequence is not None:
            raise ValueError("Cannot advance time when using time_sequence. Use time_sequence parameter instead.")
        self.current_time += seconds

    def set_time(self, time_value):
        """Set the mocked time to a specific value."""
        if self.time_sequence is not None:
            raise ValueError("Cannot set time when using time_sequence. Use time_sequence parameter instead.")
        self.current_time = time_value

    def mock_time(self):
        """Return the current mocked time."""
        if self.time_sequence is not None:
            # Return values from sequence, cycling back to the last value if we run out
            if self.call_index < len(self.time_sequence):
                time_value = self.time_sequence[self.call_index]
                self.call_index += 1
                return time_value
            else:
                # Return the last value repeatedly if we've exhausted the sequence
                return self.time_sequence[-1]
        else:
            return self.current_time

    def __enter__(self):
        """Context manager entry - patch time module reference in target module only."""
        # Dynamically import the target module
        target_module_obj = __import__(self.target_module, fromlist=[''])

        # Store the original time module reference from target module
        self.original_time_module = target_module_obj.time

        # Create a mock time module that only replaces the time() function
        class MockTimeModule:
            def __init__(self, original_module, mock_time_func):
                self.original_module = original_module
                self.time = mock_time_func

            def __getattr__(self, name):
                # Delegate all other attributes to the original time module
                return getattr(self.original_module, name)

        # Replace the time module reference in target module with our mock
        target_module_obj.time = MockTimeModule(self.original_time_module, self.mock_time)
        self.target_module_obj = target_module_obj  # Store reference for cleanup
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - restore original time module reference."""
        self.target_module_obj.time = self.original_time_module

def mock_module_time(target_module, time_sequence=None, start_time=0.0):
    """
    Context manager to mock time.time() calls within any specified module.

    Usage:
        # Mock time in a specific module
        with mock_module_time('some.module', [0.0, 1.0, 2.0]) as time_controller:
            # Code that uses time.time() in 'some.module' will get mocked values
            pass

        # Mock time in multiple modules (use multiple context managers)
        with mock_module_time('module1', [0.0, 1.0]), \
             mock_module_time('module2', [0.0, 2.0]):
            # Both modules will have their time mocked independently
            pass

    Args:
        target_module (str): Module path to patch (eg., 'utils.py_utils', 'some.other.module')
        time_sequence (list): List of time values to return on successive calls to time.time()
        start_time (float): Initial time value to start with (ignored if time_sequence is provided)

    Returns:
        MockTimeController: Controller object to manipulate time
    """
    return MockTimeController(target_module, time_sequence=time_sequence, start_time=start_time)

def import_all_modules():
    os.environ['DOTENV_PATH'] = 'UNDEFINED' # disable loading .env files
    engine_dir = Path(__file__).parent.parent / 'engine'
    for py_path in engine_dir.rglob('*.py'):
        if py_path.name == '__init__.py' or '__pycache__' in py_path.parts:
            continue
        rel_path = py_path.relative_to(engine_dir.parent)
        module_name = '.'.join(rel_path.with_suffix('').parts)
        importlib.import_module(module_name)
