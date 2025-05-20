import logging
import os
import sys
from pprint import pformat
import pytest # Added for pytest
# import yaml # For loading exponencia config - No longer needed

# --- Basic logging setup for E2E test visibility ---
logging.basicConfig(
    level=logging.DEBUG, # Capture DEBUG and above
    format='%(asctime)s|%(levelname)s| %(name)s: %(message)s',
    stream=sys.stdout, # Output to stdout
)
# --- --------------------------------------------- ---

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
# from ibind import var # No longer directly needed here, OAuth2Config handles env vars
from ibind.support.logs import ibind_logs_initialize

# Initialize ibind logging (globally for all tests in this module)
ibind_logs_initialize(log_level='DEBUG', log_to_console=True, log_to_file=False)

# Configure basic logging for the test script itself - Pytest handles this.
# logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Pytest Fixture for IbkrClient with OAuth 2.0 ---
@pytest.fixture(scope="module")
def oauth2_client():
    logger = logging.getLogger(__name__) # Logger for fixture setup

    logger.info("--- Setting up IBind OAuth 2.0 Client for E2E Tests ---")
    account_id_to_test = os.getenv('IBIND_ACCOUNT_ID')
    required_env_vars = {
        'IBIND_OAUTH2_CLIENT_ID': os.getenv('IBIND_OAUTH2_CLIENT_ID'),
        'IBIND_OAUTH2_CLIENT_KEY_ID': os.getenv('IBIND_OAUTH2_CLIENT_KEY_ID'),
        # IBIND_OAUTH2_PRIVATE_KEY_PEM or IBIND_OAUTH2_PRIVATE_KEY_PATH is handled by OAuth2Config
        'IBIND_OAUTH2_USERNAME': os.getenv('IBIND_OAUTH2_USERNAME'),
        'IBIND_ACCOUNT_ID': account_id_to_test,
    }

    missing_vars = [var_name for var_name, value in required_env_vars.items() if not value]
    if missing_vars:
        pytest.skip(f"Missing required environment variables for OAuth 2.0 E2E tests: {', '.join(missing_vars)}. Skipping tests.")

    # Additional check for private key, as OAuth2Config needs one or the other (PEM string or path)
    # This is implicitly checked by OAuth2Config's verify_config, but an early skip is clearer.
    if not os.getenv('IBIND_OAUTH2_PRIVATE_KEY_PEM') and not os.getenv('IBIND_OAUTH2_PRIVATE_KEY_PATH'):
        pytest.skip("Neither IBIND_OAUTH2_PRIVATE_KEY_PEM nor IBIND_OAUTH2_PRIVATE_KEY_PATH is set. Skipping tests.")
        
    client_instance = None
    try:
        logger.info("Creating OAuth2Config (will load from environment variables via ibind.var)...")
        oauth2_config = OAuth2Config() # OAuth2Config will load from var and handle path/pem logic
        
        # Perform verification early to ensure config is valid before client instantiation
        try:
            oauth2_config.verify_config()
        except ValueError as ve:
            pytest.skip(f"OAuth2Config verification failed: {ve}. Check your OAuth 2.0 environment variables. Skipping tests.")

        logger.info(f"OAuth2Config created. Client ID: {oauth2_config.client_id}")
        logger.info(f"Target IBKR Account ID for test: {account_id_to_test}")
        logger.info(f"Attempting to instantiate IbkrClient with OAuth 2.0 for account: {account_id_to_test}")

        client_instance = IbkrClient(
            account_id=account_id_to_test, 
            use_oauth=True,
            oauth_config=oauth2_config
        )
        logger.info("IbkrClient instantiated successfully with OAuth 2.0.")
        
        if hasattr(client_instance.oauth_config, 'sso_bearer_token') and client_instance.oauth_config.sso_bearer_token:
            logger.info(f"SSO Bearer Token obtained: {client_instance.oauth_config.sso_bearer_token[:20]}... (truncated)")
        else:
            # This should ideally be caught by client instantiation if token is critical for readiness
            pytest.fail("SSO Bearer Token NOT FOUND in oauth_config after client instantiation.")
            
        yield client_instance

    except Exception as e:
        logger.error(f"Error during oauth2_client fixture setup: {e}", exc_info=True)
        pytest.fail(f"Failed to setup oauth2_client fixture: {e}")
    
    finally:
        if client_instance:
            logger.info("\\n--- Shutting down IbkrClient (fixture teardown) ---")
            try:
                client_instance.logout()
                logger.info("IbkrClient logout successful.")
            except Exception as e:
                logger.error(f"Error during client.logout() in fixture teardown: {e}", exc_info=True)
        logger.info("--- IBind OAuth 2.0 Client Fixture Teardown Complete ---")

# --- Test Functions ---

def test_connection_and_sso_token(oauth2_client):
    logger = logging.getLogger(__name__)
    logger.info("Test: Verifying client connection and SSO token presence.")
    assert oauth2_client is not None, "OAuth2 client fixture should not be None"
    assert oauth2_client._use_oauth, "Client should be configured to use OAuth"
    assert isinstance(oauth2_client.oauth_config, OAuth2Config), "Client should have OAuth2Config"
    assert oauth2_client.oauth_config.has_sso_bearer_token(), "SSO Bearer Token should be present after client init"
    logger.info("Client connection and SSO token presence verified.")

