from typing import TYPE_CHECKING

from ibind.base.rest_client import Result
from ibind.client.ibkr_utils import Answers, handle_questions
from ibind.support.py_utils import OneOrMany

if TYPE_CHECKING:
    from ibind import IbkrClient



class OrderMixin():

    def reply(self: 'IbkrClient', question_id: str, reply: bool) -> Result:  # pragma: no cover
        return self.post(f'iserver/reply/{question_id}', params={"confirmed": reply})

    def get_order(self: 'IbkrClient', order_id: str) -> Result:  # pragma: no cover
        return self.get(f'iserver/account/order/status/{order_id}')

    def cancel_order(self: 'IbkrClient', order_id: str, account_id: str = None) -> Result:  # pragma: no cover
        if account_id is None:
            account_id = self.account_id
        return self.delete(f'iserver/account/{account_id}/order/{order_id}')

    def get_live_orders(self: 'IbkrClient', filters: OneOrMany[str] = None, force: bool = False) -> Result:
        """
        Retrieves live orders with optional filtering. The filters, if provided, should be a list of strings. These filters are then converted and sent as a comma-separated string in the request to the API.

        Parameters:
            filters (List[str], optional): A list of strings representing the filters to be applied. Defaults to None
            force (bool, optional): Force the system to clear saved information and make a fresh request for orders. Submission will appear as a blank array. Defaults to False.

        Available filters:
            inactive:
                Order was received by the system but is no longer active because it was rejected or cancelled.
            pending_submit:
                Order has been transmitted but have not received confirmation yet that order accepted by destination exchange or venue.
            pre_submitted:
                Simulated order transmitted but the order has yet to be elected. Order is held by IB system until election criteria are met.
            submitted:
                Order has been accepted by the system.
            filled:
                Order has been completely filled.
            pending_cancel:
                Sent an order cancellation request but have not yet received confirmation order cancelled by destination exchange or venue.
            cancelled:
                The balance of your order has been confirmed canceled by the system.
            warn_state:
                Order has a specific warning message such as for basket orders.
            sort_by_time:
                There is an initial sort by order state performed so active orders are always above inactive and filled then orders are sorted chronologically.

        """
        if filters is None and force is False:
            params = None
        else:
            params = {}
            if filters is not None:
                if not isinstance(filters, list):
                    filters = [filters]
                params["filters"] = ",".join(filters)
            if force is True:
                params['force'] = True

        return self.get('iserver/account/orders', params=params)

    def submit_order(self: 'IbkrClient',order_request: dict, answers: Answers, account_id: str = None) -> Result:
        """
        Keep this in mind:
        https://interactivebrokers.github.io/tws-api/automated_considerations.html#order_placement
        """
        if account_id is None:
            account_id = self.account_id

        if isinstance(order_request, list):
            raise RuntimeError(f'IbkrClient.submit_order() does not accept a list of orders, found: {order_request}')

        result = self.post(
            f'iserver/account/{account_id}/orders',
            params={"orders": [order_request]}
        )

        return handle_questions(result, answers, self.reply)

    def modify_order(self: 'IbkrClient',order_id: str, order_request: dict, answers: Answers, account_id: str = None) -> Result:
        if account_id is None:
            account_id = self.account_id

        result = self.post(f'iserver/account/{account_id}/order/{order_id}', params=order_request)

        return handle_questions(result, answers, self.reply)