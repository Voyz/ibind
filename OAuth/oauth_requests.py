

#%%

import requests
import logging
import dotenv
import time
import os

import oauth_utils as oauth_utils
import configparser
from dotenv import load_dotenv



from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_parameters


def pem_to_dh_prime(pem_file_path):
    with open(pem_file_path, 'rb') as pem_file:
        pem_data = pem_file.read()
    
    parameters = load_pem_parameters(pem_data)
    prime = parameters.parameter_numbers().p
    prime_hex=hex(prime)
    return prime_hex



load_dotenv()
config = configparser.ConfigParser()
# config.read('../.env/datamodels_paper.env')
config.read('D:\\git_repos\\oauth_env\\oauth_test.env')
config['ibkr']['DH_PRIME']=pem_to_dh_prime(pem_file_path=config['ibkr']['DH_PRIME_FP'])


#%%


def get_oauth_header(
    request_method: str,
    request_url: str,
    oauth_token: str | None = None,
    live_session_token: str | None = None,
    extra_headers: dict[str, str] | None = None,
    request_params: dict[str, str] | None = None,
    signature_method: str = "HMAC-SHA256",
    prepend: str | None = None,
) -> requests.Response:
    
    headers = {
        "oauth_consumer_key": config['ibkr']["CONSUMER_KEY"],
        "oauth_nonce": oauth_utils.generate_oauth_nonce(),
        "oauth_signature_method": signature_method,
        "oauth_timestamp": oauth_utils.generate_request_timestamp()
    }

    if oauth_token:
        headers.update({"oauth_token": oauth_token})
    if extra_headers:
        headers.update(extra_headers)

    base_string = oauth_utils.generate_base_string(
        request_method=request_method,
        request_url=request_url,
        request_headers=headers,
        request_params=request_params,
        prepend=prepend
    )
    logging.info(
        msg={
            "message": "generated base string",
            "timestamp": time.time(),
            "details": {
                "base_string": base_string,
                "request_method": request_method,
                "request_url": request_url,
                "request_headers": headers,
                "request_params": request_params,
                "prepend": prepend,
            },
        }
    )
    if signature_method == "HMAC-SHA256":
        headers.update(
            {
                "oauth_signature": oauth_utils.generate_hmac_sha_256_signature(
                    base_string=base_string,
                    live_session_token=live_session_token,
                )
            }
        )
    else:
        headers.update(
            {
                "oauth_signature": oauth_utils.generate_rsa_sha_256_signature(
                    base_string=base_string,
                    private_signature_key=oauth_utils.read_private_key(
                        config['ibkr']["SIGNATURE_KEY_FP"]
                    ),
                )
            }
        )
    logging.info(
        msg={
            "message": "generated signature",
            "timestamp": time.time(),
            "details": {
                "signature": headers["oauth_signature"],
                "signature_method": signature_method,
            },
        }
    )

    header_oauth={
            "Authorization": oauth_utils.generate_authorization_header_string(
                request_data=headers,
                realm=config['ibkr']["REALM"],
            )
        }

    return header_oauth

# Authentication flow

def req_live_session_token(
    access_token: str,
    access_token_secret: str,
) -> tuple[str, int]:

    REQUEST_URL = "https://api.ibkr.com/v1/api/oauth/live_session_token"
    REQUEST_METHOD = "POST"
    ENCRYPTION_METHOD = "RSA-SHA256"
    dh_random = oauth_utils.generate_dh_random_bytes()
    dh_challenge = oauth_utils.generate_dh_challenge(
        dh_prime=config['ibkr']['DH_PRIME'],
        dh_generator=int(config['ibkr']['DH_GENERATOR']),
        dh_random=dh_random
    )
    prepend = oauth_utils.calculate_live_session_token_prepend(
        access_token_secret,
        oauth_utils.read_private_key(config['ibkr']["ENCRYPTION_KEY_FP"])
    )

    extra_headers={"diffie_hellman_challenge": dh_challenge}

    header_oauth = get_oauth_header(
        request_method=REQUEST_METHOD,
        request_url=REQUEST_URL,
        oauth_token=access_token,
        signature_method=ENCRYPTION_METHOD,
        extra_headers=extra_headers,
        prepend=prepend
    )

    response = requests.request(
        method=REQUEST_METHOD,
        url=REQUEST_URL,
        headers=header_oauth,
        params=None,
        timeout=10,
    )

    if not response.ok:
        raise Exception(f"Live session token request failed: {response.text}")
    response_data = response.json()
    lst_expires = response_data["live_session_token_expiration"]
    dh_response = response_data["diffie_hellman_response"]
    lst_signature = response_data["live_session_token_signature"]
    live_session_token = oauth_utils.calculate_live_session_token(
        dh_prime=config['ibkr']["DH_PRIME"],
        dh_random_value=dh_random,
        dh_response=dh_response,
        prepend=prepend,
    )
    if not oauth_utils.validate_live_session_token(
        live_session_token=live_session_token,
        live_session_token_signature=lst_signature,
        consumer_key=config['ibkr']["CONSUMER_KEY"],
    ):
        raise Exception("Live session token validation failed.")

    return live_session_token, lst_expires


