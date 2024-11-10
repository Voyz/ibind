from typing import TYPE_CHECKING

from ibind.base.rest_client import Result
from ibind.support.logs import project_logger

if TYPE_CHECKING:  # pragma: no cover
    from ibind import IbkrClient

_LOGGER = project_logger(__file__)


class AccountsMixin():  # pragma: no cover
    """
    https://ibkrcampus.com/ibkr-api-page/webapi-doc/#accounts
    """

    def account_profit_and_loss(self: 'IbkrClient',access_token:str,live_session_token:str,params) -> Result:  # pragma: no cover
        """
        Returns an object containing PnL for the selected account and its models (if any).
        """

        response= OAuth_Requests_Mixin.send_oauth_request(
        request_method="GET",
        request_url="https://api.ibkr.com/v1/api/iserver/account/pnl/partitioned",
        oauth_token=access_token,
        live_session_token=live_session_token,
        request_params=params,
        )

        return response

    def search_dynamic_account(self: 'IbkrClient', search_pattern: str,access_token:str,live_session_token:str,params) -> Result:  # pragma: no cover
        """
        Searches for broker accounts configured with the DYNACCT property using a specified pattern.

        Parameters:
            search_pattern (str): The pattern used to describe credentials to search for. Valid Format: “DU” in order to query all paper accounts.

        Note:
            - Customers without the DYNACCT property will receive the following 503 message: "Details currently unavailable. Please try again later and contact client services if the issue persists."
        """

        response = OAuth_Requests_Mixin.send_oauth_request(
        request_method="GET",
        request_url=f"https://api.ibkr.com/v1/api/iserver/account/search/{search_pattern}",
        oauth_token=access_token,
        live_session_token=live_session_token,
        request_params=params,
        )

        return response
 

    def set_dynamic_account(self: 'IbkrClient', account_id: str,access_token:str,live_session_token:str,params) -> Result:  # pragma: no cover
        """
        Set the active dynamic account. Values retrieved from Search Dynamic Account.

        Parameters:
            account_id (str): The account ID that should be set for future requests.

        Note:
            - If the account does not have the DYNACCT property, a 503 error message is returned.
        """

        response= OAuth_Requests_Mixin.send_oauth_request(
        request_method="GET",
        request_url=f"https://api.ibkr.com/v1/api/iserver/dynaccount', params={"acctId": account_id}",
        oauth_token=access_token,
        live_session_token=live_session_token,
        request_params=params,
        )

        return response


    def signatures_and_owners(self: 'IbkrClient', account_id: str,access_token:str,live_session_token:str,params) -> Result:  # pragma: no cover
        """
        Receive a list of all applicant names on the account and for which account and entity is represented.

        Parameters:
            account_id (str): Pass the account identifier to receive information for. Valid Structure: “U1234567”.
        """
        # if account_id is None:
        #     account_id = self.account_id

        response= OAuth_Requests_Mixin.send_oauth_request(
        request_method="GET",
        request_url=f"https://api.ibkr.com/v1/api/iserver/acesws/{account_id}/signatures-and-owners'",
        oauth_token=access_token,
        live_session_token=live_session_token,
        request_params=params,
        )

        return response


    def switch_account(self: 'IbkrClient', account_id: str,access_token:str,live_session_token:str,params) -> Result:
        """
        Switch the active account for how you request data.

        Only available for financial advisors and multi-account structures.

        Parameters:
            acctId (str): Identifier for the unique account to retrieve information from. Value Format: “DU1234567”.
        """
        
        response= OAuth_Requests_Mixin.send_oauth_request(
        request_method="GET",
        request_url=f"https://api.ibkr.com/v1/api/iserver/account', params={"acctId": account_id}",
        oauth_token=access_token,
        live_session_token=live_session_token,
        request_params=params,
        )

        return response

        # result = self.post('iserver/account', params={"acctId": account_id})
        # self.account_id = account_id
        # self.make_logger()
        # _LOGGER.warning(f'ALSO NEED TO SWITCH WEBSOCKET ACCOUNT TO {self.account_id}')
        # return result

    def receive_brokerage_accounts(self: 'IbkrClient',access_token:str,live_session_token:str,params) -> Result:  # pragma: no cover
        """
        Returns a list of accounts the user has trading access to, their respective aliases, and the currently selected account. Note this endpoint must be called before modifying an order or querying open orders.
        """
        response= OAuth_Requests_Mixin.send_oauth_request(
        request_method="GET",
        request_url=f"https://api.ibkr.com/v1/api/iserver/accounts",
        oauth_token=access_token,
        live_session_token=live_session_token,
        request_params=params,
        )

        return response
