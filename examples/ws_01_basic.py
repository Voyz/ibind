import os

from ibind import IbkrWsKey, IbkrClient, IbkrWsClient, ibind_logs_initialize

ibind_logs_initialize(log_to_file=False)

account_id = os.getenv('IBIND_ACCOUNT_ID', '[YOUR_ACCOUNT_ID]')

client = IbkrClient(account_id=account_id)
ws_client = IbkrWsClient(ibkr_client=client, account_id=account_id)

ws_client.start()

qa = ws_client.new_queue_accessor(IbkrWsKey.ORDERS)

ws_client.subscribe(channel='or', data=None, needs_confirmation=False)

while True:
    try:
        while not qa.empty():
            print(str(qa), qa.get())

    except KeyboardInterrupt:
        print('KeyboardInterrupt')
        break

ws_client.unsubscribe(channel='or', data=None, needs_confirmation=False)

ws_client.shutdown()
