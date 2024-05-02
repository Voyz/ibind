import datetime
import pprint
from dataclasses import dataclass, field
from typing import Optional, Dict, Union

from ibind.base.rest_client import Result, pass_result
from ibind.support.errors import ExternalBrokerError
from ibind.support.logs import project_logger
from ibind.support.py_utils import UNDEFINED, ensure_list_arg, VerboseEnum, OneOrMany

_LOGGER = project_logger(__file__)


@dataclass
class StockQuery():
    """
    A class to encapsulate query parameters for filtering stock data.

    This class is used to define a set of criteria for filtering stocks, which includes the stock symbol,
    name matching pattern, and conditions for instruments and contracts.

    Attributes:
        symbol (str): The stock symbol to query.
        name_match (Optional[str], optional): A string pattern to match against stock names. Optional.
        instrument_conditions (Optional[dict], optional): Key-value pairs representing conditions to apply to
            stock instruments. Each condition is matched exactly against the instrument's attributes.
        contract_conditions (Optional[dict], optional): Key-value pairs representing conditions to apply to
            stock contracts. Each condition is matched exactly against the contract's attributes.
    """
    symbol: str
    name_match: Optional[str] = field(default=None)
    instrument_conditions: Optional[dict] = field(default=None)
    contract_conditions: Optional[dict] = field(default=None)

StockQueries = OneOrMany[Union[StockQuery, str]]

def _filter(data: dict, conditions: dict) -> bool:
    for key, value in conditions.items():
        if data.get(key, UNDEFINED) != value:
            return False

    return True


def process_instruments(
        instruments: dict,
        name_match: str = None,
        instrument_conditions: dict = None,
        contract_conditions: dict = None,
) -> [dict]:
    """
    Filters a list of instruments based on specified name matching and conditions.

    This function processes each instrument in the given list and filters them based on the provided
    name matching pattern, instrument conditions, and contract conditions. Instruments are filtered
    to match the specified conditions exactly.

    Parameters:
        instruments (List[dict]): A list of instrument dictionaries to be filtered.
        name_match (Optional[str], optional): A string pattern for partial matching of instrument names. If specified, only instruments  with names containing this pattern are included.
        instrument_conditions (Optional[dict], optional): Key-value pairs representing exact conditions to match against each instrument's attributes.
        contract_conditions (Optional[dict], optional): Key-value pairs representing exact conditions to match against each contract within an instrument.

    Returns:
        List[dict]: A filtered list of instruments that meet the specified criteria.
    """
    filtered_instruments = []

    for instrument in instruments:
        # look for a partial match of the instrument name if provided
        if name_match is not None and name_match.upper() not in instrument['name'].upper():
            continue

        # look for an exact match of instrument properties if provided
        if instrument_conditions is not None and not _filter(instrument, instrument_conditions):
            continue

        # filter contracts by conditions provided
        if contract_conditions is not None:
            filtered_contracts = list(
                filter(
                    lambda x: _filter(x, contract_conditions),
                    instrument["contracts"],
                )
            )

            # if no contracts are left, we don't need the instrument
            if not len(filtered_contracts):
                continue

            # if all conditions are  met, accept the instrument and its contracts
            instrument = {**instrument, 'contracts': filtered_contracts}

        filtered_instruments.append(instrument)

    return filtered_instruments


@ensure_list_arg('queries')
def filter_stocks(queries: [StockQuery], result: Result, default_filtering: bool = True):
    stocks = {}
    data = result.data
    for q in queries:
        symbol, name_match, instrument_conditions, contract_conditions = process_query(q, default_filtering)

        if symbol not in data or len(data[symbol]) == 0:
            _LOGGER.error(f'Error getting stocks. Could not find valid instruments {symbol} in result: {result}')
            continue

        filtered_instruments = process_instruments(
            data[symbol],
            name_match,
            instrument_conditions,
            contract_conditions
        )

        stocks[symbol] = filtered_instruments

    return pass_result(stocks, result)


def query_to_symbols(queries):
    return ",".join([q if isinstance(q, str) else q.symbol for q in queries])


