"""
REST OAuth.
Minimal example to create a client and test OAuth
"""

#%%

from ibind import IbkrClient
import configparser
from dotenv import load_dotenv
import pandas as pd
from ibind.support.oauth import req_live_session_token, generate_oauth_headers, prepare_oauth


load_dotenv()
config = configparser.ConfigParser()

config.read('D:\\git_repos\\oauth_env\\oauth_test.env')

# Construct the client, set use_oauth=False, if working, try creating a live session by setting use_oath=True
client = IbkrClient(use_oauth=True,cacert=False)
# add self signed certificate - not working right now
# client = IbkrClient(use_oauth=True,cacert='D:\\git_repos\\certificates\\ca_cert.pem')

#%%

# print live session token
print(f'live_session_token: {client.live_session_token}')

# print access token
print(f'live_session_token_expires_ms: {client.live_session_token_expires_ms}')

#%%

# test get live session code, not in client init

# test function to get live session and access tokens
# live_session_token,live_session_token_expires_ms=client.test_get_live_session_token()

# # print live session token
# print(f'live_session_token: {live_session_token}')

# # print access token
# print(f'live_session_token_expires_ms: {live_session_token_expires_ms}')

#%%

client.tickle()

#%%

# check if extra_headers are needed for non live_session_token fun, the add dh_challenge which may cause request to fail

# get brokerage session
brokerage_session_response=client.initialize_brokerage_session(publish='true',compete='true')
brokerage_session_response.data

#%%

headers = client.get_headers(request_method="POST", request_url="https://api.ibkr.com/v1/api/iserver/auth/ssodh/init")

#%%
import requests
import OAuth.oauth_requests as oauth_requests


params = {
        "compete": "true",
        "publish": "true",
    }

request_url="https://api.ibkr.com/v1/api/iserver/auth/ssodh/init"
access_token=config['ibkr']["ACCESS_TOKEN"]
live_session_token=client.live_session_token


# header_oauth= oauth_requests.get_oauth_header(
#     request_method="POST",
#     request_url=request_url,   
#     oauth_token=access_token,
#     live_session_token=live_session_token,
#     request_params=params
# )

headers = client.get_headers(request_method="POST", request_url="https://api.ibkr.com/v1/api/iserver/auth/ssodh/init")

response = requests.request(
    method='POST',
    url=request_url,
    headers=headers,
    params=params,
    timeout=10,
    verify=False
)

response.json()



#%%

import OAuth.oauth_requests as oauth_requests


brokerage_session_response = oauth_requests.init_brokerage_session(
    access_token=config['ibkr']["ACCESS_TOKEN"],
    live_session_token=client.live_session_token)

brokerage_session_response_data = brokerage_session_response.json()
brokerage_session_response_data


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

#%%

client.logout()
