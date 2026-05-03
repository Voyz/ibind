"""
WebSocket Intermediate

In this example we:

* Demonstrate subscription to multiple channels
* Utilise queue accessors
* Use the 'signal' module to ensure we unsubscribe and shutdown upon the program termination

Assumes the Gateway is deployed at 'localhost:5000' and the IBIND_ACCOUNT_ID and IBIND_CACERT environment variables have been set.
"""

import os
import time
from typing import List

from ibind import events, IbkrWsClientV2, LogSink, QueueSink, CallbackSink, CompositeSink, ibind_logs_initialize
from ibind.subscriptions import MarketDataSubscription, OrdersSubscription, AccountLedgerSubscription, AccountSummarySubscription, PnlSubscription, TradesSubscription, MarketHistorySubscription, SubscriptionHandle

ibind_logs_initialize(log_to_file=False, log_level='DEBUG')

account_id = os.getenv('IBIND_ACCOUNT_ID', '[YOUR_ACCOUNT_ID]')
cacert = os.getenv('IBIND_CACERT', False)  # insert your cacert path here

# Queue Sink - queue-based event consumer
queue_sink = QueueSink()

# Callback Sink - callback-based event consumer
callback_sink = CallbackSink()


def on_market_data(event: events.MarketData):
    print(event)

def on_market_history(event: events.MarketHistory):
    print(event)

def on_lifecycle(event: events.LifecycleEvent):
    print(event)

callback_sink.on(events.MarketData, on_market_data)
callback_sink.on(events.MarketHistory, on_market_data)
callback_sink.on(events.WsOpen, on_lifecycle)
callback_sink.on(events.WsClose, on_lifecycle)
callback_sink.on(events.WsError, on_lifecycle)
callback_sink.on(events.WsAuthenticated, on_lifecycle)
callback_sink.on(events.WsReady, on_lifecycle)
callback_sink.on(events.WsDegraded, on_lifecycle)

# Log Sink - useful for debugging
log_sink = LogSink()

# Composite Sink - allows us to use all above sinks at once
composite_sink = CompositeSink(callback_sink, log_sink)

# ws_client = IbkrWsClient(cacert=cacert, account_id=account_id)
# ws_client = IbkrWsClientV2(cacert=cacert, account_id=account_id, sink=LogSink())
ws_client = IbkrWsClientV2(cacert=cacert, account_id=account_id, sink=composite_sink)


ws_client.start()

as_sub = AccountSummarySubscription(account_id=account_id)
al_sub = AccountLedgerSubscription(account_id=account_id)
md_sub = MarketDataSubscription(conid='265598', fields=("31", "84", "86"), expiry_seconds=30)
mh_sub = MarketHistorySubscription(conid='265598')
or_sub = OrdersSubscription()
# pl_sub = PriceLadderSubscription(conid='265598', account_id=account_id, exchange='SMART')
pnl_sub = PnlSubscription()
tr_sub = TradesSubscription()
subs = [
    # as_sub,
    # al_sub,
    md_sub,
    # mh_sub,
    # or_sub,
    # pnl_sub,
    # tr_sub
]

sub_handles: List[SubscriptionHandle] = []
for sub in subs:
    handle = ws_client.subscribe(sub)
    handle.wait()
    sub_handles.append(handle)

for handle in sub_handles:
    success = handle.wait(timeout=10)
    if not success:
        print('Subscription not active within 10 seconds')

try:
    while ws_client.is_running():
        for sub in subs:
            while not queue_sink.empty(sub.event_type):
                ev = queue_sink.get(sub.event_type)
                print(ev)

        time.sleep(1)
except KeyboardInterrupt:
    print('Interrupt')

for handle in sub_handles:
    unsub_handle = handle.unsubscribe()
    success = unsub_handle.wait(timeout=10)
    if not success:
        print('Subscription not unsubscribed within 10 seconds')

# unsub_handles = []
# for sub in subs:
#     handle = ws_client.unsubscribe(sub)
#     unsub_handles.append(handle)
#
# for handle in unsub_handles:
#     handle.wait(10)

ws_client.shutdown()
