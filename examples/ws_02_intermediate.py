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

ibind_logs_initialize(log_to_file=False)

account_id = os.getenv('IBIND_ACCOUNT_ID', '[YOUR_ACCOUNT_ID]')
cacert = os.getenv('IBIND_CACERT', False)  # insert your cacert path here

ws_client = IbkrWsClient(cacert=cacert, account_id=account_id)

ws_client.start()

subscriptions = [
    {'channel': IbkrWsKey.MARKET_DATA, 'conid': 265598, 'params': {"fields": ['55', '71', '84', '86', '88', '85', '87', '7295', '7296', '70']}},
    {'channel': IbkrWsKey.ORDERS},
    {'channel': IbkrWsKey.TRADES},
    {'channel': IbkrWsKey.ACCOUNT_SUMMARY, 'conid': account_id},
    {'channel': IbkrWsKey.ACCOUNT_LEDGER, 'conid': account_id},
    {'channel': IbkrWsKey.PNL},
]
queue_accessors = [ws_client.new_queue_accessor(subscription['channel']) for subscription in subscriptions]


def stop(_, _1):
    for subscription in subscriptions:
        if ws_client.running:
            ws_client.unsubscribe(**subscription)

    ws_client.shutdown()


signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)

for subscription in subscriptions:
    while not ws_client.subscribe(**subscription):
        time.sleep(1)

while ws_client.running:
    try:
        for qa in queue_accessors:
            while not qa.empty():
                print(str(qa), qa.get())

        time.sleep(1)
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
        break

stop(None, None)
