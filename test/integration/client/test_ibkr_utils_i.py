from pprint import pformat
from unittest import TestCase
from unittest.mock import MagicMock, patch, call

from ibind.client.ibkr_utils import StockQuery, filter_stocks, find_answer, QuestionType, handle_questions
from ibind.support.logs import project_logger
from ibind.base.rest_client import Result
from test.integration.client import ibkr_responses

from test_utils import verify_log


class TestIbkrUtilsI(TestCase):

    def setUp(self):
        self.instruments = ibkr_responses.responses['stocks']
        self.result = Result(data=self.instruments)
        self.maxDiff = None

    def test_filter_stocks(self):
        queries = [
            StockQuery(symbol='AAPL', contract_conditions={'isUS': False}, name_match='APPLE'),
            StockQuery(symbol='BBVA', contract_conditions={'exchange': 'NYSE'}),
            StockQuery(symbol='CDN', contract_conditions={'isUS': True}),
            StockQuery(symbol='CFC', contract_conditions={}),
            StockQuery(symbol='GOOG', contract_conditions={'isUS': False}, instrument_conditions={'chineseName': 'Alphabet&#x516C;&#x53F8;'}),
            'HUBS',
            StockQuery(symbol='META', name_match='meta ', contract_conditions={'isUS': False}, instrument_conditions={}),
            StockQuery(symbol='MSFT', contract_conditions={'exchange': 'NASDAQ'}),
            StockQuery(symbol='SAN', name_match='SANTANDER'),
            StockQuery(symbol='SCHW', contract_conditions={'exchange': 'NASDAQ'}),
            StockQuery(symbol='TEAM', name_match='ATLASSIAN'),
            StockQuery(symbol='INVALID_SYMBOL')
        ]
        with self.assertLogs(project_logger(), level='INFO') as cm:
            rv = filter_stocks(queries, Result(data=self.instruments), default_filtering=False)

        verify_log(self, cm, [f'Error getting stocks. Could not find valid instruments INVALID_SYMBOL in result: {self.result}. Skipping query={queries[-1]}.'])

        # pprint(rv)

        self.assertEqual([
            {
                "assetClass": "STK",
                "chineseName": "&#x82F9;&#x679C;&#x516C;&#x53F8;",
                "contracts": [
                    {"conid": 38708077, "exchange": "MEXI", "isUS": False},
                    {"conid": 273982664, "exchange": "EBS", "isUS": False},
                ],
                "name": "APPLE INC",
            },
            {
                "assetClass": "STK",
                "chineseName": "&#x82F9;&#x679C;&#x516C;&#x53F8;",
                "contracts": [
                    {"conid": 532640894, "exchange": "AEQLIT", "isUS": False}
                ],
                "name": "APPLE INC-CDR",
            },
        ], rv.data['AAPL'])

        self.assertEqual([
            {
                "assetClass": "STK",
                "chineseName": "&#x897F;&#x73ED;&#x7259;&#x5BF9;&#x5916;&#x94F6;&#x884C;",
                "contracts": [{"conid": 4815, "exchange": "NYSE", "isUS": True}],
                "name": "BANCO BILBAO VIZCAYA-SP ADR",
            },
        ], rv.data['BBVA'])

        self.assertEqual([], rv.data['CDN'])

        self.assertEqual([
            {
                "assetClass": "STK",
                "chineseName": None,
                "contracts": [{"conid": 42001300, "exchange": "IBIS", "isUS": False}],
                "name": "UET UNITED ELECTRONIC TECHNO",
            }
        ], rv.data['CFC'])

        self.assertEqual([
            {
                "assetClass": "STK",
                "chineseName": "Alphabet&#x516C;&#x53F8;",
                "contracts": [
                    {"conid": 210810667, "exchange": "MEXI", "isUS": False},
                ],
                "name": "ALPHABET INC-CL C",
            },
            {
                "assetClass": "STK",
                "chineseName": "Alphabet&#x516C;&#x53F8;",
                "contracts": [
                    {"conid": 532638805, "exchange": "AEQLIT", "isUS": False}
                ],
                "name": "ALPHABET INC - CDR",
            }
        ], rv.data['GOOG'])

        self.assertEqual([
            {
                "assetClass": "STK",
                "chineseName": "HubSpot&#x516C;&#x53F8;",
                "contracts": [{"conid": 169544810, "exchange": "NYSE", "isUS": True}],
                "name": "HUBSPOT INC",
            }
        ], rv.data['HUBS'])

        self.assertEqual([
            {
                "assetClass": "STK",
                "chineseName": "Meta&#x5E73;&#x53F0;&#x80A1;&#x4EFD;&#x6709;&#x9650;&#x516C;&#x53F8;",
                "contracts": [
                    {"conid": 114922621, "exchange": "MEXI", "isUS": False},
                ],
                "name": "META PLATFORMS INC-CLASS A",
            },
            {
                "assetClass": "STK",
                "chineseName": "Meta&#x5E73;&#x53F0;&#x80A1;&#x4EFD;&#x6709;&#x9650;&#x516C;&#x53F8;",
                "contracts": [
                    {"conid": 530091499, "exchange": "AEQLIT", "isUS": False}
                ],
                "name": "META PLATFORMS INC-CDR",
            },
        ], rv.data['META'])

        self.assertEqual([
            {
                "assetClass": "STK",
                "chineseName": "&#x5FAE;&#x8F6F;&#x516C;&#x53F8;",
                "contracts": [
                    {"conid": 272093, "exchange": "NASDAQ", "isUS": True},
                ],
                "name": "MICROSOFT CORP",
            },
        ], rv.data['MSFT'])

        self.assertEqual([
            {
                "assetClass": "STK",
                "chineseName": "&#x6851;&#x5766;&#x5FB7;",
                "contracts": [
                    {"conid": 38708867, "exchange": "MEXI", "isUS": False},
                    {"conid": 385055564, "exchange": "WSE", "isUS": False},
                ],
                "name": "BANCO SANTANDER SA",
            },
            {
                "assetClass": "STK",
                "chineseName": "&#x6851;&#x5766;&#x5FB7;",
                "contracts": [{"conid": 12442, "exchange": "NYSE", "isUS": True}],
                "name": "BANCO SANTANDER SA-SPON ADR",
            },
            {
                "assetClass": "STK",
                "chineseName": "&#x6851;&#x5766;&#x5FB7;&#x82F1;&#x56FD;&#x516C;&#x5171;&#x6709;&#x9650;&#x516C;&#x53F8;",
                "contracts": [{"conid": 80993135, "exchange": "LSE", "isUS": False}],
                "name": "SANTANDER UK PLC",
            },
        ], rv.data['SAN'])

        self.assertEqual([], rv.data['SCHW'])

        self.assertEqual([
            {
                "assetClass": "STK",
                "chineseName": None,
                "contracts": [{"conid": 589316251, "exchange": "NASDAQ", "isUS": True}],
                "name": "ATLASSIAN CORP-CL A",
            },
        ], rv.data['TEAM'])


