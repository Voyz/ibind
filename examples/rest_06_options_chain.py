"""
REST options chain

In this example we:

* Retrieve an options chain for the S&P 500 index
* Submit a spread order for two of its strikes

Assumes the Gateway is deployed at 'localhost:5000' and the IBIND_ACCOUNT_ID and IBIND_CACERT environment variables have been set.
"""
import datetime
import os
from pprint import pprint
from unittest.mock import patch, MagicMock

from ibind import IbkrClient, ibind_logs_initialize, OrderRequest, QuestionType
from ibind.support.py_utils import print_table

ibind_logs_initialize()

cacert = os.getenv('IBIND_CACERT', False)  # insert your cacert path here
client = IbkrClient(cacert=cacert, use_session=False)


###################################
#### LOOKING UP OPTIONS CHAINS ####
###################################

print('\n#### search for contract ####')
contracts = client.search_contract_by_symbol('SPX').data
spx_contract = contracts[0]
pprint(spx_contract)

# find the options section in spx_contract
options = None
for section in spx_contract['sections']:
    if section['secType'] == 'OPT':
        options = section
        break

if options is None:
    raise RuntimeError(f'No options found in spx_contract: {spx_contract}')

options['months'] = options['months'].split(';')
options['exchange'] = options['exchange'].split(';')

print('\n#### search for strikes ####')
strikes = client.search_strikes_by_conid(conid=spx_contract['conid'], sec_type='OPT', month=options['months'][0]).data
print(str(strikes).replace("'put'", "\n'put'"))

print('\n#### validate contract ####')
info = client.search_secdef_info_by_conid(
    conid=spx_contract['conid'], sec_type='OPT', month=options['months'][0], strike=strikes['call'][0], right='C'
).data

print_table(info)


#########################################
#### SUBMITTING OPTIONS SPREAD ORDER ####
#########################################

account_id = os.getenv('IBIND_ACCOUNT_ID', '[YOUR_ACCOUNT_ID]')
currency = 'USD'

# Configure the legs as needed
legs = [
    {'conid': info[0]['conid'], 'ratio': 1, 'side': 'BUY'},
    {'conid': info[1]['conid'], 'ratio': 1, 'side': 'SELL'},
]

# Look this up in the documentation to verify these conids are correct
_SPREAD_CONIDS = {
    'AUD': '61227077',
    'CAD': '61227082',
    'CHF': '61227087',
    'CNH': '136000441',
    'GBP': '58666491',
    'HKD': '61227072',
    'INR': '136000444',
    'JPY': '61227069',
    'KRW': '136000424',
    'MXN': '136000449',
    'SEK': '136000429',
    'SGD': '426116555',
    'USD': '28812380',
}

# Build conidex string for combo order
# Combo Orders follow the format of: '{spread_conid};;;{leg_conid1}/{ratio},{leg_conid2}/{ratio}'
conidex = f"{_SPREAD_CONIDS[currency]};;;"

leg_strings = []
for leg in legs:
    multiplier = 1 if leg['side'] == "BUY" else -1
    leg_string = f'{leg['conid']}/{leg['ratio'] * multiplier}'
    leg_strings.append(leg_string)

conidex = conidex + ",".join(leg_strings)

# Prepare the OrderRequest
side = 'BUY'
size = 1
order_type = 'MKT'
order_tag = f'my_order-{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}'

order_request = OrderRequest(
    conid=None, # must be None when specifying conidex
    conidex=conidex,
    side=side,
    quantity=size,
    order_type=order_type,
    acct_id=account_id,
    coid=order_tag
)

answers = {
    QuestionType.PRICE_PERCENTAGE_CONSTRAINT: True,
    # ...
}

print('\n#### Submitting spread order ####')
print(f'conidex:\n{conidex}')

# We mock the requests module to prevent submitting orders in this example script.
# Comment out the next two lines if you'd like to actually submit the orders to IBKR.
with patch('ibind.base.rest_client.requests') as requests_mock:
    requests_mock.request.return_value = MagicMock(json=MagicMock(side_effect=[[{'success': True}]]))

    response = client.place_order(order_request, answers, account_id).data

print(response)
