# Table of Contents

* [session\_mixin](#client.ibkr_client_mixins.session_mixin)
  * [SessionMixin](#client.ibkr_client_mixins.session_mixin.SessionMixin)
    * [authentication\_status](#client.ibkr_client_mixins.session_mixin.SessionMixin.authentication_status)
    * [initialize\_brokerage\_session](#client.ibkr_client_mixins.session_mixin.SessionMixin.initialize_brokerage_session)
    * [logout](#client.ibkr_client_mixins.session_mixin.SessionMixin.logout)
    * [tickle](#client.ibkr_client_mixins.session_mixin.SessionMixin.tickle)
    * [reauthenticate](#client.ibkr_client_mixins.session_mixin.SessionMixin.reauthenticate)
    * [validate](#client.ibkr_client_mixins.session_mixin.SessionMixin.validate)
    * [check\_health](#client.ibkr_client_mixins.session_mixin.SessionMixin.check_health)
    * [check\_auth\_status](#client.ibkr_client_mixins.session_mixin.SessionMixin.check_auth_status)

<a id="client.ibkr_client_mixins.session_mixin.SessionMixin"></a>

## SessionMixin

https://www.interactivebrokers.com/docs/web-api/v1/endpoints/session

<a id="client.ibkr_client_mixins.session_mixin.SessionMixin.authentication_status"></a>

### authentication\_status

```python
def authentication_status(log: bool = True) -> Result
```

Current Authentication status to the Brokerage system. Market Data and Trading is not possible if not authenticated, e.g. authenticated shows false.

Arguments:

- `log` _bool, optional_ - Log the authentication status request. Defaults to True.

<a id="client.ibkr_client_mixins.session_mixin.SessionMixin.initialize_brokerage_session"></a>

### initialize\_brokerage\_session

```python
def initialize_brokerage_session(compete: bool = True) -> Result
```

After retrieving the access token and subsequent Live Session Token, customers can initialize their brokerage session with the ssodh/init endpoint.
NOTE: This is essential for using all /iserver endpoints, including access to trading and market data.

Arguments:

- `compete` _Boolean_ - Determines if other brokerage sessions should be disconnected to prioritize this connection.
  

Notes:

  - `publish` parameter is always set to `True` as per the documentation.

<a id="client.ibkr_client_mixins.session_mixin.SessionMixin.logout"></a>

### logout

```python
def logout() -> Result
```

Logs the user out of the gateway session. Any further activity requires re-authentication.

<a id="client.ibkr_client_mixins.session_mixin.SessionMixin.tickle"></a>

### tickle

```python
def tickle(log: bool = False) -> Result
```

If the gateway has not received any requests for several minutes an open session will automatically timeout. The tickle endpoint pings the server to prevent the session from ending. It is expected to call this endpoint approximately every 60 seconds to maintain the connection to the brokerage session.

Arguments:

- `log` _bool, optional_ - Log the tickle request. Defaults to False.

<a id="client.ibkr_client_mixins.session_mixin.SessionMixin.reauthenticate"></a>

### reauthenticate

```python
def reauthenticate() -> Result
```

When using the CP Gateway, this endpoint provides a way to reauthenticate to the Brokerage system as long as there is a valid brokerage session.
All interest in reauthenticating the gateway session should be handled using the /iserver/auth/ssodh/init endpoint.

<a id="client.ibkr_client_mixins.session_mixin.SessionMixin.validate"></a>

### validate

```python
def validate() -> Result
```

Validates the current session for the SSO user.

<a id="client.ibkr_client_mixins.session_mixin.SessionMixin.check_health"></a>

### check\_health

```python
def check_health() -> bool
```

Verifies the health and authentication status of the IBKR Gateway server.

This method checks if the Gateway server is alive and whether the user is authenticated.
It also checks for any competing connections and the connection status.

Returns:

- `bool` - True if the Gateway server is authenticated, not competing, and connected, False otherwise.
  

Raises:

- `AttributeError` - If the Gateway health check request returns invalid data.
  

Notes:

  - This method returns a boolean directly without the `Result` dataclass.

<a id="client.ibkr_client_mixins.session_mixin.SessionMixin.check_auth_status"></a>

### check\_auth\_status

```python
def check_auth_status() -> bool
```

Verifies the health and authentication status of the IBKR Gateway server.

This method checks if the Gateway server is alive and whether the user is authenticated.
It also checks for any competing connections and the connection status.

Returns:

- `bool` - True if the Gateway server is authenticated, not competing, and connected, False otherwise.
  

Raises:

- `AttributeError` - If the Gateway health check request returns invalid data.
  

Notes:

  - This method returns a boolean directly without the `Result` dataclass.
