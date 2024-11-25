
# ./.venv/Scripts/Activate.ps1

#%%
import OAuth.oauth_requests as oauth_requests
import logging
import configparser
from dotenv import load_dotenv


load_dotenv()
config = configparser.ConfigParser()
# config.read('../.env/datamodels_paper.env')
config.read('D:\\git_repos\\oauth_env\\oauth_test.env')


access_token=config['ibkr']['access_token']
access_token_secret=config['ibkr']['access_token_secret']

#%%

#  1. Request the live sesssion token and its expiration time
live_session_token,live_session_token_expires_ms = oauth_requests.req_live_session_token(access_token=config['ibkr']['access_token'],access_token_secret=config['ibkr']['access_token_secret'])

#%%

# print live session token
print(f'live_session_token: {live_session_token}')

# print access token
print(f'access_token: {access_token}')

#%%

brokerage_session_response = oauth_requests.init_brokerage_session_dev(
    access_token=access_token,
    live_session_token=live_session_token)

brokerage_session_response_data = brokerage_session_response.json()
brokerage_session_response_data

#%%


port_accounts=oauth_requests.portfolio_accounts(access_token=access_token, live_session_token=live_session_token)
port_accounts.json()

#%%

port_summary=oauth_requests.portfolio_account_summary(access_token=access_token,
    live_session_token=live_session_token,
    account_id=config['ibkr']['account_id'])

port_summary.json()

#%%

api_status=oauth_requests.auth_status(
    access_token=access_token, 
    live_session_token=live_session_token)

api_status.json()

#%%

market_data_snapshot_response = oauth_requests.market_data_snapshot(
    access_token=access_token,
    live_session_token=live_session_token,
    conids=[467996780,548854840],
    fields=[84, 86])

market_data_snapshot_response.json()

#%%

market_data_history_response=oauth_requests.market_data_history(
    access_token=access_token,
    live_session_token=live_session_token, 
    conid='467996780', 
    bar='1d', 
    period='1mth',
    exchange='SEHK'
    )

market_data_history_response.json()

#%%



account_live='U16060442'
account_paper='DUD057603'

brokerage_session_response = oauth_requests.init_brokerage_session(access_token=access_token,live_session_token=live_session_token)

positions_response=oauth_requests.positions(
    access_token=access_token,
    live_session_token=live_session_token,
    account_id=account_paper,
    page= 0)

positions_response

# if response.ok:
#     positions=response.json()
# else:
#     positions=None

# response

#%%

account_summary=oauth_requests.portfolio_account_summary(access_token=access_token, 
                                                         live_session_token=live_session_token,
                                                         account_id=account_id) 

account_summary.json()

#%%

response=oauth_requests.live_orders(
    access_token=access_token,
    live_session_token=live_session_token)

response.json()

# if response.ok:
#     orders_open=response.json()
# else:
#      print(response)

# orders_open     

#%%

trades=oauth_requests.trades(
    access_token=access_token,
    live_session_token=live_session_token,
    account_id=config['ibkr']['account_id'],
    days='3')

trades.json()

#%%

contract_info=oauth_requests.contract_information_by_conid( conid='467996780',
                                                           access_token=access_token,
                                                           live_session_token=live_session_token)

contract_info.json()

#%%
from ibind import IbkrClient, make_order_request, QuestionType, ibind_logs_initialize

order_request = make_order_request(
    conid='467996780',
    side='BUY',
    price=None,
    quantity=200,
    order_type='MKT',
    acct_id=account_id,
    )

order_response=oauth_requests.place_order(
    access_token=access_token,
    live_session_token=live_session_token,
    account_id=account_id,
    order_request=order_request,
    answers=answers)


#%% logout


oauth_requests.logout(access_token=access_token, live_session_token=live_session_token)

