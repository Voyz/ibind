from typing import TYPE_CHECKING, Union, Dict, List

from ibind.base.rest_client import Result
from ibind.support.logs import project_logger

if TYPE_CHECKING:  # pragma: no cover
    from ibind import IbkrClient

_LOGGER = project_logger(__file__)


class WatchlistMixin():  # pragma: no cover
    """
    https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#watchlists
    """

    def create_watchlist(
            self: 'IbkrClient',
            id: str,
            name: str,
            rows: List[Dict[str, Union[str, int]]]
    ) -> Result:
        """
        Create a watchlist to monitor a series of contracts.

        Parameters:
            id (str): Supply a unique identifier to track a given watchlist. Must supply a number.
            name (str): Supply the human readable name of a given watchlist. Displayed in TWS and Client Portal.
            rows (List[Dict[str, Union[str, int]]]): Provide details for each contract or blank space in the watchlist. Each object may include:
                - C (int): Provide the conid, or contract identifier, of the conid to add.
                - H (str): Can be used to add a blank row between contracts in the watchlist.
        """
        return self.post('iserver/watchlist', params={'id': id, 'name': name, 'rows': rows})

    def get_all_watchlists(self: 'IbkrClient', sc: str = 'USER_WATCHLIST') -> Result:
        """
        Retrieve a list of all available watchlists for the account.

        Parameters:
            SC (str): Optional. Specify the scope of the request. Valid Values: USER_WATCHLIST.
        """
        return self.get('iserver/watchlists', params={'SC': sc})

    def get_watchlist_information(self: 'IbkrClient', id: str) -> Result:
        """
        Request the contracts listed in a particular watchlist.

        Parameters:
            id (str): Set equal to the watchlist ID you would like data for.
        """
        return self.get('iserver/watchlist', params={'id': id})

    def delete_watchlist(self: 'IbkrClient', id: str) -> Result:
        """
        Permanently delete a specific watchlist for all platforms.

        Parameters:
            id (str): Include the watchlist ID you wish to delete.
        """
        return self.delete('iserver/watchlist', params={'id': id})
