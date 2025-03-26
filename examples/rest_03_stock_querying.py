"""
REST Stock Querying

In this example we:

* Get stock security data by symbol
* Showcase using StockQuery class for advanced stock filtering
* Get conids by using StockQuery queries
* Showcase an error encountered when getting conids returns multiple contracts or instruments

Assumes the Gateway is deployed at 'localhost:5000' and the IBIND_ACCOUNT_ID and IBIND_CACERT environment variables have been set.
"""

import os
from pprint import pprint

from ibind import IbkrClient, StockQuery, ibind_logs_initialize

ibind_logs_initialize(log_to_file=False)

cacert = os.getenv('IBIND_CACERT', False)  # insert your cacert path here
client = IbkrClient(cacert=cacert)


print('#### get_stocks ####')
stocks = client.security_stocks_by_symbol('AAPL').data
print(stocks)


print('\n#### get_conids ####')
conids = client.stock_conid_by_symbol('AAPL').data
print(conids)


print('\n#### using StockQuery ####')
conids = client.stock_conid_by_symbol(StockQuery('AAPL', contract_conditions={'exchange': 'MEXI'}), default_filtering=False).data
pprint(conids)


print('\n#### mixed queries ####')
stock_queries = [StockQuery('AAPL', contract_conditions={'exchange': 'MEXI'}), 'HUBS', StockQuery('GOOG', name_match='ALPHABET INC - CDR')]
conids = client.stock_conid_by_symbol(stock_queries, default_filtering=False).data
pprint(conids)


"""
    The get_conids() method will raise an exception if the filtered stocks response doesn't provide exactly one conid.
    The default_filtering filtered the returned contracts by isUS=True which usually returns only one conid.
    If multiple conids are found, you must provide additional conditions for the particular stock in order in order to ensure only one conid is returned.

    Uncomment the following lines to see the exception raised when multiple conids are returned.
"""
# print('\n#### get_conid with too many conids ####')
# conids = client.stock_conid_by_symbol('AAPL', default_filtering=False).data
# pprint(conids)
