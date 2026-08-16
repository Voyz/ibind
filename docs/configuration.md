# Configuration

There are three fundamental configurations of IBind:

* [Constructor parameters](#constructor-parameters) for `IbkrClient` and `IbkrWsClient`
* [Environment variables](#environment-variables)
* [Logging](#logging)

# <a name="constructor-parameters"></a> Constructor Parameters

`IbkrClient` and `IbkrWsClient` have three common settings that can be configured through their constructor parameters:

* [Account ID](#account-id-configuration)
* [URL](#url-configuration)
* [CAcert](#cacert-configuration)

### <a name="account-id-configuration"></a> Account ID configuration

Many of the IBKR API endpoints require an account ID to be specified.

In most cases this value will be the constant for a particular user, hence both the `IbkrClient` and `IbkrWsClient` allow to store the account ID by specifying the `account_id` parameter upon construction.

```python
IbkrClient(account_id='DU12345678')
```

Note:
* This value can be set as an environment variable `IBIND_ACCOUNT_ID`, which will be read automatically upon construction.
* All API methods that require the account ID to be specified provide an optional `account_id` parameter allowing you to override this class field on case-by-case basis.


### <a name="url-configuration"></a> URL configuration

_Ignore this section if you're using OAuth 1.0a, as the its URL points at IBKR servers and will most likely not change._

The client classes require a URL to the Client Portal Gateway. There are two ways of specifying it:

#### 1. Provide the full URL through the `url` parameter, eg.:

```python
IbkrClient(url='https://mydomain:6060/v1/api/')
IbkrWsClient(url='wss://mydomain:6060/v1/api/ws')
```

Note:
* This value can be set as an environment variable `IBIND_REST_URL`, which will be read automatically upon construction.

#### 2. Provide the `host`, `port` and/or `base_route` parameters.

These then get combined as follows:

* `https://{host}:{port}{base_route}` for `IbkrClient`
* `wss://{host}:{port}{base_route}` for `IbkrWsClient`

Eg.:

```python
IbkrClient(port=6060)
```

The default values are:

```python
host = 'localhost'
port = '5000'
base_route = '/v1/api/' # for IbkrClient
base_route = '/v1/api/ws' # for IbkrWsClient
```

Note:
* The `host`, `port` and `base_route` parameters are ignored if the `url` parameter is provided.
* If no parameters are provided, the default `host`, `port`, and `base_route` values will be used.

### <a name="cacert-configuration"></a> CAcert configuration

_Ignore this section if you're using OAuth 1.0a, as there is no need to use CA certificates._

The Client Portal Gateway can be set up to use custom CAcerts. To communicate with it, the API client will need to use the same certificates.

The `cacert` parameter allows you to specify a path to the `cacert.pem` certificate, eg.:

```python
IbkrClient(cacert='/some/path/to/my/cacert.pem')
```

Note:
* This value can be set as an environment variable `IBIND_CACERT`, which will be read automatically upon construction.
* You can set this value to `False` which will avoid using certificates and verified HTTPS.

# <a name="environment-variables"></a> Environment variables

A full and most up-to-date list of environment variables can be found in the [`var.py`][var.py] file.

| Variable name | Default value | Description |
| ---  | ----- | --- |
| `IBIND_LOG_TO_CONSOLE` | True | Whether logs should be streamed to the standard output. |
| `IBIND_LOG_LEVEL` | 'INFO' | The global log level for the StreamHandler. |
| `IBIND_LOG_FORMAT` | '%(asctime)s\|%(levelname)-.1s\| %(message)s' | Log format that is used by IBind |
| `IBIND_LOGS_DIR` | tempfile.gettempdir() | Directory of file logs produced. |
| `IBIND_LOG_TO_FILE` | True | Whether logs should be saved to a file. |
| `IBIND_REST_URL` | None | IBKR Client Portal Gateway's URL for REST API. |
| `IBIND_WS_URL` | None | IBKR Client Portal Gateway's URL for WebSocket API. |
| `IBIND_ACCOUNT_ID` | None | IBKR account ID to use. |
| `IBIND_CACERT` | False | Path to certificates used to communicate with IBKR Client Portal Gateway. |
| `IBIND_WS_PING_INTERVAL` | 45 | Interval between WebSocket pings. |
| `IBIND_WS_MAX_PING_INTERVAL` | 300 | Max accepted interval between WebSocket pings. |
| `IBIND_WS_TIMEOUT` | 5 | Timeout for WebSocket state change verifications. |
| `IBIND_WS_SUBSCRIPTION_RETRIES` | 5 | Number of attempts to create a WebSocket subscription. |
| `IBIND_WS_SUBSCRIPTION_TIMEOUT` | 2 | Timeout for WebSocket subscription verifications. |
| `IBIND_WS_LOG_RAW_MESSAGES` | False | Whether raw WebSocket messages should be logged. |

# <a name="logging"></a> Logging

IBind produces a number of logs using the Python standard [logging module][python-logging].

Off by default, this logging functionality needs to be activated by calling the `ibind_logs_initialize()` function.

```python
from ibind import ibind_logs_initialize

ibind_logs_initialize()
```

The `ibind_logs_initialise` function accepts the following parameters:

* `log_to_console`- whether the logs should be output to the current console, `True` by default
* `log_to_file`- whether the logs should be written to a daily log file, `True` by default.
* `log_level` - what is the minimum log level of `ibind` logs, `INFO` by default.
* `log_format` - what is the log format to be used, `'%(asctime)s|%(levelname)-.1s| %(message)s'` by default.

Note:
* All of these parameters are read from the environment variables by default.
* The daily file logs are saved in the directory specified by the `IBIND_LOGS_DIR` environment variable, the system temp directory by default.
* To get more verbose logs, set either the `log_level` parameter or the `IBIND_LOG_LEVEL` environment variable to `'DEBUG'`

----
#### Next

Learn about the [IbkrClient][ibkr-client-docs].

[ibkr-client-docs]: ./rest/ibkr_client.md
[var.py]: https://github.com/Voyz/ibind/blob/master/ibind/var.py
[python-logging]: https://docs.python.org/3/library/logging.html
