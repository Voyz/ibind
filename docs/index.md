# IBind Documentation

IBind is an unofficial Python API client library for the [Interactive Brokers Client Portal Web API][ibkr-docs] (also known as Web API 1.0 or CPAPI 1.0). It provides comprehensive support for both REST and WebSocket APIs, enabling you to build automated trading systems, portfolio management tools, and market data applications. 

IBind wraps the IBKR Client Portal Web API with a REST API client (`IbkrClient`) for synchronous request/response operations like account management, order placement, contract searches, and data retrieval, and a WebSocket API client (`IbkrWsClient`) for asynchronous streaming of real-time market data, order updates, account changes, and PnL tracking. 

It supports fully headless authentication through OAuth 1.0a, eliminating the need for running additional gateway software, and includes advanced features like automated question/answer handling, parallel requests, rate limiting, subscription tracking, and health monitoring. IBind is designed for algorithmic traders building automated trading systems, quantitative researchers requiring programmatic access to IBKR data and execution, portfolio managers needing real-time account monitoring and order management, and developers integrating IBKR functionality into Python applications. You should be comfortable with Python and have an Interactive Brokers account (individual or institutional, live or paper). 

IBind provides comprehensive coverage of the IBKR Client Portal Web API 1.0, with almost all [IBKR REST API][ibkr-endpoints] endpoints mapped to `IbkrClient` methods (including session management, portfolio queries, contract searches, market data, order placement and management, historical data retrieval, and Financial Advisor operations), and full support for the [IBKR WebSocket API][ibkr-websocket] (including market data streaming, order status updates, trade notifications, account and portfolio updates, PnL tracking, and custom subscription management).

## Getting Started

### Quick Navigation

Start here
1. [Setup](setup.md) - install IBind and verify your installation
2. [Authentication](authentication.md) - choose between Client Portal Gateway or OAuth 1.0a
3. [Quickstart](quickstart.md) - get up and running in minutes

Working with the REST API
* [IbkrClient](rest/ibkr_client.md) - core REST client documentation
* [Configuration](configuration.md) - constructor parameters, environment variables, logging
* [Advanced REST](rest/advanced_rest.md) - question/answer handling, parallel requests, rate limiting

Working with the WebSocket API
* [WebSocket Overview](websocket/overview.md) - architecture and concepts
* [WebSocket Quickstart](websocket/quickstart.md) - minimal working example
* [Core Concepts](websocket/core-concepts/) - events, subscriptions, sinks, runtime lifecycle

Using OAuth 1.0a
* [OAuth 1.0a Setup](oauth/oauth_1a.md) - step-by-step guide to headless authentication
* [Advanced OAuth 1.0a](oauth/advanced_oauth_1a.md) - customisation and WebSocket usage

Examples
* [Examples folder][examples] - working code samples for common use cases

API Reference
* [API Reference](api_reference/index.md) - complete method documentation

Additional Resources
* [IBKR Compendium](ibkr_compendium.md) - community knowledge about IBKR quirks and behaviour

## Installation

```bash
pip install ibind
```

For OAuth 1.0a support:
```bash
pip install ibind[oauth]
```

## Basic Examples

### REST API Example
```python
from ibind import IbkrClient

client = IbkrClient()
print(client.check_health())
print(client.portfolio_accounts().data)
```

### WebSocket API Example
```python
from ibind import IbkrWsClient, IbkrWsKey

ws_client = IbkrWsClient(start=True)
ws_client.subscribe(channel=IbkrWsKey.PNL.channel)

while True:
    if not ws_client.empty(IbkrWsKey.PNL):
        print(ws_client.get(IbkrWsKey.PNL))
```

## Support and Contributing

* **Issues and bugs**: [GitHub Issues][issues]
* **Source code**: [GitHub Repository][github]
* **License**: [Apache 2.0][license]

## Disclaimer

IBind is not built, maintained, or endorsed by Interactive Brokers. Use at your own discretion. See the [full disclaimer][disclaimer] for details.

[ibkr-docs]: https://ibkrcampus.com/ibkr-api-page/cpapi-v1/
[ibkr-endpoints]: https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#endpoints
[ibkr-websocket]: https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#websockets
[examples]: https://github.com/Voyz/ibind/blob/master/examples
[issues]: https://github.com/Voyz/ibind/issues
[github]: https://github.com/Voyz/ibind
[license]: https://github.com/Voyz/ibind/blob/master/LICENSE
[disclaimer]: https://github.com/Voyz/ibind#disclaimer
