from pprint import pformat
from unittest.mock import MagicMock, call

import pytest

from ibind.base.rest_client import Result
from ibind.client.ibkr_utils import (
    StockQuery,
    filter_stocks,
    find_answer,
    QuestionType,
    handle_questions,
    question_type_to_message_id,
    OrderRequest,
    parse_order_request,
)
from test.integration.client import ibkr_responses
from test.test_utils_new import CaptureLogsContext


# --------------------------------------------------------------------------------------
# Stock filtering
# --------------------------------------------------------------------------------------


@pytest.fixture
def instruments():
    return ibkr_responses.responses['stocks']


@pytest.fixture
def instruments_result(instruments):
    return Result(data=instruments)


def test_filter_stocks(instruments, instruments_result):
    """Filters instruments for multiple stock queries and logs missing symbols."""
    ## Arrange
    queries = [
        StockQuery(symbol='AAPL', contract_conditions={'isUS': False}, name_match='APPLE'),
        StockQuery(symbol='BBVA', contract_conditions={'exchange': 'NYSE'}),
        StockQuery(symbol='CDN', contract_conditions={'isUS': True}),
        StockQuery(symbol='CFC', contract_conditions={}),
        StockQuery(
            symbol='GOOG',
            contract_conditions={'isUS': False},
            instrument_conditions={'chineseName': 'Alphabet&#x516C;&#x53F8;'},
        ),
        'HUBS',
        StockQuery(symbol='META', name_match='meta ', contract_conditions={'isUS': False}, instrument_conditions={}),
        StockQuery(symbol='MSFT', contract_conditions={'exchange': 'NASDAQ'}),
        StockQuery(symbol='SAN', name_match='SANTANDER'),
        StockQuery(symbol='SCHW', contract_conditions={'exchange': 'NASDAQ'}),
        StockQuery(symbol='TEAM', name_match='ATLASSIAN'),
        StockQuery(symbol='INVALID_SYMBOL'),
    ]  # fmt: skip

    ## Act
    with CaptureLogsContext('ibind', level='INFO', error_level='CRITICAL', attach_stack=False) as cm:
        rv = filter_stocks(queries, instruments_result, default_filtering=False)

    ## Assert
    expected_error = (
        f'Error getting stocks. Could not find valid instruments INVALID_SYMBOL in result: {instruments_result}. '
        f'Skipping query={queries[-1]}.'
    )
    assert expected_error in cm.output

    assert [
        {
            'assetClass': 'STK',
            'chineseName': '&#x82F9;&#x679C;&#x516C;&#x53F8;',
            'contracts': [
                {'conid': 38708077, 'exchange': 'MEXI', 'isUS': False},
                {'conid': 273982664, 'exchange': 'EBS', 'isUS': False},
            ],
            'name': 'APPLE INC',
        },
        {
            'assetClass': 'STK',
            'chineseName': '&#x82F9;&#x679C;&#x516C;&#x53F8;',
            'contracts': [{'conid': 532640894, 'exchange': 'AEQLIT', 'isUS': False}],
            'name': 'APPLE INC-CDR',
        },
    ] == rv.data['AAPL']

    assert [
        {
            'assetClass': 'STK',
            'chineseName': '&#x897F;&#x73ED;&#x7259;&#x5BF9;&#x5916;&#x94F6;&#x884C;',
            'contracts': [{'conid': 4815, 'exchange': 'NYSE', 'isUS': True}],
            'name': 'BANCO BILBAO VIZCAYA-SP ADR',
        },
    ] == rv.data['BBVA']

    assert [] == rv.data['CDN']

    assert [
        {
            'assetClass': 'STK',
            'chineseName': None,
            'contracts': [{'conid': 42001300, 'exchange': 'IBIS', 'isUS': False}],
            'name': 'UET UNITED ELECTRONIC TECHNO',
        }
    ] == rv.data['CFC']

    assert [
        {
            'assetClass': 'STK',
            'chineseName': 'Alphabet&#x516C;&#x53F8;',
            'contracts': [
                {'conid': 210810667, 'exchange': 'MEXI', 'isUS': False},
            ],
            'name': 'ALPHABET INC-CL C',
        },
        {
            'assetClass': 'STK',
            'chineseName': 'Alphabet&#x516C;&#x53F8;',
            'contracts': [{'conid': 532638805, 'exchange': 'AEQLIT', 'isUS': False}],
            'name': 'ALPHABET INC - CDR',
        },
    ] == rv.data['GOOG']

    assert [
        {
            'assetClass': 'STK',
            'chineseName': 'HubSpot&#x516C;&#x53F8;',
            'contracts': [{'conid': 169544810, 'exchange': 'NYSE', 'isUS': True}],
            'name': 'HUBSPOT INC',
        }
    ] == rv.data['HUBS']

    assert [
        {
            'assetClass': 'STK',
            'chineseName': 'Meta&#x5E73;&#x53F0;&#x80A1;&#x4EFD;&#x6709;&#x9650;&#x516C;&#x53F8;',
            'contracts': [
                {'conid': 114922621, 'exchange': 'MEXI', 'isUS': False},
            ],
            'name': 'META PLATFORMS INC-CLASS A',
        },
        {
            'assetClass': 'STK',
            'chineseName': 'Meta&#x5E73;&#x53F0;&#x80A1;&#x4EFD;&#x6709;&#x9650;&#x516C;&#x53F8;',
            'contracts': [{'conid': 530091499, 'exchange': 'AEQLIT', 'isUS': False}],
            'name': 'META PLATFORMS INC-CDR',
        },
    ] == rv.data['META']

    assert [
        {
            'assetClass': 'STK',
            'chineseName': '&#x5FAE;&#x8F6F;&#x516C;&#x53F8;',
            'contracts': [
                {'conid': 272093, 'exchange': 'NASDAQ', 'isUS': True},
            ],
            'name': 'MICROSOFT CORP',
        },
    ] == rv.data['MSFT']

    assert [
        {
            'assetClass': 'STK',
            'chineseName': '&#x6851;&#x5766;&#x5FB7;',
            'contracts': [
                {'conid': 38708867, 'exchange': 'MEXI', 'isUS': False},
                {'conid': 385055564, 'exchange': 'WSE', 'isUS': False},
            ],
            'name': 'BANCO SANTANDER SA',
        },
        {
            'assetClass': 'STK',
            'chineseName': '&#x6851;&#x5766;&#x5FB7;',
            'contracts': [{'conid': 12442, 'exchange': 'NYSE', 'isUS': True}],
            'name': 'BANCO SANTANDER SA-SPON ADR',
        },
        {
            'assetClass': 'STK',
            'chineseName': '&#x6851;&#x5766;&#x5FB7;&#x82F1;&#x56FD;&#x516C;&#x5171;&#x6709;&#x9650;&#x516C;&#x53F8;',
            'contracts': [{'conid': 80993135, 'exchange': 'LSE', 'isUS': False}],
            'name': 'SANTANDER UK PLC',
        },
    ] == rv.data['SAN']

    assert [] == rv.data['SCHW']

    assert [
        {
            'assetClass': 'STK',
            'chineseName': None,
            'contracts': [{'conid': 589316251, 'exchange': 'NASDAQ', 'isUS': True}],
            'name': 'ATLASSIAN CORP-CL A',
        },
    ] == rv.data['TEAM']


