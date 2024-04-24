from typing import TYPE_CHECKING, List, Dict

from ibind.base.rest_client import Result
from ibind.support.logs import project_logger
from ibind.support.py_utils import params_dict

if TYPE_CHECKING:  # pragma: no cover
    from ibind import IbkrClient

_LOGGER = project_logger(__file__)


class ScannerMixin():
    def scanner_parameters(self: 'IbkrClient') -> Result:
        """
        Returns an xml file containing all available parameters to be sent for the Iserver scanner request.
        """
        return self.get('iserver/scanner/params')

    def market_scanner(
            self: 'IbkrClient',
            instrument: str,
            type: str,
            location: str,
            filter: List[Dict[str, str]] = None
    ) -> Result:
        """
        Searches for contracts according to the filters specified in /iserver/scanner/params endpoint.
        Users can receive a maximum of 50 contracts from 1 request.

        Parameters:
            instrument (str): Instrument type as the target of the market scanner request. Found in the “instrument_list” section of the /iserver/scanner/params response.
            type (str): Scanner value the market scanner is sorted by. Based on the “scan_type_list” section of the /iserver/scanner/params response.
            location (str): Location value the market scanner is searching through. Based on the “location_tree” section of the /iserver/scanner/params response.
            filter (List[Dict[str, str]]): Contains any additional filters that should apply to response. Each filter object may include:
                - code (str): Code value of the filter. Based on the “code” value within the “filter_list” section of the /iserver/scanner/params response.
                - value (int): Value corresponding to the input for “code”.
        """
        params = params_dict(
            {
                'instrument': instrument,
                'type': type,
                'location': location,
            }, optional={'filter': filter}
        )
        return self.post('iserver/scanner/run', params)

    def hmds_scanner_parameters(self: 'IbkrClient') -> Result:
        """
        Query the parameter list for the HMDS market scanner.
        """
        return self.get('hmds/scanner/params')

    def hmds_market_scanner(
            self: 'IbkrClient',
            instrument: str,
            location: str,
            scan_code: str,
            sec_type: str,
            filter: List[Dict[str, str]],
            max_items: int = None,
    ) -> Result:
        """
        Request a market scanner from our HMDS service.
        Can return a maximum of 250 contracts.

        Parameters:
            instrument (str): Specify the type of instrument for the request. Found under the “instrument_list” value of the /hmds/scanner/params request.
            locations (str): Specify the type of location for the request. Found under the “location_tree” value of the /hmds/scanner/params request.
            scanCode (str): Specify the scanner type for the request. Found under the “scan_type_list” value of the /hmds/scanner/params request.
            secType (str): Specify the type of security type for the request. Found under the “location_tree” value of the /hmds/scanner/params request.
            filters (List[Dict[str, str]]): Array of objects containing all filters upon the scanner request. While “filters” must be specified in the body, no content in the array needs to be passed.
            maxItems (int, optional): Specify how many items should be returned. Default and maximum set to 250.
        """
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