def process_query(q, default_filtering: bool = True):
    if isinstance(q, str):
        q = StockQuery(symbol=q)

    symbol = q.symbol
    name_match = q.name_match
    instrument_conditions = q.instrument_conditions
    # look for US contracts only by default
    default_contract_filter = {'isUS': True} if default_filtering else None
    contract_conditions = q.contract_conditions
    if contract_conditions is None:
        contract_conditions = default_contract_filter

    return symbol, name_match, instrument_conditions, contract_conditions


class QuestionType(VerboseEnum):
    PRICE_PERCENTAGE_CONSTRAINT = 'price exceeds the Percentage constraint of 3%'
    ORDER_VALUE_LIMIT = 'exceeds the Total Value Limit of'


Answers = Dict[Union[QuestionType, str], bool]


def find_answer(question: str, answers: Answers):
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


def handle_questions(original_result: Result, answers: Answers, reply_callback: callable) -> Result:
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

    result: Result = original_result.copy()

    questions = []  # we store questions in case we need to show them at the end
    for attempt in range(20):
        data = result.data

        if 'error' in data:
            order_tag = original_result.request["json"]["orders"][0].get("cOID")
            error_match = f'Order couldn\'t be submitted: Local order ID={order_tag} is already registered.'
            if error_match in data['error']:
                raise ExternalBrokerError(f'Order couldn\'t be submitted. Order with order_tag/cOID {order_tag!r} is already registered.')

            raise ExternalBrokerError(f'While handling questions an error was returned: {pprint.pformat(data)}')

        if not isinstance(data, list):
            raise ExternalBrokerError(f'While handling questions unknown data was returned: {data!r}. Request: {result.request}')

        if len(data) != 1:
            _LOGGER.warning(f'While handling questions multiple orders were returned: {pprint.pformat(data)}')

        data = data[0]  # this assumes submitting only one order at a time

        # we interpret messages as questions, absence of which we interpret as the end of questions
        if 'message' not in data:
            return pass_result(data, original_result)

        messages = data['message']

        if len(messages) != 1:
            _LOGGER.warning(f'While handling questions multiple messages were returned: {pprint.pformat(messages)}')

        question = messages[0]
        question = question.strip().replace('\n', '')  # clean up the question
        answer = find_answer(question, answers)
        questions.append({'q': question, 'a': answer})

        if answer:
            # the result to a reply will either contain another question or a confirmation
            result = reply_callback(data['id'], True)
        else:
            raise RuntimeError(f'A question was not given a positive reply. Question: "{question}". Answers: \n{pprint.pformat(answers)}\n. Request: {result.request}')

    raise RuntimeError(f'Too many questions: {original_result}: {questions}')


