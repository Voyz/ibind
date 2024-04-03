import os
import time

import ibind
from ibind import IbkrClient

ibind.logs.initialize(log_to_file=False)

account_id = os.getenv('IBKR_ACCOUNT_ID', '[YOUR_ACCOUNT_ID]')
cacert = os.getenv('IBKR_CACERT', None) # insert your cacert path here
c = IbkrClient(
    url='https://localhost:5000/v1/api/',
    account_id=account_id,
    cacert=cacert,
)

st = time.time()
history = c.marketdata_history_by_symbols('AAPL', period='1min', bar='1min', outside_rth=True)
diff1 = time.time() - st
print('#### One symbol ####')
print(f'{history}')


st = time.time()
history = c.marketdata_history_by_symbols(['AAPL', 'MSFT', 'GOOG', 'TSLA', 'AMZN'], period='1min', bar='1min', outside_rth=True)
diff2 = time.time() - st
print('\n\n#### Five symbols ####')
print(f'{history}')


st = time.time()
history = c.marketdata_history_by_symbols(['AAPL', 'MSFT', 'GOOG', 'TSLA', 'AMZN', 'ADBE', 'AMD', 'COIN', 'META', 'DIS', 'BAC', 'XOM', 'KO', 'WMT', 'V'], period='1min', bar='1min', outside_rth=True)
diff3 = time.time() - st
print('\n\n#### Fifteen symbols ####')
print(f'{history}')

print(f'\n\n1 symbol took: {diff1:.2f}s')
print(f'5 symbols took: {diff2:.2f}s')
print(f'15 symbols took: {diff3:.2f}s')
