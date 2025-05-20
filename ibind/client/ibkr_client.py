from __future__ import annotations
import importlib.util
import os
from typing import Union, Optional, Any

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

# OAuth specific imports moved to global scope
from ibind.oauth import OAuthConfig
from ibind.oauth.oauth1a import OAuth1aConfig, generate_oauth_headers, req_live_session_token
from ibind.oauth.oauth2 import OAuth2Config, authenticate_oauth2

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
        use_oauth: bool = var.IBIND_USE_OAUTH,
        oauth_config: Optional[Union[OAuthConfig, OAuth1aConfig, OAuth2Config]] = None,
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
            oauth_config (Optional[Union['OAuthConfig', 'OAuth1aConfig', 'OAuth2Config']], optional): The configuration for OAuth. 
                                                                                 If use_oauth is True and oauth_config is None, 
                                                                                 OAuth1aConfig or OAuth2Config might be instantiated by default 
                                                                                 based on further logic or environment variables.
        """

        self._use_oauth = use_oauth
        self.oauth_config = oauth_config
        self.account_id = account_id # Set account_id early for logger
        self._tickler_thread_is_running = False # Initialize tickler state

        user_provided_url = url 

        if self.oauth_config is None:
            raise ValueError(
                "use_oauth is True but no oauth_config was provided. "
                "Please provide an instance of OAuth1aConfig or OAuth2Config."
            )

        if self._use_oauth:
            # OAuth1aConfig and OAuth2Config are globally imported
            determined_url = None
            oauth_config_url = None

            if isinstance(self.oauth_config, OAuth2Config):
                oauth_config_url = self.oauth_config.oauth_rest_url
            elif isinstance(self.oauth_config, OAuth1aConfig):
                oauth_config_url = self.oauth_config.oauth_rest_url
            else:
                raise ValueError("Unsupported oauth_config type provided for URL determination.")

            if user_provided_url is not var.IBIND_REST_URL:
                determined_url = user_provided_url
            elif oauth_config_url is not None:
                determined_url = oauth_config_url
            else:
                determined_url = user_provided_url
            
            url = determined_url 
            effective_cacert = True 
        else: 
            if user_provided_url is var.IBIND_REST_URL and var.IBIND_REST_URL is None:
                 url = f'https://{host}:{port}{base_route}'
            else: 
                 url = user_provided_url
            effective_cacert = cacert

        if url is None: 
             raise ValueError("URL could not be determined. Ensure oauth_config provides a suitable oauth_rest_url if use_oauth is True, or provide a url directly.")

        super().__init__(
            url=url,
            cacert=effective_cacert,
            timeout=timeout,
            max_retries=max_retries,
            use_session=use_session,
            auto_register_shutdown=auto_register_shutdown,
        )

        if not hasattr(self, '_headers') or self._headers is None:
            log_msg = "_headers attribute was not initialized (or was None) prior to this check. Initializing to an empty dict in IbkrClient."
            if hasattr(self, 'logger') and self.logger:
                self.logger.warning(log_msg)
            else:
                _LOGGER.warning(f"IbkrClient __init__: {log_msg} (using module logger as self.logger might be unavailable).")
            self._headers = {}

        self.logger.info('#################')
        self.logger.info(
            f'New IbkrClient(base_url={self.base_url!r}, account_id={self.account_id!r}, ssl={self.cacert!r}, timeout={self._timeout}, max_retries={self._max_retries}, use_oauth={self._use_oauth}, oauth_version={self.oauth_config.version() if self.oauth_config else None})'
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
        headers = self._headers.copy() # Start with base session headers

        if not self._use_oauth or not self.oauth_config:
            if not self._use_oauth:
                return headers # Not using OAuth, return base headers
            if not self.oauth_config:
                 _LOGGER.error(f"{self}: _use_oauth is True but oauth_config is not set in _get_headers. Returning base headers.")
                 return headers

        # OAuth types are now globally imported, no local imports needed here

        processed_oauth_header = False # Flag to track if an OAuth type was handled

        if isinstance(self.oauth_config, OAuth2Config):
            processed_oauth_header = True
            oauth_flow_urls = [
                self.oauth_config.token_url,
                self.oauth_config.sso_session_url
            ]
            if request_url in oauth_flow_urls:
                _LOGGER.debug(f"Request URL {request_url} is an OAuth 2.0 flow URL. Skipping Bearer token addition.")
            elif self.oauth_config.has_sso_bearer_token():
                headers['Authorization'] = f'Bearer {self.oauth_config.sso_bearer_token}'
            else:
                _LOGGER.error(f"OAuth 2.0 configured for {request_url}, but SSO bearer token is missing.")
        
        if isinstance(self.oauth_config, OAuth1aConfig):
            processed_oauth_header = True
            live_session_token_full_url = f'{self.base_url.rstrip('/')}/{self.oauth_config.live_session_token_endpoint.lstrip('/')}'
            if request_url == live_session_token_full_url:
                _LOGGER.debug(f"Request URL {request_url} is OAuth 1.0a live_session_token_endpoint. Returning empty headers.")
                return {} 
            else:
                _LOGGER.debug(f"Generating OAuth 1.0a headers for {request_url}")
                oauth1_headers = generate_oauth_headers(
                    oauth_config=self.oauth_config,
                    request_method=request_method,
                    request_url=request_url,
                    live_session_token=getattr(self, 'live_session_token', None)
                )
                headers.update(oauth1_headers)

        if self._use_oauth and not processed_oauth_header:
             _LOGGER.warning(f"{self}: _use_oauth is True but oauth_config type was not recognized as OAuth1aConfig or OAuth2Config. Type: {type(self.oauth_config)}. Returning base headers.")
            
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
        if not isinstance(self.oauth_config, OAuth1aConfig):
            _LOGGER.error("generate_live_session_token is only for OAuth 1.0a")
            return
        # req_live_session_token is now globally imported
        self.live_session_token, self.live_session_token_expires_ms, self.live_session_token_signature = req_live_session_token(
            self, self.oauth_config
        )

    def oauth_init(self, maintain_oauth: bool, init_brokerage_session: bool):
        """
        Initializes the OAuth authentication flow (1.0a or 2.0) for the IBKR API.

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
        if not self._use_oauth or not self.oauth_config:
            _LOGGER.error("oauth_init called but use_oauth is False or oauth_config is not set.")
            return

        _LOGGER.info(f'{self}: Initialising OAuth {self.oauth_config.version()}')

        # OAuth types and authenticate_oauth2 are now globally imported

        if isinstance(self.oauth_config, OAuth2Config):
            sso_token = authenticate_oauth2(self.oauth_config) # Removed client=self
            if not sso_token:
                raise ExternalBrokerError("Failed to obtain OAuth 2.0 SSO Bearer Token during oauth_init")

            if init_brokerage_session:
                _LOGGER.debug(f"{self}: OAuth 2.0 init_brokerage_session is True. Attempting /sso/validate.")
                try:
                    validation_result = self.validate()
                    _LOGGER.debug(f"{self}: /sso/validate result: {validation_result.data if validation_result else 'No result'}")

                    sso_is_valid = False
                    if validation_result and hasattr(validation_result, 'data') and isinstance(validation_result.data, dict):
                        if validation_result.data.get('RESULT') is True:
                            sso_is_valid = True
                            _LOGGER.debug(f"{self}: /sso/validate deemed successful based on 'RESULT': True.")
                        elif validation_result.data.get('authenticated') is True: # Fallback check
                            sso_is_valid = True
                            _LOGGER.debug(f"{self}: /sso/validate deemed successful based on 'authenticated': True.")

                    if sso_is_valid:
                        _LOGGER.debug(f"{self}: /sso/validate successful. Now attempting to establish brokerage session.")
                        try:
                            # Attempt to initialize brokerage session
                            _LOGGER.debug(f"{self}: Calling initialize_brokerage_session(compete=True).")
                            init_result = self.initialize_brokerage_session(compete=True)
                            _LOGGER.debug(f"{self}: initialize_brokerage_session(compete=True) result: {init_result.data if init_result else 'No result'}")

                            # Check auth status immediately after successful init
                            auth_status_after_init = self.authentication_status()
                            _LOGGER.debug(f"{self}: /iserver/auth/status (after compete=True init): {auth_status_after_init.data if auth_status_after_init else 'No result'}")
                            if not (auth_status_after_init and auth_status_after_init.data and auth_status_after_init.data.get('authenticated')):
                                _LOGGER.warning(f"{self}: Still not authenticated after compete=True init.")

                        except ExternalBrokerError as e_init_compete_true:
                            _LOGGER.error(f"{self}: initialize_brokerage_session(compete=True) failed: {e_init_compete_true}")
                            if e_init_compete_true.status_code == 500 and "failed to generate sso dh token" in str(e_init_compete_true):
                                _LOGGER.warning(f"{self}: Retrying initialize_brokerage_session with compete=False.")
                                try:
                                    init_result_false = self.initialize_brokerage_session(compete=False)
                                    _LOGGER.debug(f"{self}: initialize_brokerage_session(compete=False) result: {init_result_false.data if init_result_false else 'No result'}")

                                    auth_status_after_init_false = self.authentication_status()
                                    _LOGGER.debug(f"{self}: /iserver/auth/status (after compete=False init): {auth_status_after_init_false.data if auth_status_after_init_false else 'No result'}")
                                    if not (auth_status_after_init_false and auth_status_after_init_false.data and auth_status_after_init_false.data.get('authenticated')):
                                        _LOGGER.warning(f"{self}: Still not authenticated after compete=False init.")

                                except Exception as e_init_compete_false:
                                    _LOGGER.error(f"{self}: initialize_brokerage_session(compete=False) also failed: {e_init_compete_false}")
                            # else: other error from compete=True, not the DH token one.
                        except Exception as e_init_generic:
                            _LOGGER.error(f"{self}: A generic error occurred during initialize_brokerage_session(compete=True): {e_init_generic}")
                    else:
                        _LOGGER.warning(f"{self}: /sso/validate did not indicate a clear success. Cannot proceed with brokerage session initialization. Validation data: {validation_result.data if validation_result else 'No result'}")
                except Exception as e_validate_sequence:
                    _LOGGER.error(f"{self}: Error during /sso/validate or subsequent brokerage session initialization sequence: {e_validate_sequence}")

            if maintain_oauth:
                _LOGGER.info(f"{self}: Starting tickler for OAuth 2.0.")
                self.start_tickler()

        elif isinstance(self.oauth_config, OAuth1aConfig):
            if importlib.util.find_spec('Crypto') is None:
                raise ImportError('Installation lacks OAuth 1.0a support. Please install by using `pip install ibind[oauth]`')
            self.generate_live_session_token()
            from ibind.oauth.oauth1a import validate_live_session_token # Conditional import
            success = validate_live_session_token(
                live_session_token=self.live_session_token,
                live_session_token_signature=self.live_session_token_signature,
                consumer_key=self.oauth_config.consumer_key,
            )
            if not success:
                raise RuntimeError('OAuth 1.0a Live session token validation failed.')
            if maintain_oauth:
                self.start_tickler()
            if init_brokerage_session:
                self.initialize_brokerage_session()
        else:
            raise ValueError("Unsupported oauth_config type during oauth_init.")

    def start_tickler(self) -> None:
        """
        Starts the `Tickler` instance and starts it in a separate thread to maintain the session.
        This can be useful for maintaining any session, not just OAuth, especially for users not using IBeam.
        """
        if not self._tickler_thread_is_running:
            _LOGGER.info(f'{self}: Starting Tickler to maintain the connection alive')
            self._tickler = Tickler(self)
            self._tickler.start()
            self._tickler_thread_is_running = True # Set flag after starting

    def stop_tickler(self):
        """
        Stops the Tickler thread if the Tickler is running.

        The Tickler is responsible for maintaining an active session by sending periodic requests to
        the IBKR API. This method stops the Tickler process, preventing further requests.
        """
        if hasattr(self, '_tickler') and self._tickler is not None:
            self._tickler.stop()
            self._tickler_thread_is_running = False # Set flag after stopping

    def close(self):
        if self._use_oauth and self.oauth_config and self.oauth_config.shutdown_oauth:
            self.oauth_shutdown()
        super().close()

    def oauth_shutdown(self):
        """
        Shuts down the OAuth session and cleans up resources.

        This method stops the Tickler process, which keeps the session alive, and logs out from
        the IBKR API to ensure a clean session termination.
        """
        if not self._use_oauth or not self.oauth_config:
            return

        _LOGGER.info(f'{self}: Shutting down OAuth {self.oauth_config.version()} session')

        # OAuth types are now globally imported

        if isinstance(self.oauth_config, OAuth2Config):
            if self.oauth_config.has_sso_bearer_token():
                try:
                    logout_result = self.post('logout', log=False)
                    if logout_result and hasattr(logout_result, 'data') and logout_result.data.get('confirmed') is True:
                        _LOGGER.debug(f"{self}: OAuth 2.0 logout confirmed by API.")
                except Exception as e:
                    _LOGGER.error(f"Error during OAuth 2.0 logout: {e}")
            self.oauth_config.sso_bearer_token = None
            self.oauth_config.access_token = None
            self.stop_tickler()

        elif isinstance(self.oauth_config, OAuth1aConfig):
            self.stop_tickler()
            self.logout()

        else:
            _LOGGER.warning("oauth_shutdown called with unknown oauth_config type.")
