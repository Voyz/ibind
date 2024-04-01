import os
import tempfile
from pathlib import Path

##### LOGS #####

LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')
""" The global log level for the SteamHandler. """

LOGS_DIR = os.getenv('LOGS_DIR', tempfile.gettempdir())
""" Directory of file logs produced. """


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