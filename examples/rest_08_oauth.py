"""
REST basic.

Minimal example to create a client and test OAuth
"""

#%%

from ibind.client.ibkr_client.py import IbkrClient


# Construct the client, set use_oauth=False, if working, try creating a live session by setting use_oath=True
client = IbkrClient(use_oauth=False)


# Call some endpoints
print('\n#### check_health ####')
# print(client.check_health())

print('\n\n#### tickle ####')
# print(client.tickle().data)

print('\n\n#### get_accounts ####')
# print(client.portfolio_accounts().data)
