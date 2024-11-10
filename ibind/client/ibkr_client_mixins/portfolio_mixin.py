from typing import TYPE_CHECKING

from ibind.base.rest_client import Result
from ibind.support.logs import project_logger
from ibind.support.py_utils import params_dict, ensure_list_arg, OneOrMany


if TYPE_CHECKING:  # pragma: no cover
    from ibind import IbkrClient

_LOGGER = project_logger(__file__)


class PortfolioMixin():  # pragma: no cover
    """
    * https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#portfolio
    * https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#pa
    """

    def portfolio_accounts(
            self: 'IbkrClient',
            access_token:str,
            live_session_token:str) -> Result:
        """
        In non-tiered account structures, returns a list of accounts for which the user can view position and account information. This endpoint must be called prior to calling other /portfolio endpoints for those accounts.
        """
        response= OAuth_Requests_Mixin.send_oauth_request(
        request_method="GET",
        request_url="https://api.ibkr.com/v1/api/iserver/portfolio/accounts",
        oauth_token=access_token,
        live_session_token=live_session_token,
        # request_params=params,
        )

        return response
        # return self.get('portfolio/accounts')

    def portfolio_subaccounts(
            self: 'IbkrClient',
            access_token:str,
            live_session_token:str) -> Result:
        """
        Used in tiered account structures (such as Financial Advisor and IBroker Accounts) to return a list of up to 100 sub-accounts for which the user can view position and account-related information. This endpoint must be called prior to calling other /portfolio endpoints for those sub-accounts.
        """
        return self.get('portfolio/subaccounts')

    def large_portfolio_subaccounts(
            self: 'IbkrClient', 
            access_token:str,
            live_session_token:str,
            page: int = 0) -> Result:
        """
        Used in tiered account structures (such as Financial Advisor and IBroker Accounts) to return a list of sub-accounts, paginated up to 20 accounts per page, for which the user can view position and account-related information. This endpoint must be called prior to calling other /portfolio endpoints for those sub-accounts.
        """
        response= OAuth_Requests_Mixin.send_oauth_request(
        request_method="GET",
        request_url="https://api.ibkr.com/v1/api/iserver/portfolio/subaccounts2', {'page': page}",
        oauth_token=access_token,
        live_session_token=live_session_token,
        # request_params=params,
        )

        return response
        # return self.get('portfolio/subaccounts2', {'page': page})

    def portfolio_account_information(
            self: 'IbkrClient', 
            access_token:str,
            live_session_token:str,
            account_id: str = None) -> Result:
        """
        Account information related to account Id. /portfolio/accounts or /portfolio/subaccounts must be called prior to this endpoint.

        Parameters:
            account_id (str, optional): Specify the AccountID to receive portfolio information for.
        """
        if account_id == None:
            account_id = self.account_id
        
        response= OAuth_Requests_Mixin.send_oauth_request(
        request_method="GET",
        request_url="https://api.ibkr.com/v1/api/iserver/portfolio/{account_id}/meta",
        oauth_token=access_token,
        live_session_token=live_session_token,
        # request_params=params,
        )

        return response
        
        # return self.get(f'portfolio/{account_id}/meta')

    def portfolio_account_allocation(
            self: 'IbkrClient', 
            access_token:str,
            live_session_token:str, 
            account_id: str = None) -> Result:
        """
        Information about the account's portfolio allocation by Asset Class, Industry and Category. /portfolio/accounts or /portfolio/subaccounts must be called prior to this endpoint.

        Parameters:
            account_id (str, optional): Specify the account ID for the request.
        """
        if account_id == None:
            account_id = self.account_id
        
        response= OAuth_Requests_Mixin.send_oauth_request(
        request_method="GET",
        request_url="https://api.ibkr.com/v1/api/iserver/portfolio/{account_id}/allocation",
        oauth_token=access_token,
        live_session_token=live_session_token,
        # request_params=params,
        )

        return response
        
        # return self.get(f'portfolio/{account_id}/allocation')

    @ensure_list_arg('account_ids')
    def portfolio_account_allocations(self: 'IbkrClient', 
                                access_token:str,
                                live_session_token:str,  
                                account_ids: OneOrMany[str]) -> Result:
        """
        Similar to /portfolio/{accountId}/allocation but returns a consolidated view of all the accounts returned by /portfolio/accounts.

        Parameters:
            account_ids (OneOrMany[str]): Contains all account IDs as strings the user should receive data for.
        """
        params = params_dict({'acctIds': account_ids})
        
        response= OAuth_Requests_Mixin.send_oauth_request(
        request_method="GET",
        request_url="https://api.ibkr.com/v1/api/iserver/portfolio/allocation",
        oauth_token=access_token,
        live_session_token=live_session_token,
        request_params=params,
        )

        return response
        
        # return self.get(f'portfolio/allocation', params=params)

    def positions(
            self: 'IbkrClient',
            access_token:str,
            live_session_token:str,
            account_id: str = None,
            page: int = 0,
            model: str = None,
            sort: str = None,
            direction: str = None,
            period: str = None,
    ) -> Result:
        """
        Returns a list of positions for the given account. The endpoint supports paging, each page will return up to 100 positions.

        Parameters:
            account_id (str, optional): The account ID for which account should place the order.
            page_id (str, optional): The “page” of positions that should be returned. One page contains a maximum of 100 positions. Pagination starts at 0.
            model (str, optional): Code for the model portfolio to compare against.
            sort (str, optional): Declare the table to be sorted by which column.
            direction (str, optional): The order to sort by. 'a' means ascending 'd' means descending.
            period (str, optional): Period for pnl column. Value Format: 1D, 7D, 1M.
        """

        if account_id == None:
            account_id = self.account_id

        params = params_dict(
            optional={
                'model': model,
                'sort': sort,
                'direction': direction,
                'period': period,
            }
        )

        response= OAuth_Requests_Mixin.send_oauth_request(
        request_method="GET",
        request_url=f"https://api.ibkr.com/v1/api/iserver/portfolio/{account_id}/positions/{page}",
        oauth_token=access_token,
        live_session_token=live_session_token,
        # request_params=params,
        )

        return response
        
        # return self.get(f'portfolio/{account_id}/positions/{page}', params)

    def positions2(
            self: 'IbkrClient',
            access_token:str,
            live_session_token:str,
            account_id: str = None,
            model: str = None,
            sort: str = None,
            direction: str = None,
    ) -> Result:
        """
        Returns a list of positions for the given account.
        /portfolio/accounts or /portfolio/subaccounts must be called prior to this endpoint.
        This endpoint provides near-real time updates and removes caching otherwise found in the /portfolio/{accountId}/positions/{pageId} endpoint.

        Parameters:
            account_id (str, optional): The account ID for which account should place the order.
            model (str, optional): Code for the model portfolio to compare against.
            sort (str, optional): Declare the table to be sorted by which column.
            direction (str, optional): The order to sort by. 'a' means ascending 'd' means descending.
        """

        if account_id == None:
            account_id = self.account_id

        params = params_dict(
            optional={
                'model': model,
                'sort': sort,
                'direction': direction,
            }
        )
        
        response= OAuth_Requests_Mixin.send_oauth_request(
        request_method="GET",
        request_url="https://api.ibkr.com/v1/api/iserver/portfolio2/{account_id}/positions",
        oauth_token=access_token,
        live_session_token=live_session_token,
        # request_params=params,
        )

        return response
        
        # return self.get(f'portfolio2/{account_id}/positions', params)

    def positions_by_conid(self: 'IbkrClient', 
                        access_token:str,
                        live_session_token:str,   
                        account_id: str, 
                        conid: str) -> Result:
        """
        Returns a list containing position details only for the specified conid.

        Parameters:
            account_id (str): The account ID for which account should place the order.
            conid (str): The contract ID to receive position information on.
        """
        if account_id == None:
            account_id = self.account_id
        
        response= OAuth_Requests_Mixin.send_oauth_request(
        request_method="GET",
        request_url=f"https://api.ibkr.com/v1/api/iserver/portfolio/{account_id}/position/{conid}",
        oauth_token=access_token,
        live_session_token=live_session_token,
        # request_params=params,
        )

        return response
            
        # return self.get(f'/portfolio/{account_id}/position/{conid}')

    def invalidate_backend_portfolio_cache(
            self: 'IbkrClient', 
            access_token:str,
            live_session_token:str,
            account_id: str = None) -> Result:
        """
        Invalidates the cached value for your portfolio’s positions and calls the /portfolio/{accountId}/positions/0 endpoint automatically.

        Parameters:
            account_id (str): The account ID for which cache to invalidate.
        """
        if account_id is None:
            account_id = self.account_id

        response= OAuth_Requests_Mixin.send_oauth_request(
        request_method="POST",
        request_url="https://api.ibkr.com/v1/api/iserver/portfolio/{account_id}/positions/invalidate",
        oauth_token=access_token,
        live_session_token=live_session_token,
        # request_params=params,
        )

        return response
            
        # return self.post(f'portfolio/{account_id}/positions/invalidate')

    def portfolio_summary(
            self: 'IbkrClient', 
            access_token:str,
            live_session_token:str,
            account_id: str = None) -> Result:
        """
        Information regarding settled cash, cash balances, etc. in the account’s base currency and any other cash balances hold in other currencies. /portfolio/accounts or /portfolio/subaccounts must be called prior to this endpoint. The list of supported currencies is available at https://www.interactivebrokers.com/en/index.php?f=3185.

        Parameters:
            account_id (str): Specify the account ID for which account you require ledger information on.
        """
        if account_id is None:
            account_id = self.account_id

        response= OAuth_Requests_Mixin.send_oauth_request(
        request_method="GET",
        request_url="https://api.ibkr.com/v1/api/iserver/portfolio/{account_id}/summary",
        oauth_token=access_token,
        live_session_token=live_session_token,
        # request_params=params,
        )

        return response
            
        # return self.get(f'portfolio/{account_id}/summary')

    def get_ledger(
            self: 'IbkrClient', 
            access_token:str,
            live_session_token:str,
            account_id: str = None) -> Result:
        """
        Information regarding settled cash, cash balances, etc. in the account’s base currency and any other cash balances hold in other currencies. /portfolio/accounts or /portfolio/subaccounts must be called prior to this endpoint. The list of supported currencies is available at https://www.interactivebrokers.com/en/index.php?f=3185.

        Parameters:
            account_id (str): Specify the account ID for which account you require ledger information on.
        """
        if account_id is None:
            account_id = self.account_id
        
        response= OAuth_Requests_Mixin.send_oauth_request(
        request_method="GET",
        request_url="https://api.ibkr.com/v1/api/iserver/portfolio/{account_id}/ledger",
        oauth_token=access_token,
        live_session_token=live_session_token,
        # request_params=params,
        )

        return response
            
        # return self.get(f'portfolio/{account_id}/ledger')

    def position_and_contract_info(
            self: 'IbkrClient', 
            access_token:str,
            live_session_token:str,
            conid: str) -> Result:
        """
        Returns an object containing information about a given position along with its contract details.

        Parameters:
            conid (str): The contract ID to receive position information on.
        """
        response= OAuth_Requests_Mixin.send_oauth_request(
        request_method="GET",
        request_url=f"https://api.ibkr.com/v1/api/iserver/portfolio/positions/{conid}",
        oauth_token=access_token,
        live_session_token=live_session_token,
        # request_params=params,
        )

        return response
        
        # return self.get(f'portfolio/positions/{conid}')

    @ensure_list_arg('account_ids')
    def account_performance(
        self: 'IbkrClient', 
        access_token:str,
        live_session_token:str,
        account_ids: OneOrMany[str], period: str) -> Result:
        """
        Returns the performance (MTM) for the given accounts, if more than one account is passed, the result is consolidated.

        Parameters:
            account_ids (OneOrMany[str]): Include each account ID to receive data for.
            period (str): Specify the period for which the account should be analyzed. Available Values: “1D”, “7D”, “MTD”, “1M”, “YTD”, “1Y”.
        """
        
        response= OAuth_Requests_Mixin.send_oauth_request(
        request_method="GET",
        request_url="https://api.ibkr.com/v1/api/iserver/pa/performance', {'acctIds': account_ids, 'period': period}",
        oauth_token=access_token,
        live_session_token=live_session_token,
        # request_params=params,
        )

        return response
        
        # return self.get(f'pa/performance', {'acctIds': account_ids, 'period': period})

    @ensure_list_arg('account_ids', 'conids')
    def transaction_history(
            self: 'IbkrClient',
            access_token:str,
            live_session_token:str,
            account_ids: OneOrMany[str],
            conids: OneOrMany[str],
            currency: str,
            days: str = None
    ) -> Result:
        """
        Transaction history for a given number of conids and accounts. Types of transactions include dividend payments, buy and sell transactions, transfers.

        Parameters:
            account_ids (OneOrMany[str]): Include each account ID to receive data for.
            conids (OneOrMany[str]): Include contract ID to receive data for. Only supports one contract id at a time.
            currency (str): Define the currency to display price amounts with. Defaults to USD.
            days (str, optional): Specify the number of days to receive transaction data for. Defaults to 90 days of transaction history if unspecified.
        """
        params = params_dict(
            {
                'acctIds': account_ids,
                'conids': conids,
                'currency': currency,
            }, optional={'days': days}
        )

        response= OAuth_Requests_Mixin.send_oauth_request(
        request_method="GET",
        request_url="https://api.ibkr.com/v1/api/iserver/pa/transactions",
        oauth_token=access_token,
        live_session_token=live_session_token,
        # request_params=params,
        )

        return response        
        # return self.post(f'pa/transactions', params)
