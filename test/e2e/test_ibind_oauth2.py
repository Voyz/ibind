import logging
import os
import sys
from pprint import pprint
# import yaml # For loading exponencia config - No longer needed

# --- Determine Project Root and add to sys.path if necessary for local dev ---
# SCRIPT_DIR is the directory of this script (e.g., /path/to/ibind/test/e2e)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# TEST_DIR is the parent of SCRIPT_DIR (e.g., /path/to/ibind/test)
TEST_DIR = os.path.dirname(SCRIPT_DIR)
# PROJECT_ROOT is the parent of TEST_DIR (e.g., /path/to/ibind)
PROJECT_ROOT = os.path.dirname(TEST_DIR)

# If ibind is not installed and we're running from a clone,
# adding PROJECT_ROOT to sys.path allows importing 'ibind' directly.
# This is often handled by test runners or virtual environments too.
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# --- ------------------------------------------------------------- ---

# Attempt to load .env file from project root
try:
    from dotenv import load_dotenv
    dotenv_path_project_root = os.path.join(PROJECT_ROOT, '.env')
    if os.path.exists(dotenv_path_project_root):
        print(f"Loading environment variables from project root: {dotenv_path_project_root}")
        load_dotenv(dotenv_path=dotenv_path_project_root)
    else:
        print(f".env file not found in project root ({PROJECT_ROOT}). Will rely on system environment variables.")
except ImportError:
    print("python-dotenv not found. Will rely on system environment variables.")

from ibind.client.ibkr_client import IbkrClient
from ibind.oauth.oauth2 import OAuth2Config
from ibind import var # To access environment variables defaults
from ibind.support.logs import ibind_logs_initialize

# Initialize ibind logging
ibind_logs_initialize(log_level='DEBUG', log_to_console=True, log_to_file=False)

# Configure basic logging for the test script itself
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Configuration for IBIND OAuth 2.0 Test ---
# This script relies solely on environment variables for configuration.
# Ensure a .env file in the project root directory (e.g., where pyproject.toml is)
# or system environment variables are set for the following:
# - IBIND_OAUTH2_CLIENT_ID
# - IBIND_OAUTH2_CLIENT_KEY_ID
# - IBIND_OAUTH2_PRIVATE_KEY_PEM (containing the actual multi-line PEM string)
# - IBIND_OAUTH2_USERNAME (containing the actual IBKR username)
# - IBIND_ACCOUNT_ID (the IBKR account number)
# (Optional: IBIND_OAUTH2_IP_ADDRESS if you want to pre-set it)
# Note: AWS-specific variables like IBIND_OAUTH2_PRIVATE_KEY_PEM_SECRET_NAME are no longer used by ibind core.
# EXPONENCIA_CONFIG_PATH constant is no longer needed.

