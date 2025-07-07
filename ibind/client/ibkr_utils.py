import datetime
import pprint
import threading
from dataclasses import dataclass, field, fields
from typing import Optional, Dict, Union, TYPE_CHECKING
from warnings import warn

from ibind.base.rest_client import Result, pass_result
from ibind.client.ibkr_definitions import decode_data_availability
from ibind.support.errors import ExternalBrokerError
from ibind.support.logs import project_logger
from ibind.support.py_utils import UNDEFINED, ensure_list_arg, VerboseEnum, OneOrMany, exception_to_string
from ibind import var

_LOGGER = project_logger(__file__)

if TYPE_CHECKING:  # pragma: no cover
    from ibind import IbkrClient


@dataclass
class StockQuery:
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
                    instrument['contracts'],
                )
            )

            # if no contracts are left, we don't need the instrument
            if not len(filtered_contracts):
                continue

            # if all conditions are  met, accept the instrument and its contracts
            instrument['contracts'] = filtered_contracts

        filtered_instruments.append(instrument)

    return filtered_instruments


@ensure_list_arg('queries')
def filter_stocks(queries: StockQueries, result: Result, default_filtering: bool = True):
    stocks = {}
    data = result.data
    for q in queries:
        symbol, name_match, instrument_conditions, contract_conditions = process_query(q, default_filtering)

        if symbol not in data or len(data[symbol]) == 0:
            _LOGGER.error(f'Error getting stocks. Could not find valid instruments {symbol} in result: {result}. Skipping query={q}.')
            continue

        filtered_instruments = process_instruments(data[symbol], name_match, instrument_conditions, contract_conditions)

        stocks[symbol] = filtered_instruments

    return pass_result(stocks, result)


def query_to_symbols(queries):
    return ','.join([q if isinstance(q, str) else q.symbol for q in queries])


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
    """
    Enumeration of common warning messages encountered when submitting orders.

    This enum class represents different types of precautionary messages that may be returned by IBKR's API when placing an order. These warnings often require user confirmation before proceeding.

    Note:
        - Look for all suppressible message IDs in IBKR API documentation (https://www.interactivebrokers.com/campus/ibkr-api-page/cpapi-v1/#suppressible-id)
    """

    PRICE_PERCENTAGE_CONSTRAINT = 'price exceeds the Percentage constraint of 3%'
    MISSING_MARKET_DATA = (
        'You are submitting an order without market data. We strongly recommend against this as it may result in erroneous and unexpected trades.'
    )
    TICK_SIZE_LIMIT = 'exceeds the Tick Size Limit of'
    ORDER_SIZE_LIMIT = 'size exceeds the Size Limit of'
    TRIGGER_AND_FILL = 'This order will most likely trigger and fill immediately.'
    ORDER_VALUE_LIMIT = 'exceeds the Total Value Limit of'
    SIZE_MODIFICATION_LIMIT = 'size modification exceeds the size modification limit'
    MANDATORY_CAP_PRICE = 'To avoid trading at a price that is not consistent with a fair and orderly market'
    CASH_QUANTITY = 'Traders are responsible for understanding cash quantity details, which are provided on a best efforts basis only.'
    CASH_QUANTITY_ORDER = 'Orders that express size using a monetary value (cash quantity) are provided on a non-guaranteed basis.'
    STOP_ORDER_RISKS = (
        'You are about to submit a stop order. Please be aware of the various stop order types available and the risks associated with each one.'
    )
    MULTIPLE_ACCOUNTS = 'This order will be distributed over multiple accounts. We strongly suggest you familiarize yourself with our allocation facilities before submitting orders.'
    DISRUPTIVE_ORDERS = 'If your order is not immediately executable, our systems may, depending on market conditions, reject your order'
    CLOSE_POSITION = 'Would you like to cancel all open orders and then place new closing order?'


