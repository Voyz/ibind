"""
REST options chain

In this example we:

* Retrieve an options chain for the S&P 500 index

Assumes the Gateway is deployed at 'localhost:5000' and the IBIND_ACCOUNT_ID and IBIND_CACERT environment variables have been set.
"""

import os

from ibind import IbkrClient, ibind_logs_initialize
from pprint import pprint

from ibind.support.py_utils import print_table

ibind_logs_initialize()

cacert = os.getenv('IBIND_CACERT', False)  # insert your cacert path here
client = IbkrClient(cacert=cacert)


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
