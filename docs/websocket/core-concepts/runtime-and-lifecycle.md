# Runtime and Lifecycle

The WebSocket client lifecycle encompasses starting and maintaining the threads and the connection necessary for the uninterrupted functionality and health monitoring. 

The lifecycle is autonomously managed between two dedicated threads - transport and runtime threads.

- Transport thread - manages the `WebSocketApp` object handling the WebSocket connection, monitors inconsistencies between sessions and forwards all messages to the runtime thread as TransportEvents.
- Runtime thread - ensures the transport thread is alive, processes TransportEvents, and performs health checks (see [Degradation](#degradation) section below)

You can read more about the threading model in [Threading Model](./threading-model.md).

Note that there are two distinct event systems in the client - see [Events / Internal Event Systems][internal-event-systems] for more.

## Lifecycle Interface

The main lifecycle interaction from the application code are the `start()` and `shutdown()` methods, indicating the begining and end of the WebSocket connection handling accordingly. Both methods are blocking and will return a boolean indicating success.

The application code should call `start()` method and either observe its return value indicating connection success, or consume the `events.WsAuthenticated` event to respond the completion of the startup phase.  

Note that `shutdown()` does not automatically unsubscribe from topics - unsubscription needs to be handled by the application code prior to shutting down. However, upon termination of the runtime thread, a single additional pass is executed in order to flush final unsubscription payloads and update the subscription bindings accordingly.  

In addition to the main starting and shutting down methods, the `reset_websocket_app()` exposes an ability to close the existing and recreate a new `WebSocketApp`, while the `hard_reset()` will perform a full `shutdown` and `start` cycle. 


## WsState represents client state

The changes in lifecycle are represented by the `WsState` enum:

- `STOPPED` - A default "off" state after instantiation and after stopping.
- `STARTING` - `start()` has been called and the runtime thread is starting 
- `OPEN` - the connection with the IBKR is open. This state is set on either the first connect, a reconnect, or when the session becomes unauthenticated and degrades from `AUTHENTICATED`. 
- `AUTHENTICATED` - the connection is open and the session's authentication is confirmed. This is a de-facto 'ready' state.
- `DEGRADED` - the connection has degraded, usually indicating a WebSocket error or a failed health check 
- `CLOSED` - the connection has been closed, either due to an issue or during the shut down 
- `STOPPING` - the connection has been closed and the threads are going to be stopped. This is followed by the `STOPPED` state.

When state changes to `STOPPED`, `STARTING`, `OPEN`, `AUTHENTICATED`, `DEGRADED` and `CLOSED`, an appropriate WsEvent is emitted.

Current state can be queried using `get_state()` method. Additionally, the current state of the runtime thread can be queried using `is_running()` method.

## Expected Lifecycle Flows

### Nominal Startup

| Sequence | WsState              | Indicates                   | Event Emitted              |
|----------|----------------------|-----------------------------|----------------------------|
| 1        | `STOPPED`            | Initial state               |                            |
| 2        | `STARTING`   | Threads will start          | `events.WsStarting`        |     
| 3        | `OPEN`               | Connection is open          | `events.WsOpen`            |
| 4        | `AUTHENTICATED`      | Connection is authenticated | `events.WsAuthenticated`   |

### Nominal Shutdown

| Sequence | WsState         | Indicates             | Event Emitted            |
|----------|-----------------|-----------------------|--------------------------|
| 1        | `AUTHENTICATED` | Initial state         |                          |
| 2        | `CLOSED`        | Connection was closed | `events.WsClosed`        |    
| 3        | `STOPPING`      | Threads will stop     |                          |
| 4        | `STOPPED`       | Threads have stopped  | `events.WsStopped`       |

### Connection Error and Recovery


| Sequence | WsState         | Indicates                                        | Event Emitted            |
|----------|-----------------|--------------------------------------------------|--------------------------|
| 1        | `AUTHENTICATED` | Initial state                                    |                          |
| 2        | `DEGRADED`      | Connection errored out                           | `events.WsError`         |    
| 3        |                 | Client automatically reconnects<br>until success |                          |
| 4        | `OPEN`          | Reconnection succeeded                           | `events.WsOpen`          |
| 5        | `AUTHENTICATED` | Connection is authenticated                      | `events.WsAuthenticated` |

### Authentication Loss

| Sequence | WsState         | Indicates                                                                  | Event Emitted            |
|----------|-----------------|----------------------------------------------------------------------------|--------------------------|
| 1        | `AUTHENTICATED` | Initial state                                                              |                          |
| 2        | `OPEN`          | Connection is open, but unauthenticated                                    | `events.WsOpen`          |
| 3        |                 | Client automatically checks authentication <br> status until reauthenticated |                          |
| 4        | `AUTHENTICATED` | Authenticated was confirmed                                                | `events.WsAuthenticated` |

## Degradation

The health of the connection may degrade to a number of reasons, such as:

- Connection error
- IBKR server error
- Long break in ping or heartbeat
- Current session loses authentication, for example due to a conflicting login elsewhere.

In many such cases, the client will automatically attempt to restore nominal operation. Should such process fail, it is recommended to perform external checks with the IBKR servers, including simple connectivity checks, and restart the WebSocket client using `hard_reset()`.

Whenever the client loses its `AUTHENTICATED` state outside of the shut down sequence, all subscriptions will be invalidated. This will cause the client to reattempt subscriptions the next time `AUTHENTICATED` state is reestablished.

Note that IBKR provides no official indication of whether the events would be replayed upon reconnection, hence it should be assumed some events might have been missed and should be synchronised using the REST interface.

[internal-event-systems]: ./events.md#internal-event-systems
