# Table of Contents

* [order\_mixin](#client.ibkr_client_mixins.order_mixin)
  * [OrderMixin](#client.ibkr_client_mixins.order_mixin.OrderMixin)
    * [live\_orders](#client.ibkr_client_mixins.order_mixin.OrderMixin.live_orders)
    * [order\_status](#client.ibkr_client_mixins.order_mixin.OrderMixin.order_status)
    * [trades](#client.ibkr_client_mixins.order_mixin.OrderMixin.trades)
    * [place\_order](#client.ibkr_client_mixins.order_mixin.OrderMixin.place_order)
    * [reply](#client.ibkr_client_mixins.order_mixin.OrderMixin.reply)
    * [whatif\_order](#client.ibkr_client_mixins.order_mixin.OrderMixin.whatif_order)
    * [cancel\_order](#client.ibkr_client_mixins.order_mixin.OrderMixin.cancel_order)
    * [modify\_order](#client.ibkr_client_mixins.order_mixin.OrderMixin.modify_order)
    * [suppress\_messages](#client.ibkr_client_mixins.order_mixin.OrderMixin.suppress_messages)
    * [reset\_suppressed\_messages](#client.ibkr_client_mixins.order_mixin.OrderMixin.reset_suppressed_messages)

<a id="client.ibkr_client_mixins.order_mixin.OrderMixin"></a>

## OrderMixin

* https://www.interactivebrokers.com/docs/web-api/v1/endpoints/order-monitoring
* https://www.interactivebrokers.com/docs/web-api/v1/endpoints/orders

<a id="client.ibkr_client_mixins.order_mixin.OrderMixin.live_orders"></a>

### live\_orders

```python
@ensure_list_arg('filters')
def live_orders(filters: OneOrMany[str] = None,
                force: bool = None,
                account_id: str = None) -> Result
```

Retrieves live orders with optional filtering. The filters, if provided, should be a list of strings. These filters are then converted and sent as a comma-separated string in the request to the API.

Arguments:

- `filters` _List[str], optional_ - A list of strings representing the filters to be applied. Defaults to None
- `force` _bool, optional_ - Force the system to clear saved information and make a fresh request for orders. Submission will appear as a blank array. Defaults to False.
- `account_id` _str_ - For linked accounts, allows users to view orders on sub-accounts as specified.
  
  Available filter values:
  
  * `inactive`: The order is inactive and is not yet transmitted.
  * `pending_submit`: Order was received by the system but is no longer active because it was rejected or cancelled.
  * `pre_submitted`: Order has been transmitted but have not received confirmation yet that order accepted by destination exchange or venue.
  * `submitted`: Order has been accepted by the system.
  * `filled`: Order has been completely filled.
  * `pending_cancel`: Sent an order cancellation request but have not yet received confirmation order cancelled by destination exchange or venue.
  * `cancelled`: The balance of your order has been confirmed canceled by the system.
  * `warn_state`: Order has a specific warning message such as for basket orders.
  * `sort_by_time`: There is an initial sort by order state performed so active orders are always above inactive and filled then orders are sorted chronologically.
  

Notes:

  - This endpoint requires a pre-flight request. Orders is the list of live orders (cancelled, filled, submitted).
  - To retrieve order information for a specific account, clients must first query the /iserver/account endpoint to switch to the appropriate account.
  - Please be aware that filtering orders using the /iserver/account/orders endpoint will prevent order details from coming through over the websocket �sor� topic. To resolve this issue, developers should set �force=true� in a follow-up /iserver/account/orders call to clear any cached behavior surrounding the endpoint prior to calling for the websocket request.

<a id="client.ibkr_client_mixins.order_mixin.OrderMixin.order_status"></a>

### order\_status

```python
def order_status(order_id: str) -> Result
```

Retrieve the given status of an individual order using the orderId returned by the order placement response or the orderId available in the live order response.

Arguments:

- `order_id` _str_ - Order identifier for the placed order. Returned by the order placement response or the order_id available in the live order response.

<a id="client.ibkr_client_mixins.order_mixin.OrderMixin.trades"></a>

### trades

```python
def trades(days: str = None, account_id: str = None) -> Result
```

Returns a list of trades for the currently selected account for current day and six previous days. It is advised to call this endpoint once per session.

Arguments:

- `days` _str_ - Specify the number of days to receive executions for, up to a maximum of 7 days. If unspecified, only the current day is returned.
- `account_id` _str_ - Include a specific account identifier or allocation group to retrieve trades for.

<a id="client.ibkr_client_mixins.order_mixin.OrderMixin.place_order"></a>

### place\_order

```python
@ensure_list_arg('order_request')
def place_order(order_request: OneOrMany[OrderRequest],
                answers: Answers,
                account_id: str = None) -> Result
```

When connected to an IServer Brokerage Session, this endpoint will allow you to submit orders.

Notes:

  - With the exception of OCA groups and bracket orders, the orders endpoint does not currently support the placement of unrelated orders in bulk.
  - Developers should not attempt to place another order until the previous order has been fully acknowledged, that is, when no further warnings are received deferring the client to the reply endpoint.
  

Arguments:

- `order_request` _OneOrMany[OrderRequest]_ - Used to the order content.
- `answers` _Answers_ - List of question-answer pairs for order submission process.
- `account_id` _str_ - The account ID for which account should place the order.
  
  Keep this in mind:
  https://interactivebrokers.github.io/tws-api/automated_considerations.html#order_placement
  

Notes:

  - Only one order can be placed at a time due to question-reply mechanism

<a id="client.ibkr_client_mixins.order_mixin.OrderMixin.reply"></a>

### reply

```python
def reply(reply_id, confirmed: bool) -> Result
```

Confirm order precautions and warnings presented from placing orders.

Many of the warning notifications within the Client Portal API can be disabled.

Arguments:

- `reply_id` _str_ - Include the id value from the prior order request relating to the particular order's warning confirmation.
- `confirmed` _bool_ - Pass your confirmation to the reply to allow or cancel the order to go through. true will agree to the message transmit the order. false will decline the message and discard the order.

<a id="client.ibkr_client_mixins.order_mixin.OrderMixin.whatif_order"></a>

### whatif\_order

```python
def whatif_order(order_request: OrderRequest,
                 account_id: str = None) -> Result
```

This endpoint allows you to preview order without actually submitting the order and you can get commission information in the response. Also supports bracket orders.

Clients must query /iserver/marketdata/snapshot for the instrument prior to requesting the /whatif endpoint.

The body content of the /whatif endpoint will follow the same structure as the standard /iserver/account/{accountId}/orders endpoint.

Arguments:

- `account_id` _str_ - The account ID for which account should place the order. Financial Advisors may specify.
- `order_request` _dict_ - Used to the order content.

<a id="client.ibkr_client_mixins.order_mixin.OrderMixin.cancel_order"></a>

### cancel\_order

```python
def cancel_order(order_id: str, account_id: str = None) -> Result
```

Cancels an open order.

Must call /iserver/accounts endpoint prior to cancelling an order.
Use /iservers/account/orders endpoint to review open-order(s) and get latest order status.

Arguments:

- `account_id` _str_ - The account ID for which account should place the order.
- `order_id` _str_ - The orderID for that should be modified. Can be retrieved from /iserver/account/orders. Submitting '-1' will cancel all open orders.

<a id="client.ibkr_client_mixins.order_mixin.OrderMixin.modify_order"></a>

### modify\_order

```python
def modify_order(order_id: str,
                 order_request: OrderRequest,
                 answers: Answers,
                 account_id: str = None) -> Result
```

Modifies an open order.

Must call /iserver/accounts endpoint prior to modifying an order.
Use /iservers/account/orders endpoint to review open-order(s).

Arguments:

- `order_id` _str_ - The orderID for that should be modified. Can be retrieved from /iserver/account/orders.
- `order_request` _OrderRequest_ - Used to the order content. The content should mirror the content of the original order.
- `answers` _Answers_ - List of question-answer pairs for order submission process.
- `account_id` _str_ - The account ID for which account should place the order.
  

Notes:

  - Only one order can be modified at a time due to question-reply mechanism

<a id="client.ibkr_client_mixins.order_mixin.OrderMixin.suppress_messages"></a>

### suppress\_messages

```python
def suppress_messages(message_ids: List[str]) -> Result
```

Disables a messageId, or series of messageIds, that will no longer prompt the user.

Arguments:

- `message_ids` _List[str]_ - The identifier for each warning message to suppress. The array supports up to 51 messages sent in a single request. Any additional values will result in a system error. The majority of the message IDs are based on the TWS API Error Codes with a �o� prepended to the id.

<a id="client.ibkr_client_mixins.order_mixin.OrderMixin.reset_suppressed_messages"></a>

### reset\_suppressed\_messages

```python
def reset_suppressed_messages() -> Result
```

Resets all messages disabled by the Suppress Messages endpoint.
