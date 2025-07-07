import importlib.util
import os
from typing import Union, Optional, TYPE_CHECKING, cast

from ibind import var
from ibind.base.rest_client import RestClient, Result
from ibind.client.ibkr_client_mixins.accounts_mixin import AccountsMixin
from ibind.client.ibkr_client_mixins.contract_mixin import ContractMixin
from ibind.client.ibkr_client_mixins.marketdata_mixin import MarketdataMixin
from ibind.client.ibkr_client_mixins.order_mixin import OrderMixin
from ibind.client.ibkr_client_mixins.portfolio_mixin import PortfolioMixin
from ibind.client.ibkr_client_mixins.scanner_mixin import ScannerMixin
from ibind.client.ibkr_client_mixins.session_mixin import SessionMixin
from ibind.client.ibkr_client_mixins.watchlist_mixin import WatchlistMixin
from ibind.client.ibkr_utils import Tickler
from ibind.support.errors import ExternalBrokerError
from ibind.support.logs import new_daily_rotating_file_handler, project_logger
from ibind.support.py_utils import exception_to_string

if TYPE_CHECKING:  # pragma: no cover
    from ibind.oauth import OAuthConfig

_LOGGER = project_logger(__file__)


class IbkrClient(RestClient, AccountsMixin, ContractMixin, MarketdataMixin, OrderMixin, PortfolioMixin, ScannerMixin, SessionMixin, WatchlistMixin):
    """
    A client class for interfacing with the IBKR API, extending the RestClient class.

    This subclass of RestClient is specifically designed for the IBKR API. It inherits
    the foundational REST API interaction capabilities from RestClient and adds functionalities
    particular to the IBKR API, such as specific endpoint handling.

    The class provides methods to perform various operations with the IBKR API, such as
    fetching stock data, submitting orders, and managing account information.

    See: https://interactivebrokers.github.io/cpwebapi/endpoints

    Note:
        - All endpoint mappings are defined as class mixins, categorised similar to the IBKR REST API documentation. See appropriate mixins for more information.
    """

    def __init__(
        self,
        account_id: Optional[str] = var.IBIND_ACCOUNT_ID,
        url: str = var.IBIND_REST_URL,
        host: str = '127.0.0.1',
        port: str = '5000',
        base_route: str = '/v1/api/',
        cacert: Union[str, os.PathLike, bool] = var.IBIND_CACERT,
        timeout: float = 10,
        max_retries: int = 3,
        use_session: bool = var.IBIND_USE_SESSION,
        auto_register_shutdown: bool = var.IBIND_AUTO_REGISTER_SHUTDOWN,
        log_responses: bool = var.IBIND_LOG_RESPONSES,
        use_oauth: bool = var.IBIND_USE_OAUTH,
        oauth_config: 'OAuthConfig' = None,
    ) -> None:
        """
        Parameters:
            account_id (str): An identifier for the account. Defaults to None.
            url (str): The base URL for the REST API. Defaults to None.
                       If 'use_oauth' is specified, the url is taken from oauth_config.
                       Only if it couldn't be found in oauth_config, this url is used,
                       or the parameters host, port and base_route.
            host (str, optional): Host for the IBKR REST API. Defaults to 'localhost'.
            port (str, optional): Port for the IBKR REST API. Defaults to '5000'
            base_route (str, optional): Base route for the IBKR REST API. Defaults to '/v1/api/'.
            cacert (Union[os.PathLike, bool], optional): Path to the CA certificate file for SSL verification,
                                                         or False to disable SSL verification. Always True when
                                                         use_oauth is True. Defaults to False.
            timeout (float, optional): Timeout in seconds for the API requests. Defaults to 10.
            max_retries (int, optional): Maximum number of retries for failed API requests. Defaults to 3.
            use_session (bool, optional): Whether to use a persistent session for making requests. Defaults to True.
            auto_register_shutdown (bool, optional): Whether to automatically register a shutdown handler for this client. Defaults to True.
            use_oauth (bool, optional): Whether to use OAuth authentication. Defaults to False.
            oauth_config (OAuthConfig, optional): The configuration for the OAuth authentication. OAuth1aConfig is used if not specified.
        """
        self._tickler: Optional[Tickler] = None
        self._use_oauth = use_oauth

        if self._use_oauth:
            from ibind.oauth.oauth1a import OAuth1aConfig

            # cast to OAuth1aConfig for type checking, since currently 1.0a is the only version used
            self.oauth_config = cast(OAuth1aConfig, oauth_config) if oauth_config is not None else OAuth1aConfig()
            url = url if url is not None and self.oauth_config.oauth_rest_url is None else self.oauth_config.oauth_rest_url

        if url is None:
            url = f'https://{host}:{port}{base_route}'

        self.account_id = account_id

        cacert = True if self._use_oauth else cacert
        super().__init__(
            url=url,
            cacert=cacert,
            timeout=timeout,
            max_retries=max_retries,
            use_session=use_session,
            auto_register_shutdown=auto_register_shutdown,
            log_responses=log_responses,
        )

        self.logger.info('#################')
        self.logger.info(
            f'New IbkrClient(base_url={self.base_url!r}, account_id={self.account_id!r}, ssl={self.cacert!r}, timeout={self._timeout}, max_retries={self._max_retries}, use_oauth={self._use_oauth})'
        )

        if self._use_oauth:
            self.oauth_config.verify_config()

            if self.oauth_config.init_oauth:
                self.oauth_init(
                    maintain_oauth=self.oauth_config.maintain_oauth,
                    init_brokerage_session=self.oauth_config.init_brokerage_session,
                )

    def _make_logger(self):
        self._logger = new_daily_rotating_file_handler('IbkrClient', os.path.join(var.LOGS_DIR, f'ibkr_client_{self.account_id}'))

    def _request(self, method: str, endpoint: str, base_url: str = None, extra_headers: dict = None, log: bool = True, **kwargs) -> Result:
        """Handle IBKR-specific errors."""

        try:
            return super()._request(method, endpoint, base_url, extra_headers, log, **kwargs)
        except ExternalBrokerError as e:
            if 'Bad Request: no bridge' in str(e) and e.status_code == 400:
                raise ExternalBrokerError('IBKR returned 400 Bad Request: no bridge. Try calling `initialize_brokerage_session()` first.') from e
            raise

    def _get_headers(self, request_method: str, request_url: str):
        if (not self._use_oauth) or request_url == f'{self.base_url}{self.oauth_config.live_session_token_endpoint}':
            # No need for extra headers if we don't use oauth or getting live session token
            return {}

        # get headers for endpoints other than live session token request
        from ibind.oauth.oauth1a import generate_oauth_headers

        headers = generate_oauth_headers(
            oauth_config=self.oauth_config, request_method=request_method, request_url=request_url, live_session_token=self.live_session_token
        )

        return headers

    def generate_live_session_token(self):
        """
        Generates a new live session token for OAuth 1.0a authentication.

        This method requests a new OAuth live session token from the IBKR API using the configured
        OAuth credentials. The token is stored along with its expiration time and signature.

        The live session token is required for authenticated requests to IBKR's OAuth 1.0a API.

        Raises:
            ExternalBrokerError: If the token request fails.
        """
        from ibind.oauth.oauth1a import req_live_session_token

        self.live_session_token, self.live_session_token_expires_ms, self.live_session_token_signature = req_live_session_token(
            self, self.oauth_config
        )

    def oauth_init(self, maintain_oauth: bool, init_brokerage_session: bool):
        """
        Initializes the OAuth authentication flow for the IBKR API.

        This method sets up OAuth authentication by generating a live session token, validating it,
        and optionally starting a tickler to maintain the session. It also allows initializing a brokerage session if specified.

        OAuth authentication is required for certain IBKR API operations. The process includes:
        - Checking for the necessary cryptographic dependencies.
        - Generating and validating a live session token.
        - Optionally maintaining the session by running a tickler.
        - Initializing a brokerage session if required.

        Parameters:
            maintain_oauth (bool): If True, starts the Tickler process to keep the session alive.
            init_brokerage_session (bool): If True, initializes the brokerage session after authentication.

        Raises:
            ImportError: If the required cryptographic dependencies (`Crypto` module) are missing.
            RuntimeError: If live session token validation fails.

        See:
            - `generate_live_session_token`: Generates a new OAuth session token.
            - `validate_live_session_token`: Validates the generated OAuth session token.
            - `start_tickler`: Maintains the session by periodically sending requests.
            - `initialize_brokerage_session`: Establishes a brokerage session post-authentication.
        """
        _LOGGER.info(f'{self}: Initialising OAuth {self.oauth_config.version()}')

        if importlib.util.find_spec('Crypto') is None:
            raise ImportError('Installation lacks OAuth support. Please install by using `pip install ibind[oauth]`')

        # get live session token for OAuth authentication
        self.generate_live_session_token()

        # validate the live session token once
        from ibind.oauth.oauth1a import validate_live_session_token

        success = validate_live_session_token(
            live_session_token=self.live_session_token,
            live_session_token_signature=self.live_session_token_signature,
            consumer_key=self.oauth_config.consumer_key,
        )
        if not success:
            raise RuntimeError('Live session token validation failed.')

        if maintain_oauth:
            self.start_tickler()

        if init_brokerage_session:
            self.initialize_brokerage_session()

    def start_tickler(self, interval: int = var.IBIND_TICKLER_INTERVAL):
        """
        Starts the `Tickler` instance and starts it in a separate thread to maintain the OAuth session.

        The Tickler sends periodic requests to the IBKR API to prevent the session from expiring.
        This is necessary when using OAuth authentication to keep the connection active.

        Parameters:
            interval (Union[int, float]): Interval between tickles in seconds. Default is 60 seconds.

        Note:
            - The Tickler should be stopped when the session is no longer needed using `stop_tickler()`.

        """
        _LOGGER.info(f'{self}: Starting Tickler to maintain the connection alive')
        if self._tickler is None:
            self._tickler = Tickler(self, interval)
        self._tickler.start()

    def stop_tickler(self, timeout:float=None):
        """
        Stops the Tickler thread if the Tickler is running.

        The Tickler is responsible for maintaining an active session by sending periodic requests to
        the IBKR API. This method stops the Tickler process, preventing further requests.

        Parameters:
            timeout (Optional[float]): Maximum time to wait for the Tickler thread to terminate.
                                       If None, waits indefinitely.
        """
        if self._tickler is not None:
            self._tickler.stop(timeout)

    def close(self):
        if self._use_oauth and self.oauth_config.shutdown_oauth:
            self.oauth_shutdown()
        super().close()

    def oauth_shutdown(self):
        """
        Shuts down the OAuth session and cleans up resources.

        This method stops the Tickler process, which keeps the session alive, and logs out from
        the IBKR API to ensure a clean session termination.
        """
        _LOGGER.info(f'{self}: Shutting down OAuth')
        self.stop_tickler()
        self.logout()


    def handle_health_status(self) -> bool:
        """
        Handles the health status of the IBKR connection.

        If the connection is not healthy, it attempts to re-establish OAuth authentication.

        Returns:
            bool: True if the connection is healthy, False otherwise.
        """
        healthy = self.check_health()
        if healthy:
            # All good, do nothing.
            return True

        if not self._use_oauth:
            # Do nothing; wait for a reconnection either from IBeam or manually.
            _LOGGER.warning('IBKR connection is not healthy. Ensure authentication with the Gateway is re-established.')
            return False

        _LOGGER.warning('IBKR connection is not healthy. Attempting to re-establish OAuth authentication.')
        try:
            self.stop_tickler(15)
        except Exception as e:  # pragma: no cover
            _LOGGER.error(f'Error stopping tickler during reauthentication: {exception_to_string(e)}')

        try:
            self.oauth_init(
                maintain_oauth=self.oauth_config.maintain_oauth,
                init_brokerage_session=self.oauth_config.init_brokerage_session,
            )
        except Exception as e: # pragma: no cover
            _LOGGER.error(f'Error reauthenticating OAuth during reauthentication: {exception_to_string(e)}')
        return False
