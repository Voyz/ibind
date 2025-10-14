import copy
import inspect
import os
import sys
import threading
import time
import traceback
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum, EnumMeta
from functools import wraps
from collections.abc import Mapping
from typing import List, TypeVar, Union, Dict

from ibind.support.logs import project_logger

UNDEFINED = object()
_PRECISION_OFFSET = 7

S = TypeVar('S')
OneOrMany = Union[S, List[S]]

_LOGGER = project_logger(__file__)


def ensure_list_arg(*arg_names: str) -> callable:  # pragma: no cover
    """
    Decorator to ensure that the arguments specified by arg_names are lists.
    If an argument is not a list, it is wrapped in one.
    This version supports ensuring multiple argument names.
    """

    def decorator(func: callable):
        @wraps(func)
        def ensure_list_args_wrapper(*args, **kwargs):
            param_names = list(inspect.signature(func).parameters.keys())

            # Convert args to a list to potentially modify positional arguments
            args_list = list(args)

            for arg_name in arg_names:
                arg_index = param_names.index(arg_name) if arg_name in param_names else None

                # If arg_name was passed as a positional argument
                if arg_index is not None and arg_index < len(args_list):
                    if not isinstance(args_list[arg_index], list):
                        args_list[arg_index] = [args_list[arg_index]]

                # If arg_name was passed as a keyword argument
                elif arg_name in kwargs and not isinstance(kwargs[arg_name], list):
                    kwargs[arg_name] = [kwargs[arg_name]]

            return func(*args_list, **kwargs)

        return ensure_list_args_wrapper

    return decorator


class VerboseEnumMeta(EnumMeta):  # pragma: no cover
    def __getitem__(cls, key):
        return cls.from_string(key)

    def from_string(cls, key):
        enums = list(cls)

        lookup = key.upper().strip()

        for enum in enums:
            if str(enum) == lookup:
                return enum

        raise AttributeError(f'Invalid {cls.__name__}: {key!r} ({type(key)}) | expected: {cls.values()}')

    def values(cls):
        return [entry.value for entry in list(cls)]


class VerboseEnum(str, Enum, metaclass=VerboseEnumMeta):  # pragma: no cover
    """
    A custom base class for enumeration, extending the capabilities of standard Enum types.

    This base class allows for additional functionalities in Enums such as retrieving an enum instance
    using a string representation of its name, and providing a method to get all values of the enum.

    """

    def __init__(self, *args, **kwargs):
        super().__init__()

    def __str__(self):
        return self.value

    def __repr__(self):
        return f'{self.__class__.__name__}.{self.value}'

    def __reduce_ex__(self, proto):
        return self.__class__, (self.value,)

    def __lt__(self, other):
        return self.value < other.value

    def to_json(self):
        return f'{self.__class__.__name__}.{str(self)}'

    def copy(self):
        return copy.copy(self)


def execute_with_key(key, func, *args, **kwargs):  # pragma: no cover
    try:
        return key, func(*args, **kwargs)
    except Exception as e:
        return key, e


def execute_in_parallel(
    func: callable, requests: Union[List[dict], Dict[str, dict]], max_workers: int = None, max_per_second: int = 20
) -> Union[dict, list]:
    """
    Executes a function in parallel using multiple sets of arguments with rate limiting.


    This function utilises a thread pool to execute the given 'func' concurrently across different sets
    of arguments specified in 'requests'. The 'requests' can be either a list or a dictionary.

    Parameters:
        func (callable): The function to be executed in parallel.
        requests (dict[str, dict] or list): A dictionary where keys are unique identifiers and values are
            dictionaries with 'args' and 'kwargs' for the 'func', or a list of such dictionaries.
        max_workers (int, optional): The maximum number of threads to use.
        max_per_second (int, optional): The maximum number of function executions per second. Defaults to 20.


    Returns:
        Union[dict, list]: A collection of results from the function executions, keyed by the same keys as
        'requests' if it is a dictionary, or a list in the same order as the 'requests' list.
        The function returns results in a dictionary if 'requests' was a dictionary, and a list if  'requests' was a list.
    """

    _requests = requests
    if isinstance(requests, list):
        _requests = {key: request for key, request in enumerate(requests)}

    results = {}
    start_time = time.time()
    num_requests = 0

    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix=func.__name__) as executor:
        futures = []
        for key, request in _requests.items():
            while num_requests >= max_per_second:
                if time.time() - start_time >= 1:
                    # Reset the counter and timer every second
                    num_requests = 0
                    start_time = time.time()

            args = request.get('args', [])
            kwargs = request.get('kwargs', {})
            future = executor.submit(execute_with_key, key, func, *args, **kwargs)
            futures.append(future)
            num_requests += 1

        for future in as_completed(futures):
            result = future.result()
            results[result[0]] = result[1]

    if isinstance(requests, list):
        results = [results[key] for key in range(len(requests))]

    return results


def filter_none(d):  # pragma: no cover
    """
    Recursively filters out None values from a dictionary or mapping object.

    This function iteratively processes each key-value pair in the provided dictionary (or any object
    that implements the Mapping interface) and removes any pairs where the value is None. If the value
    itself is a Mapping, the function is applied recursively to it.

    Parameters:
        d (Mapping): The dictionary or mapping object from which to filter out None values.

    Returns:
        Mapping: A new dictionary or mapping object with all None values removed. If the input is not
        a Mapping, it is returned unchanged.

    Note:
        - The function operates recursively, so nested dictionaries will also have None values removed.
        - This function does not modify the original dictionary but returns a new one with the changes.
    """
    if isinstance(d, Mapping):
        return {k: filter_none(v) for k, v in d.items() if v is not None}
    else:
        return d


