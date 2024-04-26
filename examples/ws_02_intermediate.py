import os
import signal
import time

from ibind import IbkrWsKey, IbkrClient, IbkrWsClient, ibind_logs_initialize

ibind_logs_initialize(log_to_file=False)

account_id = os.getenv('IBIND_ACCOUNT_ID', '[YOUR_ACCOUNT_ID]')
cacert = os.getenv('IBIND_CACERT', False) # insert your cacert path here

client = IbkrClient(account_id=account_id, cacert=cacert)

ws_client = IbkrWsClient(
    ibkr_client=client,
    account_id=account_id,
    cacert=cacert,
)

ws_client.start()

requests = [
    {'channel': 'md+265598', 'data': {"fields": ['55', '71', '84', '86', '88', '85', '87', '7295', '7296', '70']}, 'needs_confirmation': False},
    {'channel': 'or', 'data': None, 'needs_confirmation': False},
    {'channel': 'tr', 'data': None, 'needs_confirmation': False},
]
queue_accessors = [
    ws_client.new_queue_accessor(IbkrWsKey.TRADES),
    ws_client.new_queue_accessor(IbkrWsKey.MARKET_DATA),
    ws_client.new_queue_accessor(IbkrWsKey.ORDERS),
]


def stop(_, _1):
    for request in requests:
        ws_client.unsubscribe(**request)

    ws_client.shutdown()


signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)

for request in requests:
    while not ws_client.subscribe(**request):
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

ws_client.shutdown()
