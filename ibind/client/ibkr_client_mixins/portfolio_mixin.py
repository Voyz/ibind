from typing import TYPE_CHECKING

from ibind.base.rest_client import Result
from ibind.support.logs import project_logger

if TYPE_CHECKING:
    from ibind import IbkrClient


_LOGGER = project_logger(__file__)

class PortfolioMixin():
    def get_accounts(self: 'IbkrClient') -> Result:  # pragma: no cover
        return self.get('portfolio/accounts')

    def get_ledger(self: 'IbkrClient') -> Result:  # pragma: no cover
        return self.get(f'portfolio/{self.account_id}/ledger')

    def get_positions(self: 'IbkrClient',page: int = 0) -> Result:  # pragma: no cover
        return self.get(f'portfolio/{self.account_id}/positions/{page}')

    def portfolio_invalidate(self: 'IbkrClient',account_id: str = None) -> Result:  # pragma: no cover
        if account_id is None:
            account_id = self.account_id
        return self.post(f'portfolio/{account_id}/positions/invalidate')