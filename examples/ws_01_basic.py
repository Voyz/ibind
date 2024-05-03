"""
WebSocket Basic

In this example we:

* Demonstrate the basic usage of the IbkrWsClient
* Acquire a QueueAccessor for Orders channel
* Subscribe to the Orders channel
* Wait for a new order. If there are no orders being created there will be no data printed.
* Upon a KeyboardInterrupt we unsubscribe from the Orders channel and shutdown the client
"""
from ibind import IbkrWsKey, IbkrClient, IbkrWsClient, ibind_logs_initialize

# Initialise the logger
ibind_logs_initialize(log_to_file=False)

# Construct the client
ws_client = IbkrWsClient()

# Start the WebSocket worker thread
ws_client.start()

# Acquire a QueueAccessor for the Orders channel
qa = ws_client.new_queue_accessor(IbkrWsKey.ORDERS)

# Subscribe to the Orders channel
ws_client.subscribe(channel='or', data=None, needs_confirmation=False)

# Wait for new items in the Orders queue.
while True:
    try:
        while not qa.empty():
            print(str(qa), qa.get())

    except KeyboardInterrupt:
        print('KeyboardInterrupt')
        break

# Unsubscribe from the Orders channel and shutdown the client
ws_client.unsubscribe(channel='or', data=None, needs_confirmation=False)

ws_client.shutdown()
