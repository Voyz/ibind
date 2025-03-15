# Table of Contents

* [StockQuery](#client.ibkr_utils.StockQuery)
* [make\_order\_request](#client.ibkr_utils.make_order_request)
* [ibind\_logs\_initialize](#support.logs.ibind_logs_initialize)
* [execute\_in\_parallel](#support.py_utils.execute_in_parallel)

<a id="client.ibkr_utils.StockQuery"></a>

## StockQuery

A class to encapsulate query parameters for filtering stock data.

This class is used to define a set of criteria for filtering stocks, which includes the stock symbol,
name matching pattern, and conditions for instruments and contracts.

Attributes:

- `symbol` _str_ - The stock symbol to query.
- `name_match` _Optional[str], optional_ - A string pattern to match against stock names. Optional.
- `instrument_conditions` _Optional[dict], optional_ - Key-value pairs representing conditions to apply to
  stock instruments. Each condition is matched exactly against the instrument's attributes.
- `contract_conditions` _Optional[dict], optional_ - Key-value pairs representing conditions to apply to
  stock contracts. Each condition is matched exactly against the contract's attributes.

<a id="client.ibkr_utils.make_order_request"></a>

## make\_order\_request

```python
def make_order_request(conid: Union[int, str],
                       side: str,
                       quantity: float,
                       order_type: str,
                       acct_id: str,
                       price: float = None,
                       conidex: str = None,
                       sec_type: str = None,
                       coid: str = None,
                       parent_id: str = None,
                       listing_exchange: str = None,
                       is_single_group: bool = None,
                       outside_rth: bool = None,
                       aux_price: float = None,
                       ticker: str = None,
                       tif: str = 'GTC',
                       trailing_amt: float = None,
                       trailing_type: str = None,
                       referrer: str = None,
                       cash_qty: float = None,
                       fx_qty: float = None,
                       use_adaptive: bool = None,
                       is_ccy_conv: bool = None,
                       allocation_method: str = None,
                       strategy: str = None,
                       strategy_parameters=None)
```

Create an order request object. Arguments set as None will not be included.

Arguments:

- `conid` _int | str_ - Identifier of the security to trade.
- `side` _str_ - Order side, either 'SELL' or 'BUY'.
- `quantity` _int_ - Order quantity in number of shares.
- `order_type` _str_ - Type of the order (e.g., LMT, MKT, STP).
- `price` _float_ - Order limit price, depends on order type.
- `coid` _str_ - Customer Order ID, unique for a 24h span.
- `acctId` _str, optional_ - Account ID, defaults to the first account if not provided.
  
- `conidex` _str, Optional_ - Concatenated value of contract identifier and exchange.
- `sec_type` _str, Optional_ - Concatenated value of contract-identifier and security type.
- `parent_id` _str, Optional_ - Used for child orders in bracket orders, must match the parent's cOID.
- `listing_exchange` _str, Optional, optional_ - Exchange for order routing, default is "SMART".
- `is_single_group` _bool, Optional_ - Set to True for placing single group orders (OCA).
- `outside_rth` _bool, Optional_ - Set to True if the order can be executed outside regular trading hours.
- `aux_price` _float, Optional_ - Auxiliary price parameter.
- `ticker` _str, Optional_ - Underlying symbol for the contract.
- `tif` _str, Optional_ - Time-In-Force for the order (e.g., GTC, OPG, DAY, IOC). Default: "GTC".
- `trailing_amt` _float, Optional_ - Trailing amount for TRAIL or TRAILLMT orders.
- `trailing_type` _str, Optional_ - Trailing type ('amt' or '%') for TRAIL or TRAILLMT orders.
- `referrer` _str, Optional_ - Custom order reference.
- `cash_qty` _float, Optional_ - Cash Quantity for the order.
- `fx_qty` _float, Optional_ - Cash quantity for Currency Conversion Orders.
- `use_adaptive` _bool, Optional_ - Set to True to use the Price Management Algo.
- `is_ccy_conv` _bool, Optional_ - Set to True for FX conversion orders.
- `allocation_method` _str, Optional_ - Allocation method for FA account orders.
- `strategy` _str, Optional_ - IB Algo algorithm to use for the order.
- `strategy_parameters` _dict, Optional_ - Parameters for the specified IB Algo algorithm.

<a id="support.logs.ibind_logs_initialize"></a>

## ibind\_logs\_initialize

```python
def ibind_logs_initialize(log_to_console: bool = var.LOG_TO_CONSOLE,
                          log_to_file: bool = var.LOG_TO_FILE,
                          log_level: str = var.LOG_LEVEL,
                          log_format: str = var.LOG_FORMAT)
```

Initialises the logging system.

Arguments:

- `log_to_console` _bool_ - Whether the logs should be output to the current console, `True` by default
- `log_to_file` _bool_ - Whether the logs should be written to a daily log file, `True` by default.
- `log_level` _str_ - What is the minimum log level of `ibind` logs, `INFO` by default.
- `log_format` _str_ - What is the log format to be used, `'%(asctime)s|%(levelname)-.1s| %(message)s'` by default.
  

Notes:

  - All of these parameters are read from the environment variables by default.
  - The daily file logs are saved in the directory specified by the `IBIND_LOGS_DIR` environment variable, the system temp directory by default.
  - To get more verbose logs, set either the `log_level` parameter or the `IBIND_LOG_LEVEL` environment variable to `'DEBUG'`

<a id="support.py_utils.execute_in_parallel"></a>

## execute\_in\_parallel

```python
def execute_in_parallel(func: callable,
                        requests: Union[List[dict], Dict[str, dict]],
                        max_workers: int = None,
                        max_per_second: int = 20) -> Union[dict, list]
```

Executes a function in parallel using multiple sets of arguments with rate limiting.


This function utilises a thread pool to execute the given 'func' concurrently across different sets
of arguments specified in 'requests'. The 'requests' can be either a list or a dictionary.

Arguments:

- `func` _callable_ - The function to be executed in parallel.
- `requests` _dict[str, dict] or list_ - A dictionary where keys are unique identifiers and values are
  dictionaries with 'args' and 'kwargs' for the 'func', or a list of such dictionaries.
- `max_workers` _int, optional_ - The maximum number of threads to use.
- `max_per_second` _int, optional_ - The maximum number of function executions per second. Defaults to 20.
  
  

Returns:

  Union[dict, list]: A collection of results from the function executions, keyed by the same keys as
  'requests' if it is a dictionary, or a list in the same order as the 'requests' list.
  The function returns results in a dictionary if 'requests' was a dictionary, and a list if  'requests' was a list.