# FIXME: Fill in the remaining question types as we find out what they are
_MESSAGE_ID_TO_QUESTION_TYPE = {
    "o163": (QuestionType.PRICE_PERCENTAGE_CONSTRAINT, "The following order exceeds the price percentage limit"),
    "o354": (QuestionType.MISSING_MARKET_DATA, "You are submitting an order without market data. We strongly recommend against this as it may result in erroneous and unexpected trades. Are you sure you want to submit this order?"),
    "o382": (QuestionType.TICK_SIZE_LIMIT, "The following value exceeds the tick size limit"),
    "o383": (QuestionType.ORDER_SIZE_LIMIT, "The following order BUY 650 AAPL NASDAQ.NMS size exceeds the Size Limit of 500.\nAre you sure you want to submit this order?"),
    "o403": (QuestionType.TRIGGER_AND_FILL, "This order will most likely trigger and fill immediately.\nAre you sure you want to submit this order?"),
    "o451": (QuestionType.ORDER_VALUE_LIMIT, "The following order BUY 650 AAPL NASDAQ.NMS value estimate of 124,995.00 USD exceeds \nthe Total Value Limit of 100,000 USD.\nAre you sure you want to submit this order?"),
    "o2136": (UNDEFINED, "Mixed allocation order warning"),
    "o2137": (UNDEFINED, "Cross side order warning"),
    "o2165": (UNDEFINED, "Warns that instrument does not support trading in fractions outside regular trading hours"),
    "o10082": (UNDEFINED, "Called Bond warning"),
    "o10138": (QuestionType.SIZE_MODIFICATION_LIMIT, "The following order size modification exceeds the size modification limit."),
    "o10151": (UNDEFINED, "Warns about risks with Market Orders"),
    "o10152": (UNDEFINED, "Warns about risks associated with stop orders once they become active"),
    "o10153": (QuestionType.MANDATORY_CAP_PRICE, "<h4>Confirm Mandatory Cap Price</h4>To avoid trading at a price that is not consistent with a fair and orderly market, IB may set a cap (for a buy order) or sell order). THIS MAY CAUSE AN ORDER THAT WOULD OTHERWISE BE MARKETABLE TO NOT BE TRADED."),
    "o10164": (QuestionType.CASH_QUANTITY, "Traders are responsible for understanding cash quantity details, which are provided on a best efforts basis only."),
    "o10223": (QuestionType.CASH_QUANTITY_ORDER, "<h4>Cash Quantity Order Confirmation</h4>Orders that express size using a monetary value (cash quantity) are provided on a non-guaranteed basis. The system simulates the order by cancelling it once the specified amount is spent (for buy orders) or collected (for sell orders). In addition to the monetary value, the order uses a maximum size that is calculated using the Cash Quantity Estimate Factor, which you can modify in Presets."),
    "o10288": (UNDEFINED, "Warns about risks associated with market orders for Crypto"),
    "o10331": (QuestionType.STOP_ORDER_RISKS, "You are about to submit a stop order. Please be aware of the various stop order types available and the risks associated with each one.\nAre you sure you want to submit this order?"),
    "o10332": (UNDEFINED, "OSL Digital Securities LTD Crypto Order Warning"),
    "o10333": (UNDEFINED, "Option Exercise at the Money warning"),
    "o10334": (UNDEFINED, "Warns that order will be placed into current omnibus account instead of currently selected global account."),
    "o10335": (UNDEFINED, "Serves internal Rapid Entry window."),
    "p6": (QuestionType.MULTIPLE_ACCOUNTS, "This order will be distributed over multiple accounts. We strongly suggest you familiarize yourself with our allocation facilities before submitting orders."),
    "p12": (QuestionType.DISRUPTIVE_ORDERS, "If your order is not immediately executable, our systems may, depending on market conditions, reject your order if its limit price is more than the allowed amount away from the reference price at that time. If this happens, you will not receive a fill. This is a control designed to ensure that we comply with our regulatory obligations to avoid submitting disruptive orders to the marketplace.\\nUse the Price Management Algo?"),
}

_QUESTION_TYPE_TO_MESSAGE_ID = {v[0]: k if v[0] is not UNDEFINED else 'undefined' for k, v in _MESSAGE_ID_TO_QUESTION_TYPE.items()}


def question_type_to_message_id(question_type: QuestionType) -> str:
    """
    Converts a QuestionType to its corresponding message ID.

    Parameters:
        question_type (QuestionType): The QuestionType enum value.

    Returns:
        str: The corresponding message ID string.

    Note:
        - Look for all suppressible message IDs in IBKR API documentation (https://www.interactivebrokers.com/campus/ibkr-api-page/cpapi-v1/#suppressible-id)
    """
    if question_type not in _QUESTION_TYPE_TO_MESSAGE_ID:
        raise ValueError(f'QuestionType {question_type} is not currently dynamically mapped to a message id. Please look the ID up manually.')

    return _QUESTION_TYPE_TO_MESSAGE_ID[question_type]


