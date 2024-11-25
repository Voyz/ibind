"""
REST OAuth.
Minimal example to create a client and test OAuth
"""

#%%

from ibind import IbkrClient

import configparser
from dotenv import load_dotenv
import pandas as pd


load_dotenv()
config = configparser.ConfigParser()
config.read('D:\\git_repos\\oauth_env\\oauth_test.env')

#%%

# Construct the client, set use_oauth=False, if working, try creating a live session by setting use_oath=True
client = IbkrClient(use_oauth=True)
# add self signed certificate - not working right now
# client = IbkrClient(use_oauth=True,cacert='D:\\git_repos\\certificates\\ca_cert.pem')


#%%

# test function to get live session and access tokens
# live_session_token,live_session_token_expires_ms=client.req_live_session_token()


#%%

# print live session token
print(f'live_session_token: {client.live_session_token}')

# print access token
print(f'live_session_token_expires_ms: {client.live_session_token_expires_ms}')

#%%
# get brokerage session
brokerage_session_response=client.initialize_brokerage_session(publish='true',compete='true')
brokerage_session_response.data

#%%
# get account positions
account_positions=client.positions(account_id=config['ibkr']['account_id'])
pd.DataFrame(account_positions.data)

#%%
# get live orders

orders_live=client.live_orders(account_id=config['ibkr']['account_id'])

#%%

# market data

snapshot=client.live_marketdata_snapshot(conids='499871328', fields=['83']) 
pd.DataFrame(snapshot.data)
