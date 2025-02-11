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
            host: str = 'localhost',
            port: str = '5000',
            base_route: str = '/v1/api/',
            cacert: Union[str, os.PathLike, bool] = var.IBIND_CACERT,
            timeout: float = 10,
            max_retries: int = 3,
            use_oauth: bool = var.IBIND_USE_OAUTH,
            oauth_config: 'OAuthConfig' = None
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
            use_oauth (bool, optional): Whether to use OAuth authentication. Defaults to False.
            oauth_config (OAuthConfig, optional): The configuration for the OAuth authentication. OAuth1aConfig is used if not specified.
        """

        self._use_oauth = use_oauth

        if self._use_oauth:
            from ibind.oauth.oauth1a import OAuth1aConfig
            # cast to OAuth1aConfig for type checking, since currently 1.0a is the only version used
            self.oauth_config = cast(OAuth1aConfig, oauth_config) if oauth_config is not None else OAuth1aConfig()
            url = url if self.oauth_config.oauth_rest_url is None else self.oauth_config.oauth_rest_url

        if url is None:
            url = f'https://{host}:{port}{base_route}'

        self.account_id = account_id

        cacert = True if self._use_oauth else cacert
        super().__init__(url=url, cacert=cacert, timeout=timeout, max_retries=max_retries)

        self.logger.info('#################')
        self.logger.info(f'New IbkrClient(base_url={self.base_url!r}, account_id={self.account_id!r}, ssl={self.cacert!r}, timeout={self._timeout}, max_retries={self._max_retries}, use_oauth={self._use_oauth})')

        if self._use_oauth:
            if self.oauth_config.init_oauth:
                self.oauth_init(
                    maintain_oauth=self.oauth_config.maintain_oauth,
                    shutdown_oauth=self.oauth_config.shutdown_oauth,
                    init_brokerage_session=self.oauth_config.init_brokerage_session,
                )

    def make_logger(self):
        self._logger = new_daily_rotating_file_handler('IbkrClient', os.path.join(var.LOGS_DIR, f'ibkr_client_{self.account_id}'))

    def _request(
            self,
            method: str,
            endpoint: str,
            base_url: str = None,
            extra_headers: dict = None,
            attempt: int = 0,
            log: bool = True,
            **kwargs
    ) -> Result:
        """ Handle IBKR-specific errors."""

        try:
            return super()._request(method, endpoint, base_url, extra_headers, attempt, log, **kwargs)
        except ExternalBrokerError as e:
            if 'Bad Request: no bridge' in str(e) and e.status_code == 400:
                raise ExternalBrokerError(f'IBKR returned 400 Bad Request: no bridge. Try calling `initialize_brokerage_session()` first.') from e
            raise

    def get_headers(self, request_method: str, request_url: str):
        if (not self._use_oauth) or request_url == f'{self.base_url}{self.oauth_config.live_session_token_endpoint}':
            # No need for extra headers if we don't use oauth or getting live session token
            return {}

        # get headers for endpoints other than live session token request
        from ibind.oauth.oauth1a import generate_oauth_headers
        headers = generate_oauth_headers(
            oauth_config=self.oauth_config,
            request_method=request_method,
            request_url=request_url,
            live_session_token=self.live_session_token
        )

        return headers

    def generate_live_session_token(self):
        from ibind.oauth.oauth1a import req_live_session_token
        self.live_session_token, self.live_session_token_expires_ms, self.live_session_token_signature \
            = req_live_session_token(self, self.oauth_config)

    def oauth_init(
            self,
            maintain_oauth: bool,
            shutdown_oauth: bool,
            init_brokerage_session: bool
    ):
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
            consumer_key=self.oauth_config.consumer_key
        )
        if not success:
            raise RuntimeError("Live session token validation failed.")

        if maintain_oauth:
            self.start_tickler()

        if shutdown_oauth:
            self.register_shutdown_handler()

        if init_brokerage_session:
            self.initialize_brokerage_session()

    def start_tickler(self):
        # start Tickler to maintain the connection alive
        _LOGGER.info(f'{self}: Starting Tickler to maintain the connection alive')
        self._tickler = Tickler(self)
        self._tickler.start()

    def stop_tickler(self):
        if hasattr(self, '_tickler') and self._tickler is not None:
            self._tickler.stop()

    def register_shutdown_handler(self):
        _LOGGER.info(f'{self}: Registering automatic shutdown handler')
        # add signal handlers to gracefully shut down the Tickler and the client
        import signal
        existing_handler_int = signal.getsignal(signal.SIGINT)
        existing_handler_term = signal.getsignal(signal.SIGTERM)

        def _stop(signum, frame):
            self.oauth_shutdown()

            if signum == signal.SIGINT and callable(existing_handler_int):
                existing_handler_int(signum, frame)

            if signum == signal.SIGTERM and callable(existing_handler_term):
                existing_handler_term(signum, frame)

        signal.signal(signal.SIGINT, _stop)
        signal.signal(signal.SIGTERM, _stop)

    def oauth_shutdown(self):
        _LOGGER.info(f'{self}: Shutting down OAuth')
        self.stop_tickler()
        self.logout()