Answers = Dict[Union[QuestionType, str], bool]
"""
A mapping of order warnings to user responses.

This dictionary type is used to associate specific warning messages from the IBKR API (either predefined in `QuestionType` or as raw strings) with a boolean response
indicating whether the user accepts or rejects the warning.

Key:
    - `QuestionType`: A predefined enum representing common IBKR warning messages.
    - `str`: A raw string warning message (if not covered by `QuestionType`).

Value:
    - `bool`:
        - `True` if the user acknowledges and accepts the warning.
        - `False` if the user rejects it, potentially preventing the order submission.

Example:
    >>> user_answers = {
    ...     QuestionType.PRICE_PERCENTAGE_CONSTRAINT: True,
    ...     "Some custom warning message": False
    ... }
"""


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
            if "Order couldn't be submitted: Local order ID=" in data['error']:
                raise ExternalBrokerError(f"Order couldn't be submitted. Orders are already registered: {original_result.request.get('json', {}).get('orders', {})}")

            raise ExternalBrokerError(f'While handling questions an error was returned: {pprint.pformat(data)}')

        if not isinstance(data, list):
            raise ExternalBrokerError(f'While handling questions unknown data was returned: {data!r}. Request: {result.request}')

        first_data = data[0]  # this assumes submitting only one order at a time

        # we interpret messages as questions, absence of which we interpret as the end of questions
        if 'message' not in first_data:
            if len(data) == 1:
                data = data[0]
            return pass_result(data, original_result)

        if len(data) != 1:
            _LOGGER.warning(f'While handling questions multiple orders were returned: {pprint.pformat(data)}')

        messages = first_data['message']

        if len(messages) != 1:
            _LOGGER.warning(f'While handling questions multiple messages were returned: {pprint.pformat(messages)}')

        question = messages[0]
        question = question.strip().replace('\n', '')  # clean up the question
        answer = find_answer(question, answers)
        questions.append({'q': question, 'a': answer})

        if answer:
            # the result to a reply will either contain another question or a confirmation
            result = reply_callback(first_data['id'], True)
        else:
            raise RuntimeError(
                f'A question was not given a positive reply. Question: "{question}". Answers: \n{pprint.pformat(answers)}\n. Request: {result.request}'
            )

    raise RuntimeError(f'Too many questions: {original_result}: {questions}')


@dataclass
class OrderRequest:
    conid: Optional[int]
    side: str
    quantity: float
    order_type: str
    acct_id: str

    # optional
    price: Optional[float] = field(default=None)
    conidex: Optional[str] = field(default=None)
    sec_type: Optional[str] = field(default=None)
    coid: Optional[str] = field(default=None)
    parent_id: Optional[str] = field(default=None)
    listing_exchange: Optional[str] = field(default=None)
    is_single_group: Optional[bool] = field(default=None)
    outside_rth: Optional[bool] = field(default=None)
    aux_price: Optional[float] = field(default=None)
    ticker: Optional[str] = field(default=None)
    tif: Optional[str] = field(default='GTC')
    trailing_amt: Optional[float] = field(default=None)
    trailing_type: Optional[str] = field(default=None)
    referrer: Optional[str] = field(default=None)
    cash_qty: Optional[float] = field(default=None)
    fx_qty: Optional[float] = field(default=None)
    use_adaptive: Optional[bool] = field(default=None)
    is_ccy_conv: Optional[bool] = field(default=None)
    allocation_method: Optional[str] = field(default=None)
    strategy: Optional[str] = field(default=None)
    strategy_parameters: Optional[dict] = field(default=None)

    # undocumented
    is_close: Optional[bool] = field(default=None)

    def to_dict(self) -> dict:
        """Convert dataclass to a dictionary, excluding None values."""
        return {f.name: getattr(self, f.name) for f in fields(self) if getattr(self, f.name) is not None}


_ORDER_REQUEST_MAPPING = {
    'conid': 'conid',
    'side': 'side',
    'quantity': 'quantity',
    'order_type': 'orderType',
    'price': 'price',
    'coid': 'cOID',
    'acct_id': 'acctId',
    'conidex': 'conidex',
    'sec_type': 'secType',
    'parent_id': 'parentId',
    'listing_exchange': 'listingExchange',
    'is_single_group': 'isSingleGroup',
    'outside_rth': 'outsideRTH',
    'aux_price': 'auxPrice',
    'ticker': 'ticker',
    'tif': 'tif',
    'trailing_amt': 'trailingAmt',
    'trailing_type': 'trailingType',
    'referrer': 'referrer',
    'cash_qty': 'cashQty',
    'fx_qty': 'fxQty',
    'use_adaptive': 'useAdaptive',
    'is_ccy_conv': 'isCcyConv',
    'allocation_method': 'allocationMethod',
    'strategy': 'strategy',
    'strategy_parameters': 'strategyParameters',
    'is_close': 'isClose',
}


