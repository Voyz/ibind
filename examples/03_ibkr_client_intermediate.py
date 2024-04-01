import var

from ibind import IbkrClient
import ibind

ibind.logs.initialize()

c = IbkrClient(
    url='https://localhost:5000/v1/api/',
    cacert=var.IBKR_CACERT,
)

print('\n#### get_accounts ####')
accounts = c.get_accounts().data
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
positions = c.get_positions().data
for position in positions:
    print(f'\t Position {position["ticker"]}: {position["position"]} (${position["mktValue"]})')
