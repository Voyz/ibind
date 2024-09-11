"""
WebSocket Market Data History

In this example we:

* Create a custom SubscriptionProcessor that overrides the default make_unsubscribe_payload method to use the server id instead of the conid
* Use a custom unsubscribe method to iterate over all server ids for market history and attempt to unsubscribe
* Demonstrate using the Market Data History channel
* Use the 'signal' module to ensure we unsubscribe and shutdown upon the program termination

Assumes the Gateway is deployed at 'localhost:5000' and the IBIND_ACCOUNT_ID and IBIND_CACERT environment variables have been set.
"""

import os
import signal
import time

from ibind import IbkrSubscriptionProcessor, IbkrWsKey, IbkrWsClient, ibind_logs_initialize
from ibind.client.ibkr_ws_client import IbkrSubscription

ibind_logs_initialize(log_to_file=False)

cacert = os.getenv('IBIND_CACERT', False)  # insert your cacert path here

ws_client = IbkrWsClient(cacert=cacert)


# override the default subscription processor since we need to use the server id instead of conid
class MhSubscriptionProcessor(IbkrSubscriptionProcessor):  # pragma: no cover
    def make_unsubscribe_payload(self, channel: str, data: dict = None) -> str:
        return f'umh+{data['params']["server_id"]}'


subscription_processor = MhSubscriptionProcessor()


def unsubscribe():
    # loop all server ids for market history and attempt to unsubscribe
    channel = IbkrWsKey.MARKET_HISTORY
    for server_id, conid in ws_client.server_ids(channel).items():
        needs_confirmation = conid != None # if we know the conid let's try to confirm the unsubscription

        confirmed = ws_client.unsubscribe(channel, conid, {'server_id': server_id}, needs_confirmation, subscription_processor)

        print(f'Unsubscribing channel {channel!r} from server {server_id!r}: {"unconfirmed" if confirmed == False else "confirmed"}.')


request = {
    'channel': IbkrWsKey.MARKET_HISTORY,
    'conid': 265598,
    'params': {"period": '1min', 'bar': '1min', 'outsideRTH': True, 'source': 'trades', "format": "%o/%c/%h/%l"}
}

ws_client.start()

qa = ws_client.new_queue_accessor(request['channel'])


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
