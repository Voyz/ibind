import os
from typing import Union, Optional

from ibind import var
from ibind.base.rest_client import RestClient
from ibind.client.ibkr_client_mixins.accounts_mixin import AccountsMixin
from ibind.client.ibkr_client_mixins.contract_mixin import ContractMixin
from ibind.client.ibkr_client_mixins.marketdata_mixin import MarketdataMixin
# from ibind.client.ibkr_client_mixins.oauth_mixin import OAuthMixin
from ibind.client.ibkr_client_mixins.order_mixin import OrderMixin
from ibind.client.ibkr_client_mixins.portfolio_mixin import PortfolioMixin
from ibind.client.ibkr_client_mixins.scanner_mixin import ScannerMixin
from ibind.client.ibkr_client_mixins.session_mixin import SessionMixin
from ibind.client.ibkr_client_mixins.watchlist_mixin import WatchlistMixin
from ibind.support.logs import new_daily_rotating_file_handler, project_logger
from ibind.support.oauth import req_live_session_token, generate_oauth_headers, prepare_oauth

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
            use_oauth: bool = False,
            account_id: Optional[str] = var.IBIND_ACCOUNT_ID,
            url: str = var.IBIND_REST_URL,
            host: str = 'localhost',
            port: str = '5000',
            base_route: str = '/v1/api/',
            cacert: Union[str, os.PathLike, bool] = var.IBIND_CACERT,
            timeout: float = 10,
            max_retries: int = 3,
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
        """

        if url is None:
            url = f'https://{host}:{port}{base_route}'

        self.account_id = account_id
        self._use_oauth = use_oauth
        self.oauth_base_url="https://api.ibkr.com/v1/api/"
        super().__init__(url=url, cacert=cacert, timeout=timeout, max_retries=max_retries)

        if self._use_oauth:
            self.live_session_token, self.live_session_token_expires_ms = req_live_session_token(self)

        self.logger.info('#################')
        self.logger.info(f'New IbkrClient(base_url={self.base_url!r}, account_id={self.account_id!r}, ssl={self.cacert!r}, timeout={self._timeout}, max_retries={self._max_retries})')

    def make_logger(self):
        self._logger = new_daily_rotating_file_handler('IbkrClient', os.path.join(var.LOGS_DIR, f'ibkr_client_{self.account_id}'))

    def get_headers(
            self,
            request_method: str,
            request_url: str
            ):

        # TODO: this second check shouldn't be hardcoded. Temporary fix for now
        if (not self._use_oauth) or request_url == 'https://api.ibkr.com/v1/api/oauth/live_session_token':
            return {}

        prepend, extra_headers, _, _ = prepare_oauth()

        # extra headers only needed for req live session token
        if request_url == 'https://api.ibkr.com/v1/api/oauth/live_session_token':
            extra_headers=extra_headers
        else:
            extra_headers=None


        headers = generate_oauth_headers(
            request_method=request_method,
            request_url=request_url,
            extra_headers=extra_headers,
            prepend=prepend,
            live_session_token=self.live_session_token
        )

        return headers


    def test_get_live_session_token(self):
        live_session_token,live_session_token_expires_ms=req_live_session_token(self)
        return live_session_token,live_session_token_expires_ms
    
