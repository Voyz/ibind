import os
from pprint import pprint

import ibind
from ibind.client.ibkr_utils import StockQuery
from ibind import IbkrClient

ibind.logs.initialize(log_to_file=False)

cacert = os.getenv('IBKR_CACERT', False) # insert your cacert path here
c = IbkrClient(
    url='https://localhost:5000/v1/api/',
    cacert=cacert,
)


print('#### get_stocks ####')
stocks = c.get_stocks('AAPL').data
print(stocks)


print('\n#### get_conids ####')
conids = c.get_conids('AAPL').data
print(conids)


print('\n#### using StockQuery ####')
conids = c.get_conids(StockQuery('AAPL', contract_conditions={'exchange': 'MEXI'}), default_filtering=False).data
pprint(conids)


print('\n#### mixed queries ####')
stock_queries = [
    StockQuery('AAPL', contract_conditions={'exchange': 'MEXI'}),
    'HUBS',
    StockQuery('GOOG', name_match='ALPHABET INC - CDR')
]
conids = c.get_conids(stock_queries, default_filtering=False).data
pprint(conids)


"""
    The get_conids() method will raise an exception if the filtered stocks response doesn't provide exactly one conid.
    The default_filtering filtered the returned contracts by isUS=True which usually returns only one conid.
    If multiple conids are found, you must provide additional conditions for the particular stock in order in order to ensure only one conid is returned. 
    
    Uncomment the following lines to see the exception raised when multiple conids are returned.
"""
# print('\n#### get_conid with too many conids ####')
# conids = c.get_conids('AAPL', default_filtering=False).data
# pprint(conids)