# Session management

def init_brokerage_session(
    access_token: str, 
    live_session_token: str
) -> requests.Response:
    params = {
        "compete": "true",
        "publish": "true",
    }

    request_url="https://api.ibkr.com/v1/api/iserver/auth/ssodh/init"

    header_oauth= get_oauth_header(
        request_method="POST",
        request_url=request_url,   
        oauth_token=access_token,
        live_session_token=live_session_token,
        request_params=params
    )

    response = requests.request(
        method='POST',
        url=request_url,
        headers=header_oauth,
        params=params,
        timeout=10,
    )

    return response


# def init_brokerage_session(
#     access_token: str, live_session_token: str
# ) -> requests.Response:
#     params = {
#         "compete": "true",
#         "publish": "true",
#     }
#     return send_oauth_request(
#         request_method="POST",
#         request_url="https://api.ibkr.com/v1/api/iserver/auth/ssodh/init",
#         oauth_token=access_token,
#         live_session_token=live_session_token,
#         request_params=params,
#     )


def tickle(access_token: str, live_session_token: str) -> requests.Response:
    return get_oauth_header(
        request_method="POST",
        request_url="https://api.ibkr.com/v1/api/tickle",
        oauth_token=access_token,
        live_session_token=live_session_token,
    )


def auth_status(access_token: str, live_session_token: str) -> requests.Response:
    return get_oauth_header(
        request_method="GET",
        request_url="https://api.ibkr.com/v1/api/iserver/auth/status",
        oauth_token=access_token,
        live_session_token=live_session_token,
    )


def logout(access_token: str, live_session_token: str) -> requests.Response:
    return get_oauth_header(
        request_method="POST",
        request_url="https://api.ibkr.com/v1/api/logout",
        oauth_token=access_token,
        live_session_token=live_session_token,
    )


# Account information & management


def brokerage_accounts(access_token: str, live_session_token: str) -> requests.Response:
    return get_oauth_header(
        request_method="GET",
        request_url="https://api.ibkr.com/v1/api/iserver/accounts",
        oauth_token=access_token,
        live_session_token=live_session_token,
    )


# Portfolio information


def account_ledger(
    access_token: str, live_session_token: str, account_id: str
) -> requests.Response:
    return get_oauth_header(
        request_method="GET",
        request_url=f"https://api.ibkr.com/v1/api/account/{account_id}/ledger",
        oauth_token=access_token,
        live_session_token=live_session_token,
    )



def positions(
        access_token: str,
        live_session_token: str,
        account_id: str,
        page: int = 0
    ) -> requests.Response:  
        """
        Returns a list of positions for the given account. The endpoint supports paging, each page will return up to 100 positions.

        Parameters:
            account_id (str, optional): The account ID for which account should place the order.
            page_id (str, optional): The “page” of positions that should be returned. One page contains a maximum of 100 positions. Pagination starts at 0.
            model (str, optional): Code for the model portfolio to compare against.
            sort (str, optional): Declare the table to be sorted by which column.
            direction (str, optional): The order to sort by. 'a' means ascending 'd' means descending.
            period (str, optional): Period for pnl column. Value Format: 1D, 7D, 1M.
        """

        return get_oauth_header(
            request_method="GET",
            request_url=f"https://api.ibkr.com/v1/api/iserver/portfolio2/{account_id}/positions",
            oauth_token=access_token,
            live_session_token=live_session_token
        )


def portfolio_accounts(access_token: str, live_session_token: str) -> requests.Response:
    return get_oauth_header(
        request_method="GET",
        request_url=f"https://api.ibkr.com/v1/api/portfolio/accounts",
        oauth_token=access_token,
        live_session_token=live_session_token,
    )


# Market data requests


def market_data_snapshot(
    access_token: str,
    live_session_token: str,
    conids: list[int],
    fields: list[int],
    since: int = 0,
) -> requests.Response:
    params = {
        "since": since,
        "conids": ",".join([str(conid) for conid in conids]),
        "fields": ",".join([str(field) for field in fields]),
    }
    return get_oauth_header(
        request_method="GET",
        request_url="https://api.ibkr.com/v1/api/iserver/marketdata/snapshot",
        oauth_token=access_token,
        live_session_token=live_session_token,
        request_params=params,
    )



def trades(
    access_token: str,
    live_session_token: str,
    days:str,
    account_id: str,
    ) -> requests.Response:

        """
        Returns a list of trades for the currently selected account for current day and six previous days. It is advised to call this endpoint once per session.

        Parameters:
            days (str): Specify the number of days to receive executions for, up to a maximum of 7 days. If unspecified, only the current day is returned.
            account_id (str): Include a specific account identifier or allocation group to retrieve trades for.
        """
        params ={
                'days': days,
                'accountId': account_id,
            }

        return get_oauth_header(
            request_method="GET",
            request_url="https://api.ibkr.com/v1/api/iserver/account/trades",
            oauth_token=access_token,
            live_session_token=live_session_token,
            request_params=params,
        )