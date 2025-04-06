"""
REST Place Order

In this example we:

* Set up an order_request using make_order_request() method
* Prepare the place_order answers based on the QuestionType enum
* Mock the place_order endpoint to prevent submitting an actual order
* Call the place_order() method

Assumes the Gateway is deployed at 'localhost:5000' and the IBIND_ACCOUNT_ID and IBIND_CACERT environment variables have been set.
"""

import datetime
import os
from unittest.mock import patch, MagicMock

from ibind import IbkrClient, QuestionType, ibind_logs_initialize
from ibind.client.ibkr_utils import OrderRequest

ibind_logs_initialize(log_to_file=False)

account_id = os.getenv('IBIND_ACCOUNT_ID', '[YOUR_ACCOUNT_ID]')
cacert = os.getenv('IBIND_CACERT', False)  # insert your cacert path here
client = IbkrClient(cacert=cacert)

conid = '265598'
side = 'BUY'
size = 1
order_type = 'MKT'
order_tag = f'my_order-{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}'

order_request = OrderRequest(conid=conid, side=side, quantity=size, order_type=order_type, acct_id=account_id, coid=order_tag)

answers = {
    QuestionType.PRICE_PERCENTAGE_CONSTRAINT: True,
    QuestionType.ORDER_VALUE_LIMIT: True,
    'Unforeseen new question': True,
}

mocked_responses = [
    [{'id': 0, 'message': ['price exceeds the Percentage constraint of 3%.']}],
    [{'id': 1, 'message': ['exceeds the Total Value Limit of']}],
    [{'success': True}],
]

print('#### submit_order ####')

# We mock the requests module to prevent submitting orders in this example script.
# Comment out the next two lines if you'd like to actually submit the orders to IBKR.
with patch('ibind.base.rest_client.requests') as requests_mock:
    requests_mock.request.return_value = MagicMock(json=MagicMock(side_effect=mocked_responses))

    response = client.place_order(order_request, answers, account_id).data

print(response)
