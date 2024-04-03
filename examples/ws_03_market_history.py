import os
import signal
import time

import ibind
from ibind import IbkrSubscriptionProcessor, IbkrWsKey, IbkrClient, IbkrWsClient

ibind.logs.initialize(log_to_file=False)

account_id = os.getenv('IBKR_ACCOUNT_ID', '[YOUR_ACCOUNT_ID]')
cacert = os.getenv('IBKR_CACERT', None) # insert your cacert path here
client = IbkrClient(
    url='https://localhost:5000/v1/api/',
    account_id=account_id,
    cacert=cacert,
)

ws_client = IbkrWsClient(
    ibkr_client=client,
    account_id=account_id,
    url='wss://localhost:5000/v1/api/ws',
    cacert=cacert,
)


# override the default subscription processor since we need to use the server id instead of conid
class IbkrMarketHistorySubscriptionProcessor(IbkrSubscriptionProcessor):  # pragma: no cover
    def make_unsubscribe_payload(self, channel: str, server_id: dict = None) -> str:
        return f'umh+{server_id}'


subscription_processor = IbkrMarketHistorySubscriptionProcessor()


def unsubscribe():
    # loop all server ids for market history and attempt to unsubscribe
    for server_id, conid in ws_client.server_ids(IbkrWsKey.MARKET_HISTORY).items():
        channel = 'mh'
        needs_confirmation = False

        if conid != None:  # if we know the conid let's try to confirm the unsubscription
            channel += f'+{conid}'
            needs_confirmation = True

        confirmed = ws_client.unsubscribe(channel, server_id, needs_confirmation, subscription_processor)

        print(f'Unsubscribing channel {channel!r} from server {server_id!r}: {"unconfirmed" if confirmed == False else "confirmed"}.')


request = {
    'channel': 'mh+265598',
    'data': {"period": '1min', 'bar': '1min', 'outsideRTH': True, 'source': 'trades', "format": "%o/%c/%h/%l"},
    'needs_confirmation': True
}

ws_client.start()

qa = ws_client.new_queue_accessor(IbkrWsKey.MARKET_HISTORY)

def stop(_, _1):
    unsubscribe()
    ws_client.shutdown()


signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)

while not ws_client.subscribe(**request):
    time.sleep(1)

while ws_client.running:
    try:
        while not qa.empty():
            print(str(qa), qa.get())

        time.sleep(1)
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
        break

ws_client.shutdown()
