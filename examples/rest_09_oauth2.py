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

# --- Add python-dotenv logic to load .env from project root ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Project root is one level up from the 'examples' directory
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
dotenv_path_project_root = os.path.join(PROJECT_ROOT, '.env')

try:
    from dotenv import load_dotenv
    if os.path.exists(dotenv_path_project_root):
        print(f"Loading environment variables from project root: {dotenv_path_project_root}")
        load_dotenv(dotenv_path=dotenv_path_project_root)
    else:
        print(f".env file not found in project root ({PROJECT_ROOT}). Will rely on system environment or pre-set vars.")
except ImportError:
    print("python-dotenv library not found. Cannot load .env file. Ensure it is installed (`uv pip install python-dotenv`).")
# --- End of python-dotenv logic ---

from ibind import IbkrClient, ibind_logs_initialize
from ibind.oauth.oauth2 import OAuth2Config

# Initialize IBind logs (optional, but good for seeing what's happening)
ibind_logs_initialize()

cacert = os.getenv('IBIND_CACERT', False)  # Standard cacert, though OAuth usually implies HTTPS

# --- Option 1: Rely on Environment Variables (as described in docstring) ---
# Ensure IBIND_USE_OAUTH=True and all IBIND_OAUTH2_* vars are set.
# client = IbkrClient(cacert=cacert, use_oauth=True)

# --- Option 2: Provide OAuth2Config dynamically (recommended for private_key_pem) ---
# This approach is often easier for managing the private key PEM.

# Check if core OAuth2 env vars are present to decide which path to take for the example
# This is just for the example's logic; in your own code, you'd choose one method.
if (os.getenv('IBIND_OAUTH2_CLIENT_ID') and
    os.getenv('IBIND_OAUTH2_CLIENT_KEY_ID') and
    os.getenv('IBIND_OAUTH2_PRIVATE_KEY_PEM') and
    os.getenv('IBIND_OAUTH2_USERNAME')):
    print("Found OAuth 2.0 environment variables. Initializing IbkrClient with use_oauth=True.")
    print("Ensure IBIND_USE_OAUTH is also set to True in your environment, or use_oauth=True is passed explicitly.")
    # When using env vars, IbkrClient will internally create an OAuth2Config if it detects
    # that it should be using OAuth2 based on some logic (e.g. if specific OAuth2 vars are present)
    # or if you explicitly pass an OAuth2Config instance.
    # For this example, assuming IBIND_USE_OAUTH=True is set in the environment
    # and IbkrClient correctly picks OAuth2Config based on available env vars.
    # A more explicit way when relying on env vars for OAuth2 would be:
    # client = IbkrClient(cacert=cacert, use_oauth=True, oauth_config=OAuth2Config())
    # This tells it to definitely use OAuth2Config, which will then pull from env vars.
    client = IbkrClient(cacert=cacert, use_oauth=True, oauth_config=OAuth2Config())
    print("IbkrClient initialized. Will attempt API calls.")
else:
    print("Core OAuth 2.0 environment variables not found.")
    print("Please set IBIND_OAUTH2_CLIENT_ID, IBIND_OAUTH2_CLIENT_KEY_ID, IBIND_OAUTH2_PRIVATE_KEY_PEM, and IBIND_OAUTH2_USERNAME.")
    print("Alternatively, configure OAuth2Config dynamically in the script (see example comments).")
    print("Exiting example as configuration is missing.")
    client = None # Ensure client is None if not configured

if client:
    try:
        print('\n#### Attempting to tickle (check connection/authentication) ####')
        tickle_result = client.tickle()
        if tickle_result and tickle_result.data:
            print(f'Tickle successful: {tickle_result.data}')
        else:
            print(f'Tickle call did not return expected data or failed. Result: {tickle_result}')

        print('\n\n#### get_accounts ####')
        # Ensure account_id is set if operations require it, though portfolio_accounts might not.
        # client.account_id = 'YourSpecificAccountId' # If needed for other calls
        accounts_result = client.portfolio_accounts()
        if accounts_result and accounts_result.data:
            accounts = accounts_result.data
            print(accounts)
            # Set account_id from the first found account for subsequent calls if needed
            if isinstance(accounts, list) and len(accounts) > 0 and 'accountId' in accounts[0]:
                client.account_id = accounts[0]['accountId']
                print(f"Set client.account_id to: {client.account_id}")
            else:
                print("Could not determine accountId from portfolio_accounts response.")
        else:
            print(f'get_accounts call did not return expected data or failed. Result: {accounts_result}')

        # Check authentication status if available
        if hasattr(client, 'authentication_status'):
            print('\n\n#### authentication_status ####')
            auth_status_result = client.authentication_status()
            if auth_status_result and auth_status_result.data:
                print(auth_status_result.data)
            else:
                print(f'authentication_status call did not return expected data or failed. Result: {auth_status_result}')

        if client.account_id: # Proceed only if account_id was set
            print('\n\n#### get_ledger ####')
            ledger_result = client.get_ledger(client.account_id)
            if ledger_result and ledger_result.data:
                ledger = ledger_result.data
                for currency, subledger in ledger.items():
                    print(f'\t Ledger currency: {currency}')
                    print(f'\t cash balance: {subledger.get("cashbalance", "N/A")}')
                    print(f'\t net liquidation value: {subledger.get("netliquidationvalue", "N/A")}')
                    print(f'\t stock market value: {subledger.get("stockmarketvalue", "N/A")}')
                    print()
            else:
                print(f'get_ledger call did not return expected data or failed. Result: {ledger_result}')

            print('\n#### get_positions ####')
            positions_result = client.positions(client.account_id)
            if positions_result and positions_result.data:
                positions = positions_result.data
                for position in positions:
                    print(f'\t Position {position.get("ticker", "N/A")}: {position.get("position", 0)} (${position.get("mktValue", 0.0)})')
            else:
                print(f'get_positions call did not return expected data or failed. Result: {positions_result}')
        else:
            print("\nSkipping Ledger and Positions calls as client.account_id is not set.")

    except Exception as e:
        print(f"\nAn error occurred during API calls: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if hasattr(client, 'close'):
            print("\nClosing client session.")
            client.close() # Important to close to allow oauth_shutdown to be called
else:
    print("Client not initialized due to missing configuration.")

print("\nExample finished.")