class TimeoutLock:  # pragma: no cover
    """
    A lock with a timeout mechanism, extending the standard threading.RLock.

    This class provides a reentrant lock (RLock) that can be acquired for a limited duration. If the lock
    cannot be acquired within the specified timeout, the acquire method fails, preventing indefinite blocking.

    Constructor Parameters:
        timeout (int): The maximum time in seconds to wait for the lock to become available.
    """

    def __init__(self, timeout: int):
        self._lock = threading.RLock()
        self._timeout = timeout
        self._acquired = False

    def acquire(self, *args, **kwargs):
        self._acquired = self._lock.acquire(*args, timeout=self._timeout, **kwargs)

    def release(self):
        if self._acquired:
            self._lock.release()

    def __enter__(self):
        self.acquire()

    def __exit__(self, type, value, traceback):
        self.release()


# from https://stackoverflow.com/a/37135014/3508719
def exception_to_string(excp) -> str:  # pragma: no cover
    """
    Converts an exception into its string representation including chained exceptions.

    This function takes an exception object as input and returns a string representation of it,
    including any chained exceptions (exceptions raised with 'from' keyword).
    It is typically used for logging purposes or displaying error messages in a user-readable format.

    Parameters:
        excp (Exception): The exception object to be converted into a string.

    Returns:
        str: A string representation of the exception including chained exceptions.
    """
    stack = make_clean_stack() + traceback.extract_tb(excp.__traceback__)
    pretty = traceback.format_list(stack)
    excp_str = '\n' + ''.join(pretty) + '\n  {} {}'.format(excp.__class__, excp)

    # Handling chained exceptions
    cause = excp.__cause__
    while cause:
        cause_stack = traceback.extract_tb(cause.__traceback__)
        pretty_cause = traceback.format_list(cause_stack)
        excp_str += '\n\nThe below exception was the direct cause of the above exception:\n\n'
        excp_str += ''.join(pretty_cause) + '\n  {} {}'.format(cause.__class__, cause)
        cause = cause.__cause__

    return excp_str


def make_clean_stack() -> [traceback.FrameSummary]:  # pragma: no cover
    return [
        s
        for s in traceback.extract_stack()
        if all(substring not in s.filename for substring in ['JetBrains', os.path.join('Lib', 'unittest'), os.path.join('Lib', 'logging')])
    ][:-2]


def wait_until(condition: callable, timeout_message: str = None, timeout: float = 5, sleep: float = 0.1) -> bool:
    """
     Pauses program execution until a specified condition becomes True or a timeout is reached.

    Parameters:
         condition (callable): A callable that returns a boolean value. The function waits until this callable returns True.
         timeout_message (str, optional): A message to log as an error if the timeout is reached. If None, no message is logged. Defaults to None.
         timeout (float, optional): The maximum time to wait for the condition to become True, in seconds. Defaults to 5 seconds.
         sleep (float, optional): The delay between condition reattempts.

     Returns:
         bool: True if the condition becomes True within the timeout period, False otherwise.
    """

    deadline = time.time() + timeout
    while time.time() < deadline:
        if condition():
            return True
        time.sleep(sleep)

    if timeout_message is not None:
        _LOGGER.error(timeout_message)

    return False


def tname():  # pragma: no cover
    """
    Generates a unique name for the current thread.

    Returns:
        str: A string combining the current thread's name and its unique identifier.
    """
    return f'{threading.current_thread().name}-{threading.get_ident()}'


def params_dict(required: dict = None, optional: dict = None, preprocessors: dict = None):
    d = required if required is not None else {}

    if optional is None:
        return d

    for key, value in optional.items():
        if value is not None and value != [None]:
            new_value = value
            if preprocessors is not None and key in preprocessors:
                new_value = preprocessors[key](value)
            d[key] = new_value

    if d == {}:
        return None

    return d


def print_table(my_dict, column_order=None):
    if not column_order:
        column_order = list(my_dict[0].keys() if my_dict else [])
    rv = [column_order]  # 1st row = header
    for item in my_dict:
        rv.append([str(item[col] if item[col] is not None else '') for col in column_order])
    column_size = [max(map(len, col)) for col in zip(*rv)]
    formatter = '   '.join(['{{:>{}}}'.format(i) for i in column_size])
    for i, item in enumerate(rv):
        print(formatter.format(*item))


def patch_dotenv():
    try:
        import dotenv
        from dotenv import load_dotenv

        # Wrap the original load_dotenv function
        def warn_if_late_load(*args, **kwargs):
            if 'ibind.var' in sys.modules:
                warnings.warn(
                    '⚠️ WARNING: `load_dotenv()` was called after `ibind` was imported. Environment variables were already read and changes may not take effect. Call `load_dotenv()` before importing `ibind` to ensure proper behavior.',
                    RuntimeWarning,
                    stacklevel=2,
                )
            return load_dotenv(*args, **kwargs)

        # Replace the original load_dotenv with the wrapped version
        dotenv.load_dotenv = warn_if_late_load

    except ImportError:
        pass  # dotenv is not installed, nothing to patch