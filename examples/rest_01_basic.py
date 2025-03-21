"""
REST basic.

Minimal example of using the IbkrClient class.
"""

from ibind import IbkrClient

# Construct the client
client = IbkrClient()

# Call some endpoints
print('\n#### check_health ####')
print(client.check_health())

print('\n\n#### tickle ####')
print(client.tickle().data)

print('\n\n#### get_accounts ####')
print(client.portfolio_accounts().data)
