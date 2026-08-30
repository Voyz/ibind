# Table of Contents

* [rest\_client](#base.rest_client)
  * [Result](#base.rest_client.Result)
* [ibkr\_client](#client.ibkr_client)
  * [IbkrClient](#client.ibkr_client.IbkrClient)
    * [\_\_init\_\_](#client.ibkr_client.IbkrClient.__init__)
    * [generate\_live\_session\_token](#client.ibkr_client.IbkrClient.generate_live_session_token)
    * [oauth\_init](#client.ibkr_client.IbkrClient.oauth_init)
    * [start\_tickler](#client.ibkr_client.IbkrClient.start_tickler)
    * [stop\_tickler](#client.ibkr_client.IbkrClient.stop_tickler)
    * [oauth\_shutdown](#client.ibkr_client.IbkrClient.oauth_shutdown)
    * [handle\_auth\_status](#client.ibkr_client.IbkrClient.handle_auth_status)

<a id="base.rest_client.Result"></a>

## Result

A class to encapsulate the result of an API request.

This class is used to store and handle data returned from an API call. It includes the response data and
the original request details.

Attributes:

- `data` _Optional[Union[list, dict]]_ - The data returned from the operation. Can be either a list or a dictionary.
- `request` _Optional[dict]_ - Details of the request that resulted in this data.

<a id="client.ibkr_client.IbkrClient"></a>

## IbkrClient

A client class for interfacing with the IBKR API, extending the RestClient class.

This subclass of RestClient is specifically designed for the IBKR API. It inherits
the foundational REST API interaction capabilities from RestClient and adds functionalities
particular to the IBKR API, such as specific endpoint handling.

The class provides methods to perform various operations with the IBKR API, such as
fetching stock data, submitting orders, and managing account information.

See: https://interactivebrokers.github.io/cpwebapi/endpoints

Notes:

  - All endpoint mappings are defined as class mixins, categorised similar to the IBKR REST API documentation. See appropriate mixins for more information.

<a id="client.ibkr_client.IbkrClient.__init__"></a>

### \_\_init\_\_

```python
def __init__(account_id: Optional[str] = var.IBIND_ACCOUNT_ID,
             url: str = var.IBIND_REST_URL,
             host: str = '127.0.0.1',
             port: str = '5000',
             base_route: str = '/v1/api/',
             cacert: Union[str, os.PathLike, bool] = var.IBIND_CACERT,
             timeout: float = 10,
             max_retries: int = 3,
             use_session: bool = var.IBIND_USE_SESSION,
             auto_recreate_session: bool = True,
             auto_register_shutdown: bool = var.IBIND_AUTO_REGISTER_SHUTDOWN,
             log_responses: bool = var.IBIND_LOG_RESPONSES,
             verbose_retries: bool = var.IBIND_VERBOSE_RETRIES,
             use_oauth: bool = var.IBIND_USE_OAUTH,
             oauth_config: 'OAuthConfig' = None) -> None
```

Arguments:

- `account_id` _str_ - An identifier for the account. Defaults to None.
- `url` _str_ - The base URL for the REST API. Defaults to None.
  If 'use_oauth' is specified, the url is taken from oauth_config.
  Only if it couldn't be found in oauth_config, this url is used,
  or the parameters host, port and base_route.
- `host` _str, optional_ - Host for the IBKR REST API. Defaults to 'localhost'.
- `port` _str, optional_ - Port for the IBKR REST API. Defaults to '5000'
- `base_route` _str, optional_ - Base route for the IBKR REST API. Defaults to '/v1/api/'.
- `cacert` _Union[os.PathLike, bool], optional_ - Path to the CA certificate file for SSL verification,
  or False to disable SSL verification. Always True when
  use_oauth is True. Defaults to False.
- `timeout` _float, optional_ - Timeout in seconds for the API requests. Defaults to 10.
- `max_retries` _int, optional_ - Maximum number of retries for failed API requests. Defaults to 3.
- `use_session` _bool, optional_ - Whether to use a persistent session for making requests. Defaults to True.
- `auto_recreate_session` _bool, optional_ - Whether to automatically recreate the session on connection errors. Defaults to True.
- `auto_register_shutdown` _bool, optional_ - Whether to automatically register a shutdown handler for this client. Defaults to True.
- `log_responses` _bool, optional_ - Whether to log responses from the API. Defaults to False.
- `verbose_retries` _bool, optional_ - Whether to log verbose retry information. Defaults to False.
- `use_oauth` _bool, optional_ - Whether to use OAuth authentication. Defaults to False.
- `oauth_config` _OAuthConfig, optional_ - The configuration for the OAuth authentication. OAuth1aConfig is used if not specified.

<a id="client.ibkr_client.IbkrClient.generate_live_session_token"></a>

### generate\_live\_session\_token

```python
def generate_live_session_token()
```

Generates a new live session token for OAuth 1.0a authentication.

This method requests a new OAuth live session token from the IBKR API using the configured
OAuth credentials. The token is stored along with its expiration time and signature.

The live session token is required for authenticated requests to IBKR's OAuth 1.0a API.

Raises:

- `ExternalBrokerError` - If the token request fails.

<a id="client.ibkr_client.IbkrClient.oauth_init"></a>

### oauth\_init

```python
def oauth_init(maintain_oauth: bool, init_brokerage_session: bool)
```

Initializes the OAuth authentication flow for the IBKR API.

This method sets up OAuth authentication by generating a live session token, validating it,
and optionally starting a tickler to maintain the session. It also allows initializing a brokerage session if specified.

OAuth authentication is required for certain IBKR API operations. The process includes:
- Checking for the necessary cryptographic dependencies.
- Generating and validating a live session token.
- Optionally maintaining the session by running a tickler.
- Initializing a brokerage session if required.

Arguments:

- `maintain_oauth` _bool_ - If True, starts the Tickler process to keep the session alive.
- `init_brokerage_session` _bool_ - If True, initializes the brokerage session after authentication.
  

Raises:

- `ImportError` - If the required cryptographic dependencies (`Crypto` module) are missing.
- `RuntimeError` - If live session token validation fails.
  
  See:
  - `generate_live_session_token`: Generates a new OAuth session token.
  - `validate_live_session_token`: Validates the generated OAuth session token.
  - `start_tickler`: Maintains the session by periodically sending requests.
  - `initialize_brokerage_session`: Establishes a brokerage session post-authentication.

<a id="client.ibkr_client.IbkrClient.start_tickler"></a>

### start\_tickler

```python
def start_tickler(interval: int = var.IBIND_TICKLER_INTERVAL)
```

Starts the `Tickler` instance and starts it in a separate thread to maintain the OAuth session.

The Tickler sends periodic requests to the IBKR API to prevent the session from expiring.
This is necessary when using OAuth authentication to keep the connection active.

Arguments:

- `interval` _Union[int, float]_ - Interval between tickles in seconds. Default is 60 seconds.
  

Notes:

  - The Tickler should be stopped when the session is no longer needed using `stop_tickler()`.

<a id="client.ibkr_client.IbkrClient.stop_tickler"></a>

### stop\_tickler

```python
def stop_tickler(timeout: float = None)
```

Stops the Tickler thread if the Tickler is running.

The Tickler is responsible for maintaining an active session by sending periodic requests to
the IBKR API. This method stops the Tickler process, preventing further requests.

Arguments:

- `timeout` _Optional[float]_ - Maximum time to wait for the Tickler thread to terminate.
  If None, waits indefinitely.

<a id="client.ibkr_client.IbkrClient.oauth_shutdown"></a>

### oauth\_shutdown

```python
def oauth_shutdown()
```

Shuts down the OAuth session and cleans up resources.

This method stops the Tickler process, which keeps the session alive, and logs out from
the IBKR API to ensure a clean session termination.

<a id="client.ibkr_client.IbkrClient.handle_auth_status"></a>

### handle\_auth\_status

```python
def handle_auth_status(raise_exceptions: bool = False) -> bool
```

Handles the authentication status of the IBKR connection.

If the connection is not healthy, it attempts to re-establish OAuth authentication.

Arguments:

- `raise_exceptions` _bool_ - Whether to raise exceptions if the connection is not healthy.
  

Returns:

- `bool` - True if the connection is healthy, False otherwise.
