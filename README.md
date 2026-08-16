<p align="center">
    <a id="ibind" href="#ibind">
        <img src="https://raw.githubusercontent.com/Voyz/ibind/master/media/ibind_logo.png" alt="IBind logo" title="IBind logo" width="600"/>
    </a>
</p>
<p align="center">
    <a href="https://pypi.org/project/ibind">
      <img src="https://img.shields.io/pypi/pyversions/ibind.svg"/>
    </a>
    <a href="https://github.com/Voyz/ibind/releases">
        <img src="https://img.shields.io/pypi/v/ibind?label=version"/> 
    </a>
    <a href="https://opensource.org/licenses/Apache-2.0">
        <img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg"/>
    </a>
</p>

IBind is an unofficial Python API client library for the [Interactive Brokers Client Portal Web API.][ibkr-docs] (also known as Web API 1.0 or CPAPI 1.0) It supports both REST and WebSocket APIs of the IBKR Web API 1.0. Now fully headless with [OAuth 1.0a][wiki-oauth1a] support.

## Installation

```rich
pip install ibind
```

## Authentication

IBind supports fully headless authentication using [OAuth 1.0a][wiki-oauth1a]. This means no longer needing to run any type software to communicate with IBKR API.

Alternatively, use [IBeam][ibeam] along with this library for easier setup and maintenance of the CP Gateway.

See [Authentication][wiki-authentication] page to learn more.

## Documentation

See full [IBind documentation][wiki].

* [Installation][wiki-installation]
* [Authentication][wiki-authentication]
* [OAuth 1.0a][wiki-oauth1a]
* [IBind Configuration][wiki-ibind-configuration]
* [IbkrClient][wiki-ibkr-client] - REST Python client for [IBKR REST API][ibkr-endpoints].
* [IbkrWsClient][wiki-ibkr-ws-client] - WebSocket Python client for [IBKR WebSocket API][ibkr-websocket].
* [API Reference][api-ibkr-client]

Features:
* REST:
  * [Automated question/answer handling][wiki-question-answer]
  * [Parallel requests][wiki-parallel-requests]
  * [Rate limiting][wiki-rate-limiting]
  * [Conid unpacking][wiki-conid-unpacking]
  * [Financial Advisor model portfolios][api-fa-mixin]
  * [and more][wiki-advanced-api]
* WebSocket:
  * [Multi-threaded with async event propagation][wiki-ws-lifecycle]
  * [Typed, idempotent subscription interface][wiki-ws-subscriptions]
  * [Event-driven consumption sinks][wiki-ws-sinks]
  * [Automatic health monitoring and connection recovery][wiki-ws-health-monitoring]
  * [and more][wiki-advanced-websocket]

<a href="https://www.youtube.com/watch?v=34iHETvbdas">
    <img src="https://raw.githubusercontent.com/Voyz/voyz_public/master/ibind_promo_vidA_A01.gif" alt="IBind showcase gif" title="IBind showcase gif" width="500"/>
</a>

## Overview

IBind's core functionality consists of two client classes:

* [`IbkrClient`][ibkr-client-docs] - for [IBKR REST API][ibkr-endpoints]

  Using the `IbkrClient` requires constructing it with appropriate arguments, then calling the API methods.

* [`IbkrWsClientV2`][ibkr-ws-client-docs] - for [IBKR WebSocket API][ibkr-websocket]

  Using the `IbkrWsClientV2` involves handling three areas:

  * Managing its lifecycle. It is asynchronous and runs on separate internal threads, hence we need to construct it, start it, and manage it from the originating thread.
  * Subscribing and unsubscribing. It uses a typed subscription interface with idempotent semantics, allowing flexible subscription management.
  * Consuming data. It uses a sink-based pattern supporting callbacks, queues, or custom implementations for flexible event consumption.

Their usage differs substantially. Users are encouraged to familiarise themselves with the `IbkrClient` class first.

## Examples

See [all examples][examples].

### Basic REST Example

```python
from ibind import IbkrClient

# Construct the client
client = IbkrClient()

# Call some endpoints
print('\n#### check_health ####')
print(client.check_health())

print('\n\n#### tickle ####')
print(client.tickle().data)

print('\n\n#### get_accounts ####')
print(client.portfolio_accounts().data)
```

### Basic WebSocket Example

