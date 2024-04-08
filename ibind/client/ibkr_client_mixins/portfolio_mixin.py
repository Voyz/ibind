from typing import TYPE_CHECKING

from ibind.base.rest_client import Result
from ibind.support.logs import project_logger
from ibind.support.py_utils import params_dict, ensure_list_arg, OneOrMany

if TYPE_CHECKING:  # pragma: no cover
    from ibind import IbkrClient

_LOGGER = project_logger(__file__)


class PortfolioMixin():
    def portfolio_accounts(self: 'IbkrClient') -> Result:
        return self.get('portfolio/accounts')

    def portfolio_subaccounts(self: 'IbkrClient') -> Result:
        return self.get('portfolio/subaccounts')

    def large_portfolio_subaccounts(self: 'IbkrClient', page: int = 0) -> Result:
        return self.get('portfolio/subaccounts2', {'page': page})

    def portfolio_account_information(self: 'IbkrClient', account_id: str) -> Result:
        if account_id == None:
            account_id = self.account_id
        return self.get(f'portfolio/{account_id}/meta')

    def portfolio_account_allocation(self: 'IbkrClient', account_id: str) -> Result:
        if account_id == None:
            account_id = self.account_id
        return self.get(f'portfolio/{account_id}/allocation')

    def portfolio_account_allocations(self: 'IbkrClient') -> Result:
        return self.get(f'portfolio/allocation')

    def positions(
            self: 'IbkrClient',
            account_id: str = None,
            page: int = 0,
            model: str = None,
            sort: str = None,
            direction: str = None,
            period: str = None,

    ) -> Result:
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
        return self.get(f'portfolio/{account_id}/positions/{page}', params)

    def positions_by_conid(self: 'IbkrClient', account_id: str, conid: str) -> Result:
        if account_id == None:
            account_id = self.account_id
        return self.get(f'/portfolio/{account_id}/position/{conid}')

    def invalidate_backend_portfolio_cache(self: 'IbkrClient', account_id: str = None) -> Result:
        if account_id is None:
            account_id = self.account_id
        return self.post(f'portfolio/{account_id}/positions/invalidate')

    def portfolio_summary(self: 'IbkrClient', account_id: str = None) -> Result:
        if account_id is None:
            account_id = self.account_id
        return self.get(f'portfolio/{account_id}/summary')

    def get_ledger(self: 'IbkrClient', account_id: str = None) -> Result:
        if account_id is None:
            account_id = self.account_id
        return self.get(f'portfolio/{account_id}/ledger')

    def position_and_contract_info(self: 'IbkrClient', conid: str = None) -> Result:
        return self.get(f'portfolio/positions/{conid}')

    @ensure_list_arg('account_ids')
    def account_performance(self: 'IbkrClient', account_ids: OneOrMany[str], period: str) -> Result:
        return self.get(f'pa/performance', {'acctIds': account_ids, 'period': period})

    @ensure_list_arg('account_ids', 'conids')
    def transaction_history(
            self: 'IbkrClient',
            account_ids: OneOrMany[str],
            conids: OneOrMany[str],
            currency: str,
            days: str = None
    ) -> Result:
        params = params_dict(
            {
                'acctIds': account_ids,
                'conids': conids,
                'currency': currency,
            }, optional={'days': days}
        )
        return self.get(f'pa/transactions', params)
