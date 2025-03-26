"""
WebSocket Basic

In this example we:

* Demonstrate the basic usage of the IbkrWsClient
* Select the PNL WebSocket channel
* Subscribe to the PNL channel
* Wait for a new item. If there are no PnL reports there will be no data printed.

Assumes the Gateway is deployed at 'localhost:5000' and the IBIND_ACCOUNT_ID and IBIND_CACERT environment variables have been set.
"""

from ibind import IbkrWsKey, IbkrWsClient

# Construct the client. Assumes IBIND_ACCOUNT_ID and IBIND_CACERT environment variables have been set.
ws_client = IbkrWsClient(start=True)

# Choose the WebSocket channel
ibkr_ws_key = IbkrWsKey.PNL

# Subscribe to the PNL channel
ws_client.subscribe(channel=ibkr_ws_key.channel)

# Wait for new items in the PNL queue.
while True:
    while not ws_client.empty(ibkr_ws_key):
        print(ws_client.get(ibkr_ws_key))
