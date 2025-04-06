"""
REST Market Data History

In this example we:

* Query historical market data by conid
* Query historical market data by symbol
* Showcase using the marketdata_history_by_symbols to query one and multiple symbols
* Showcase the time difference between these various calls

Assumes the Gateway is deployed at 'localhost:5000' and the IBIND_ACCOUNT_ID and IBIND_CACERT environment variables have been set.
"""

import os
import time

from ibind import IbkrClient, ibind_logs_initialize

ibind_logs_initialize(log_to_file=False)

cacert = os.getenv('IBIND_CACERT', False)  # insert your cacert path here
client = IbkrClient(cacert=cacert, timeout=2)

st = time.time()
history = client.marketdata_history_by_conid('265598', period='1d', bar='1d', outside_rth=True)
diff_one_conid = time.time() - st
print('#### One conid ####')
print(f'{history}')

st = time.time()
history = client.marketdata_history_by_symbol('AAPL', period='1d', bar='1d', outside_rth=True)
diff_one_symbol_raw = time.time() - st
print('\n\n#### One symbol raw ####')
print(f'{history}')

st = time.time()
history = client.marketdata_history_by_symbols('AAPL', period='1d', bar='1d', outside_rth=True)
diff_one_symbol = time.time() - st
print('\n\n#### One symbol ####')
print(f'{history}')

st = time.time()
history_sync = client.marketdata_history_by_symbols(
    ['AAPL', 'MSFT', 'GOOG', 'TSLA', 'AMZN'], period='1d', bar='1d', outside_rth=True, run_in_parallel=False
)
diff_five_symbols_sync = time.time() - st
print('\n\n#### Five symbols synchronous ####')
print(f'{history_sync}')


st = time.time()
history = client.marketdata_history_by_symbols(['AAPL', 'MSFT', 'GOOG', 'TSLA', 'AMZN'], period='1d', bar='1d', outside_rth=True)
diff_five_symbols = time.time() - st
print('\n\n#### Five symbols parallel ####')
print(f'{history}')

time.sleep(5)
st = time.time()
history = client.marketdata_history_by_symbols(
    ['AAPL', 'MSFT', 'GOOG', 'TSLA', 'AMZN', 'ADBE', 'AMD', 'COIN', 'META', 'DIS', 'BAC', 'XOM', 'KO', 'WMT', 'V'],
    period='1d',
    bar='1d',
    outside_rth=True,
)
diff_fifteen_symbols = time.time() - st
print('\n\n#### Fifteen symbols ####')
print(f'{history}')

print(f'\n\n1 conid took: {diff_one_conid:.2f}s')
print(f'1 symbol raw took: {diff_one_symbol_raw:.2f}s')
print(f'1 symbol took: {diff_one_symbol:.2f}s')
print(f'5 symbols sync took: {diff_five_symbols_sync:.2f}s')
print(f'5 symbols took: {diff_five_symbols:.2f}s')
print(f'15 symbols took: {diff_fifteen_symbols:.2f}s')
