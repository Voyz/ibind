from typing import TYPE_CHECKING

from ibind.base.rest_client import Result
from ibind.support.logs import project_logger

if TYPE_CHECKING:
    from ibind import IbkrClient

_LOGGER = project_logger(__file__)


class AccountsMixin():
    def account_profit_and_loss(self: 'IbkrClient') -> Result:
        """
        Returns an object containing PnL for the selected account and its models (if any).
        """
        return self.get('/iserver/account/pnl/partitioned')

    def search_dynamic_account(self: 'IbkrClient', search_pattern: str) -> Result:
        """
        Returns a list of accounts matching a query pattern set in the request.
        """
        return self.get(f'/iserver/account/search/{search_pattern}')

    def set_dynamic_account(self: 'IbkrClient', account_id: str) -> Result:
        """
        Set the active dynamic account. Values retrieved from Search Dynamic Account
        """
        return self.post(f'/iserver/dynaccount', params={"acctId": account_id})

    def signatures_and_owners(self: 'IbkrClient', account_id: str) -> Result:
        """
        Receive a list of all applicant names on the account and for which account and entity is represented.
        """
        return self.get(f'/acesws/{account_id}/signatures-and-owners')

    def switch_account(self: 'IbkrClient', account_id: str) -> Result:
        """
        Switch the active account for how you request data.
        Only available for financial advisors and multi-account structures.
        """
        result = self.post('iserver/account', params={"acctId": account_id})
        self.account_id = account_id
        self.make_logger()
        _LOGGER.warning(f'ALSO NEED TO SWITCH WEBSOCKET ACCOUNT TO {self.account_id}')
        return result

    def receive_brokerage_accounts(self: 'IbkrClient') -> Result:
        """
        Returns a list of accounts the user has trading access to, their respective aliases and the currently selected account. Note this endpoint must be called before modifying an order or querying open orders.
        """
        return self.get('/iserver/accounts')