class TestFindAnswer(TestCase):
    def setUp(self):
        # Setup Answers dictionary here
        self.answers = {QuestionType.PRICE_PERCENTAGE_CONSTRAINT: True}

    def test_valid_question(self):
        question = f"Some {QuestionType.PRICE_PERCENTAGE_CONSTRAINT} specific question"
        answer = find_answer(question, self.answers)
        self.assertTrue(answer)

    def test_invalid_question(self):
        question = "Nonexistent question type"
        with self.assertRaises(ValueError):
            find_answer(question, self.answers)

class TestHandleQuestionsI(TestCase):
    def setUp(self):
        self.original_result = Result(
            data=[{'id': '12345', 'message': ['price exceeds the Percentage constraint of 3%.']}],
            request={'url': 'test_url'}
        )
        self.answers = {QuestionType.PRICE_PERCENTAGE_CONSTRAINT: True}
        self.reply_callback = MagicMock()


    @patch('ibind.client.ibkr_utils.QuestionType')
    def test_successful_handling(self, question_type_mock):
        # Mocking the QuestionType enum
        question_type_mock.PRICE_PERCENTAGE_CONSTRAINT.__str__.return_value = 'price exceeds the Percentage constraint of 3%.'
        question_type_mock.ADDITIONAL_QUESTION_TYPE.__str__.return_value = 'This is an additional question.'

        self.answers = {
            question_type_mock.PRICE_PERCENTAGE_CONSTRAINT: True,
            question_type_mock.ADDITIONAL_QUESTION_TYPE: True
        }

        # Mock reply_callback to simulate the sequence of question-answer interactions
        replies = [
            Result(data=[{'id': '12346', 'message': ['This is an additional question.']}], request={'url': 'another_question_url'}),
            Result(data=[{'id': '12347'}], request={'url': 'final_url'})  # No more questions
        ]
        self.reply_callback.side_effect = replies

        result = handle_questions(self.original_result, self.answers, self.reply_callback)
        self.assertEqual(result.request['url'], self.original_result.request['url'])
        self.assertEqual(len(self.reply_callback.call_args_list), 2)
        # Expected calls to self.reply_callback
        expected_calls = [
            call(self.original_result.data[0]['id'], self.answers[question_type_mock.PRICE_PERCENTAGE_CONSTRAINT]),  # First call with question ID '12346' and reply True
            call(replies[0].data[0]['id'], self.answers[question_type_mock.ADDITIONAL_QUESTION_TYPE])   # Second call with question ID '12347' and reply True
        ]

        # Check if the calls to self.reply_callback are as expected
        self.assertEqual(expected_calls, self.reply_callback.call_args_list)


    def test_too_many_questions(self):
        # Simulate repetitive questions to exceed the question limit
        self.reply_callback.side_effect = [self.original_result] * 21

        with self.assertRaises(RuntimeError) as cm_err:
            handle_questions(self.original_result, self.answers, self.reply_callback)

        self.assertIn("Too many questions", str(cm_err.exception))


    def test_negative_reply(self):
        # Set a negative answer
        self.answers[QuestionType.PRICE_PERCENTAGE_CONSTRAINT] = False

        with self.assertRaises(RuntimeError) as cm_err:
            handle_questions(self.original_result, self.answers, self.reply_callback)
        self.assertEqual(f'A question was not given a positive reply. Question: "{self.original_result.data[0]["message"][0]}". Answers: \n{self.answers}\n. Request: {self.original_result.request}', str(cm_err.exception))

    def test_multiple_orders_returned(self):
        # Simulate multiple orders in the data
        self.original_result.data = [{'id': '12345', 'message': [str(QuestionType.PRICE_PERCENTAGE_CONSTRAINT)]}, {'id': '12346', 'message': [str(QuestionType.PRICE_PERCENTAGE_CONSTRAINT)]}]
        self.reply_callback.return_value = self.original_result.copy(data=[{}])

        with self.assertLogs(project_logger(), level='INFO') as cm:
            handle_questions(self.original_result, self.answers, self.reply_callback)

        verify_log(self, cm, ["While handling questions multiple orders were returned: " + pformat(self.original_result.data)])

    def test_multiple_messages_returned(self):
        # Simulate a single order with multiple messages
        self.original_result.data = [{'id': '12345', 'message': [str(QuestionType.PRICE_PERCENTAGE_CONSTRAINT), 'Message 2']}]
        self.reply_callback.return_value = self.original_result.copy(data=[{}])

        with self.assertLogs(project_logger(), level='INFO') as cm:
            handle_questions(self.original_result, self.answers, self.reply_callback)

        verify_log(self, cm, ["While handling questions multiple messages were returned: " + pformat(self.original_result.data[0]['message'])])
