"""
REST basic.

Minimal example of using the IbkrClient class.
"""

import warnings

from ibind import IbkrClient

# In this example we provide no CAcert, hence we need to silence this warning.
warnings.filterwarnings("ignore", message="Unverified HTTPS request is being made to host 'localhost'")

# Construct the client
client = IbkrClient()

# Call some endpoints
print('\n#### check_health ####')
print(client.check_health())

print('\n\n#### tickle ####')
print(client.tickle().data)

print('\n\n#### get_accounts ####')
print(client.portfolio_accounts().data)
