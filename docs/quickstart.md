# Quickstart

Get up and running with IBind in minutes.

## Prerequisites

- Python 3.10+
- IBind installed: `pip install ibind`
- IBKR Client Portal Gateway running (or OAuth 1.0a credentials configured)

See [Authentication][wiki-authentication] for setup details.

## REST API (IbkrClient)

### 1. Create a client

```python
from ibind import IbkrClient

client = IbkrClient()
```

### 2. Check connectivity

```python
# Verify the connection is working
print(client.check_health())
```

If this succeeds, your authentication is valid and the gateway is reachable.

### 3. Make a simple request

```python
# Fetch your accounts
accounts = client.portfolio_accounts()
print(accounts.data)
```

That's it - you can now call any [IbkrClient method][wiki-ibkr-client] to interact with the IBKR REST API.

## WebSocket API (IbkrWsClient)

If you need real-time streaming data (market data, account updates, etc.), use the WebSocket client:

```python
from ibind import IbkrWsClient, QueueSink, events
from ibind.subscriptions import PnlSubscription

# Create a queue-based event sink
sink = QueueSink()

# Create and start the WebSocket client
ws_client = IbkrWsClient(sink=sink)
ws_client.start()

# Subscribe to a topic (eg. account PnL updates)
ws_client.subscribe(PnlSubscription())

# Consume events from the queue
while True:
    while not sink.empty(events.Pnl):
        print(sink.get(events.Pnl))
```

See [WebSocket Client Quickstart][wiki-ws-quickstart] for a step-by-step walkthrough, or [IbkrWsClient][wiki-ibkr-ws-client] for full details on lifecycle, subscriptions, and data consumption.

----
#### Next

- See the [examples][examples] folder for more realistic workflows.
- Check [IbkrClient][wiki-ibkr-client] for all available methods.
- Read [IbkrWsClient][wiki-ibkr-ws-client] for streaming data.
- Learn about [IBind Configuration][wiki-ibind-configuration] for advanced setup.

[wiki-authentication]: ./authentication.md
[wiki-ibkr-client]: ./rest/ibkr_client.md
[wiki-ibkr-ws-client]: ./websocket/overview.md
[wiki-ws-quickstart]: ./websocket/quickstart.md
[wiki-ibind-configuration]: ./configuration.md
[examples]: https://github.com/Voyz/ibind/blob/master/examples
