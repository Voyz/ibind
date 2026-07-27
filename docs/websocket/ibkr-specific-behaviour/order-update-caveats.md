# <a name="missing-order-updates"></a> Missing Order Updates

The data received through the 'orders' channel is affected by the calls to Live Orders endpoint. The [documentation][live-orders-endpoint] states:

> Please be aware that filtering orders using the /iserver/account/orders endpoint will prevent order details from coming through over the [websocket “sor” topic](https://www.interactivebrokers.com/campus/ibkr-api-page/cpapi-v1/#ws-order-updates-sub). To resolve this issue, developers should set “force=true” in a follow-up /iserver/account/orders call to clear any cached behavior surrounding the endpoint prior to calling for the websocket request.

What this implies:

* Calling `live_orders(filters=...)` will cause the 'orders' channel to stop receiving data.
* Importantly: this is true no matter when that call is made - before or after a subscription to the 'orders' channel.
* `live_orders(force=True)` must be called after each such request to clean the cache.
* It is recommended to call `live_orders(force=True)` prior to every order submission to attempt ensuring this server cache is cleared.
* It is also recommended to use `threading.Lock` to prevent placing orders and calling `live_orders(filters=...)` at the same time

How this could be implemented:
```python
class OrderHandler():

    def __init__(self, client: IbkrClient):
        self._client = client
        self._orders_lock = threading.Lock()

    def get_live_orders(self, filters):
        """
        Retrieves live orders from the brokerage and clears the orders cache.
        """
        with self._orders_lock:
            orders = self._client.live_orders(filters=filters)  # get the filtered orders
            self._client.live_orders(force=True)  # ensure the cache is cleared immediately
        return orders

    def place_order(self, order_request: OrderRequest, answers: Answers):
        """
        Clears the orders cache and submits an order to the brokerage.
        """
        with self._orders_lock:
            self._client.live_orders(force=True)  # ensure the cache is cleared prior to submission
            response = self._client.place_order(order_request, answers)
        return response
```

[live-orders-endpoint]: https://www.interactivebrokers.com/campus/ibkr-api-page/cpapi-v1/#live-orders
