"""
REST Intermediate

In this example we:

* Initialise the IBind logs
* Provide a CAcert (assuming the Gateway is using the same one)
* Showcase several REST API calls

Assumes the Gateway is deployed at 'localhost:5000' and the IBIND_ACCOUNT_ID and IBIND_CACERT environment variables have been set.
"""

import os

from ibind import IbkrClient, ibind_logs_initialize

ibind_logs_initialize()

cacert = os.getenv('IBIND_CACERT', False)  # insert your cacert path here
client = IbkrClient(cacert=cacert)

print('\n#### get_accounts ####')
accounts = client.portfolio_accounts().data
client.account_id = accounts[0]['accountId']
print(accounts)

print('\n\n#### get_ledger ####')
ledger = client.get_ledger().data
for currency, subledger in ledger.items():
    print(f'\t Ledger currency: {currency}')
    print(f'\t cash balance: {subledger["cashbalance"]}')
    print(f'\t net liquidation value: {subledger["netliquidationvalue"]}')
    print(f'\t stock market value: {subledger["stockmarketvalue"]}')
    print()

print('\n#### get_positions ####')
positions = client.positions().data
for position in positions:
    print(f'\t Position {position["ticker"]}: {position["position"]} (${position["mktValue"]})')