def parse_order_request(order_request: OrderRequest, mapping: dict = None) -> dict:
    if mapping is None:
        mapping = _ORDER_REQUEST_MAPPING

    if isinstance(order_request, dict):
        _LOGGER.warning("Order request supplied as a dict. Use 'OrderRequest' dataclass instead.")
        d = order_request
    else:
        d = {mapping[k]: v for k, v in order_request.to_dict().items() if v is not None}

    if 'conidex' in d and 'conid' in d:
        raise ValueError("Both 'conidex' and 'conid' are provided. When using 'conidex', specify `conid=None`.")

    return d


def make_order_request(
    conid: Union[int, str],
    side: str,
    quantity: float,
    order_type: str,
    acct_id: str,
    # optional
    price: float = None,
    conidex: str = None,
    sec_type: str = None,
    coid: str = None,
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
        conid (int | str): Identifier of the security to trade.
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
    warn("'make_order_request' is deprecated. Use 'OrderRequest' dataclass instead.", DeprecationWarning, stacklevel=2)

    order_request = {}

    if conid is not None:
        order_request['conid'] = int(conid)

    if side is not None:
        order_request['side'] = str(side)

    if quantity is not None:
        order_request['quantity'] = int(quantity)

    if order_type is not None:
        order_request['orderType'] = str(order_type)

    if price is not None:
        order_request['price'] = price

    if coid is not None:
        order_request['cOID'] = coid

    # optional

    if acct_id is not None:
        order_request['acctId'] = acct_id

    if conidex is not None:
        order_request['conidex'] = conidex

    if sec_type is not None:
        order_request['secType'] = sec_type

    if parent_id is not None:
        order_request['parentId'] = parent_id

    if listing_exchange is not None:
        order_request['listingExchange'] = listing_exchange

    if is_single_group is not None:
        order_request['isSingleGroup'] = is_single_group

    if outside_rth is not None:
        order_request['outsideRTH'] = outside_rth

    if aux_price is not None:
        order_request['auxPrice'] = aux_price

    if ticker is not None:
        order_request['ticker'] = ticker

    if tif is not None:
        order_request['tif'] = tif

    if trailing_amt is not None:
        order_request['trailingAmt'] = trailing_amt

    if trailing_type is not None:
        order_request['trailingType'] = trailing_type

    if referrer is not None:
        order_request['referrer'] = referrer

    if cash_qty is not None:
        order_request['cashQty'] = cash_qty

    if fx_qty is not None:
        order_request['fxQty'] = fx_qty

    if use_adaptive is not None:
        order_request['useAdaptive'] = use_adaptive

    if is_ccy_conv is not None:
        order_request['isCcyConv'] = is_ccy_conv

    if allocation_method is not None:
        order_request['allocationMethod'] = allocation_method

    if strategy is not None:
        order_request['strategy'] = strategy

    if strategy_parameters is not None:
        order_request['strategyParameters'] = strategy_parameters

    return order_request


def date_from_ibkr(d: str) -> datetime.datetime:
    try:
        return datetime.datetime(int(d[:4]), int(d[4:6]), int(d[6:8]), int(d[8:10]), int(d[10:12]), int(d[12:14]))
    except ValueError:
        raise ValueError(
            f'Date seems to be missing fields: year={d[0:4]}, month={d[4:6]}, day={d[6:8]}, hour={d[8:10]}, minute={d[10:12]}, second={d[12:14]}'
        )


def extract_conid(data):
    # by default conid should be made available as 'smh+<conid>', let's look for it
    if 'topic' in data and '+' in data['topic']:
        return data['topic'].split('+')[-1]

    # as a backup we try to include the conid in the payload, IBKR seems to send it back to us
    elif 'payload' in data and 'conid' in data['payload']:
        return data['payload']['conid']

    return None


class Tickler:
    """
    Utility class used for maintaining the OAuth connection alive by repeatedly calling the `tickle` method.

    The Tickler runs in a separate thread and periodically sends requests to the IBKR API to prevent
    the session from expiring. This is essential for keeping the OAuth session active.
    """

    def __init__(self, client: 'IbkrClient', interval: Union[int, float] = var.IBIND_TICKLER_INTERVAL):
        """
        Initializes the Tickler instance.

        Parameters:
            client (IbkrClient): The client instance with a `tickle` method that maintains the session.
            interval (Union[int, float]): Interval between tickles in seconds. Default is 60 seconds.
        """
        self._client = client
        self._interval = interval
        self._stop_event = threading.Event()
        self._thread = None

    def _worker(self):
        _LOGGER.info(f'Tickler starts with interval={self._interval} seconds.')
        while not self._stop_event.wait(self._interval):
            try:
                self._client.tickle()
            except KeyboardInterrupt:
                _LOGGER.info('Tickler interrupted')
                break
            except TimeoutError:
                _LOGGER.warning(f'Tickler encountered a timeout error. This could indicate the servers are restarting. Investigate further if you see this log repeat frequently.')
            except Exception as e:
                _LOGGER.error(f'Tickler error: {exception_to_string(e)}')

        _LOGGER.info('Tickler gracefully stopped.')

    def start(self):
        """
        Starts the Tickler in a separate thread.

        This method creates and starts a daemon thread that periodically calls `tickle()` to keep the
        session alive.
        """
        if self._thread is not None:
            _LOGGER.info('Tickler thread already running. Stop the existing thread first by calling Tickler.stop()')
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self, timeout:float=None):
        """
        Stops the Tickler thread.

        This method stops and joins the Tickler thread.

        Parameters:
            timeout (Optional[float]): Maximum time to wait for the Tickler thread to terminate.
                                       If None, waits indefinitely.
        """
        if self._thread is None:
            return

        self._stop_event.set()  # Wake up the sleeping thread immediately
        self._thread.join(timeout)
        self._thread = None  # Ensure cleanup