def make_order_request(
        conid: str,
        side: str,
        quantity: float,
        order_type: str,
        price: float,
        coid: str,
        acct_id: str,

        # optional
        conidex: str = None,
        sec_type: str = None,
        parent_id: str = None,
        listing_exchange: str = None,
        is_single_group: bool = None,
        outside_rth: bool = None,
        aux_price: float = None,
        ticker: str = None,
        tif: str = 'GTC',
        trailing_amt: float = None,
        trailing_type: str = None,
        referrer: str = None,
        cash_qty: float = None,
        fx_qty: float = None,
        use_adaptive: bool = None,
        is_ccy_conv: bool = None,
        allocation_method: str = None,
        strategy: str = None,
        strategy_parameters=None,

):  # pragma: no cover
    """
     Create an order request object. Arguments set as None will not be included.

    Parameters:
        conid (str): Identifier of the security to trade.
        side (str): Order side, either 'SELL' or 'BUY'.
        quantity (int): Order quantity in number of shares.
        order_type (str): Type of the order (e.g., LMT, MKT, STP).
        price (float): Order limit price, depends on order type.
        coid (str): Customer Order ID, unique for a 24h span.
        acctId (str, optional): Account ID, defaults to the first account if not provided.

        conidex (str, Optional): Concatenated value of contract identifier and exchange.
        sec_type (str, Optional): Concatenated value of contract-identifier and security type.
        parent_id (str, Optional): Used for child orders in bracket orders, must match the parent's cOID.
        listing_exchange (str, Optional, optional): Exchange for order routing, default is "SMART".
        is_single_group (bool, Optional): Set to True for placing single group orders (OCA).
        outside_rth (bool, Optional): Set to True if the order can be executed outside regular trading hours.
        aux_price (float, Optional): Auxiliary price parameter.
        ticker (str, Optional): Underlying symbol for the contract.
        tif (str, Optional): Time-In-Force for the order (e.g., GTC, OPG, DAY, IOC). Default: "GTC".
        trailing_amt (float, Optional): Trailing amount for TRAIL or TRAILLMT orders.
        trailing_type (str, Optional): Trailing type ('amt' or '%') for TRAIL or TRAILLMT orders.
        referrer (str, Optional): Custom order reference.
        cash_qty (float, Optional): Cash Quantity for the order.
        fx_qty (float, Optional): Cash quantity for Currency Conversion Orders.
        use_adaptive (bool, Optional): Set to True to use the Price Management Algo.
        is_ccy_conv (bool, Optional): Set to True for FX conversion orders.
        allocation_method (str, Optional): Allocation method for FA account orders.
        strategy (str, Optional): IB Algo algorithm to use for the order.
        strategy_parameters (dict, Optional): Parameters for the specified IB Algo algorithm.
     """

    order_request = {}

    if conid is not None:
        order_request["conid"] = conid

    if side is not None:
        order_request["side"] = str(side)

    if quantity is not None:
        order_request["quantity"] = int(quantity)

    if order_type is not None:
        order_request["orderType"] = str(order_type)

    if price is not None:
        order_request["price"] = price

    if coid is not None:
        order_request["cOID"] = coid

    # optional

    if acct_id is not None:
        order_request["acctId"] = acct_id

    if conidex is not None:
        order_request["conidex"] = conidex

    if sec_type is not None:
        order_request["secType"] = sec_type

    if parent_id is not None:
        order_request["parentId"] = parent_id

    if listing_exchange is not None:
        order_request["listingExchange"] = listing_exchange

    if is_single_group is not None:
        order_request["isSingleGroup"] = is_single_group

    if outside_rth is not None:
        order_request["outsideRTH"] = outside_rth

    if aux_price is not None:
        order_request["auxPrice"] = aux_price

    if ticker is not None:
        order_request["ticker"] = ticker

    if tif is not None:
        order_request["tif"] = tif

    if trailing_amt is not None:
        order_request["trailingAmt"] = trailing_amt

    if trailing_type is not None:
        order_request["trailingType"] = trailing_type

    if referrer is not None:
        order_request["referrer"] = referrer

    if cash_qty is not None:
        order_request["cashQty"] = cash_qty

    if fx_qty is not None:
        order_request["fxQty"] = fx_qty

    if use_adaptive is not None:
        order_request["useAdaptive"] = use_adaptive

    if is_ccy_conv is not None:
        order_request["isCcyConv"] = is_ccy_conv

    if allocation_method is not None:
        order_request["allocationMethod"] = allocation_method

    if strategy is not None:
        order_request["strategy"] = strategy

    if strategy_parameters is not None:
        order_request["strategyParameters"] = strategy_parameters

    return order_request


def date_from_ibkr(d: str) -> datetime.datetime:
    try:
        return datetime.datetime(int(d[:4]), int(d[4:6]), int(d[6:8]), int(d[8:10]), int(d[10:12]), int(d[12:14]))
    except ValueError:
        raise ValueError(f'Date seems to be missing fields: year={d[0:4]}, month={d[4:6]}, day={d[6:8]}, hour={d[8:10]}, minute={d[10:12]}, second={d[12:14]}')


def extract_conid(data):
    # by default conid should be made available as 'smh+<conid>', let's look for it
    if 'topic' in data and '+' in data['topic']:
        return data['topic'].split('+')[-1]

    # as a backup we try to include the conid in the payload, IBKR seems to send it back to us
    elif 'payload' in data and 'conid' in data['payload']:
        return data['payload']['conid']

    return None
