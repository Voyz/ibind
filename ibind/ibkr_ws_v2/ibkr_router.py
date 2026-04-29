import json
from collections import defaultdict
from typing import Dict

from client import ibkr_definitions
from client.ibkr_utils import extract_conid
from ibkr_ws_v2 import ibkr_events
from ibkr_ws_v2.ibkr_events import ParsedIbkrMessage, IbkrWsKey
from support.logs import project_logger
from support.py_utils import UNDEFINED, OneOrMany
from ws_v2.events import WsEvent

_LOGGER = project_logger(__file__)


def parse_raw_message(raw_message: str):
    message = json.loads(raw_message)
    # print(message)
    topic = message.get('topic', UNDEFINED)

    if topic is UNDEFINED:
        return message, None, None, None, None

    data = message.get('args', {})

    # subscribed is the indicator of whether it was a subscription or unsubscription, defined by the first letter
    # channel is the actual channel we received the information about
    subscribed, channel = topic[0], topic[1:]

    return message, topic, data, subscribed, channel


class IbkrRouter():
    def __init__(
        self,
        log_raw_messages: bool = False,
        unwrap_market_data: bool = True
    ):
        self._log_raw_messages = log_raw_messages
        self._unwrap_market_data = unwrap_market_data
        self._server_id_conid_pairs: Dict[IbkrWsKey, Dict[str, int]] = defaultdict(dict)

    def _preprocess_market_data_message(self, data: dict) -> OneOrMany[WsEvent]:
        """
        API will only return fields that were updated. If you are not receiving certain fields in the response - means that they remain unchanged.
        """
        if 'conid' not in data:  # pragma: no cover
            # sometimes the ticker message is just an empty update, we ignore it
            return []

        if not self._unwrap_market_data:
            return ibkr_events.MarketData(conid=data['conid'], data=data)
            # return {data['conid']: data}

        # result = {'conid': data['conid'], '_updated': data['_updated'], 'topic': data['topic']}
        fields = {}
        for key, value in data.items():
            if key in ibkr_definitions.snapshot_by_id:
                # result[ibkr_definitions.snapshot_by_id[key]] = value
                fields[ibkr_definitions.snapshot_by_id[key]] = value
        return ibkr_events.MarketData(conid=str(data['conid']), fields=fields)
        # return {data['conid']: result}

    def _preprocess_market_history_message(self, data: dict) -> OneOrMany[WsEvent]:
        mh_server_id_conid_pairs = self._server_id_conid_pairs[IbkrWsKey.MARKET_HISTORY]
        if 'serverId' in data and data['serverId'] not in mh_server_id_conid_pairs:
            mh_server_id_conid_pairs[data['serverId']] = extract_conid(data)

        return ibkr_events.MarketHistory(conid=str(data['conid']), data=data)

    def _preprocess_account_leger(self, data):
        events = []
        for entry in data['result']:
            if 'acctCode' not in entry:
                continue
            event = ibkr_events.AccountLedger(data=entry, account_id=entry['acctCode'])
            events.append(event)
        return events

    def _handle_subscribed_message(self, channel: str, data: dict) -> OneOrMany[WsEvent] | None:
        try:
            ibkr_ws_key = IbkrWsKey.from_channel(channel[:2])
        except ValueError:
            # ValueError means we don't support this channel
            return None

        if ibkr_ws_key == IbkrWsKey.ACCOUNT_SUMMARY:
            return ibkr_events.AccountSummary(data=data)
        elif ibkr_ws_key == IbkrWsKey.ACCOUNT_LEDGER:
            return self._preprocess_account_leger(data)
        elif ibkr_ws_key == IbkrWsKey.MARKET_DATA:
            return self._preprocess_market_data_message(data)
        elif ibkr_ws_key == IbkrWsKey.MARKET_HISTORY:
            return self._preprocess_market_history_message(data)
        elif ibkr_ws_key == IbkrWsKey.PRICE_LADDER:
            return ibkr_events.PriceLadder(data=data)
        elif ibkr_ws_key == IbkrWsKey.ORDERS:
            return ibkr_events.Orders(data=data)
        elif ibkr_ws_key == IbkrWsKey.PNL:
            return ibkr_events.Pnl(data=data)
        elif ibkr_ws_key == IbkrWsKey.TRADES:
            return ibkr_events.Trades(data=data)
        else:
            _LOGGER.error(f'{self}: Unhandled subscribed message: {data}')
            return None

    def _handle_account_update(self, message, arguments) -> OneOrMany[WsEvent]:
        # if 'accounts' in data and self._account_id not in data['accounts']:
        #     _LOGGER.error(f'{self}: Account ID mismatch: expected={self._account_id}, received={data["accounts"]}')
        # if 'acctProps' in data:  # expected account update that we ignore
        #     return []

        _LOGGER.info(f'{self}: Account update: {arguments}')
        return ibkr_events.AccountUpdate(data=arguments)

    def _handle_authentication_status(self, message, arguments) -> OneOrMany[WsEvent]:
        # if 'authenticated' in arguments:
        #     if arguments.get('authenticated') is False:
        #         _LOGGER.error(f'{self}: Status unauthenticated: {arguments}')
        #
        #     # TODO: this needs to be handled in IbkrWsClient or WsRuntime
        #     # self.set_authenticated(data.get('authenticated'))
        # elif 'competing' in arguments:
        #     if arguments.get('competing') is False:
        #         pass
        #     _LOGGER.error(f'{self}: Authentication competing: {arguments}')

        if 'authenticated' in arguments:
            _LOGGER.info(f'{self}: Authentication status: {arguments}')
            return ibkr_events.AuthenticationStatus(data=arguments, authenticated=arguments.get('authenticated'), competing=arguments.get('competing'))
        elif (  # expected status updates that we ignore
                arguments == {'message': ''} or
                arguments.get('fail', '') == '' or
                'serverName' in arguments or
                'serverVersion' in arguments or
                'username' in arguments
        ):
            _LOGGER.info(f'{self}: Authentication silenced: {arguments}')
            pass

        return []

    def _handle_bulletin(self, message) -> OneOrMany[WsEvent]:  # pragma: no cover
        return ibkr_events.Bulletin(message=message)

    def _handle_error(self, message) -> OneOrMany[WsEvent]:
        _LOGGER.error(f'{self}: on_message error: {message}')
        return ibkr_events.IbkrError(message=message)

    def _handle_notification(self, data) -> OneOrMany[WsEvent]:  # pragma: no cover
        events = []
        for notification in data:
            _LOGGER.info(f'{self}: IBKR notification: {notification}')
            events.append(ibkr_events.Notification(message=notification))
        return events

    def _handle_market_history_unsubscribe(self, data) -> OneOrMany[WsEvent]:
        server_id = data['message'].split('Unsubscribed ')[-1]
        mh_server_id_conid_pairs = self._server_id_conid_pairs[IbkrWsKey.MARKET_HISTORY]
        if server_id in mh_server_id_conid_pairs:
            conid = mh_server_id_conid_pairs[server_id]
            _LOGGER.info(f'{self}: Received unsubscribing confirmation for server_id={server_id!r}/conid={conid!r}.')
            if conid is not None:
                return ibkr_events.Unsubscription(target_key=IbkrWsKey.MARKET_HISTORY, conid=conid)
                # self.modify_subscription(f'mh+{conid}', status=False)

            _LOGGER.warning(f'{self}: Unknown conid={conid!r}. Cannot mark the subscription as unsubscribed.')
        else:
            _LOGGER.warning(
                f'{self}: Received unsubscribing confirmation for unknown server_id={server_id!r}. Existing server_ids: {mh_server_id_conid_pairs}'
            )
        return []

    def _handle_message_without_topic(self, message: dict) -> OneOrMany[WsEvent]:
        if 'message' in message:
            if message['message'] == 'waiting for session':
                _LOGGER.info(f'{self}: Waiting for an active IBKR session.')
                return ibkr_events.WaitingForSession()

            if 'Unsubscribed' in message['message']:
                return self._handle_market_history_unsubscribe(message)

        elif 'result' in message:
            if message['result'] == 'unsubscribed from summary':
                return ibkr_events.Unsubscription(target_key=IbkrWsKey.ACCOUNT_SUMMARY)
                # return self.modify_subscription(f'sd+{self._account_id}', status=False)
            elif message['result'] == 'unsubscribed from ledger':
                return ibkr_events.Unsubscription(target_key=IbkrWsKey.ACCOUNT_LEDGER)
                # return self.modify_subscription(f'ld+{self._account_id}', status=False)

        _LOGGER.error(f'{self}: Unrecognised message without a topic: {message}')
        return ParsedIbkrMessage(message=message)

    def _preprocess_raw_message(self, raw_message: str):
        message = json.loads(raw_message)
        # print(message)
        topic = message.get('topic', UNDEFINED)

        if topic is UNDEFINED:
            return message, None, None, None, None

        data = message.get('args', {})

        # subscribed is the indicator of whether it was a subscription or unsubscription, defined by the first letter
        # channel is the actual channel we received the information about
        subscribed, channel = topic[0], topic[1:]

        return message, topic, data, subscribed, channel

    def route(self, raw_message: str) -> OneOrMany[WsEvent]:
        if self._log_raw_messages:
            _LOGGER.debug(f'{self}: Raw message: {raw_message}')
        message, topic, arguments, subscribed, channel = parse_raw_message(raw_message)

        if 'error' in message:
            return self._handle_error(message)

        elif topic is None:
            # in general most message should carry a topic, other than for few exceptions
            return self._handle_message_without_topic(message)

        elif topic == 'tic':
            self._tic_message = message

        elif topic == 'system':
            if 'hb' in message:
                self._last_heartbeat = message['hb']
            return ibkr_events.System(data=message)

        elif topic == 'act':
            return self._handle_account_update(message, arguments)

        elif topic == 'blt':
            return self._handle_bulletin(message)

        elif topic == 'ntf':
            return self._handle_notification(arguments)

        elif topic == 'sts':
            return self._handle_authentication_status(message, arguments)

        elif topic == 'error':
            return self._handle_error(message)
            # _LOGGER.error(f'{self}: Error message:  {message}')

        # elif self.has_subscription(channel):
        #     if not self.is_subscription_active(channel):
        #         self.modify_subscription(channel, status=True)
        else:
            events = self._handle_subscribed_message(channel, message)
            if events is None:
                _LOGGER.error(f'{self}: Channel "{channel}" subscribed but lacking a handler. Message: {message}')
                events = ParsedIbkrMessage(message=message, topic=topic, data=arguments, subscribed=subscribed, channel=channel)
            return events
            # _LOGGER.warning(f'{self}: Handled a channel "{channel}" message that is missing a subscription. Message: {message}')

        _LOGGER.error(f'{self}: Topic "{topic}" unrecognised. Message: {message}')
        return ParsedIbkrMessage(message=message, topic=topic, data=arguments, subscribed=subscribed, channel=channel)

    # def route(self, raw_message) -> List[WsEvent]:
    # _LOGGER.debug(f'{self}: Routing message: {raw_message}')
    # message, topic, data, subscribed, channel = parse_raw_message(raw_message)
    # return [ParsedIbkrMessage(message=message, topic=topic, data=data, subscribed=subscribed, channel=channel)]

    def __str__(self):
        return f'{self.__class__.__qualname__}()'