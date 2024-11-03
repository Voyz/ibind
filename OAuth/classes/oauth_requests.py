
#%%
import pprint
import requests
import logging
import dotenv
import configparser
from dotenv import load_dotenv
import time
import datetime
import os
import oauth_utils

from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_parameters

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

# Read the environment variables and configure the environment
# dotenv.load_dotenv('../oauth.env')
# app_config = {
#     "CONSUMER_KEY": os.getenv("CONSUMER_KEY"),
#     "SIGNATURE_KEY_FP": os.getenv("SIGNATURE_KEY_FP"),
#     "ENCRYPTION_KEY_FP": os.getenv("ENCRYPTION_KEY_FP"),
#     "DH_PRIME": os.getenv("DH_PRIME"),
#     "DH_GENERATOR": int(os.getenv("DH_GENERATOR", default=2)),
#     "REALM": os.getenv("REALM", default="limited_poa"),
# }

# Helper functions

class oauth_requests():
    def __init__(self):
        self.oauth_utils=OAuth_Utils()

    def setup_logger(self):

        # Clear the log file
        log_file='oauth.log'
        with open(log_file, 'w'):
            pass

        # Create a logger
        logger = logging.getLogger('oauth')
        logger.setLevel(logging.INFO) 
        # Create a file handler and set the level to info
        fh = logging.FileHandler(f'./{log_file}')
        fh.setLevel(logging.INFO)

        # Create a formatter and set it for the handler
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)

        # Add the handler to the logger
        logger.addHandler(fh)

        return logger  

    # logger=setup_logger()



    def pem_to_dh_prime(self,pem_file_path):
        with open(pem_file_path, 'rb') as pem_file:
            pem_data = pem_file.read()
        
        parameters = load_pem_parameters(pem_data)
        prime = parameters.parameter_numbers().p
        return prime


    def self.send_oauth_request(
        self,
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
            "oauth_consumer_key": consumer_key,
            "oauth_nonce": oauth_utils.generate_oauth_nonce(),
            "oauth_signature_method": signature_method,
            "oauth_timestamp": oauth_utils.generate_request_timestamp(),
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
            prepend=prepend,
        )
        logger.info(
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
                            signature_key_fp
                        ),
                    )
                }
            )
        logger.info(
            msg={
                "message": "generated signature",
                "timestamp": time.time(),
                "details": {
                    "signature": headers["oauth_signature"],
                    "signature_method": signature_method,
                },
            }
        )
        response = requests.request(
            method=request_method,
            url=request_url,
            headers={
                "Authorization": oauth_utils.generate_authorization_header_string(
                    request_data=headers,
                    realm=realm,
                )
            },
            params=request_params,
            timeout=10,
        )
        logger.info(
            msg={
                "message": "sent oauth request",
                "timestamp": time.time(),
                "details": {
                    "request_method": request_method,
                    "request_url": response.request.url,
                    "request_headers": response.request.headers,
                    "request_body": response.request.body,
                    "response_status_code": response.status_code,
                    "response_error_message": response.text if not response.ok else None,
                },
            }
        )
        return response


    # Authentication flow


    def live_session_token(self,access_token: str,access_token_secret: str) -> tuple[str, int]:
        REQUEST_URL = "https://api.ibkr.com/v1/api/oauth/live_session_token"
        REQUEST_METHOD = "POST"
        ENCRYPTION_METHOD = "RSA-SHA256"
        dh_random = oauth_utils.generate_dh_random_bytes()
        dh_prime=oauth_utils.pem_to_dh_prime(pem_file_path=dh_prime_fp)
        dh_challenge = oauth_utils.generate_dh_challenge(
            dh_prime=dh_prime,
            dh_generator=dh_generator,
            dh_random=dh_random,
        )
        prepend = oauth_utils.calculate_live_session_token_prepend(
            access_token_secret,
            oauth_utils.read_private_key(
                encription_key_fp,
            ),
        )
        response = self.self.send_oauth_request(
            request_method=REQUEST_METHOD,
            request_url=REQUEST_URL,
            oauth_token=access_token,
            signature_method=ENCRYPTION_METHOD,
            extra_headers={
                "diffie_hellman_challenge": dh_challenge,
            },
            prepend=prepend,
        )
        if not response.ok:
            raise Exception(f"Live session token request failed: {response.text}")
        response_data = response.json()
        lst_expires = response_data["live_session_token_expiration"]
        dh_response = response_data["diffie_hellman_response"]
        lst_signature = response_data["live_session_token_signature"]
        live_session_token = oauth_utils.calculate_live_session_token(
            dh_prime=dh_prime,
            dh_random_value=dh_random,
            dh_response=dh_response,
            prepend=prepend,
        )
        if not oauth_utils.validate_live_session_token(
            live_session_token=live_session_token,
            live_session_token_signature=lst_signature,
            consumer_key=consumer_key,
        ):
            raise Exception("Live session token validation failed.")

        return live_session_token, lst_expires


    # Session management

    def init_brokerage_session(
        self,
        access_token: str, live_session_token: str
    ) -> requests.Response:
        params = {
            "compete": "true",
            "publish": "true",
        }
        return self.send_oauth_request(
            request_method="POST",
            request_url="https://api.ibkr.com/v1/api/iserver/auth/ssodh/init",
            oauth_token=access_token,
            live_session_token=live_session_token,
            request_params=params,
        )


    def tickle(self,access_token: str, live_session_token: str) -> requests.Response:
        return self.send_oauth_request(
            request_method="POST",
            request_url="https://api.ibkr.com/v1/api/tickle",
            oauth_token=access_token,
            live_session_token=live_session_token,
        )


    def auth_status(self,access_token: str, live_session_token: str) -> requests.Response:
        return self.send_oauth_request(
            request_method="GET",
            request_url="https://api.ibkr.com/v1/api/iserver/auth/status",
            oauth_token=access_token,
            live_session_token=live_session_token,
        )


    def logout(self,access_token: str, live_session_token: str) -> requests.Response:
        return self.send_oauth_request(
            request_method="POST",
            request_url="https://api.ibkr.com/v1/api/logout",
            oauth_token=access_token,
            live_session_token=live_session_token,
        )


    # Account information & management


    def brokerage_accounts(self,access_token: str, live_session_token: str) -> requests.Response:
        return self.send_oauth_request(
            request_method="GET",
            request_url="https://api.ibkr.com/v1/api/iserver/accounts",
            oauth_token=access_token,
            live_session_token=live_session_token
        )


    #  contract information
    def contract_information_by_conid(self,conid: str, access_token:str, live_session_token:str): 
            """
            Requests full contract details for the given conid.
            Parameters:
                conid (str): Contract ID for the desired contract information.
            """
            return self.send_oauth_request(
            request_method="GET",
            request_url=f"https://api.ibkr.com/v1/api/iserver/contract/{conid}/info",
            oauth_token=access_token,
            live_session_token=live_session_token)
        

    # Portfolio information


    def account_ledger(self,access_token: str, live_session_token: str, account_id: str) -> requests.Response:
        return self.send_oauth_request(
            request_method="GET",
            request_url=f"https://api.ibkr.com/v1/api/account/{account_id}/ledger",
            oauth_token=access_token,
            live_session_token=live_session_token,
        )


    def portfolio_accounts(self,access_token: str, live_session_token: str) -> requests.Response:
        return self.send_oauth_request(
            request_method="GET",
            request_url=f"https://api.ibkr.com/v1/api/portfolio/accounts",
            oauth_token=access_token,
            live_session_token=live_session_token,
        )


    def portfolio_account_summary(self,access_token: str, live_session_token: str,account_id:str) -> requests.Response:
        return self.send_oauth_request(
            request_method="GET",
            request_url=f"https://api.ibkr.com/v1/api/portfolio/{account_id}/summary",
            oauth_token=access_token,
            live_session_token=live_session_token,
        )



    def positions(
            self,
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

            return self.send_oauth_request(
                request_method="GET",
                request_url=f"https://api.ibkr.com/v1/api/iserver/portfolio/{account_id}/positions/{page}",
                oauth_token=access_token,
                live_session_token=live_session_token
            )


    # Market data requests


    def market_data_snapshot(
        self,
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
        return self.send_oauth_request(
            request_method="GET",
            request_url="https://api.ibkr.com/v1/api/iserver/marketdata/snapshot",
            oauth_token=access_token,
            live_session_token=live_session_token,
            request_params=params,
        )



    def market_data_history(
        self,
        access_token: str,
        live_session_token: str,
        conid: str,
        bar: str,
        period: str = None,
        exchange: str = None,    
        outside_rth: bool = None,
        start_time: datetime.datetime = None
    ) -> requests.Response:
        params = {
                    'conid': conid,
                    'bar': bar,
                    'exchange': exchange,
                    'period': period,
                    'outsideRth': outside_rth,
                    'startTime': start_time
                }
        return self.send_oauth_request(
            request_method="GET",
            request_url="https://api.ibkr.com/v1/api/iserver/marketdata/history",
            oauth_token=access_token,
            live_session_token=live_session_token,
            request_params=params,
        )

    #  Orders

    def live_orders(
        self,
        access_token: str,
        live_session_token: str
        ) -> requests.Response:  
            """
            Retrieves live orders with optional filtering. The filters, if provided, should be a list of strings. These filters are then converted and sent as a comma-separated string in the request to the API.

            Parameters:
                filters (List[str], optional): A list of strings representing the filters to be applied. Defaults to None
                force (bool, optional): Force the system to clear saved information and make a fresh request for orders. Submission will appear as a blank array. Defaults to False.
                account_id (str): For linked accounts, allows users to view orders on sub-accounts as specified.

            Available filters:
                * Inactive:
                    Order was received by the system but is no longer active because it was rejected or cancelled.
                * PendingSubmit:
                    Order has been transmitted but have not received confirmation yet that order accepted by destination exchange or venue.
                * PreSubmitted:
                    Simulated order transmitted but the order has yet to be elected. Order is held by IB system until election criteria are met.
                * Submitted:
                    Order has been accepted by the system.
                * Filled:
                    Order has been completely filled.
                * PendingCancel:
                    Sent an order cancellation request but have not yet received confirmation order cancelled by destination exchange or venue.
                * Cancelled:
                    The balance of your order has been confirmed canceled by the system.
                * WarnState:
                    Order has a specific warning message such as for basket orders.
                * SortByTime:
                    There is an initial sort by order state performed so active orders are always above inactive and filled then orders are sorted chronologically.

            Note:
                - This endpoint requires a pre-flight request. Orders is the list of live orders (cancelled, filled, submitted).

            """

            return self.send_oauth_request(
                request_method="GET",
                request_url="https://api.ibkr.com/v1/api/iserver/account/orders",
                oauth_token=access_token,
                live_session_token=live_session_token,
                # request_params=None,
            )
            
    def place_order(
        self,
        access_token: str,
        live_session_token: str,
        account_id: str,    
        order_request, 
        answers    
        ) -> requests.Response:  

            """
            When connected to an IServer Brokerage Session, this endpoint will allow you to submit orders.

            Notes:
            - With the exception of OCA groups and bracket orders, the orders endpoint does not currently support the placement of unrelated orders in bulk.
            - Developers should not attempt to place another order until the previous order has been fully acknowledged, that is, when no further warnings are received deferring the client to the reply endpoint.

            Parameters:
                account_id (str): The account ID for which account should place the order.
                answers (Answers): List of question-answer pairs for order submission process.
                order_request (OneOrMany[dict]): Used to the order content.

            Keep this in mind:
            https://interactivebrokers.github.io/tws-api/automated_considerations.html#order_placement
            """

            params={"orders": order_request}
            
            result= self.send_oauth_request(
                request_method="POST",
                request_url=f"https://api.ibkr.com/v1/api/iserver/account/{account_id}/orders",
                oauth_token=access_token,
                live_session_token=live_session_token,
                request_params=params
            )

            return self.handle_questions(result, answers, reply)


    def handle_questions(self,original_result, answers, reply_callback: callable) :
        """
        Handles a series of interactive questions that may arise during a request, especially when submitting orders.

        This method iteratively processes questions contained within the response data. It expects
        each question to be answered affirmatively to proceed. If a question does not receive
        a positive reply or if there are too many questions (more than 10 attempts), a RuntimeError
        is raised.

        Parameters:
            original_result (support.rest_client.Result): The initial result object containing the data that may include questions.
            answers (Answers): A collection of answers to the expected questions.

        Returns:
            support.rest_client.Result: The updated result object after all questions have been successfully answered.

        Raises:
            RuntimeError: If a question does not receive a positive reply or if there are too many questions.

        See:
            QuestionType: for types of answers currently supported.

        Note:
            - The function assumes that each response will contain at most one question.
        """

        result = original_result.copy()

        questions = []  # we store questions in case we need to show them at the end
        for attempt in range(20):
            data = result.data

            if 'error' in data:
                order_tag = original_result.request["json"]["orders"][0].get("cOID")
                error_match = f'Order couldn\'t be submitted: Local order ID={order_tag} is already registered.'
                if error_match in data['error']:
                    raise Exception(f'Order couldn\'t be submitted. Order with order_tag/cOID {order_tag!r} is already registered.')

                raise Exception(f'While handling questions an error was returned: {pprint.pformat(data)}')

            if not isinstance(data, list):
                raise Exception(f'While handling questions unknown data was returned: {data!r}. Request: {result.request}')

            first_data = data[0]  # this assumes submitting only one order at a time

            # we interpret messages as questions, absence of which we interpret as the end of questions
            if 'message' not in first_data:
                if len(data) == 1:
                    data = data[0]
                return pass_result(data, original_result)

            # if len(data) != 1:
            #     _LOGGER.warning(f'While handling questions multiple orders were returned: {pprint.pformat(data)}')

            messages = first_data['message']

            # if len(messages) != 1:
            #     _LOGGER.warning(f'While handling questions multiple messages were returned: {pprint.pformat(messages)}')

            question = messages[0]
            question = question.strip().replace('\n', '')  # clean up the question
            answer = find_answer(question, answers)
            questions.append({'q': question, 'a': answer})

            if answer:
                # the result to a reply will either contain another question or a confirmation
                result = reply_callback(first_data['id'], True)
            else:
                raise RuntimeError(f'A question was not given a positive reply. Question: "{question}". Answers: \n{pprint.pformat(answers)}\n. Request: {result.request}')

        raise RuntimeError(f'Too many questions: {original_result}: {questions}')




    def reply(
        self,
        access_token: str,
        live_session_token: str,
        reply_id, 
        confirmed: bool
        ) -> requests.Response:

            """
            Confirm order precautions and warnings presented from placing orders.
            Many of the warning notifications within the Client Portal API can be disabled.
            Parameters:
                reply_id (str): Include the id value from the prior order request relating to the particular order's warning confirmation.
                confirmed (bool): Pass your confirmation to the reply to allow or cancel the order to go through. true will agree to the message transmit the order. false will decline the message and discard the order.
            """
            
            params={"confirmed": confirmed}

            result= self.send_oauth_request(
                request_method="POST",
                request_url=f"https://api.ibkr.com/v1/api/iserver/reply/{reply_id}/orders",
                oauth_token=access_token,
                live_session_token=live_session_token,
                request_params=params
            )

            return result

            # return self.post(f'iserver/reply/{reply_id}', params={"confirmed": confirmed})



    def pass_result(self,data: dict, old_result) :
        return old_result.copy(data=data)

    def find_answer(self,question: str, answers):
        """
        Retrieves a predefined answer for a given question based on question types defined in the
        QuestionType enum.

        This function matches the given question against known question types and returns the corresponding
        predefined answer. It uses the 'QuestionType' enum to identify types of questions and their
        associated answers.

        Parameters:
            question (str): The question for which an answer is sought.
            answers (Answers): A dictionary mapping QuestionType enum members to their corresponding boolean answers.

        Returns:
            bool: The predefined answer (boolean) corresponding to the given question.

        Raises:
            ValueError: If no predefined answer is found for the given question.
        """
        for question_type, answer in answers.items():
            if str(question_type) in question:
                return answer

        raise ValueError(f'No answer found for question: "{question}"')


    #  Trades

    def trades(
        self,
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

            return self.send_oauth_request(
                request_method="GET",
                request_url="https://api.ibkr.com/v1/api/iserver/account/trades",
                oauth_token=access_token,
                live_session_token=live_session_token,
                request_params=params,
            )
            

