"""
WebSocket Basic

In this example we:

* Demonstrate the basic usage of the IbkrWsClient
* Subscribe to the PNL channel
* Wait for a new item. If there are no PnL reports there will be no data printed.

Assumes the Gateway is deployed at 'localhost:5000' and the IBIND_ACCOUNT_ID and IBIND_CACERT environment variables have been set.
"""

from ibind import events, IbkrWsClient, QueueSink
from ibind.subscriptions import PnlSubscription

# Create a queue sink to receive events
queue_sink = QueueSink()

# Construct the client. Assumes IBIND_ACCOUNT_ID and IBIND_CACERT environment variables have been set.
ws_client = IbkrWsClient(sink=queue_sink)

# Start the WebSocket client
ws_client.start()

# Create and subscribe to the PNL subscription
pnl_sub = PnlSubscription()
handle = ws_client.subscribe(pnl_sub)
handle.wait()

# Wait for new items in the PNL queue.
try:
    while ws_client.is_running():
        while not queue_sink.empty(events.Pnl):
            print(queue_sink.get(events.Pnl))
except KeyboardInterrupt:
    print('Interrupt')

# Unsubscribe and shutdown
handle.unsubscribe().wait()
ws_client.shutdown()
