# Table of Contents

* [ibkr\_utils](#client.ibkr_utils)
  * [StockQuery](#client.ibkr_utils.StockQuery)
  * [OrderRequest](#client.ibkr_utils.OrderRequest)
* [logs](#support.logs)
  * [ibind\_logs\_initialize](#support.logs.ibind_logs_initialize)
* [py\_utils](#support.py_utils)
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

<a id="client.ibkr_utils.OrderRequest"></a>

## OrderRequest

<a id="support.logs.ibind_logs_initialize"></a>

## ibind\_logs\_initialize

```python
def ibind_logs_initialize(log_to_console: bool = var.LOG_TO_CONSOLE,
                          log_to_file: bool = var.LOG_TO_FILE,
                          log_level: str = var.LOG_LEVEL,
                          log_format: str = var.LOG_FORMAT,
                          print_file_logs: bool = var.PRINT_FILE_LOGS)
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
