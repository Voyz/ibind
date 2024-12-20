"""
REST OAuth.
Minimal example to create a client and test OAuth
"""

import threading
import time
from datetime import datetime
from ibind import IbkrClient
from ibind import var

import pandas as pd
from ibind.support.oauth import req_live_session_token, generate_oauth_headers, prepare_oauth

client = IbkrClient(use_oauth=True,cacert=False)

# print live session token
print(f'live_session_token: {client.live_session_token}')
# print access token
print(f'live_session_token_expires_ms: {client.live_session_token_expires_ms}')

#%%


# Function that contains the while loop
def background_task(client):
    global stop_thread
    while not stop_thread:
        client.tickle()
        now = datetime.now().strftime('%d-%b-%y %H:%M:%S')
        print(f"Tickle...{now}")
        time.sleep(60)  # Sleep for 2 seconds

# Stop the background thread
def stop_tickle(background_thread):
    global stop_thread
    stop_thread = True
    background_thread.join()


# Flag to control the thread
stop_thread = False

# Create a thread for the background task
# background_thread = threading.Thread(target=background_task(client))
background_thread = threading.Thread(target=background_task, args=(client,))

# Set the thread as a daemon so it will not prevent the program from exiting
background_thread.daemon = True

# Start the thread
background_thread.start()

# Let it run for 3 minutes (180 seconds)
# time.sleep(180)
# Stop the background tickle
# stop_tickle(background_thread)

#%%

transactions = client.transaction_history(account_ids=var.IBIND_ACCOUNT_ID,conids='391638829',currency='HKD',days='30')
# ExternalBrokerError: IbkrClient: response error Result(data=None, request={'url': 'https://api.ibkr.com/v1/api/pa/transactions'}) :: 400 :: Bad Request :: {"error":"Bad Request: account id missing","statusCode":400}

account_summary=client.account_performance(account_ids=var.IBIND_ACCOUNT_ID,period="7D")
account_summary

# ExternalBrokerError: IbkrClient: response error Result(data=None, request={'url': 'https://api.ibkr.com/v1/api/pa/performance'}) :: 400 :: Bad Request :: {"error":"Bad Request: account id missing","statusCode":400}


#%%
accounts=client.portfolio_accounts()
pd.DataFrame(accounts.data).T

#%%
# positions
positions=client.positions(account_id=var.IBIND_ACCOUNT_ID)
pd.DataFrame(positions.data)
#%%
# get brokerage session
brokerage_session_response=client.initialize_brokerage_session(publish='true',compete='true')
brokerage_session_response.data
#%%
# get account positions
portfolio_summary=client.portfolio_summary(account_id=var.IBIND_ACCOUNT_ID)
pd.DataFrame(portfolio_summary.data).T
#%%
# get live orders
orders_live=client.live_orders(account_id=var.IBIND_ACCOUNT_ID)
pd.DataFrame(orders_live.data)
#%%
# trades
trades=client.trades(days='3',account_id=var.IBIND_ACCOUNT_ID)
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