def test_question_type_to_message_id_successful():
    """Maps a QuestionType to its expected IBKR message id."""
    ## Arrange
    question_type = QuestionType.PRICE_PERCENTAGE_CONSTRAINT

    ## Act
    message_id = question_type_to_message_id(question_type)

    ## Assert
    assert message_id == 'o163'


# --------------------------------------------------------------------------------------
# Finding answers
# --------------------------------------------------------------------------------------


@pytest.fixture
def answers():
    return {QuestionType.PRICE_PERCENTAGE_CONSTRAINT: True}


def test_valid_question(answers):
    """Returns True when a known question type is found in the question string."""
    ## Arrange
    question = f'Some {QuestionType.PRICE_PERCENTAGE_CONSTRAINT} specific question'

    ## Act
    answer = find_answer(question, answers)

    ## Assert
    assert answer is True


def test_invalid_question(answers):
    """Raises when no answer matches the provided question string."""
    ## Arrange
    question = 'Nonexistent question type'

    ## Act & Assert
    with pytest.raises(ValueError):
        find_answer(question, answers)


# --------------------------------------------------------------------------------------
# Handling interactive questions
# --------------------------------------------------------------------------------------


@pytest.fixture
def original_result():
    return Result(
        data=[{'id': '12345', 'message': ['price exceeds the Percentage constraint of 3%.']}],
        request={'url': 'test_url'},
    )


@pytest.fixture
def reply_callback():
    return MagicMock()


