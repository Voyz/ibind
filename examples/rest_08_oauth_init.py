"""
REST OAuth.
Minimal example to create a client and test OAuth
"""

#%%

from ibind import IbkrClient

# Construct the client, set use_oauth=False, if working, try creating a live session by setting use_oath=True
client = IbkrClient(use_oauth=True)
# add self signed certificate - not working right now
# client = IbkrClient(use_oauth=True,cacert='D:\\git_repos\\certificates\\ca_cert.pem')


#%%

# get live session and access tokens
# live_session_token,access_token=client.req_live_session_token()

# print live session token
print(f'live_session_token: {client.live_session_token}')


# print access token
print(f'access_token: {client.access_token}')
