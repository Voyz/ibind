import os
from typing import Union, Optional

from ibind import var
from ibind.base.rest_client import RestClient
from ibind.client.ibkr_client_mixins.accounts_mixin import AccountsMixin
from ibind.client.ibkr_client_mixins.contract_mixin import ContractMixin
from ibind.client.ibkr_client_mixins.marketdata_mixin import MarketdataMixin
from ibind.client.ibkr_client_mixins.order_mixin import OrderMixin
from ibind.client.ibkr_client_mixins.portfolio_mixin import PortfolioMixin
from ibind.client.ibkr_client_mixins.scanner_mixin import ScannerMixin
from ibind.client.ibkr_client_mixins.session_mixin import SessionMixin
from ibind.client.ibkr_client_mixins.watchlist_mixin import WatchlistMixin
from ibind.client.ibkr_utils import Tickler
from ibind.support.logs import new_daily_rotating_file_handler, project_logger

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
    ) -> None:
        """
        Parameters:
            account_id (str): An identifier for the account.
            url (str): The base URL for the REST API.
            host (str, optional): Host for the IBKR REST API. Defaults to 'localhost'.
            port (str, optional): Port for the IBKR REST API. Defaults to '5000'
            base_route (str, optional): Base route for the IBKR REST API. Defaults to '/v1/api/'.
            cacert (Union[os.PathLike, bool], optional): Path to the CA certificate file for SSL verification,
                                                         or False to disable SSL verification. Defaults to False.
            timeout (float, optional): Timeout in seconds for the API requests. Defaults to 10.
            max_retries (int, optional): Maximum number of retries for failed API requests. Defaults to 3.
            use_oauth (bool, optional): Whether to use OAuth authentication. Defaults to False.
        """

        self._use_oauth = use_oauth

        url = var.IBIND_OAUTH_REST_URL if self._use_oauth else url

        if url is None:
            url = f'https://{host}:{port}{base_route}'

        self.account_id = account_id
        super().__init__(url=url, cacert=cacert, timeout=timeout, max_retries=max_retries)

        self.logger.info('#################')
        self.logger.info(f'New IbkrClient(base_url={self.base_url!r}, account_id={self.account_id!r}, ssl={self.cacert!r}, timeout={self._timeout}, max_retries={self._max_retries})')

        if self._use_oauth:
            self.oauth_init()

    def make_logger(self):
        self._logger = new_daily_rotating_file_handler('IbkrClient', os.path.join(var.LOGS_DIR, f'ibkr_client_{self.account_id}'))

    def oauth_init(self):
        from ibind.support.oauth import req_live_session_token
        import signal

        # get live session token for OAuth authentication
        self.live_session_token, self.live_session_token_expires_ms = req_live_session_token(self)

        # start Tickler to maintain the connection alive
        self._tickler = Tickler(self)
        self._tickler.start()

        # add signal handlers to gracefully shut down the Tickler and the client
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
        if hasattr(self, '_tickler') and self._tickler is not None:
            self._tickler.stop()

        self.logout()

    def get_headers(self, request_method: str, request_url: str):
        if (not self._use_oauth) or request_url == f'{self.base_url}{var.IBIND_LIVE_SESSION_TOKEN_ENDPOINT}':
            # No need for extra headers if we don't use oauth or getting live session token
            return {}

        from ibind.support.oauth import generate_oauth_headers
        # get headers for endpoints other than live session token request
        headers = generate_oauth_headers(
            request_method=request_method,
            request_url=request_url,
            live_session_token=self.live_session_token
        )

        return headers
