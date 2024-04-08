import datetime
from typing import Union, TYPE_CHECKING

from ibind.base.rest_client import Result
from ibind.client.ibkr_definitions import decode_data_availability
from ibind.client.ibkr_utils import StockQuery, StockQueries
from ibind.support.errors import ExternalBrokerError
from ibind.support.logs import project_logger
from ibind.support.py_utils import ensure_list_arg, OneOrMany, execute_in_parallel, params_dict

if TYPE_CHECKING:  # pragma: no cover
    from ibind import IbkrClient

_LOGGER = project_logger(__file__)


class MarketdataMixin():

    @ensure_list_arg('conids')
    def live_marketdata_snapshot(self: 'IbkrClient', conids: OneOrMany[str], fields: OneOrMany[str]) -> Result:
        params = {
            'conids': ','.join(conids),
            'fields': ','.join(fields)
        }
        return self.get(f'iserver/secdef/search', params)

    def regulatory_snapshot(self: 'IbkrClient', conid: str) -> Result:
        return self.get(f'md/regsnapshot', {'conid': conid})

    def marketdata_history_by_conid(
            self: 'IbkrClient',
            conid: str,
            bar: str,
            exchange: str = None,
            period: str = None,
            outside_rth: bool = None,
            start_time: datetime.datetime = None
    ) -> Result:  # pragma: no cover
        """
        period: {1-30}min, {1-8}h, {1-1000}d, {1-792}w, {1-182}m, {1-15}y
        bar: 1min, 2min, 3min, 5min, 10min, 15min, 30min, 1h, 2h, 3h, 4h, 8h, 1d, 1w, 1m
        """
        params = params_dict(
            {
                'conid': conid,
                'bar': bar
            },
            optional={
                'exchange': exchange,
                'period': period,
                'outsideRth': outside_rth,
                'startTime': start_time
            },
            preprocessors={
                'startTime': lambda x: x.strftime('')
            }
        )

        return self.get('iserver/marketdata/history', params)

    def historical_marketdata_beta(
            self: 'IbkrClient',
            conid: str,
            period: str,
            bar: str,
            outside_rth: bool = None,
            start_time: datetime.datetime = None,
            direction: str = None,
            bar_type: str = None,
    ) -> Result:  # pragma: no cover
        """
        period: {1-30}min, {1-8}h, {1-1000}d, {1-792}w, {1-182}m, {1-15}y
        bar: 1min, 2min, 3min, 5min, 10min, 15min, 30min, 1h, 2h, 3h, 4h, 8h, 1d, 1w, 1m
        """
        params = params_dict(
            {
                'conid': conid,
                'period': period,
                'bar': bar
            },
            optional={
                'outsideRth': outside_rth,
                'startTime': start_time,
                'direction': direction,
                'barType': bar_type,
            },
            preprocessors={
                'startTime': lambda x: x.strftime('')
            }
        )

        return self.get('hmds/history', params)

    def marketdata_history_by_symbol(
            self: 'IbkrClient',
            symbol: Union[str, StockQuery],
            exchange: str = None,
            period: str = None,
            bar: str = None,
            outside_rth: bool = None
    ) -> Result:  # pragma: no cover
        conid = self.get_conids(symbol).data[symbol]
        return self.marketdata_history_by_conid(conid, exchange, period, bar, outside_rth)

    @ensure_list_arg('conids')
    def marketdata_unsubscribe(self: 'IbkrClient', conids: OneOrMany[int]):
        # we unsubscribe from all conids simultaneously
        unsubscribe_requests = {conid: {'args': [f'iserver/marketdata/{conid}/unsubscribe']} for conid in conids}
        results = execute_in_parallel(self.post, unsubscribe_requests)

        for conid, result in results.items():
            if isinstance(result, Exception):
                # 404 means that no such subscription was found in first place, which we ignore
                if isinstance(result, ExternalBrokerError) and result.status_code == 404:
                    continue
                raise result

        return results

    def marketdata_unsubscribe_all(self: 'IbkrClient') -> Result:  # pragma: no cover
        return self.get(f'iserver/marketdata/unsubscribeall')

    @ensure_list_arg('queries')
    def marketdata_history_by_symbols(
            self: 'IbkrClient',
            queries: StockQueries,
            period: str = "1min",
            bar: str = "1min",
            outside_rth: bool = True
    ) -> dict:
        conids = self.get_conids(queries).data

        static_params = {"period": period, "bar": bar, "outside_rth": outside_rth}
        requests = {symbol: {"kwargs": {'conid': conid} | static_params} for symbol, conid in conids.items()}

        # /iserver/marketdata/history accepts 5 concurrent requests at a time
        history = execute_in_parallel(self.marketdata_history_by_conid, requests=requests, max_workers=5)

        results = {}
        for symbol, entry in history.items():
            if isinstance(entry, Exception):  # pragma: no cover
                _LOGGER.error(f'Error fetching market data for {symbol}')
                raise entry

            # check if entry['mdAvailability'] has 'S' or 'R' in it
            if 'mdAvailability' in entry.data and not (any((key in entry.data['mdAvailability'].upper()) for key in ['S', 'R'])):
                _LOGGER.warning(f'Market data for {symbol} is not live: {decode_data_availability(entry.data["mdAvailability"])}')

            data = entry.data['data']
            records = []
            for record in data:
                records.append({
                    "open": record['o'],
                    "high": record['h'],
                    "low": record['l'],
                    "close": record['c'],
                    "volume": record['v'],
                    "date": datetime.datetime.fromtimestamp(record['t'] / 1000)
                })
            results[symbol] = records

        return results
