from typing import TYPE_CHECKING, List, Dict

from ibind.base.rest_client import Result
from ibind.support.logs import project_logger
from ibind.support.py_utils import params_dict

if TYPE_CHECKING:  # pragma: no cover
    from ibind import IbkrClient

_LOGGER = project_logger(__file__)


class ScannerMixin():
    def scanner_parameters(self: 'IbkrClient') -> Result:
        return self.get('iserver/scanner/params')

    def market_scanner(
            self: 'IbkrClient',
            instrument: str,
            type: str,
            location: str,
            filter: List[Dict[str, str]] = None
    ) -> Result:
        params = params_dict(
            {
                'instrument': instrument,
                'type': type,
                'location': location,
            }, optional={'filter': filter}
        )
        return self.post('iserver/scanner/run', params)

    def hmds_scanner_parameters(self: 'IbkrClient') -> Result:
        return self.get('hmds/scanner/params')

    def hmds_market_scanner(
            self: 'IbkrClient',
            instrument: str,
            location: str,
            scan_code: str,
            sec_type: str,
            max_items: int = None,
            filter: List[Dict[str, str]] = None
    ) -> Result:
        params = params_dict(
            {
                'instrument': instrument,
                'location': location,
                'scanCode': scan_code,
                'secType': sec_type
            }, optional={
                'maxItems': max_items,
                'filter': filter
            }
        )
        return self.post('hmds/scanner/run', params)