def test_successful_handling(mocker, original_result, reply_callback):
    """Replies to a sequence of questions and returns the final result."""
    ## Arrange
    question_type_mock = mocker.patch('ibind.client.ibkr_utils.QuestionType')

    question_type_mock.PRICE_PERCENTAGE_CONSTRAINT.__str__.return_value = 'price exceeds the Percentage constraint of 3%.'
    question_type_mock.ADDITIONAL_QUESTION_TYPE.__str__.return_value = 'This is an additional question.'

    answers = {question_type_mock.PRICE_PERCENTAGE_CONSTRAINT: True, question_type_mock.ADDITIONAL_QUESTION_TYPE: True}

    replies = [
        Result(data=[{'id': '12346', 'message': ['This is an additional question.']}], request={'url': 'another_question_url'}),
        Result(data=[{'id': '12347'}], request={'url': 'final_url'}),
    ]
    reply_callback.side_effect = replies

    ## Act
    result = handle_questions(original_result, answers, reply_callback)

    ## Assert
    assert result.request['url'] == original_result.request['url']
    assert len(reply_callback.call_args_list) == 2

    expected_calls = [
        call(original_result.data[0]['id'], answers[question_type_mock.PRICE_PERCENTAGE_CONSTRAINT]),
        call(replies[0].data[0]['id'], answers[question_type_mock.ADDITIONAL_QUESTION_TYPE]),
    ]

    assert expected_calls == reply_callback.call_args_list


def test_too_many_questions(original_result, answers, reply_callback):
    """Raises when the question loop exceeds the maximum number of attempts."""
    ## Arrange
    reply_callback.side_effect = [original_result] * 21

    ## Act & Assert
    with pytest.raises(RuntimeError) as cm_err:
        handle_questions(original_result, answers, reply_callback)

    assert 'Too many questions' in str(cm_err.value)


def test_negative_reply(original_result, answers, reply_callback):
    """Raises when a question is answered negatively."""
    ## Arrange
    answers[QuestionType.PRICE_PERCENTAGE_CONSTRAINT] = False

    ## Act & Assert
    with pytest.raises(RuntimeError) as cm_err:
        handle_questions(original_result, answers, reply_callback)

    assert (
        f'A question was not given a positive reply. Question: "{original_result.data[0]["message"][0]}". Answers: \n{answers}\n. Request: {original_result.request}'
        == str(cm_err.value)
    )


def test_multiple_orders_returned(original_result, answers, reply_callback):
    """Logs a message when multiple orders are returned while handling questions."""
    ## Arrange
    original_result.data = [
        {'id': '12345', 'message': [str(QuestionType.PRICE_PERCENTAGE_CONSTRAINT)]},
        {'id': '12346', 'message': [str(QuestionType.PRICE_PERCENTAGE_CONSTRAINT)]},
    ]
    reply_callback.return_value = original_result.copy(data=[{}])

    expected = 'While handling questions multiple orders were returned: ' + pformat(original_result.data)

    ## Act & Assert
    with CaptureLogsContext('ibind', level='INFO', expected_errors=[expected], attach_stack=False):
        handle_questions(original_result, answers, reply_callback)


def test_multiple_messages_returned(original_result, answers, reply_callback):
    """Logs a message when multiple messages are returned for a single order."""
    ## Arrange
    original_result.data = [{'id': '12345', 'message': [str(QuestionType.PRICE_PERCENTAGE_CONSTRAINT), 'Message 2']}]
    reply_callback.return_value = original_result.copy(data=[{}])

    expected = 'While handling questions multiple messages were returned: ' + pformat(original_result.data[0]['message'])

    ## Act & Assert
    with CaptureLogsContext('ibind', level='INFO', expected_errors=[expected], attach_stack=False):
        handle_questions(original_result, answers, reply_callback)


# --------------------------------------------------------------------------------------
# Order request parsing
# --------------------------------------------------------------------------------------


def test_parse_both_with_conidex():
    """Parses OrderRequest with conid=None and conidex set into API payload."""
    ## Arrange
    order_request = OrderRequest(
        conid=None,
        side='BUY',
        quantity=321,
        order_type='MKT',
        acct_id='DU1234567',
        conidex='33333',
    )

    ## Act
    d = parse_order_request(order_request)

    ## Assert
    assert {
        'side': 'BUY',
        'quantity': 321,
        'orderType': 'MKT',
        'acctId': 'DU1234567',
        'conidex': '33333',
        'tif': 'GTC',
    } == d


def test_raise_with_conid_and_conidex():
    """Raises when both conid and conidex are provided."""
    ## Arrange

    ## Act & Assert
    with pytest.raises(ValueError) as cm_err:
        order_request = OrderRequest(
            conid=123,
            side='BUY',
            quantity=321,
            order_type='MKT',
            acct_id='DU1234567',
            conidex='33333',
        )

        parse_order_request(order_request)

    assert "Both 'conidex' and 'conid' are provided. When using 'conidex', specify `conid=None`." == str(cm_err.value)