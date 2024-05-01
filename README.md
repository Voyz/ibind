*This library is currently being developed. See something that's broken? Did we get something
wrong? [Create an issue and let us know!][issues]*



<p align="center">
    <a id="ibind" href="#ibind">
        <img src="https://github.com/Voyz/ibind/blob/master/media/ibind_logo.png" alt="IBind logo" title="IBind logo" width="600"/>
    </a>
</p>
<p align="center">
    <a href="https://opensource.org/licenses/Apache-2.0">
        <img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg"/>
    </a>
    <a href="https://github.com/Voyz/ibind/releases">
        <img src="https://img.shields.io/pypi/v/ibind?label=version"/> 
    </a>
</p>

IBind is a REST and WebSocket client library for [Interactive Brokers Client Portal Web API.][ibkr-docs]

## Installation

```rich
pip install ibind
```

Use [IBeam][ibeam] along with this library for easier authentication with IBKR.

## NOTICE
### This library is a work in progres. I haven't published it yet. Many things are due to change without any notice. 

## Documentation

See full [IBind documentation][wiki].

* [Installation][wiki-installation]
* [Basic Concepts][wiki-basic-concepts]
* [IBind Configuration][wiki-ibind-configuration]
* [IbkrClient][wiki-ibkr-client] - REST Python client for [IBKR REST API][ibkr-endpoints].
* [IbkrWsClient][wiki-ibkr-ws-client] - WebSocket Python client for [IBKR WebSocket API][ibkr-websocket].

Features:
* REST:
  * [Automated question/answer handling][wiki-question-answer]
  * [Parallel requests][wiki-parallel-requests]
  * [Rate limiting][wiki-rate-limiting]
  * [Conid unpacking][wiki-conid-unpacking]
  * [and more][wiki-advanced-api]
* WebSocket:
  * [WebSocket thread lifecycle handling][wiki-ws-lifecycle]
  * [Thread-safe Queue data stream][wiki-ws-queues]
  * [Internal subscription tracking][wiki-ws-subscriptions]
  * [Health monitoring][wiki-ws-health-monitoring]
  * [and more][wiki-advanced-websocket]


## Examples

See [all examples][examples]

### 01 IbkrClient basic

```python
import warnings

from ibind import IbkrClient

warnings.filterwarnings("ignore", message="Unverified HTTPS request is being made to host 'localhost'")

c = IbkrClient(url='https://localhost:5000/v1/api/')

print('\n#### check_health ####')
print(c.check_health())

print('\n\n#### tickle ####')
print(c.tickle().data)

print('\n\n#### get_accounts ####')
print(c.portfolio_accounts().data)
```

### 02 IbkrClient intermediate

```python
import var

from ibind import IbkrClient, ibind_logs_initialize

ibind_logs_initialize()

c = IbkrClient(
    url='https://localhost:5000/v1/api/',
    cacert=var.IBIND_CACERT,
)

print('\n#### get_accounts ####')
accounts = c.portfolio_accounts().data
c.account_id = accounts[0]['accountId']
print(accounts)

print('\n\n#### get_ledger ####')
ledger = c.get_ledger().data
for currency, subledger in ledger.items():
    print(f'\t Ledger currency: {currency}')
    print(f'\t cash balance: {subledger["cashbalance"]}')
    print(f'\t net liquidation value: {subledger["netliquidationvalue"]}')
    print(f'\t stock market value: {subledger["stockmarketvalue"]}')
    print()

print('\n#### get_positions ####')
positions = c.positions().data
for position in positions:
    print(f'\t Position {position["ticker"]}: {position["position"]} (${position["mktValue"]})')
```

### IbkrWsClient basic

```python
import os
import time


from ibind.client.ibkr_definitions import snapshot_keys_to_ids
from ibind import IbkrWsKey, IbkrClient, IbkrWsClient, ibind_logs_initialize

ibind_logs_initialize(log_to_file=False)

account_id = os.getenv('IBIND_ACCOUNT_ID', '[YOUR_ACCOUNT_ID]')

client = IbkrClient(
    account_id=account_id,
    url='https://localhost:5000/v1/api/',
)

ws_client = IbkrWsClient(
    ibkr_client=client,
    account_id=account_id,
    url='wss://localhost:5000/v1/api/ws'
)

ws_client.start()
channel = 'md+265598'
fields = [str(x) for x in snapshot_keys_to_ids(['symbol', 'open', 'high', 'low', 'close', 'volume',])]

qa = ws_client.new_queue_accessor(IbkrWsKey.MARKET_DATA)

ws_client.subscribe(channel, {'fields': fields}, needs_confirmation=False)

while ws_client.running:
    try:
        while not qa.empty():
            print(str(qa), qa.get())

        time.sleep(1)
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
        break

ws_client.unsubscribe(channel, {'fields': fields}, needs_confirmation=False)

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

Hi! Thanks for checking out and using this library. If you are interested in discussing your project, require
mentorship, consider hiring me, or just wanna chat - I'm happy to talk.

You can email me to get in touch: hello@voyzan.com

Or if you'd just want to give something back, I've got a Buy Me A Coffee account:

<a href="https://www.buymeacoffee.com/voyzan" rel="nofollow">
    <img src="https://raw.githubusercontent.com/Voyz/voyz_public/master/vz_BMC.png" alt="Buy Me A Coffee" style="max-width:100%;" width="192">
</a>

Thanks and have an awesome day 👋


[ibeam]: https://github.com/Voyz/ibeam
[examples]: https://github.com/Voyz/ibind/blob/master/examples
[issues]: https://github.com/Voyz/ibind/issues

[ibkr-docs]: https://ibkrcampus.com/ibkr-api-page/webapi-doc/
[ibkr-endpoints]: https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#endpoints
[ibkr-websocket]: https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#websockets

[wiki]: https://github.com/Voyz/ibind/wiki
[wiki-installation]: https://github.com/Voyz/ibind/wiki/Installation
[wiki-basic-concepts]: https://github.com/Voyz/ibind/wiki/Basic-Concepts
[wiki-ibind-configuration]: https://github.com/Voyz/ibind/wiki/IBind-Configuration
[wiki-ibkr-client]: https://github.com/Voyz/ibind/wiki/Ibkr-Client
[wiki-ibkr-ws-client]: https://github.com/Voyz/ibind/wiki/Ibkr-Ws-Client

[wiki-question-answer]: https://github.com/Voyz/ibind/wiki/Ibkr-Client#-place_order
[wiki-parallel-requests]: https://github.com/Voyz/ibind/wiki/Ibkr-Client#-marketdata_history_by_symbols
[wiki-rate-limiting]: https://github.com/Voyz/ibind/wiki/Ibkr-Client#-marketdata_history_by_symbols
[wiki-conid-unpacking]: https://github.com/Voyz/ibind/wiki/Ibkr-Client#-security_stocks_by_symbol
[wiki-advanced-api]: https://github.com/Voyz/ibind/wiki/Ibkr-Client#advanced-api

[wiki-ws-lifecycle]: https://github.com/Voyz/ibind/wiki/Ibkr-Ws-Client#-managing-the-lifecycle
[wiki-ws-queues]: https://github.com/Voyz/ibind/wiki/Ibkr-Ws-Client#-consuming-data
[wiki-ws-subscriptions]: https://github.com/Voyz/ibind/wiki/Ibkr-Ws-Client#-subscribing-and-unsubscribing
[wiki-ws-health-monitoring]: https://github.com/Voyz/ibind/wiki/Ibkr-Ws-Client#health-monitoring
[wiki-advanced-websocket]: https://github.com/Voyz/ibind/wiki/Advanced-WebSocket
