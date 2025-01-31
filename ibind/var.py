import os
import tempfile

# from: https://github.com/drgarcia1986/simple-settings/pull/281/files
_MAP = {
    'y': True,
    'yes': True,
    't': True,
    'true': True,
    'on': True,
    '1': True,
    'n': False,
    'no': False,
    'f': False,
    'false': False,
    'off': False,
    '0': False
}


def strtobool(value):
    try:
        return _MAP[str(value).lower()]
    except KeyError:
        raise ValueError('"{}" is not a valid bool value'.format(value))


def to_bool(value):
    return bool(strtobool(str(value)))


##### LOGS #####

LOG_TO_CONSOLE = to_bool(os.environ.get('IBIND_LOG_TO_CONSOLE', True))
""" Whether logs should be streamed to the standard output. """

LOG_TO_FILE = to_bool(os.environ.get('IBIND_LOG_TO_FILE', True))
""" Whether logs should be saved to a file. """

LOG_LEVEL = os.getenv('IBIND_LOG_LEVEL', 'INFO')
""" The global log level for the StreamHandler. """

LOG_FORMAT = os.getenv('IBIND_LOG_FORMAT', '%(asctime)s|%(levelname)-.1s| %(message)s')
""" Log format that is used by IBind """

LOGS_DIR = os.getenv('IBIND_LOGS_DIR', tempfile.gettempdir())
""" Directory of file logs produced. """

##### IBKR #####

IBIND_REST_URL = os.getenv('IBIND_REST_URL', None)
""" IBKR Client Portal Gateway's URL for REST API."""

IBIND_WS_URL = os.getenv('IBIND_WS_URL', None)
""" IBKR Client Portal Gateway's URL for WebSocket API."""

IBIND_ACCOUNT_ID = os.getenv('IBIND_ACCOUNT_ID', None)
""" IBKR account ID to use."""

IBIND_CACERT = os.getenv('IBIND_CACERT', False)
""" Path to certificates used to communicate with IBKR Client Portal Gateway."""

IBIND_WS_PING_INTERVAL = int(os.getenv('IBIND_WS_PING_INTERVAL', 45))
""" Interval between WebSocket pings. """

IBIND_WS_MAX_PING_INTERVAL = int(os.getenv('IBIND_WS_MAX_PING_INTERVAL', 300))
""" Max accepted interval between WebSocket pings. """

IBIND_WS_TIMEOUT = int(os.getenv('IBIND_WS_TIMEOUT', 5))
""" Timeout for WebSocket state change verifications. """

IBIND_WS_SUBSCRIPTION_RETRIES = int(os.getenv('IBIND_WS_SUBSCRIPTION_RETRIES', 5))
""" Number of attempts to create a WebSocket subscription. """

IBIND_WS_SUBSCRIPTION_TIMEOUT = int(os.getenv('IBIND_WS_SUBSCRIPTION_TIMEOUT', 2))
""" Timeout for WebSocket subscription verifications. """

IBIND_WS_LOG_RAW_MESSAGES = to_bool(os.environ.get('IBIND_WS_LOG_RAW_MESSAGES', False))
""" Whether raw WebSocket messages should be logged. """

##### OAuth #####

IBIND_USE_OAUTH = to_bool(os.environ.get('IBIND_USE_OAUTH', False))
""" Whether OAuth should be used. """

IBIND_OAUTH_REST_URL = os.getenv('IBIND_OAUTH_REST_URL', 'https://api.ibkr.com/v1/api/')
""" IBKR Client Portal OAuth base URL for REST API. """

IBIND_OAUTH_WS_URL = os.getenv('IBIND_OAUTH_WS_URL', 'wss://api.ibkr.com/v1/api/ws')
""" IBKR Client Portal OAuth base URL for WebSocket API. """

IBIND_LIVE_SESSION_TOKEN_ENDPOINT = os.getenv('IBIND_LIVE_SESSION_TOKEN_ENDPOINT', 'oauth/live_session_token')
""" Endpoint for OAuth Live Session Token. """

IBIND_ACCESS_TOKEN = os.getenv('IBIND_ACCESS_TOKEN', None)
""" OAuth access token generated in the self-service portal. """

IBIND_ACCESS_TOKEN_SECRET = os.getenv('IBIND_ACCESS_TOKEN_SECRET', None)
""" OAuth access token secret generated in the self-service portal. """

IBIND_CONSUMER_KEY = os.getenv('IBIND_CONSUMER_KEY', None)
""" The consumer key configured during the onboarding process. This uniquely identifies the project in the IBKR ecosystem. """

IBIND_DH_PRIME = os.getenv('IBIND_DH_PRIME', None)
""" The hex representation of the Diffie-Hellman prime. """

IBIND_ENCRYPTION_KEY_FP = os.getenv('IBIND_ENCRYPTION_KEY_FP', None)
""" The path to the private OAuth encryption key. """

IBIND_SIGNATURE_KEY_FP = os.getenv('IBIND_SIGNATURE_KEY_FP', None)
""" The path to the private OAuth signature key. """

IBIND_DH_GENERATOR = int(os.getenv('IBIND_DH_GENERATOR', 2))
""" The Diffie-Hellman generator value. """

IBIND_REALM = os.getenv('IBIND_REALM', 'limited_poa')
""" OAuth connection type. This is generally set to "limited_poa", however should be set to "test_realm" when using the TESTCONS consumer key. """

IBIND_INIT_OAUTH = to_bool(os.environ.get('IBIND_INIT_OAUTH', True))
""" Whether OAuth should be automatically initialised. """

IBIND_MAINTAIN_OAUTH = to_bool(os.environ.get('IBIND_MAINTAIN_OAUTH', True))
""" Whether OAuth should be automatically maintained. """

IBIND_SHUTDOWN_OAUTH = to_bool(os.environ.get('IBIND_SHUTDOWN_OAUTH', True))
""" Whether OAuth should be automatically stopped on termination. """