import os

from ibind import IbkrClient, ibind_logs_initialize

ibind_logs_initialize()

cacert = os.getenv('IBIND_CACERT', False) # insert your cacert path here
c = IbkrClient(cacert=cacert)

print('\n#### get_accounts ####')
accounts = c.portfolio_accounts().data
c.account_id = accounts[0]['accountId']
print(accounts)

print('\n\n#### get_ledger ####')
ledger = c.get_ledger().data
for currency, subledger in ledger.items():
    print(f'\t Ledger currency: {currency}')
    print(f'\t cash balance: {subledger["cashbalance"]}')
    print(f'\t net liquidation value: {subledger["netliquidationvalue"]}')
    print(f'\t stock market value: {subledger["stockmarketvalue"]}')
    print()

print('\n#### get_positions ####')
positions = c.positions().data
for position in positions:
    print(f'\t Position {position["ticker"]}: {position["position"]} (${position["mktValue"]})')
