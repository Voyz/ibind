"""
WebSocket Intermediate

In this example we:

* Demonstrate subscription to multiple channels
* Utilise queue accessors
* Use the 'signal' module to ensure we unsubscribe and shutdown upon the program termination

Assumes the Gateway is deployed at 'localhost:5000' and the IBIND_ACCOUNT_ID and IBIND_CACERT environment variables have been set.
"""

import os
import signal
import time

from ibind import IbkrWsKey, IbkrWsClient, ibind_logs_initialize
from ibkr_ws_v2.ibkr_subscriptions import MarketDataSubscription, OrdersSubscription, AccountLedgerSubscription
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

md_sub = MarketDataSubscription(conid='265598')
or_sub = OrdersSubscription()
al_sub = AccountLedgerSubscription(account_id=account_id)

ws_client.subscribe(md_sub)
ws_client.subscribe(or_sub)
ws_client.subscribe(al_sub)

try:
    while ws_client.is_running():
        time.sleep(1)
except KeyboardInterrupt:
    print('Interrupt')

ws_client.unsubscribe(md_sub)
ws_client.unsubscribe(or_sub)
ws_client.unsubscribe(al_sub)
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