def cleanup_market_history_responses(
    market_history_response: Dict[str, Union[Exception, Result]],
    raise_on_error: bool = False,
):
    """
    Processes and cleans up market history responses, converting raw data into structured records.

    This function iterates over market history responses, extracts relevant trading data, and
    formats it into a structured dictionary. If errors are encountered, they are either logged
    and included in the results or raised based on the `raise_on_error` flag.

    Parameters:
        market_history_response (Dict[str, Union[Exception, Result]]):
            A dictionary where keys are symbols and values are either:
            - `Result` objects containing market history data.
            - `Exception` instances representing failed requests.

        raise_on_error (bool, optional):
            If `True`, raises encountered exceptions instead of storing them in the results.
            Defaults to `False`.

    Returns:
        Dict[str, Union[list[dict], Exception]]:
            A dictionary where keys are symbols and values are either:
            - A list of structured historical market data records, each containing:
                - `"open"`: Open price.
                - `"high"`: High price.
                - `"low"`: Low price.
                - `"close"`: Close price.
                - `"volume"`: Trading volume.
                - `"date"`: Datetime object representing the timestamp.
            - An `Exception` object if an error occurred (only if `raise_on_error=False`).

    Logs:
        - Errors when fetching market data if `raise_on_error=True`.
        - Warnings if market data is not live (i.e., missing 'S' or 'R' in `mdAvailability`).

    Raises:
        Exception: If `raise_on_error=True` and an error occurs.

    Example:
        >>> market_history_responses = {
        ...     symbol: client.marketdata_history_by_conid(**request)
        ...     for symbol, request in requests.items()
        ... }  # fmt: skip
        >>> results = cleanup_market_history_responses(market_history_responses)
        {
            "AAPL": [
                {"open": 150.0, "high": 155.0, "low": 149.0, "close": 153.0,
                 "volume": 500000, "date": datetime.datetime(2023, 11, 14, 10, 53, 20)}
            ],
            "TSLA": Exception("Failed to fetch data")
        }
    """
    results = {}
    for symbol, entry in market_history_response.items():
        if isinstance(entry, Exception):  # pragma: no cover
            if raise_on_error:
                _LOGGER.error(f'Error fetching market data for {symbol}')
                raise entry
            else:
                results[symbol] = entry
                continue

        # check if entry['mdAvailability'] has 'S' or 'R' in it
        if 'mdAvailability' in entry.data and not (any((key in entry.data['mdAvailability'].upper()) for key in ['S', 'R'])):
            _LOGGER.warning(f'Market data for {symbol} is not live: {decode_data_availability(entry.data["mdAvailability"])}')

        data = entry.data['data']
        records = []
        for record in data:
            records.append(
                {
                    'open': record['o'],
                    'high': record['h'],
                    'low': record['l'],
                    'close': record['c'],
                    'volume': record['v'],
                    'date': datetime.datetime.fromtimestamp(record['t'] / 1000),
                }
            )
        results[symbol] = records
    return results
