"""
WebSocket Intermediate

In this example we:

* Demonstrate subscription to multiple channels
* Utilise queue sink to receive events
* Use the 'signal' module to ensure we unsubscribe and shutdown upon the program termination

Assumes the Gateway is deployed at 'localhost:5000' and the IBIND_ACCOUNT_ID and IBIND_CACERT environment variables have been set.
"""

import os
import signal
import time
from typing import List

from ibind import events, IbkrWsClient, QueueSink, ibind_logs_initialize
from ibind.subscriptions import (
    MarketDataSubscription,
    OrdersSubscription,
    TradesSubscription,
    AccountSummarySubscription,
    AccountLedgerSubscription,
    PnlSubscription,
    SubscriptionHandle,
)

ibind_logs_initialize(log_to_file=False)

account_id = os.getenv('IBIND_ACCOUNT_ID', '[YOUR_ACCOUNT_ID]')
cacert = os.getenv('IBIND_CACERT', False)  # insert your cacert path here

# Create a queue sink to receive events
queue_sink = QueueSink()

ws_client = IbkrWsClient(cacert=cacert, account_id=account_id, sink=queue_sink)

ws_client.start()

# Create subscriptions
subs = [
    MarketDataSubscription(conid='265598', fields=['55', '71', '84', '86', '88', '85', '87', '7295', '7296', '70']),
    OrdersSubscription(),
    TradesSubscription(),
    AccountSummarySubscription(account_id=account_id),
    AccountLedgerSubscription(account_id=account_id),
    PnlSubscription(),
]

# Event types corresponding to each subscription
event_types = [
    events.MarketData,
    events.Orders,
    events.Trades,
    events.AccountSummary,
    events.AccountLedger,
    events.Pnl,
]

sub_handles: List[SubscriptionHandle] = []


def stop(_, _1):
    for handle in sub_handles:
        handle.unsubscribe().wait(timeout=10)

    ws_client.shutdown()


signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)

# Subscribe to all channels
for sub in subs:
    handle = ws_client.subscribe(sub)
    handle.wait()
    sub_handles.append(handle)

while ws_client.is_running():
    try:
        for event_type in event_types:
            while not queue_sink.empty(event_type):
                print(event_type.__name__, queue_sink.get(event_type))

        time.sleep(1)
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
        break

stop(None, None)
