from typing import TYPE_CHECKING, Union, Dict, List

from ibind.support.logs import project_logger
from ibind.base.rest_client import Result

if TYPE_CHECKING:  # pragma: no cover
    from ibind import IbkrClient

_LOGGER = project_logger(__file__)


class WatchlistMixin():

    def create_watchlist(
            self: 'IbkrClient',
            id: str,
            name: str,
            rows: List[Dict[str, Union[str, int]]]
    ) -> Result:  # pragma: no cover
        return self.post('iserver/watchlist', params={'id':id, 'name': name, 'rows':rows})

    def get_all_watchlists(
            self: 'IbkrClient',
            sc:str = 'USER_WATCHLIST'
    ) -> Result:  # pragma: no cover
        return self.get('iserver/watchlist', params={'SC':sc})
