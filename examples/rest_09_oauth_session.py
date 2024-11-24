"""
REST OAuth.
Minimal example to create a client, start OAuth and query a few endpoints
"""

#%%

from ibind import IbkrClient

# Construct the client, set use_oauth=False, if working, try creating a live session by setting use_oath=True
client = IbkrClient(use_oauth=True)
# add self signed certificate - not working right now
# client = IbkrClient(use_oauth=True,cacert='D:\\git_repos\\certificates\\ca_cert.pem')

#%%

# print live session token
print(f'live_session_token: {client.live_session_token}')

# print access token
print(f'access_token: {client.access_token}')

#%%
# Initialize the brokerage session

def init_brokerage_session():
    params = {
        "compete": "true",
        "publish": "true",
    }

    request_url="https://api.ibkr.com/v1/api/iserver/auth/ssodh/init"

    header_oauth= client.get_headers(
        request_method="POST",
        request_url=request_url,
        oauth_token=client.access_token,
        live_session_token=client.live_session_token,
        request_params=params
    )
    
    result=client.post(path=request_url,params=params,headers = header_oauth, log = True)

    return result


brokerage_session_response = init_brokerage_session()

# if not brokerage_session_response.ok:
#     raise Exception(
#         "Failed to initialize brokerage session: {}".format(
#             brokerage_session_response.text
#         )
#     )
# brokerage_session_response_data = brokerage_session_response.json()

#%%
# account