def main():
    logger.info("--- Starting IBind OAuth 2.0 Direct Test Script ---")

    # The script now relies solely on environment variables.
    # Ensure IBIND_OAUTH2_CLIENT_ID and IBIND_ACCOUNT_ID are set.
    account_id_to_test = os.getenv('IBIND_ACCOUNT_ID')
    if not account_id_to_test:
        logger.error("IBIND_ACCOUNT_ID environment variable not set. Please define it in your .env file or system environment. Exiting.")
        return
    if not os.getenv('IBIND_OAUTH2_CLIENT_ID') or \
       not os.getenv('IBIND_OAUTH2_CLIENT_KEY_ID') or \
       not os.getenv('IBIND_OAUTH2_PRIVATE_KEY_PEM') or \
       not os.getenv('IBIND_OAUTH2_USERNAME'): 
        logger.error("Critical OAuth 2.0 environment variables (IBIND_OAUTH2_CLIENT_ID, "
                     "IBIND_OAUTH2_CLIENT_KEY_ID, IBIND_OAUTH2_PRIVATE_KEY_PEM, IBIND_OAUTH2_USERNAME) "
                     "are not set.")
        logger.error("Please create/update .env file or set system environment variables with these actual values. Exiting.")
        return

    client = None # Initialize client to None for finally block
    try:
        logger.info("Creating OAuth2Config (will load from environment variables via ibind.var)...")
        oauth2_config = OAuth2Config()
        logger.info(f"OAuth2Config created. Client ID: {oauth2_config.client_id}")
        logger.info(f"Target IBKR Account ID for test: {account_id_to_test}")
        logger.info(f"Attempting to instantiate IbkrClient with OAuth 2.0 for account: {account_id_to_test}")

        client = IbkrClient(
            account_id=account_id_to_test, 
            use_oauth=True,
            oauth_config=oauth2_config
        )

        logger.info("IbkrClient instantiated successfully with OAuth 2.0.")
        if hasattr(client.oauth_config, 'sso_bearer_token') and client.oauth_config.sso_bearer_token:
            logger.info(f"SSO Bearer Token: {client.oauth_config.sso_bearer_token[:20]}... (truncated)")
        else:
            logger.error("SSO Bearer Token NOT FOUND in oauth_config after client instantiation.")
            return

        # --- Test some simple API calls ---
        logger.info("\n--- Testing API Calls with OAuth 2.0 Token ---")

        # 1. Tickle (simple session keep-alive)
        try:
            logger.info("Calling client.tickle()...")
            tickle_result = client.tickle()
            logger.info("tickle() result:")
            pprint(tickle_result.data if tickle_result else None)
        except Exception as e:
            logger.error(f"Error calling client.tickle(): {e}", exc_info=True)

        # 2. Portfolio Accounts (requires authentication)
        try:
            logger.info("\nCalling client.portfolio_accounts()...")
            portfolio_accounts_result = client.portfolio_accounts()
            logger.info("portfolio_accounts() result:")
            pprint(portfolio_accounts_result.data if portfolio_accounts_result else None)
        except Exception as e:
            logger.error(f"Error calling client.portfolio_accounts(): {e}", exc_info=True)

        # 3. Account Summary for the primary account_id (using portfolio_summary)
        try:
            logger.info(f"\nCalling client.portfolio_summary(account_id='{client.account_id}')...")
            summary_result = client.portfolio_summary(account_id=client.account_id)
            logger.info(f"portfolio_summary(account_id='{client.account_id}') result:")
            pprint(summary_result.data if summary_result else None)
        except Exception as e:
            logger.error(f"Error calling client.portfolio_summary(): {e}", exc_info=True)

        # 4. Positions for the primary account_id
        try:
            logger.info(f"\nCalling client.positions(account_id='{client.account_id}', page=0)...")
            positions_result = client.positions(account_id=client.account_id, page=0)
            logger.info(f"positions(account_id='{client.account_id}', page=0) result:")
            # Positions can be a list, pprint it directly
            pprint(positions_result.data if positions_result else None)
        except Exception as e:
            logger.error(f"Error calling client.positions(): {e}", exc_info=True)

        # 5. Market Data Snapshot for a few symbols
        try:
            symbols_to_test = ["AAPL", "MSFT"] # Keep it short for testing
            # Common field codes: 31 (Last Price), 84 (Bid), 86 (Ask)
            # These might need to be adjusted based on ibind.client.ibkr_definitions
            fields_to_request = ["31", "84", "86"]
            
            logger.info(f"\nCalling client.live_marketdata_snapshot_by_symbol(queries={symbols_to_test}, fields={fields_to_request})...")
            # The StockQuery type can also be just a list of strings (symbols)
            snapshot_result = client.live_marketdata_snapshot_by_symbol(queries=symbols_to_test, fields=fields_to_request)
            logger.info(f"live_marketdata_snapshot_by_symbol result:")
            pprint(snapshot_result) # This method returns a dict directly
        except Exception as e:
            logger.error(f"Error calling client.live_marketdata_snapshot_by_symbol(): {e}", exc_info=True)

        # 6. Recent Trades (Order History)
        try:
            logger.info(f"\nCalling client.trades(account_id='{client.account_id}', days='7')...")
            # Request trades for the last 7 days
            trades_result = client.trades(account_id=client.account_id, days="7")
            logger.info(f"trades(days='7') result:")
            # Trades result is typically a list of trade objects
            pprint(trades_result.data if trades_result else None)
        except Exception as e:
            logger.error(f"Error calling client.trades(): {e}", exc_info=True)

    except Exception as e:
        logger.error(f"An error occurred during the IBind OAuth 2.0 test: {e}", exc_info=True)
    finally:
        if client: # Check if client was successfully instantiated
            logger.info("\n--- Shutting down IbkrClient ---")
            client.logout() # Changed from client.shutdown()
        logger.info("--- IBind OAuth 2.0 Direct Test Script Finished ---")

if __name__ == "__main__":
    main() 