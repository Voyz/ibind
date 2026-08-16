# Advanced OAuth 1.0a

This page covers the advanced concepts of using OAuth 1.0a with IBind.

* [Advanced OAuth 1.0a Configuration](#advanced_oauth1a_configuration)
* [WebSockets with OAuth 1.0a](#websockets_with_oauth1a)
* [OAuth 2.0](#oauth2)

## <a name="advanced_oauth1a_configuration"></a> Advanced OAuth 1.0a Configuration

Once the `IbkrClient` class is set up correctly - whether though environment variables or constructor parameters - it will automatically handle the remaining responsibilities of establishing and maintaining an OAuth 1.0a authentication with IBKR servers. This includes:

* Changing the URL to IBKR OAuth 1.0a URL
* Generating a live session token and validating it
* Maintaining the connection active by repeatedly calling the `tickle` endpoint on an interval
* Registering a `SIGINT` and `SIGTERM` shutdown handler that will call `logout` endpoint upon program termination
* Calling `initialize_brokerage_session` endpoint in order to gain complete access to the IBKR API functionality

The following subsections discuss how each of these automated behaviours can be customised.

### OAuth 1.0a URL Customisation

When communicating with IBKR using OAuth 1.0a the client should direct all requests to a URL provided by IBKR, currently: `https://api.ibkr.com/v1/api/`.

* You can change this default by modifying either `IBIND_OAUTH1A_REST_URL` env var or `OAuth1aConfig.oauth_rest_url` field.

### Generating Live Session Token

Once you are registered in the Self-Service portal, all authentication will begin with the `/live_session_token` endpoint. IBind will [generate][live_session_token], [validate][validate_live_session_token], store and use that token automatically for you.

* Set the `IBIND_INIT_OAUTH` env var or the `OAuth1aConfig.init_oauth` field to `False` to alter this behaviour.
* This will skip the entire process of initialisation, allowing you to carry it out on your own.
* Disabling initialisation also disables automatically carrying out maintenance and shutdown handling.

### Maintaining The Connection

In order to maintain the connection active, [IBKR recommends][ibkr-tickle] calling the `tickle` endpoint every 60 seconds. IBind provides a class called `Tickler` which will carry this task out automatically.

During initialisation `IbkrClient` will construct and start an instance of `Tickler`.

* Set the `IBIND_MAINTAIN_OAUTH` env var or the `OAuth1aConfig.maintain_oauth` field to `False` to alter this behaviour.
* This will skip the internal instantiation of `Tickler`, allowing you to either instantiate it yourself or call the `tickle` endpoint in your own fashion.
* This functionality will not be carried out automatically if you've disabled initialisation altogether. You can enable it manually by calling `IbkrClient.start_tickler()` method.

### Shutdown Handler

During initialisation, IBind registers a signal handler for `SIGINT` and `SIGTERM` signals in order to call the `logout` endpoint and optionally stop the `Tickler` if it is running.

* Set the `IBIND_SHUTDOWN_OAUTH` env var or the `OAuth1aConfig.shutdown_oauth` field to `False` to alter this behaviour.
* This will prevent registering the signal handler, allowing you to handle logging out and stopping the `Tickler` in your own fashion.
* This functionality will not be carried out automatically if you've disabled initialisation altogether. You can enable it manually by calling `IbkrClient.register_shutdown_handler()` method.

### Initializing Brokerage Session

The default session created using OAuth 1.0a authentication flow is considered 'uninitialized'. It allows you to access a limited scope of endpoints, however it will not cause any other currently logged in sessions to be closed - for example if you have TWS running with the same credentials. To fully utilize the API you need to [initialize the brokerage session][ibkr-initialize_brokerage_session] by calling `iserver/auth/ssodh/init` endpoint by using the `IbkrClient.initialize_brokerage_session()` method. Note that this will close any other currently logged in sessions.

When using the CP Gateway, the session established seems to always be initialised by default, however when using OAuth 1.0a `IbkrClient` will handle calling that endpoint for you.

* Set the `IBIND_INIT_BROKERAGE_SESSION` env var or the `OAuth1aConfig.init_brokerage_session` field to `False` to alter this behaviour.
* This will prevent `IbkrClient.initialize_brokerage_session()` method from being called, allowing you to use the session as uninitialized or to initialize it in your own fashion.
* This functionality will not be carried out automatically if you've disabled initialisation altogether. You can enable it manually by calling `IbkrClient.initialize_brokerage_session()` method.

### Example

Following code snipped demonstrates how to configure the OAuth 1.0a setup and carry out the initialization manually:

```python
# create a client with all OAuth 1.0a initialization disabled
client = IbkrClient(
    use_oauth=True,
    oauth_config=OAuth1aConfig(
        init_oauth=False,
        init_brokerage_session=False,
        maintain_oauth=False,
        shutdown_oauth=False,
        ...
    )
)

# manually generate a live session token (required)
client.generate_live_session_token()

# manually start the Tickler instance (optional)
client.start_tickler()

# manually register the shutdown handler (optional)
client.register_shutdown_handler()

# manually initialize the brokerage session (required for complete functionality)
client.initialize_brokerage_session()
```

## <a name="websockets_with_oauth1a"></a> WebSockets With OAuth 1.0a

Using WebSocket with OAuth1.0a requires an established OAuth 1.0a session. The `IbkrWsClient` will use an instance of `IbkrClient` to acquire the currently active session.

* If you exclusively use environment variables to set OAuth 1.0a up, the `IbkrWsClient` will automatically create a valid `IbkrClient` class which should handle the session initialisation for you.
    ```python
    ibkr_ws_client = IbkrWsClient() # initializes OAuth from environment variables
    ```
* If you'd like to use constructor parameters, first create an instance of `IbkrClient` that has been correctly set up for OAuth 1.0a, then pass it as `ibkr_client` argument to `IbkrWsClient`. Additionally, you'll need to specify the `use_oauth` and `access_token` parameters.
    ```python
    ibkr_client = IbkrClient(use_oauth=True, oauth_config=OAuth1aConfig(...))
    ibkr_ws_client = IbkrWsClient(ibkr_client=ibkr_client, use_oauth=True, access_token='my_access_token')
    ```

When using OAuth 1.0a, the `IbkrWsClient` will also modify the URL to `wss://api.ibkr.com/v1/api/ws`, which you can customise by setting the `IBIND_OAUTH1A_WS_URL` env var.

## <a name="oauth2"></a> OAuth 2.0

At the time of writing this, IBKR mentions availability of OAuth 2.0 however no documentation is made available on how to implement it. Some users with business type accounts [got access][oauth2-access] to it by talking to IBKR directly. If you learn how we could implement OAuth 2.0, please create a new issue and let us know.

IBKR support agent commented:

> OAuth 2.0 access at Interactive Brokers is currently in a highly restrictive beta state and is only rolled out in case of absolute need for very unique Financial Advisor situations at this time. OAuth 2.0 is provided on an as-needed basis by our integration team when connecting with Interactive Brokers.

----

#### Next

Learn about [IBind Configuration][ibind-configuration].


[live_session_token]: https://www.interactivebrokers.com/campus/ibkr-api-page/cpapi-v1/#lst

[validate_live_session_token]: https://www.interactivebrokers.com/campus/ibkr-api-page/cpapi-v1/#validate-lst

[ibkr-tickle]: https://www.interactivebrokers.com/campus/ibkr-api-page/cpapi-v1/#tickle

[ibkr-initialize_brokerage_session]: https://www.interactivebrokers.com/campus/ibkr-api-page/cpapi-v1/#ssodh-init

[ibind-configuration]: ../configuration.md

[oauth2-access]: https://github.com/Voyz/ibind/pull/34#issuecomment-2630642031
