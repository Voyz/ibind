"""
REST Bracket Orders

In this example we:

* Set up the bracket order request dicts using make_order_request() method
* Prepare the place_order answers based on the QuestionType enum
* Submit the bracket orders

Assumes the Gateway is deployed at 'localhost:5000' and the IBIND_ACCOUNT_ID and IBIND_CACERT environment variables have been set.
"""

import datetime
import os
from functools import partial

from ibind import IbkrClient, make_order_request, QuestionType, ibind_logs_initialize

ibind_logs_initialize(log_to_file=False)

account_id = os.getenv('IBIND_ACCOUNT_ID', '[YOUR_ACCOUNT_ID]')
cacert = os.getenv('IBIND_CACERT', False)  # insert your cacert path here
client = IbkrClient(cacert=cacert)

conid = '265598'
price = 211.07
order_tag = f'my_order-{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}'

order_request_partial = partial(make_order_request, conid=conid, acct_id=account_id, quantity=1)

parent = order_request_partial(side='BUY', order_type='LMT', price=price, coid=order_tag)
stop_loss = order_request_partial(side='SELL', order_type='STP', price=price - 1, parent_id=order_tag)
take_profit = order_request_partial(side='SELL', order_type='LMT', price=price + 1, parent_id=order_tag)

requests = [parent, stop_loss, take_profit]

answers = {
    QuestionType.PRICE_PERCENTAGE_CONSTRAINT: True,
    QuestionType.ORDER_VALUE_LIMIT: True,
    QuestionType.MISSING_MARKET_DATA: True,
    QuestionType.STOP_ORDER_RISKS: True,
}

print('#### submit_order ####')

response = client.place_order(requests, answers, account_id).data

print(response)
