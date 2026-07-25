# Shut down cleanly

Call `client.shutdown()` to stop the client. It blocks until all internal threads have stopped.

```python
ws_client.start()

# ... your application logic ...

ws_client.shutdown()
```

## Unsubscribe before shutting down

If you want to notify the server of your unsubscriptions before disconnecting, call `unsubscribe()` first. The shutdown sequence waits for one more runtime cycle before stopping, so any unsubscription payloads queued immediately before `shutdown()` will be sent:

```python
from ibind.subscriptions import MarketDataSubscription

sub = MarketDataSubscription(conid='265598', fields=['31'])
handle = ws_client.subscribe(sub)

# ...

unsub_handle = ws_client.unsubscribe(sub)
unsub_handle.wait(timeout=5)
ws_client.shutdown()
```

`unsub_handle.wait()` is optional - `shutdown()` will allow one cycle for unsubscriptions regardless. Waiting gives you the confirmation that the server acknowledged it.

## Handling KeyboardInterrupt

The most common pattern is a main loop that breaks on interrupt, then shuts down cleanly:

```python
from ibind.subscriptions import PnlSubscription

sub = PnlSubscription()
handle = ws_client.subscribe(sub)

try:
    while ws_client.is_running():
        # consume events
        time.sleep(0.1)
except KeyboardInterrupt:
    pass
finally:
    ws_client.unsubscribe(sub)
    ws_client.shutdown()
```

The `finally` block runs whether the loop exits normally, on interrupt, or due to an exception.

## Signal-based shutdown

For long-running processes, register a shutdown handler for `SIGINT` and `SIGTERM`. A robust version preserves any previously registered handlers, guards against being called twice, and also registers with `atexit` so shutdown runs on normal program exit:

```python
import atexit
import signal

def register_shutdown_handler(callback):
    existing_int = signal.getsignal(signal.SIGINT)
    existing_term = signal.getsignal(signal.SIGTERM)
    stopped = [False]

    def _stop():
        if stopped[0]:
            return
        stopped[0] = True
        callback()

    def _on_signal(signum, frame):
        _stop()
        if signum == signal.SIGINT and callable(existing_int):
            existing_int(signum, frame)
        if signum == signal.SIGTERM and callable(existing_term):
            existing_term(signum, frame)

    try:
        signal.signal(signal.SIGINT, _on_signal)
        signal.signal(signal.SIGTERM, _on_signal)
    except ValueError:
        pass  # not on main thread, signal registration skipped

    atexit.register(_stop)


def shutdown():
    ws_client.unsubscribe(sub)
    ws_client.shutdown()

register_shutdown_handler(shutdown)
```

The `stopped` flag prevents `shutdown()` from being called twice if both a signal and `atexit` fire. The `try/except ValueError` handles the case where signal registration is attempted from a non-main thread.

## What not to do

`shutdown()` must not be called from within a callback or from the runtime thread. Doing so raises a `RuntimeError` or deadlocks. If you need to shut down in response to an event, defer it:

```python
import threading

def on_degraded(event: events.WsDegraded):
    threading.Thread(target=ws_client.shutdown, daemon=True).start()

sink.on(events.WsDegraded, on_degraded)
```

See [Threading Model][threading-model] for more on which thread callbacks run on.

[threading-model]: ../core-concepts/threading-model.md
[subscriptions]: ../core-concepts/subscriptions.md
