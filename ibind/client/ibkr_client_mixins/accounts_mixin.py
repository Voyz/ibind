from typing import TYPE_CHECKING

from ibind.base.rest_client import Result
from ibind.support.logs import project_logger

if TYPE_CHECKING:
    from ibind import IbkrClient


_LOGGER = project_logger(__file__)

class AccountsMixin():
    def switch_account(self: 'IbkrClient',account_id: str) -> Result:
        result = self.post('iserver/account', params={"acctId": account_id})
        self.account_id = account_id
        self.make_logger()
        _LOGGER.warning(f'ALSO NEED TO SWITCH WEBSOCKET ACCOUNT TO {self.account_id}')
        return result