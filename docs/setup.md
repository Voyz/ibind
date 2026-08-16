# Setup

## Install

Use `pip` to install IBind in your project.

```posh
pip install ibind
```

For OAuth 1.0a support:

```posh
pip install ibind[oauth]
```

## Authentication

There currently are two ways you can authenticate with IBKR CP Web API:

1. Using Client Portal Gateway
1. Using OAuth 1.0a

Learn more about which to choose in the [Authentication][authentication] page.

## Core Functionality

IBind's core functionality consists of two client classes:

* [`IbkrClient`][ibkr-client-docs] - for [IBKR REST API][ibkr-endpoints]

  Using the `IbkrClient` requires constructing it with appropriate arguments, then calling the API methods.

* [`IbkrWsClient`][ibkr-ws-client-docs] - for [IBKR WebSocket API][ibkr-websockets]

  Using the `IbkrWsClient` involves handling three areas:

    * Managing its lifecycle. It is asynchronous and it will run on a separate thread, hence we need to construct it, start it and then manage its lifecycle on the originating thread.
    * Subscribing and unsubscribing. It is subscription-based, hence we need to specify which channels we want to subscribe to and remember to unsubscribe later.
    * Consuming data. It uses a queue system, hence we need to access these queues and consume their data.

Their usage differs substantially. Users are encouraged to familiarise themselves with the `IbkrClient` class first.

## Verify the Installation

Once you have an authenticated setup, verify the IBind installation by running:

```python
from ibind import IbkrClient

print(IbkrClient().tickle())
```

----

#### Next

To get started, familiarise yourself with the [Authentication][authentication].

Above code snippet expects the Gateway URL to be the default `https://localhost:5000/v1/api/`, which may not be the case in your setup. You can learn more about configuring this and other settings in [IBind Configuration][ibind-configuration].

[gateway]: https://www.interactivebrokers.com/docs/web-api/authentication/introduction#client-portal-gateway

[ibeam]: https://github.com/Voyz/ibeam

[authentication]: ./authentication.md

[ibkr-client-docs]: ./rest/ibkr_client.md

[ibkr-ws-client-docs]: ./websocket/overview.md

[ibkr-endpoints]: https://www.interactivebrokers.com/docs/web-api/v1/endpoints/introduction

[ibkr-websockets]: https://www.interactivebrokers.com/docs/web-api/v1/ws/introduction

[ibind-configuration]: ./configuration.md
