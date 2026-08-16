# Table of Contents

* [scanner\_mixin](#client.ibkr_client_mixins.scanner_mixin)
  * [ScannerMixin](#client.ibkr_client_mixins.scanner_mixin.ScannerMixin)
    * [scanner\_parameters](#client.ibkr_client_mixins.scanner_mixin.ScannerMixin.scanner_parameters)
    * [market\_scanner](#client.ibkr_client_mixins.scanner_mixin.ScannerMixin.market_scanner)
    * [hmds\_scanner\_parameters](#client.ibkr_client_mixins.scanner_mixin.ScannerMixin.hmds_scanner_parameters)
    * [hmds\_market\_scanner](#client.ibkr_client_mixins.scanner_mixin.ScannerMixin.hmds_market_scanner)

<a id="client.ibkr_client_mixins.scanner_mixin.ScannerMixin"></a>

## ScannerMixin

https://www.interactivebrokers.com/docs/web-api/v1/endpoints/scanner

<a id="client.ibkr_client_mixins.scanner_mixin.ScannerMixin.scanner_parameters"></a>

### scanner\_parameters

```python
def scanner_parameters() -> Result
```

Returns an xml file containing all available parameters to be sent for the Iserver scanner request.

<a id="client.ibkr_client_mixins.scanner_mixin.ScannerMixin.market_scanner"></a>

### market\_scanner

```python
def market_scanner(instrument: str,
                   type: str,
                   location: str,
                   filter: List[Dict[str, str]] = None) -> Result
```

Searches for contracts according to the filters specified in /iserver/scanner/params endpoint.
Users can receive a maximum of 50 contracts from 1 request.

Arguments:

- `instrument` _str_ - Instrument type as the target of the market scanner request. Found in the �instrument_list� section of the /iserver/scanner/params response.
- `type` _str_ - Scanner value the market scanner is sorted by. Based on the �scan_type_list� section of the /iserver/scanner/params response.
- `location` _str_ - Location value the market scanner is searching through. Based on the �location_tree� section of the /iserver/scanner/params response.
- `filter` _List[Dict[str, str]]_ - Contains any additional filters that should apply to response. Each filter object may include:
  - code (str): Code value of the filter. Based on the �code� value within the �filter_list� section of the /iserver/scanner/params response.
  - value (int): Value corresponding to the input for �code�.

<a id="client.ibkr_client_mixins.scanner_mixin.ScannerMixin.hmds_scanner_parameters"></a>

### hmds\_scanner\_parameters

```python
def hmds_scanner_parameters() -> Result
```

Query the parameter list for the HMDS market scanner.

<a id="client.ibkr_client_mixins.scanner_mixin.ScannerMixin.hmds_market_scanner"></a>

### hmds\_market\_scanner

```python
def hmds_market_scanner(instrument: str,
                        location: str,
                        scan_code: str,
                        sec_type: str,
                        filter: List[Dict[str, str]],
                        max_items: int = None) -> Result
```

Request a market scanner from our HMDS service.
Can return a maximum of 250 contracts.

Arguments:

- `instrument` _str_ - Specify the type of instrument for the request. Found under the �instrument_list� value of the /hmds/scanner/params request.
- `locations` _str_ - Specify the type of location for the request. Found under the �location_tree� value of the /hmds/scanner/params request.
- `scanCode` _str_ - Specify the scanner type for the request. Found under the �scan_type_list� value of the /hmds/scanner/params request.
- `secType` _str_ - Specify the type of security type for the request. Found under the �location_tree� value of the /hmds/scanner/params request.
- `filters` _List[Dict[str, str]]_ - Array of objects containing all filters upon the scanner request. While �filters� must be specified in the body, no content in the array needs to be passed.
- `maxItems` _int, optional_ - Specify how many items should be returned. Default and maximum set to 250.
