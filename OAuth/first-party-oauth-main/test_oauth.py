#%%
import oauth_requests
import oauth_utils
import logging
from enum import Enum, EnumMeta
import datetime
import dotenv
import configparser
from dotenv import load_dotenv
import os


class QuestionType(Enum):
    PRICE_PERCENTAGE_CONSTRAINT = 'price exceeds the Percentage constraint of 3%'
    ORDER_VALUE_LIMIT = 'exceeds the Total Value Limit of'
    MISSING_MARKET_DATA = 'You are submitting an order without market data. We strongly recommend against this as it may result in erroneous and unexpected trades.'
    STOP_ORDER_RISKS = 'You are about to submit a stop order. Please be aware of the various stop order types available and the risks associated with each one.'
    CLOSE_POSITION="The closing order quantity is greater than your current position.Are you sure you want to submit this order?"
    EXCEEDS_SIZE_LIMIT="The following order size exceeds the Size Limit"
    SANITY_CHECK="Are you sure you want to submit this order?"

answers={
            QuestionType.PRICE_PERCENTAGE_CONSTRAINT: True,
            QuestionType.ORDER_VALUE_LIMIT: True,
            QuestionType.MISSING_MARKET_DATA:True,
            QuestionType.STOP_ORDER_RISKS:True,
            QuestionType.CLOSE_POSITION:True,
            QuestionType.EXCEEDS_SIZE_LIMIT:True,
            QuestionType.SANITY_CHECK:True
        }

# Read the environment variables and configure the environment
load_dotenv()
config = configparser.ConfigParser()
config.read('../oauth.env')

account_id=config['ibkr']['ACCOUNT_ID']
consumer_key = config['consumer_key']['CONSUMER_KEY']
access_token=config['access_token']['ACCESS_TOKEN']
access_token_secret=config['access_token_secret']['ACCESS_TOKEN_SECRET']
signature_key_fp=config['keys']['SIGNATURE_KEY_FP']
encription_key_fp=config['keys']['ENCRYPTION_KEY_FP']
dh_prime_fp=config['Diffie_Hellman']['DH_PRIME_FP']
dh_generator=config['Diffie_Hellman']['DH_GENERATOR']
realm=config['realm']['REALM']


#%%

# logger.info('starting oauth')

#%%


live_session_token,live_session_token_expires_ms = oauth_requests.live_session_token(
    access_token=access_token,
    access_token_secret=access_token_secret)

#%%
# this is the pre-flight data request call


brokerage_session_response = oauth_requests.init_brokerage_session(
    access_token=access_token,
    live_session_token=live_session_token)

brokerage_session_response_data = brokerage_session_response.json()
brokerage_session_response_data

#%%

account_ledger=oauth_requests.account_ledger(access_token=access_token, 
                                             live_session_token=live_session_token, 
                                             account_id=account_id) 
account_ledger.json()

#%%

account=oauth_requests.brokerage_accounts(access_token=access_token, live_session_token=live_session_token)
account.json()

#%%

port_accounts=oauth_requests.portfolio_accounts(access_token=access_token, live_session_token=live_session_token)
port_accounts.json()

#%%

port_summary=oauth_requests.portfolio_account_summary(access_token=access_token,
    live_session_token=live_session_token,
    account_id=account_id)

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

positions_response=oauth_requests.positions(
    access_token=access_token,
    live_session_token=live_session_token,
    account_id=account_id,
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
    account_id=account_id,
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


#%%
