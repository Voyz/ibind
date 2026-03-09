"""
REST OAuth 2.0.

Showcases usage of OAuth 2.0 with IbkrClient.

This example demonstrates authenticating using OAuth 2.0 and making some basic API calls.

Using IbkrClient with OAuth 2.0 support will automatically handle generating the JWTs
and managing the SSO bearer token. You should be able to use all endpoints in the same
way as when not using OAuth.

IMPORTANT: In order to use OAuth 2.0, you're required to set up the following
environment variables:

- IBIND_USE_OAUTH: Set to True (or pass use_oauth=True to IbkrClient).
- IBIND_OAUTH2_CLIENT_ID: Your OAuth 2.0 Client ID.
- IBIND_OAUTH2_CLIENT_KEY_ID: Your OAuth 2.0 Client Key ID (kid).
- IBIND_OAUTH2_PRIVATE_KEY_PEM: Your OAuth 2.0 private key in PEM format.
    To set this as an environment variable, you should replace newlines (\n)
    in your PEM file with the literal characters '\\n'.
    For example, if your key is:
    ----BEGIN PRIVATE KEY-----
    ABC\nDEF
    -----END PRIVATE KEY-----
    You would set the environment variable as:
    IBIND_OAUTH2_PRIVATE_KEY_PEM="-----BEGIN PRIVATE KEY-----\\nABC\\nDEF\\n-----END PRIVATE KEY-----"
- IBIND_OAUTH2_USERNAME: Your IBKR username associated with the OAuth 2.0 app.

Optionally, you can also set these if they differ from the defaults:
- IBIND_OAUTH2_TOKEN_URL: Defaults to 'https://api.ibkr.com/oauth2/api/v1/token'.
- IBIND_OAUTH2_SSO_SESSION_URL: Defaults to 'https://api.ibkr.com/gw/api/v1/sso-sessions'.
- IBIND_OAUTH2_AUDIENCE: Defaults to '/token'.
- IBIND_OAUTH2_SCOPE: Defaults to 'sso-sessions.write'.
- IBIND_OAUTH2_REST_URL: Defaults to 'https://api.ibkr.com/v1/api/'.
- IBIND_OAUTH2_IP_ADDRESS: Your public IP address. If not set, the library will attempt to fetch it.

If you prefer setting these variables inline, you can pass an instance of the
OAuth2Config class as the 'oauth_config' parameter to the IbkrClient constructor.
This is especially useful if managing the PEM key via environment variables is cumbersome.

Example of dynamic configuration:
from ibind import IbkrClient
from ibind.oauth.oauth2 import OAuth2Config

oauth_cfg = OAuth2Config(
    client_id='your_client_id',
    client_key_id='your_client_key_id',
    private_key_pem='-----BEGIN PRIVATE KEY-----\nYOUR KEY HERE\n-----END PRIVATE KEY-----', # Direct string
    username='your_ibkr_username'
    # ... any other overrides
)
client = IbkrClient(use_oauth=True, oauth_config=oauth_cfg)

This example assumes environment variables are set for simplicity.
"""

import os

from ibind import IbkrClient, ibind_logs_initialize
from ibind.oauth.oauth2 import OAuth2Config

ibind_logs_initialize()

client = IbkrClient(
    cacert=os.getenv('IBIND_CACERT', False),
    use_oauth=True,
    oauth_config=OAuth2Config(),
)

try:
    print(client.tickle().data)
finally:
    client.close()
