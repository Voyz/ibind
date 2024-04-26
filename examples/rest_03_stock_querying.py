import os
from pprint import pprint

from ibind import IbkrClient, StockQuery, ibind_logs_initialize

ibind_logs_initialize(log_to_file=False)

cacert = os.getenv('IBIND_CACERT', False) # insert your cacert path here
c = IbkrClient(cacert=cacert)


print('#### get_stocks ####')
stocks = c.security_stocks_by_symbol('AAPL').data
print(stocks)


print('\n#### get_conids ####')
conids = c.stock_conid_by_symbol('AAPL').data
print(conids)


print('\n#### using StockQuery ####')
conids = c.stock_conid_by_symbol(StockQuery('AAPL', contract_conditions={'exchange': 'MEXI'}), default_filtering=False).data
pprint(conids)


print('\n#### mixed queries ####')
stock_queries = [
    StockQuery('AAPL', contract_conditions={'exchange': 'MEXI'}),
    'HUBS',
    StockQuery('GOOG', name_match='ALPHABET INC - CDR')
]
conids = c.stock_conid_by_symbol(stock_queries, default_filtering=False).data
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
