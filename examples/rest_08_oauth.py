"""
REST OAuth.

Showcases usage of OAuth with IbkrClient.

This example is equivalent to rest_02_intermediate.py, except that it uses OAuth for authentication.

Using IbkrClient with OAuth support will automatically handle generating the OAuth live session token and tickling the connection to maintain it active. You should be able to use all endpoints in the same way as when not using OAuth.

Importantly, in order to use OAuth you're required to set up the following environment variables:

- IBIND_USE_OAUTH: Set to True.
- IBIND_ACCESS_TOKEN: OAuth access token generated in the self-service portal.
- IBIND_ACCESS_TOKEN_SECRET: OAuth access token secret generated in the self-service portal.
- IBIND_CONSUMER_KEY: The consumer key configured during the onboarding process. This uniquely identifies the project in the IBKR ecosystem.
- IBIND_DH_PRIME: The hex representation of the Diffie-Hellman prime.
- IBIND_ENCRYPTION_KEY_FP: The path to the private OAuth encryption key.
- IBIND_SIGNATURE_KEY_FP: The path to the private OAuth signature key.

Optionally, you can also set:
- IBIND_REALM: OAuth connection type. This is generally set to "limited_poa", however should be set to "test_realm" when using the TESTCONS consumer key. (optional, defaults to "limited_poa")
- IBIND_DH_GENERATOR: The Diffie-Hellman generator value (optional, defaults to 2).

If you prefer setting these variables inline, you can pass an instance of OAuthConfig class as an optional 'oauth_config' parameter to the IbkrClient constructor. Any variables not specified will be taken from the environment variables.
"""
import os

from ibind import IbkrClient, ibind_logs_initialize
from ibind.support.oauth import OAuthConfig

ibind_logs_initialize()

cacert = os.getenv('IBIND_CACERT', False)  # insert your cacert path here


client = IbkrClient(
    cacert=cacert,
    use_oauth=True,

    # Optionally, specify OAuth variables dynamically by passing an OAuthConfig instance
    # oauth_config=OAuthConfig(access_token='my_access_token',access_token_secret='my_access_token_secret')
)

print('\n#### live session token ####')
print(client.live_session_token)

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