```python
from ibind import QueueSink, IbkrWsClientV2, events
from ibind.subscriptions import PnlSubscription

# Create a queue-based event sink
sink = QueueSink()

# Construct and start the client
ws_client = IbkrWsClientV2(account_id='[YOUR_ACCOUNT_ID]', sink=sink)
ws_client.start()

# Subscribe to PnL updates
ws_client.subscribe(PnlSubscription())

# Consume PnL events
while True:
    while not sink.empty(events.Pnl):
        event = sink.get(events.Pnl)
        print(event)

ws_client.shutdown()
```


## Licence

See [LICENSE](https://github.com/Voyz/ibind/blob/master/LICENSE)

## Disclaimer

IBind is not built, maintained, or endorsed by the Interactive Brokers.

Use at own discretion. IBind and its authors give no guarantee of uninterrupted run of and access to the Interactive
Brokers Client Portal Web API. You should prepare for breaks in connectivity to IBKR servers and should not
depend on continuous uninterrupted connection and functionality. To partially reduce the potential risk use Paper Account credentials.

IBind is provided on an AS IS and AS AVAILABLE basis without any representation or endorsement made and without warranty
of any kind whether express or implied, including but not limited to the implied warranties of satisfactory quality,
fitness for a particular purpose, non-infringement, compatibility, security and accuracy. To the extent permitted by
law, IBind's authors will not be liable for any indirect or consequential loss or damage whatever (including without
limitation loss of business, opportunity, data, profits) arising out of or in connection with the use of IBind. IBind's
authors make no warranty that the functionality of IBind will be uninterrupted or error free, that defects will be
corrected or that IBind or the server that makes it available are free of viruses or anything else which may be harmful
or destructive.

## Acknowledgement

IBind has been enriched by incorporating work developed in collaboration with  [Kinetic](https://www.kinetic.xyz/) and [Grant Stenger](https://github.com/GrantStenger), which now forms part of the initial open-source release. I appreciate their significant contribution to this community-driven initiative. Cheers Kinetic! 🍻

## Built by Voy

Hi! Thanks for checking out and using this library. 

If you are in need of some help with your project and would like to hire me, or just wanna chat about trading - I'm happy to talk. 

You can contact me through: https://voyzan.com

Or if you'd just want to give something back, I've got a Buy Me A Coffee account:

<a href="https://www.buymeacoffee.com/voyzan" rel="nofollow">
    <img src="https://raw.githubusercontent.com/Voyz/voyz_public/master/vz_BMC.png" alt="Buy Me A Coffee" style="max-width:100%;" width="192">
</a>

Thanks and have an awesome day 👋


[ibeam]: https://github.com/Voyz/ibeam
[examples]: https://github.com/Voyz/ibind/blob/master/examples
[issues]: https://github.com/Voyz/ibind/issues
[api-ibkr-client]: ./docs/api_reference/ibkr_client.md
[api-fa-mixin]: ./docs/api_reference/ibkr_client.md#famixin
[ibkr-client-docs]: ./docs/rest/ibkr_client.md
[ibkr-ws-client-docs]: ./docs/websocket/overview.md

[ibkr-docs]: https://ibkrcampus.com/ibkr-api-page/cpapi-v1/
[ibkr-endpoints]: https://www.interactivebrokers.com/docs/web-api/v1/endpoints/introduction
[ibkr-websocket]: https://www.interactivebrokers.com/docs/web-api/v1/ws/introduction


[wiki]: ./docs/index.md
[wiki-installation]: ./docs/setup.md
[wiki-authentication]: ./docs/authentication.md
[wiki-oauth1a]: ./docs/oauth/oauth_1a.md
[wiki-ibind-configuration]: ./docs/configuration.md
[wiki-ibkr-client]: ./docs/rest/ibkr_client.md
[wiki-ibkr-ws-client]: ./docs/websocket/overview.md

[wiki-question-answer]: ./docs/rest/ibkr_client.md#-place_order
[wiki-parallel-requests]: ./docs/rest/ibkr_client.md#-marketdata_history_by_symbols
[wiki-rate-limiting]: ./docs/rest/ibkr_client.md#-marketdata_history_by_symbols
[wiki-conid-unpacking]: ./docs/rest/ibkr_client.md#-security_stocks_by_symbol
[wiki-advanced-api]: ./docs/rest/ibkr_client.md#advanced-api

[wiki-ws-lifecycle]: ./docs/websocket/overview.md#-managing-the-lifecycle
[wiki-ws-sinks]: ./docs/websocket/overview.md#-consuming-data
[wiki-ws-subscriptions]: ./docs/websocket/overview.md#-subscribing-and-unsubscribing
[wiki-ws-health-monitoring]: ./docs/websocket/overview.md#health-monitoring
[wiki-advanced-websocket]: ./docs/websocket/overview.md
