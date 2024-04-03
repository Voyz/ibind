import os
import time

import ibind
from ibind import IbkrClient

ibind.logs.initialize(log_to_file=False)

account_id = os.getenv('IBKR_ACCOUNT_ID', '[YOUR_ACCOUNT_ID]')
cacert = os.getenv('IBKR_CACERT', False) # insert your cacert path here
c = IbkrClient(
    url='https://localhost:5000/v1/api/',
    account_id=account_id,
    cacert=cacert,
)

st = time.time()
history = c.marketdata_history_by_conid('265598', period='1min', bar='1min', outside_rth=True)
diff_one_conid = time.time() - st
print('#### One conid ####')
print(f'{history}')


st = time.time()
history = c.marketdata_history_by_symbol('AAPL', period='1min', bar='1min', outside_rth=True)
diff_one_symbol_raw = time.time() - st
print('\n\n#### One symbol raw ####')
print(f'{history}')


st = time.time()
history = c.marketdata_history_by_symbols('AAPL', period='1min', bar='1min', outside_rth=True)
diff_one_symbol = time.time() - st
print('\n\n#### One symbol ####')
print(f'{history}')


st = time.time()
history = c.marketdata_history_by_symbols(['AAPL', 'MSFT', 'GOOG', 'TSLA', 'AMZN'], period='1min', bar='1min', outside_rth=True)
diff_five_symbols = time.time() - st
print('\n\n#### Five symbols ####')
print(f'{history}')


st = time.time()
history = c.marketdata_history_by_symbols(['AAPL', 'MSFT', 'GOOG', 'TSLA', 'AMZN', 'ADBE', 'AMD', 'COIN', 'META', 'DIS', 'BAC', 'XOM', 'KO', 'WMT', 'V'], period='1min', bar='1min', outside_rth=True)
diff_fifteen_symbols = time.time() - st
print('\n\n#### Fifteen symbols ####')
print(f'{history}')

print(f'\n\n1 conid took: {diff_one_conid:.2f}s')
print(f'1 symbol raw took: {diff_one_symbol_raw:.2f}s')
print(f'1 symbol took: {diff_one_symbol:.2f}s')
print(f'5 symbols took: {diff_five_symbols:.2f}s')
print(f'15 symbols took: {diff_fifteen_symbols:.2f}s')
