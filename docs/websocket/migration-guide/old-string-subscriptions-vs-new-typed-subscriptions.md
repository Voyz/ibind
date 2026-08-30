# V1 String Subscriptions vs V2 Typed Subscriptions

In the v1 client, subscriptions were raw string channel identifiers assembled by hand, with extra parameters passed as a separate `data` dict. In v2 each channel type has a dedicated `Subscription` class that encapsulates the channel string, parameters, and confirmation behaviour.

## Channel to subscription class mapping

| Old channel                          | Subscription class           |
|--------------------------------------|------------------------------|
| `md+<conid>`                         | `MarketDataSubscription`     |
| `mh+<conid>`                         | `MarketHistorySubscription`  |
| `or`                                 | `OrdersSubscription`         |
| `pl`                                 | `PnlSubscription`            |
| `tr`                                 | `TradesSubscription`         |
| `sd+<account_id>`                    | `AccountSummarySubscription` |
| `ld+<account_id>`                    | `AccountLedgerSubscription`  |
| `bd+<account_id>+<conid>+<exchange>` | `PriceLadderSubscription`    |

All subscription classes are importable from `ibind.subscriptions`.

## Subscribe and unsubscribe

The call signatures have changed. In the old client, `subscribe()` and `unsubscribe()` accepted raw strings and an optional `data` dict:

```python
client.subscribe('md+265598', data={'fields': ['31', '84', '86']})
client.unsubscribe('md+265598', data={})
```

In v2, both accept a `Subscription` instance:

```python
from ibind.subscriptions import MarketDataSubscription

sub = MarketDataSubscription(conid='265598', fields=['31', '84', '86'])
handle = client.subscribe(sub)
client.unsubscribe(sub)
```

The return type has also changed. The v1 `subscribe()` returned `bool` and blocked until confirmation (for channels that confirm subscription). The v2 `subscribe()` returns a `SubscriptionHandle` immediately, is non-blocking and idempotent. Use `handle.wait(timeout)` if you need to block until the subscription is confirmed active.


## Market history

Market history was the most complex subscription in the v1 client. Unsubscribing required tracking the `serverId` returned by the server and a custom `SubscriptionProcessor` subclass:

**Before:**
```python
class MhSubscriptionProcessor(IbkrSubscriptionProcessor):
    def make_unsubscribe_payload(self, channel: str, server_id: dict = None) -> str:
        return f'umh+{server_id}'

processor = MhSubscriptionProcessor()

client.subscribe('mh+265598', data={'period': '1min', 'bar': '1min'})

# unsubscribe required looking up the server id manually
for server_id, conid in client.server_ids(IbkrWsKey.MARKET_HISTORY).items():
    client.unsubscribe(f'mh+{conid}', server_id, True, processor)
```

**After:**
```python
from ibind.subscriptions import MarketHistorySubscription

sub = MarketHistorySubscription(conid='265598', period='1min', bar='1min')
handle = client.subscribe(sub)

# unsubscribe using the same instance - server id is tracked internally
client.unsubscribe(sub)
```

The `server_id` is now set on the subscription instance automatically when the first `MarketHistory` event is received for that conid. No custom processor or manual tracking required. To ensure this functionality works, make sure to pass the same subscription instance to `subscribe()` and `unsubscribe()` or populate the `server_id` manually. 

## Account-keyed subscriptions

**Before:**
```python
client.subscribe(f'sd+{account_id}')
client.subscribe(f'ld+{account_id}')
```

**After:**
```python
from ibind.subscriptions import AccountSummarySubscription, AccountLedgerSubscription

client.subscribe(AccountSummarySubscription(account_id=account_id))
client.subscribe(AccountLedgerSubscription(account_id=account_id))
```

## Parameterless subscriptions

**Before:**
```python
client.subscribe('or')
client.subscribe('pl')
client.subscribe('tr')
```

**After:**
```python
from ibind.subscriptions import OrdersSubscription, PnlSubscription, TradesSubscription

client.subscribe(OrdersSubscription())
client.subscribe(PnlSubscription())
client.subscribe(TradesSubscription())
```


[subscriptions]: ../core-concepts/subscriptions.md