import datetime
import os
from unittest.mock import patch, MagicMock

import ibind
from ibind.client.ibkr_utils import make_order_request, QuestionType
from ibind import IbkrClient

ibind.logs.initialize(log_to_file=False)

account_id = os.getenv('IBKR_ACCOUNT_ID', '[YOUR_ACCOUNT_ID]')
cacert = os.getenv('IBKR_CACERT', False) # insert your cacert path here
c = IbkrClient(
    url='https://localhost:5000/v1/api/',
    account_id=account_id,
    cacert=cacert,
)

conid = '265598'
side = 'BUY'
size = 1
order_type = 'MARKET'
price = 100
order_tag = f'my_order-{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}'

order_request = make_order_request(
    conid=conid,
    side=str(side),
    quantity=float(size),
    order_type=order_type,
    price=float(price),
    acct_id=account_id,
    coid=order_tag
)

answers = {
    QuestionType.PRICE_PERCENTAGE_CONSTRAINT: True,
    QuestionType.ORDER_VALUE_LIMIT: True,
    "Unforeseen new question": True,
}

mocked_responses = [
    [{'id': 0, 'message': ['price exceeds the Percentage constraint of 3%.']}],
    [{'id': 1, 'message': ['exceeds the Total Value Limit of']}],
    [{'success': True}]
]

print('#### submit_order ####')

# We mock the requests module to prevent submitting orders in this example script.
# Comment out the next two lines if you'd like to actually submit the orders to IBKR.
with patch('ibind.base.rest_client.requests') as requests_mock:
    requests_mock.request.return_value = MagicMock(json=MagicMock(side_effect=mocked_responses))

    response = c.submit_order(order_request, answers, account_id).data

print(response)
