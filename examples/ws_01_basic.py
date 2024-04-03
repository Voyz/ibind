import os
import time

import ibind
from ibind.client.ibkr_definitions import snapshot_keys_to_ids
from ibind import IbkrWsKey, IbkrClient, IbkrWsClient

ibind.logs.initialize(log_to_file=False)

account_id = os.getenv('IBKR_ACCOUNT_ID', '[YOUR_ACCOUNT_ID]')

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
