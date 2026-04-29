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

from ibind import ibind_logs_initialize
from ibkr_ws_v2.ibkr_subscriptions import MarketDataSubscription, OrdersSubscription, AccountLedgerSubscription, AccountSummarySubscription, PriceLadderSubscription, PnlSubscription, TradesSubscription
from ibkr_ws_v2.ibkr_ws_client_v2 import IbkrWsClientV2

ibind_logs_initialize(log_to_file=False, log_level='DEBUG')

account_id = os.getenv('IBIND_ACCOUNT_ID', '[YOUR_ACCOUNT_ID]')
cacert = os.getenv('IBIND_CACERT', False)  # insert your cacert path here

# ws_client = IbkrWsClient(cacert=cacert, account_id=account_id)
ws_client = IbkrWsClientV2(cacert=cacert, account_id=account_id)

# def stop(_, _1):
#     print('exit')
#     ws_client.shutdown()
#     print('done')
#     return False
#
# signal.signal(signal.SIGINT, stop)
# signal.signal(signal.SIGTERM, stop)

ws_client.start()

as_sub = AccountSummarySubscription(account_id=account_id)
al_sub = AccountLedgerSubscription(account_id=account_id)
md_sub = MarketDataSubscription(conid='265598', fields=("31", "84", "86"))
or_sub = OrdersSubscription()
# pl_sub = PriceLadderSubscription(conid='265598', account_id=account_id, exchange='SMART')
pnl_sub = PnlSubscription()
tr_sub = TradesSubscription()
subs = [
    as_sub,
    al_sub,
    md_sub,
    or_sub,
    pnl_sub,
    tr_sub
]

for sub in subs:
    ws_client.subscribe(sub)

try:
    while ws_client.is_running():
        time.sleep(1)
except KeyboardInterrupt:
    print('Interrupt')

for sub in subs:
    ws_client.unsubscribe(sub)
# time.sleep(5)
ws_client.shutdown()

# requests = [
#     {'channel': 'md+265598', 'data': {'fields': ['55', '71', '84', '86', '88', '85', '87', '7295', '7296', '70']}},
#     {'channel': 'or'},
#     {'channel': 'tr'},
#     {'channel': f'sd+{account_id}'},
#     {'channel': f'ld+{account_id}'},
#     {'channel': 'pl'},
# ]
#
#
#

#
# for request in requests:
#     while not ws_client.subscribe(**request):
#         time.sleep(1)
#
# while ws_client.running:
#     try:
#         for qa in queue_accessors:
#             while not qa.empty():
#                 print(str(qa), qa.get())
#
#         time.sleep(1)
#     except KeyboardInterrupt:
#         print('KeyboardInterrupt')
#         break
#
# stop(None, None)