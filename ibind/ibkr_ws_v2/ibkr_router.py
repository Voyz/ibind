import json
from collections import defaultdict
from typing import Dict

from ibind.client import ibkr_definitions
from ibind.client.ibkr_utils import extract_conid

from ibind import events
from ibind.events import GenericIbkrEvent, IbkrTopicEvent
from ibind.support.logs import project_logger
from ibind.support.py_utils import UNDEFINED, OneOrMany
from ibind.events import WsEvent

_LOGGER = project_logger('ibkr_ws_client')


def get_ibkr_topic_event(topic: str):
    topic_to_event_type = {
        'sd': events.AccountSummary,
        'ld': events.AccountLedger,
        'md': events.MarketData,
        'mh': events.MarketHistory,
        'bd': events.PriceLadder,
        'or': events.Orders,
        'pl': events.Pnl,
        'tr': events.Trades,
    }
    if topic in topic_to_event_type:
        return topic_to_event_type[topic]
    raise ValueError(f"No Ibkr event associated with topic '{topic}'")


def parse_raw_message(raw_message: str):
    message = json.loads(raw_message)
    topic = message.get('topic', UNDEFINED)

    if topic is UNDEFINED:
        return message, None, None

    arguments = message.get('args', {})

    return message, topic, arguments


class IbkrRouter:
    def __init__(self, log_raw_messages: bool = False, unwrap_market_data: bool = True):
        self._log_raw_messages = log_raw_messages
        self._unwrap_market_data = unwrap_market_data
        self._server_id_conid_pairs: Dict[type[IbkrTopicEvent], Dict[str, str]] = defaultdict(dict)

    def _preprocess_market_data_message(self, data: dict) -> OneOrMany[WsEvent]:
        """
        API will only return fields that were updated. If you are not receiving certain fields in the response - means that they remain unchanged.
        """
        if 'conid' not in data:  # pragma: no cover
            # sometimes the ticker message is just an empty update, we ignore it
            return []

        if not self._unwrap_market_data:
            return events.MarketData(conid=data['conid'], data=data)

        unwrapped_data = {}
        for key, value in data.items():
            if key in ibkr_definitions.snapshot_by_id:
                unwrapped_data[ibkr_definitions.snapshot_by_id[key]] = value
        return events.MarketData(conid=str(data['conid']), data=unwrapped_data)

    def _preprocess_market_history_message(self, data: dict) -> OneOrMany[WsEvent]:
        mh_server_id_conid_pairs = self._server_id_conid_pairs[events.MarketHistory]
        rv = []
        conid = extract_conid(data)
        if 'serverId' in data and data['serverId'] not in mh_server_id_conid_pairs:
            mh_server_id_conid_pairs[data['serverId']] = str(conid)
            rv.append(events.ServerId(conid=str(conid), server_id=data['serverId'], target_event_type=events.MarketHistory))

        rv.append(events.MarketHistory(conid=str(conid), data=data))
        return rv

    def _preprocess_account_ledger(self, data: dict) -> OneOrMany[WsEvent]:
        rv = []
        for entry in data['result']:
            if 'acctCode' not in entry:
                continue
            event = events.AccountLedger(data=entry, account_id=entry['acctCode'])
            rv.append(event)
        return rv

    def _preprocess_account_summary(self, data: dict) -> OneOrMany[WsEvent]:
        summary = {}
        timestamp = data['result'][0]['timestamp']
        for entry in data['result']:
            key = entry.pop('key')
            entry.pop('timestamp')

            if entry == {}:
                continue

            summary[key] = entry

        if summary == {}:
            return []

        if 'AccountCode' not in summary or 'value' not in summary['AccountCode']:
            _LOGGER.error(f'{self}: Account code not found in account summary: {summary}')
            return []

        account_id = summary['AccountCode']['value']
        summary['timestamp'] = timestamp

        event = events.AccountSummary(data=summary, account_id=account_id)
        return event

    def _preprocess_orders(self, data: dict) -> OneOrMany[WsEvent]:
        for order_data in data.get('args', []):
            order_data.pop('bgColor', None)
            order_data.pop('fgColor', None)
        return events.Orders(data=data)

    def _handle_subscribed_message(self, topic: str, data: dict) -> OneOrMany[WsEvent] | None:
        try:
            # ibkr_ws_key = IbkrWsKey.from_topic(topic[1:3])
            event_type = get_ibkr_topic_event(topic[1:3])
        except ValueError:
            # ValueError means we don't support this topic
            return None

        if event_type == events.AccountSummary:
            rv = self._preprocess_account_summary(data)
        elif event_type == events.AccountLedger:
            rv = self._preprocess_account_ledger(data)
        elif event_type == events.MarketData:
            rv = self._preprocess_market_data_message(data)
        elif event_type == events.MarketHistory:
            rv = self._preprocess_market_history_message(data)
        elif event_type == events.PriceLadder:
            rv = events.PriceLadder(data=data)
        elif event_type == events.Orders:
            rv = self._preprocess_orders(data)
        elif event_type == events.Pnl:
            rv = events.Pnl(data=data)
        elif event_type == events.Trades:
            rv = events.Trades(data=data)
        else:
            _LOGGER.error(f'{self}: Unhandled subscribed message: {data}')
            rv = None
        return rv

    def _handle_account_update(self, data, arguments) -> OneOrMany[WsEvent]:
        return events.AccountUpdate(data=arguments)

    def _handle_authentication_status(self, data, arguments) -> OneOrMany[WsEvent]:
        if 'authenticated' in arguments or 'competing' in arguments:
            return events.AuthenticationStatus(data=arguments, authenticated=arguments.get('authenticated'), competing=arguments.get('competing'))
        elif (  # expected status updates that we ignore
            arguments == {'message': ''}
            or arguments.get('fail', '') == ''
            or 'serverName' in arguments
            or 'serverVersion' in arguments
            or 'username' in arguments
        ):
            pass

        return []

    def _handle_bulletin(self, data) -> OneOrMany[WsEvent]:  # pragma: no cover
        return events.Bulletin(data=data)

    def _handle_error(self, data: dict) -> OneOrMany[WsEvent]:
        _LOGGER.error(f'{self}: on_message error: {data}')
        return events.IbkrError(data=data)

    def _handle_notification(self, data) -> OneOrMany[WsEvent]:  # pragma: no cover
        rv = []
        for notification in data:
            rv.append(events.Notification(data=notification))
        return rv

    def _handle_market_history_unsubscribe(self, data) -> OneOrMany[WsEvent]:
        server_id = data['message'].split('Unsubscribed ')[-1]
        mh_server_id_conid_pairs = self._server_id_conid_pairs[events.MarketHistory]
        if server_id in mh_server_id_conid_pairs:
            conid = mh_server_id_conid_pairs[server_id]
            _LOGGER.info(f'{self}: Received unsubscribing confirmation for server_id={server_id!r}, conid={conid!r}.')
            if conid is not None:
                return events.Unsubscription(target_event_type=events.MarketHistory, conid=str(conid))

            _LOGGER.warning(f'{self}: Unknown conid={conid!r}. Cannot mark the subscription as unsubscribed.')
        else:
            _LOGGER.warning(
                f'{self}: Received unsubscribing confirmation for unknown server_id={server_id!r}. Existing server_ids: {mh_server_id_conid_pairs}'
            )
        return []

    def _handle_message_without_topic(self, data: dict) -> OneOrMany[WsEvent]:
        if 'message' in data:
            if data['message'] == 'waiting for session':
                _LOGGER.info(f'{self}: Waiting for an active IBKR session.')
                return events.WaitingForSession()

            if 'Unsubscribed' in data['message']:
                return self._handle_market_history_unsubscribe(data)

        elif 'result' in data:
            if data['result'] == 'unsubscribed from summary':
                return events.Unsubscription(target_event_type=events.AccountSummary)
            elif data['result'] == 'unsubscribed from ledger':
                return events.Unsubscription(target_event_type=events.AccountLedger)

        _LOGGER.error(f'{self}: Unrecognised message without a topic: {data}')
        return GenericIbkrEvent(message=data)

    def route(self, raw_message: str) -> OneOrMany[WsEvent]:
        if self._log_raw_messages:
            _LOGGER.debug(f'{self}: Raw data: {raw_message}')
        data, topic, arguments = parse_raw_message(raw_message)

        if 'error' in data:
            rv = self._handle_error(data)

        elif topic is None:
            # in general most data should carry a topic, other than for few exceptions
            rv = self._handle_message_without_topic(data)

        elif topic == 'tic':
            # self._tic_message = data
            rv = events.System(data=data)

        elif topic == 'system':
            rv = events.System(data=data)

        elif topic == 'act':
            rv = self._handle_account_update(data, arguments)

        elif topic == 'blt':
            rv = self._handle_bulletin(data)

        elif topic == 'ntf':
            rv = self._handle_notification(arguments)

        elif topic == 'sts':
            rv = self._handle_authentication_status(data, arguments)

        elif topic == 'error':
            rv = self._handle_error(data)

        else:
            rv = self._handle_subscribed_message(topic, data)
            if rv is None:
                _LOGGER.error(f'{self}: topic "{topic}" subscribed but lacking a handler. Message: {data}')
                rv = GenericIbkrEvent(message=data, topic=topic, data=arguments)

        return rv

    def __str__(self):
        return f'{self.__class__.__qualname__}()'
