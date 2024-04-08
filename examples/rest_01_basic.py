import warnings

from ibind import IbkrClient

warnings.filterwarnings("ignore", message="Unverified HTTPS request is being made to host 'localhost'")

c = IbkrClient(url='https://localhost:5000/v1/api/')

print('\n#### check_health ####')
print(c.check_health())

print('\n\n#### tickle ####')
print(c.tickle().data)

print('\n\n#### get_accounts ####')
print(c.portfolio_accounts().data)


