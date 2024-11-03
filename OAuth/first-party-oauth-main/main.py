
import oauth_requests
import logging


def main(access_token: str, access_token_secret: str):

    # 1. Request the live sesssion token and its expiration time
    (
        live_session_token,
        live_session_token_expires_ms,
    ) = oauth_requests.live_session_token(
        access_token=access_token,
        access_token_secret=access_token_secret,
    )
    print("Live session token:", live_session_token)
    print("Live session token expires:", live_session_token_expires_ms)

    # 2. Initialize the brokerage session
    brokerage_session_response = oauth_requests.init_brokerage_session(
        access_token=access_token,
        live_session_token=live_session_token,
    )
    if not brokerage_session_response.ok:
        raise Exception(
            "Failed to initialize brokerage session: {}".format(
                brokerage_session_response.text
            )
        )
    brokerage_session_response_data = brokerage_session_response.json()
    print("Brokerage session:", brokerage_session_response_data)

    # 3. Make API requests, for example request market data snapshot
    market_data_snapshot_response = oauth_requests.market_data_snapshot(
        access_token=access_token,
        live_session_token=live_session_token,
        conids=[265598],
        fields=[84, 86],
    )
    if not market_data_snapshot_response.ok:
        raise Exception(
            "Failed to request market data snapshot: {}".format(
                market_data_snapshot_response.text
            )
        )
    market_data_snapshot_response_data = market_data_snapshot_response.json()
    print("Market data snapshot:", market_data_snapshot_response_data)

    # 4 get account data
    account_response=oauth_requests.brokerage_accounts(
        access_token=access_token,
        live_session_token=live_session_token
    )

    if not account_response.ok:
        raise Exception(
            "Failed to request account data: {}".format(
                account_response.text
            )
        )
    account_response_data = account_response.json()
    print("Account response:", account_response_data)



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s", filemode="w", filename="oauth.log")
    access_token = None
    access_token_secret = None
    if access_token is None or access_token_secret is None:
        raise Exception(
            "Please set the access token and access token secret generated in the self-service portal. \
            The self-service portal can be found at: https://ndcdyn.interactivebrokers.com/sso/Login?action=OAUTH&RL=1&ip2loc=US"
        )
        
    main(access_token, access_token_secret)
