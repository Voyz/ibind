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
from ibind import IbkrClient, OAuth2Config

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

# Initialize IBind logs (optional, but good for seeing what's happening)
ibind_logs_initialize()

cacert = os.getenv('IBIND_CACERT', False)  # Standard cacert, though OAuth usually implies HTTPS

# --- Essential OAuth 2.0 Environment Variables ---
# These must be set for the example to run using environment-based configuration.
required_env_vars = [
    'IBIND_OAUTH2_CLIENT_ID',
    'IBIND_OAUTH2_CLIENT_KEY_ID',
    'IBIND_OAUTH2_PRIVATE_KEY_PEM',
    'IBIND_OAUTH2_USERNAME',
    'IBIND_USE_OAUTH' # Ensure this is also set, typically to "True"
]

missing_vars = [var_name for var_name in required_env_vars if not os.getenv(var_name)]

client = None
if missing_vars:
    print("Missing required OAuth 2.0 environment variables for this example:")
    for var_name in missing_vars:
        print(f"  - {var_name}")
    print("Please set them to run this example, or configure OAuth2Config dynamically (see docstring).")
    print("Exiting example.")
else:
    if os.getenv('IBIND_USE_OAUTH', '').lower() != 'true':
        print("Warning: IBIND_USE_OAUTH is not set to 'True'.")
        print("         The client might not attempt OAuth 2.0 as expected by this example.")
        # Proceeding anyway, as IbkrClient might still be configured via oauth_config directly below

    print("Found required OAuth 2.0 environment variables. Initializing IbkrClient...")
    # IbkrClient will use OAuth2Config by default if use_oauth=True and relevant OAuth2 env vars are present.
    # Passing an explicit OAuth2Config() ensures it uses OAuth2 and loads from env vars.
    try:
        client = IbkrClient(cacert=cacert, use_oauth=True, oauth_config=OAuth2Config())
        print("IbkrClient initialized for OAuth 2.0.")
    except Exception as e:
        print(f"Error initializing IbkrClient: {e}")
        client = None

if client:
    print("\nAttempting a simple API call to confirm OAuth 2.0 authentication...")
    try:
        tickle_result = client.tickle()
        if tickle_result and tickle_result.data and tickle_result.data.get('session') == 'authenticated': # Or other relevant check
            print("Tickle successful! OAuth 2.0 authentication appears to be working.")
            # Optionally print some part of tickle_result.data for confirmation
            # print(f"Tickle data: {tickle_result.data}")
        elif tickle_result and tickle_result.data: # Successful call but maybe not the expected auth confirmation
            print("Tickle call successful, but session status might not be 'authenticated' or as expected.")
            print(f"Tickle data: {tickle_result.data}")
        else:
            print("Tickle call failed or did not return expected data.")
            if tickle_result:
                print(f"Tickle result status: {tickle_result.status_code}, Raw response: {tickle_result.raw_response}")
            else:
                print("Tickle call returned no result object.")

    except Exception as e:
        print(f"\nAn error occurred during the API call: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if hasattr(client, 'close'):
            print("\nClosing client session.")
            client.close()
else:
    # This part is reached if client initialization failed earlier (e.g. missing env vars)
    # The message about missing env vars or init error would have already been printed.
    pass # No further action needed here, initial error messages suffice

print("\nExample finished.")