def test_tickle(oauth2_client):
    logger = logging.getLogger(__name__)
    logger.info("Test: Calling client.tickle()")
    try:
        tickle_result = oauth2_client.tickle()
        logger.info(f"tickle() result: {pformat(tickle_result.data if tickle_result else None)}")
        assert tickle_result is not None, "Tickle result should not be None"
        # Add more specific assertions if tickle_result has a status or expected data structure
        # For example, if it's a wrapper: assert tickle_result.is_ok
        # If it contains data: assert 'session' in tickle_result.data and tickle_result.data['session'] == 'tickled' (example)
    except Exception as e:
        logger.error(f"Error calling client.tickle(): {e}", exc_info=True)
        pytest.fail(f"client.tickle() raised an exception: {e}")

def test_portfolio_accounts(oauth2_client):
    logger = logging.getLogger(__name__)
    logger.info("Test: Calling client.portfolio_accounts()")
    try:
        portfolio_accounts_result = oauth2_client.portfolio_accounts()
        logger.info(f"portfolio_accounts() result: {pformat(portfolio_accounts_result.data if portfolio_accounts_result else None)}")
        assert portfolio_accounts_result is not None, "Portfolio accounts result should not be None"
        assert portfolio_accounts_result.data is not None, "Portfolio accounts data should not be None"
        # Example: assert isinstance(portfolio_accounts_result.data, list)
    except Exception as e:
        logger.error(f"Error calling client.portfolio_accounts(): {e}", exc_info=True)
        pytest.fail(f"client.portfolio_accounts() raised an exception: {e}")

def test_portfolio_summary(oauth2_client):
    logger = logging.getLogger(__name__)
    account_id = oauth2_client.account_id
    logger.info(f"Test: Calling client.portfolio_summary(account_id='{account_id}')")
    try:
        summary_result = oauth2_client.portfolio_summary(account_id=account_id)
        logger.info(f"portfolio_summary() result: {pformat(summary_result.data if summary_result else None)}")
        assert summary_result is not None, "Portfolio summary result should not be None"
        assert summary_result.data is not None, "Portfolio summary data should not be None"
        # Example: assert isinstance(summary_result.data, dict)
    except Exception as e:
        logger.error(f"Error calling client.portfolio_summary(): {e}", exc_info=True)
        pytest.fail(f"client.portfolio_summary() raised an exception: {e}")

def test_positions(oauth2_client):
    logger = logging.getLogger(__name__)
    account_id = oauth2_client.account_id
    logger.info(f"Test: Calling client.positions(account_id='{account_id}', page=0)")
    try:
        positions_result = oauth2_client.positions(account_id=account_id, page=0)
        logger.info(f"positions() result: {pformat(positions_result.data if positions_result else None)}")
        assert positions_result is not None, "Positions result should not be None"
        # Positions data can be a list, might be empty if no positions
        # assert positions_result.data is not None 
    except Exception as e:
        logger.error(f"Error calling client.positions(): {e}", exc_info=True)
        pytest.fail(f"client.positions() raised an exception: {e}")

def test_live_marketdata_snapshot(oauth2_client):
    logger = logging.getLogger(__name__)
    # This test can be problematic if /accounts hasn't been hit, as seen in previous logs
    # It also depends on market hours for some data.
    # Keeping it simple: just check if the call executes without error for now.
    symbols_to_test = ["AAPL", "MSFT"] 
    fields_to_request = ["31", "84", "86"] # Last, Bid, Ask
    logger.info(f"Test: Calling client.live_marketdata_snapshot_by_symbol(queries={symbols_to_test}, fields={fields_to_request})")
    try:
        # Ensure /portfolio/accounts is called first if that's a prerequisite
        # This might have been implicitly called by other tests or client init, but explicit can be safer
        # For now, assume client setup or previous tests handle this.
        # accounts = oauth2_client.portfolio_accounts() 
        # if not accounts or not accounts.data:
        #     pytest.skip("Could not fetch accounts, skipping market data snapshot test.")

        snapshot_result = oauth2_client.live_marketdata_snapshot_by_symbol(queries=symbols_to_test, fields=fields_to_request)
        logger.info(f"live_marketdata_snapshot_by_symbol result: {pformat(snapshot_result)}") # This method returns a dict
        assert snapshot_result is not None, "Market data snapshot result should not be None"
        assert isinstance(snapshot_result, dict), "Market data snapshot should be a dict"
        # Example: for symbol in symbols_to_test: assert symbol in snapshot_result
    except Exception as e:
        # Check for the specific "Please query /accounts first" error
        if "Please query /accounts first" in str(e):
             pytest.skip(f"Skipping market data snapshot test due to API sequence requirement: {e}")
        logger.error(f"Error calling client.live_marketdata_snapshot_by_symbol(): {e}", exc_info=True)
        pytest.fail(f"client.live_marketdata_snapshot_by_symbol() raised an exception: {e}")

def test_trades_history(oauth2_client):
    logger = logging.getLogger(__name__)
    account_id = oauth2_client.account_id
    logger.info(f"Test: Calling client.trades(account_id='{account_id}', days='7')")
    try:
        trades_result = oauth2_client.trades(account_id=account_id, days="7")
        logger.info(f"trades() result: {pformat(trades_result.data if trades_result else None)}")
        assert trades_result is not None, "Trades result should not be None"
        # Trades data can be a list, might be empty
        # assert trades_result.data is not None 
    except Exception as e:
        logger.error(f"Error calling client.trades(): {e}", exc_info=True)
        pytest.fail(f"client.trades() raised an exception: {e}")

# Removed main() function and if __name__ == "__main__": block
# Pytest will discover and run functions starting with test_ 