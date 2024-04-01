import os
import tempfile
from distutils.util import strtobool


def to_bool(value):
    return bool(strtobool(str(value)))


##### LOGS #####

LOG_TO_CONSOLE = to_bool(os.environ.get('IBIND_LOG_TO_CONSOLE', True))
"""Whether logs should be streamed to the standard output."""

LOG_LEVEL = os.getenv('IBIND_LOG_LEVEL', 'DEBUG')
""" The global log level for the StreamHandler. """

LOG_FORMAT = os.getenv('IBIND_LOG_FORMAT', '%(asctime)s|%(levelname)-.1s| %(message)s')
""" Log format that is used by IBind """

LOGS_DIR = os.getenv('IBIND_LOGS_DIR', tempfile.gettempdir())
""" Directory of file logs produced. """

LOG_TO_FILE = to_bool(os.environ.get('IBIND_LOG_TO_FILE', True))
"""Whether logs should be saved to a file."""

##### IBKR #####

IBKR_URL = os.getenv('IBKR_URL', None)
""" IBKR Client Portal Gateway's URL for REST API."""

IBKR_WS_URL = os.getenv('IBKR_WS_URL', None)
""" IBKR Client Portal Gateway's URL for WebSocket API."""

IBKR_ACCOUNT_ID = os.getenv('IBKR_ACCOUNT_ID', None)
""" IBKR account ID to use."""

IBKR_CACERT = os.getenv('IBKR_CACERT', False)
""" Path to certificates used to communicate with IBKR Client Portal Gateway."""

IBKR_WS_PING_INTERVAL = int(os.getenv('IBKR_WS_PING_INTERVAL', 45))
""" Interval between WebSocket pings. """

IBKR_WS_MAX_PING_INTERVAL = int(os.getenv('IBKR_WS_MAX_PING_INTERVAL', 300))
""" Max accepted interval between WebSocket pings. """

IBKR_WS_TIMEOUT = int(os.getenv('IBKR_WS_TIMEOUT', 5))
""" Timeout for WebSocket state change verifications. """

IBKR_WS_SUBSCRIPTION_RETRIES = int(os.getenv('IBKR_WS_SUBSCRIPTION_RETRIES', 5))
""" Number of attempts to create a WebSocket subscription. """

IBKR_WS_SUBSCRIPTION_TIMEOUT = int(os.getenv('IBKR_WS_SUBSCRIPTION_TIMEOUT', 2))
""" Timeout for WebSocket subscription verifications. """
