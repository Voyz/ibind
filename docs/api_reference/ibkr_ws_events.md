# Table of Contents

* [ibkr\_events](#ibkr_ws.ibkr_events)
  * [GenericIbkrEvent](#ibkr_ws.ibkr_events.GenericIbkrEvent)
  * [IbkrError](#ibkr_ws.ibkr_events.IbkrError)
  * [WaitingForSession](#ibkr_ws.ibkr_events.WaitingForSession)
  * [Notification](#ibkr_ws.ibkr_events.Notification)
  * [Bulletin](#ibkr_ws.ibkr_events.Bulletin)
  * [AccountUpdate](#ibkr_ws.ibkr_events.AccountUpdate)
  * [System](#ibkr_ws.ibkr_events.System)
  * [AuthenticationStatus](#ibkr_ws.ibkr_events.AuthenticationStatus)
  * [IbkrTopicEvent](#ibkr_ws.ibkr_events.IbkrTopicEvent)
  * [AccountSummary](#ibkr_ws.ibkr_events.AccountSummary)
  * [AccountLedger](#ibkr_ws.ibkr_events.AccountLedger)
  * [MarketData](#ibkr_ws.ibkr_events.MarketData)
  * [MarketHistory](#ibkr_ws.ibkr_events.MarketHistory)
  * [Orders](#ibkr_ws.ibkr_events.Orders)
  * [PriceLadder](#ibkr_ws.ibkr_events.PriceLadder)
  * [Pnl](#ibkr_ws.ibkr_events.Pnl)
  * [Trades](#ibkr_ws.ibkr_events.Trades)
  * [ServerId](#ibkr_ws.ibkr_events.ServerId)
  * [Unsubscription](#ibkr_ws.ibkr_events.Unsubscription)
* [\_ws\_events](#ws._ws_events)
  * [WsEvent](#ws._ws_events.WsEvent)
  * [LifecycleEvent](#ws._ws_events.LifecycleEvent)
  * [WsStarting](#ws._ws_events.WsStarting)
  * [WsStopping](#ws._ws_events.WsStopping)
  * [WsStopped](#ws._ws_events.WsStopped)
  * [WsOpen](#ws._ws_events.WsOpen)
  * [WsAuthenticated](#ws._ws_events.WsAuthenticated)
  * [WsDegraded](#ws._ws_events.WsDegraded)
  * [WsReady](#ws._ws_events.WsReady)
  * [WsClose](#ws._ws_events.WsClose)
  * [WsError](#ws._ws_events.WsError)
  * [Router](#ws._ws_events.Router)
    * [route](#ws._ws_events.Router.route)

<a id="ibkr_ws.ibkr_events.GenericIbkrEvent"></a>

## GenericIbkrEvent

Fallback event for IBKR messages that could not be mapped to a specific event type.

Produced when a message carries an unrecognised topic-less payload, or when a known
topic has no dedicated handler.

Attributes:

- `message` _dict | None_ - The full raw message as received from IBKR.
- `topic` _str | None_ - The message topic, if one was present. Default: None.
- `data` _dict | None_ - The message arguments, if any were extracted. Default: None.

<a id="ibkr_ws.ibkr_events.IbkrError"></a>

## IbkrError

An error reported by IBKR.

Attributes:

- `data` _dict_ - The raw error payload from IBKR.

<a id="ibkr_ws.ibkr_events.WaitingForSession"></a>

## WaitingForSession

Signals that the client is waiting for an active IBKR brokerage session to be established.

<a id="ibkr_ws.ibkr_events.Notification"></a>

## Notification

An unsolicited IBKR notification (topic `ntf`), emitted once per notification.

Attributes:

- `data` _dict_ - The notification payload.

<a id="ibkr_ws.ibkr_events.Bulletin"></a>

## Bulletin

An unsolicited IBKR bulletin message (topic `blt`).

Attributes:

- `data` _dict_ - The bulletin payload.

<a id="ibkr_ws.ibkr_events.AccountUpdate"></a>

## AccountUpdate

Details of the current account (topic `act`).

Attributes:

- `data` _dict_ - The account update payload.

<a id="ibkr_ws.ibkr_events.System"></a>

## System

A system-level message such as a connection or heartbeat confirmation (topics `system` and `tic`).

Attributes:

- `data` _dict_ - The system message payload.

<a id="ibkr_ws.ibkr_events.AuthenticationStatus"></a>

## AuthenticationStatus

A change to the session's authentication status (topic `sts`).

Attributes:

- `data` _dict_ - The raw status payload.
- `authenticated` _bool | None_ - Whether the session is authenticated, or None when not reported.
- `competing` _bool | None_ - Whether another session is competing for the same account, or None
  when not reported.

<a id="ibkr_ws.ibkr_events.IbkrTopicEvent"></a>

## IbkrTopicEvent

Base class for solicited, topic-based IBKR events.

Attributes:

- `topic` _ClassVar[str]_ - The IBKR topic code the subclass corresponds to.

<a id="ibkr_ws.ibkr_events.AccountSummary"></a>

## AccountSummary

Account summary data (topic `sd`).

Attributes:

- `account_id` _str_ - The account the summary belongs to.
- `data` _dict_ - The account summary payload.

<a id="ibkr_ws.ibkr_events.AccountLedger"></a>

## AccountLedger

Account ledger data (topic `ld`).

Attributes:

- `account_id` _str_ - The account the ledger entry belongs to.
- `data` _dict_ - The ledger payload.

<a id="ibkr_ws.ibkr_events.MarketData"></a>

## MarketData

A market data update for a contract (topic `md`).

IBKR only sends fields that changed, so `data` may contain a subset of the subscribed fields;
absent fields are unchanged.

Attributes:

- `conid` _str_ - The contract identifier the update applies to.
- `data` _dict_ - The changed market data fields. Default: empty dict.

<a id="ibkr_ws.ibkr_events.MarketHistory"></a>

## MarketHistory

Historical OHLC bar data for a contract (topic `mh`).

Attributes:

- `conid` _str_ - The contract identifier the bars apply to.
- `data` _dict_ - The historical bar payload.

<a id="ibkr_ws.ibkr_events.Orders"></a>

## Orders

Live order updates (topic `or`).

Attributes:

- `data` _dict_ - The order update payload.

<a id="ibkr_ws.ibkr_events.PriceLadder"></a>

## PriceLadder

BookTrader price ladder data (topic `bd`).

Attributes:

- `account_id` _str_ - The account the ladder is requested for.
- `conid` _str_ - The contract identifier the ladder applies to.
- `exchange` _str | None_ - The exchange echoed by IBKR, when present.
- `data` _list[dict]_ - The price ladder rows.

<a id="ibkr_ws.ibkr_events.Pnl"></a>

## Pnl

Live profit and loss information (topic `pl`).

Attributes:

- `data` _dict_ - The profit and loss payload.

<a id="ibkr_ws.ibkr_events.Trades"></a>

## Trades

A reported trade execution (topic `tr`).

Attributes:

- `data` _dict_ - The trade payload.

<a id="ibkr_ws.ibkr_events.ServerId"></a>

## ServerId

Derived event capturing the server ID that IBKR assigns to a subscription.

Produced when a `serverId` is first seen for a topic, recording its mapping to a contract so the
subscription can later be unsubscribed by that server ID. Currently used for `MarketHistory`.

Attributes:

- `target_event_type` _type[IbkrTopicEvent]_ - The topic event the server ID belongs to.
- `conid` _str_ - The contract identifier mapped to the server ID.
- `server_id` _str_ - The server ID assigned by IBKR.

<a id="ibkr_ws.ibkr_events.Unsubscription"></a>

## Unsubscription

Derived event confirming that a subscription has been cancelled.

Attributes:

- `target_event_type` _type[IbkrTopicEvent]_ - The topic event that was unsubscribed.
- `conid` _str | None_ - The contract identifier when the subscription was contract-specific,
  otherwise None. Default: None.

<a id="ws._ws_events.WsEvent"></a>

## WsEvent

Base class for all WebSocket events.

Immutable event model that tracks when it was received.

<a id="ws._ws_events.LifecycleEvent"></a>

## LifecycleEvent

Base class for WebSocket connection lifecycle events.

Attributes:

- `previous_state` _WsState_ - The state before the transition.
- `current_state` _WsState_ - The state after the transition.

<a id="ws._ws_events.WsStarting"></a>

## WsStarting

Emitted when the WebSocket connection is starting.

<a id="ws._ws_events.WsStopping"></a>

## WsStopping

Emitted when the WebSocket connection is stopping.

<a id="ws._ws_events.WsStopped"></a>

## WsStopped

Emitted when the WebSocket connection is stopped.

<a id="ws._ws_events.WsOpen"></a>

## WsOpen

Emitted when the WebSocket connection is successfully opened.

<a id="ws._ws_events.WsAuthenticated"></a>

## WsAuthenticated

Emitted when the WebSocket connection is authenticated.

<a id="ws._ws_events.WsDegraded"></a>

## WsDegraded

Emitted when the WebSocket connection enters a degraded state.

<a id="ws._ws_events.WsReady"></a>

## WsReady

Emitted when the WebSocket connection is ready for use.

<a id="ws._ws_events.WsClose"></a>

## WsClose

Emitted when the WebSocket connection is closed.

<a id="ws._ws_events.WsError"></a>

## WsError

Emitted when a WebSocket error occurs.

<a id="ws._ws_events.Router"></a>

## Router

Protocol for routing raw WebSocket messages to typed events.

Implementations parse raw messages and convert them to one or more WsEvent instances.

<a id="ws._ws_events.Router.route"></a>

### route

```python
def route(raw_message) -> OneOrMany[WsEvent]
```

Route a raw message to one or more events.

Arguments:

- `raw_message` - The raw message to route.
  

Returns:

- `OneOrMany[WsEvent]` - One or more events, or None to skip the message.
