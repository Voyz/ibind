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
from ibind.support.logs import new_daily_rotating_file_handler, project_logger

_LOGGER = project_logger(__file__)




class IbkrClient(RestClient, AccountsMixin, ContractMixin, MarketdataMixin, OrderMixin, PortfolioMixin, ScannerMixin, SessionMixin, WatchlistMixin):
    """
    A client class for interfacing with the Interactive Brokers API, extending the RestClient class.

    This subclass of RestClient is specifically designed for the Interactive Brokers API. It inherits
    the foundational REST API interaction capabilities from RestClient and adds functionalities
    particular to the Interactive Brokers API, such as specific endpoint handling.

    The class provides methods to perform various operations with the Interactive Brokers API, such as
    fetching stock data, submitting orders, and managing account information.

    See: https://interactivebrokers.github.io/cpwebapi/endpoints
    """

    def __init__(
            self,
            account_id: Optional[str] = var.IBKR_ACCOUNT_ID,
            url: str = var.IBKR_URL,
            host: str = 'localhost',
            port: str = '5000',
            base_route: str = '/v1/api/',
            cacert: Union[str, os.PathLike, bool] = var.IBKR_CACERT,
            timeout: float = 10,
            max_retries: int = 3,
    ) -> None:
        """
        Parameters:
            url (str): The base URL for the REST API.
            account_id (str): An identifier for the account.
            cacert (Union[os.PathLike, bool], optional): Path to the CA certificate file for SSL verification,
                                                         or False to disable SSL verification. Defaults to False.
            timeout (float, optional): Timeout in seconds for the API requests. Defaults to 10.
            max_retries (int, optional): Maximum number of retries for failed API requests. Defaults to 3.
        """

        if url is None:
            url = f'https://{host}:{port}{base_route}'

        self.account_id = account_id
        super().__init__(url=url, cacert=cacert, timeout=timeout, max_retries=max_retries)

        self.logger.info('#################')
        self.logger.info(f'New IbkrClient(base_url={self.base_url!r}, account_id={self.account_id!r}, ssl={self.cacert!r}, timeout={self._timeout}, max_retries={self._max_retries})')

    def make_logger(self):
        self._logger = new_daily_rotating_file_handler('IbkrClient', os.path.join(var.LOGS_DIR, f'ibkr_client_{self.account_id}'))
