from threading import Lock
from typing import TYPE_CHECKING, List

from ibind.base.rest_client import Result
from ibind.client.ibkr_utils import Answers, handle_questions
from ibind.support.py_utils import OneOrMany, params_dict, ensure_list_arg

if TYPE_CHECKING:  # pragma: no cover
    from ibind import IbkrClient


class OrderMixin():
    """
    * https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#order-monitor
    * https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#orders
    """
    order_submission_lock = Lock()

    @ensure_list_arg('filters')
    def live_orders(
            self: 'IbkrClient',
            filters: OneOrMany[str] = None,
            force: bool = None,
            account_id: str = None
    ) -> Result:  # pragma: no cover
        """
        Retrieves live orders with optional filtering. The filters, if provided, should be a list of strings. These filters are then converted and sent as a comma-separated string in the request to the API.

        Parameters:
            filters (List[str], optional): A list of strings representing the filters to be applied. Defaults to None
            force (bool, optional): Force the system to clear saved information and make a fresh request for orders. Submission will appear as a blank array. Defaults to False.
            account_id (str): For linked accounts, allows users to view orders on sub-accounts as specified.

        Available filters:
            * Inactive:
                Order was received by the system but is no longer active because it was rejected or cancelled.
            * PendingSubmit:
                Order has been transmitted but have not received confirmation yet that order accepted by destination exchange or venue.
            * PreSubmitted:
                Simulated order transmitted but the order has yet to be elected. Order is held by IB system until election criteria are met.
            * Submitted:
                Order has been accepted by the system.
            * Filled:
                Order has been completely filled.
            * PendingCancel:
                Sent an order cancellation request but have not yet received confirmation order cancelled by destination exchange or venue.
            * Cancelled:
                The balance of your order has been confirmed canceled by the system.
            * WarnState:
                Order has a specific warning message such as for basket orders.
            * SortByTime:
                There is an initial sort by order state performed so active orders are always above inactive and filled then orders are sorted chronologically.

        Note:
            - This endpoint requires a pre-flight request. Orders is the list of live orders (cancelled, filled, submitted).

        """

        params = params_dict(
            optional={
                'filters': filters,
                'accountId': account_id,
                'force': force
            },
            preprocessors={
                'filters': ",".join
            }
        )

        return self.get('iserver/account/orders', params=params)

    def order_status(self: 'IbkrClient', order_id: str) -> Result:  # pragma: no cover
        """
        Retrieve the given status of an individual order using the orderId returned by the order placement response or the orderId available in the live order response.

        Parameters:
            order_id (str): Order identifier for the placed order. Returned by the order placement response or the order_id available in the live order response.
        """
        return self.get(f'iserver/account/order/status/{order_id}')

    def trades(
            self: 'IbkrClient',
            days: str = None,
            account_id: str = None
    ) -> Result:  # pragma: no cover
        """
        Returns a list of trades for the currently selected account for current day and six previous days. It is advised to call this endpoint once per session.

        Parameters:
            days (str): Specify the number of days to receive executions for, up to a maximum of 7 days. If unspecified, only the current day is returned.
            account_id (str): Include a specific account identifier or allocation group to retrieve trades for.
        """
        if account_id is None:
            account_id = self.account_id

        params = params_dict(
            optional={
                'days': days,
                'accountId': account_id,
            }
        )
        return self.get(f'iserver/account/trades/', params=params)

    @ensure_list_arg('order_request')
    def place_order(self: 'IbkrClient', order_request: OneOrMany[dict], answers: Answers, account_id: str = None) -> Result:
        """
        When connected to an IServer Brokerage Session, this endpoint will allow you to submit orders.

        Notes:
        - With the exception of OCA groups and bracket orders, the orders endpoint does not currently support the placement of unrelated orders in bulk.
        - Developers should not attempt to place another order until the previous order has been fully acknowledged, that is, when no further warnings are received deferring the client to the reply endpoint.

        Parameters:
            account_id (str): The account ID for which account should place the order.
            answers (Answers): List of question-answer pairs for order submission process.
            order_request (OneOrMany[dict]): Used to the order content.

        Keep this in mind:
        https://interactivebrokers.github.io/tws-api/automated_considerations.html#order_placement

        Note:
            - Only one order can be placed at a time due to question-reply mechanism
        """
        if account_id is None:
            account_id = self.account_id

        with self.order_submission_lock:
            result = self.post(
                f'iserver/account/{account_id}/orders',
                params={"orders": order_request}
            )

            return handle_questions(result, answers, self.reply)

    def reply(self: 'IbkrClient', reply_id, confirmed: bool) -> Result:  # pragma: no cover
        """
        Confirm order precautions and warnings presented from placing orders.

        Many of the warning notifications within the Client Portal API can be disabled.

        Parameters:
            reply_id (str): Include the id value from the prior order request relating to the particular order's warning confirmation.
            confirmed (bool): Pass your confirmation to the reply to allow or cancel the order to go through. true will agree to the message transmit the order. false will decline the message and discard the order.
        """
        return self.post(f'iserver/reply/{reply_id}', params={"confirmed": confirmed})

    def whatif_order(self: 'IbkrClient', order_request: dict, account_id: str) -> Result:  # pragma: no cover
        """
        This endpoint allows you to preview order without actually submitting the order and you can get commission information in the response. Also supports bracket orders.

        Clients must query /iserver/marketdata/snapshot for the instrument prior to requesting the /whatif endpoint.

        The body content of the /whatif endpoint will follow the same structure as the standard /iserver/account/{accountId}/orders endpoint.

        Parameters:
            account_id (str): The account ID for which account should place the order. Financial Advisors may specify.
            order_request (dict): Used to the order content.
        """
        if account_id == None:
            account_id = self.account_id

        return self.post(f'iserver/account/{account_id}/orders/whatif', params={"orders": [order_request]})

    def cancel_order(self: 'IbkrClient', order_id: str, account_id: str = None) -> Result:  # pragma: no cover
        """
        Cancels an open order.

        Must call /iserver/accounts endpoint prior to cancelling an order.
        Use /iservers/account/orders endpoint to review open-order(s) and get latest order status.

        Parameters:
            account_id (str): The account ID for which account should place the order.
            order_id (str): The orderID for that should be modified. Can be retrieved from /iserver/account/orders. Submitting '-1' will cancel all open orders.
        """
        if account_id is None:
            account_id = self.account_id

        return self.delete(f'iserver/account/{account_id}/order/{order_id}')

    def modify_order(self: 'IbkrClient', order_id: str, order_request: dict, answers: Answers, account_id: str = None) -> Result:
        """
        Modifies an open order.

        Must call /iserver/accounts endpoint prior to modifying an order.
        Use /iservers/account/orders endpoint to review open-order(s).

        Parameters:
            order_id (str): The orderID for that should be modified. Can be retrieved from /iserver/account/orders.
            order_request (dict): Used to the order content. The content should mirror the content of the original order.
            answers (Answers): List of question-answer pairs for order submission process.
            account_id (str): The account ID for which account should place the order.

        Note:
            - Only one order can be modified at a time due to question-reply mechanism
        """
        if account_id is None:
            account_id = self.account_id

        with self.order_submission_lock:
            result = self.post(f'iserver/account/{account_id}/order/{order_id}', params=order_request)

            return handle_questions(result, answers, self.reply)

    def suppress_messages(self: 'IbkrClient', message_ids: List[str]) -> Result:  # pragma: no cover
        """
        Disables a messageId, or series of messageIds, that will no longer prompt the user.

        Parameters:
            message_ids (List[str]): The identifier for each warning message to suppress. The array supports up to 51 messages sent in a single request. Any additional values will result in a system error. The majority of the message IDs are based on the TWS API Error Codes with a “o” prepended to the id.
        """
        return self.post(f'iserver/questions/suppress', params={"messageIds": message_ids})

    def reset_suppressed_messages(self: 'IbkrClient') -> Result:  # pragma: no cover
        """
        Resets all messages disabled by the Suppress Messages endpoint.
        """
        return self.post(f'/iserver/questions/suppress/reset')
