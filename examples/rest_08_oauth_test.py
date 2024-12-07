"""
REST OAuth.
Minimal example to create a client and test OAuth
"""

#%%


import threading
import time
from datetime import datetime
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

#  run tickle every 60s in its own thread to keep connection open

# Flag to control the thread 
stop_thread = False

# Function that contains the while loop
def background_task():
    global stop_thread
    while not stop_thread:
        client.tickle()
        now = datetime.now().strftime('%d-%b-%y %H:%M:%S')
        print(f"Tickle...{now}")
        time.sleep(60)  # Sleep for 2 seconds

# Create a thread for the background task
background_thread = threading.Thread(target=background_task)

# Set the thread as a daemon so it will not prevent the program from exiting
background_thread.daemon = True

# Start the thread
background_thread.start()

# Stop the background thread 
def stop_tickle():
    global stop_thread
    stop_thread = True 
    background_thread.join()

#%%

accounts=client.portfolio_accounts()
pd.DataFrame(accounts.data).T

#%%
# not working
account_summary=client.account_performance(account_ids=config['ibkr']['account_id'],period="7D")
account_summary

#%%
# positions

positions=client.positions(account_id=config['ibkr']['account_id'])
pd.DataFrame(positions.data)


#%%
# get brokerage session
brokerage_session_response=client.initialize_brokerage_session(publish='true',compete='true')
brokerage_session_response.data

#%%

# get account positions
portfolio_summary=client.portfolio_summary(account_id=config['ibkr']['account_id'])
pd.DataFrame(portfolio_summary.data).T

#%%
# get live orders
orders_live=client.live_orders(account_id=config['ibkr']['account_id'])
pd.DataFrame(orders_live.data)

#%%
# trades
trades=client.trades(days='3',account_id=config['ibkr']['account_id'])
pd.DataFrame(trades.data)

#%%

# snapshot
snapshot=client.live_marketdata_snapshot(conids='391638829', fields=['83','84','85']) 
pd.DataFrame(snapshot.data)

#%%
# historical market data

market_data=client.marketdata_history_by_conid(conid='391638829',bar='1d',period='1m',exchange='SEHK')
market_data.data

#%%

client.logout()

#%%

# test get live session code, not in client init

# test function to get live session and access tokens
# live_session_token,live_session_token_expires_ms=client.test_get_live_session_token()

# # print live session token
# print(f'live_session_token: {live_session_token}')

# # print access token
# print(f'live_session_token_expires_ms: {live_session_token_expires_ms}')
