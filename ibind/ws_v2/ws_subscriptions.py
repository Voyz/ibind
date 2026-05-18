import copy
import time
from enum import Enum
from threading import Condition, RLock
from typing import Dict, Optional, Callable, Protocol, Tuple, Literal

from pydantic import BaseModel, ConfigDict

from ibind import events
from ibind.support.logs import project_logger
from ibind.support.py_utils import exception_to_string
from ibind.events import WsEvent

_LOGGER = project_logger('ibkr_ws_client')


class Subscription(BaseModel):  # pragma: no cover
    """
    Base class for WebSocket subscriptions.

    Immutable model defining subscription behaviour including payload generation,
    confirmation requirements, and expiry settings. Subclasses implement specific
    subscription types by overriding abstract methods.

    Attributes:
        expiry_seconds (int | None): Time in seconds before subscription expires and
            requires renewal. None means no expiry. Default: None.
    """

    model_config = ConfigDict(frozen=True)
    expiry_seconds: int | None = None

    @property
    def topic(self) -> str:
        """Get the subscription topic identifier."""
        raise NotImplementedError

    def subscribe_payload(self) -> str:
        """Generate the payload string to send for subscribing."""
        raise NotImplementedError

    def unsubscribe_payload(self) -> str:
        """Generate the payload string to send for unsubscribing."""
        raise NotImplementedError

    @property
    def confirms_subscribe(self) -> bool:
        """Whether the server sends confirmation when subscription succeeds."""
        return True

    @property
    def confirms_unsubscribe(self) -> bool:
        """Whether the server sends confirmation when unsubscription succeeds."""
        return False

    def binding_key(self):
        """Get the unique key identifying this subscription binding."""
        return self.subscribe_payload()

    def __str__(self):
        return f'{self.__class__.__qualname__}({self.binding_key()})'


class SubscriptionResolver(Protocol):  # pragma: no cover
    """
    Protocol for resolving subscription binding keys from events.

    Implementations determine which subscription an event belongs to and whether
    the event indicates an active or inactive subscription state.
    """

    def resolve_binding_key(self, event: WsEvent) -> Tuple[bool, str]:
        """
        Resolve the binding key and active state from an event.

        Args:
            event (WsEvent): Event to resolve.

        Returns:
            tuple[bool, str]: (is_active, binding_key) where is_active indicates
                subscription is active, and binding_key identifies the subscription.
                Returns (None, None) if event is not subscription-related.
        """
        ...


class BindingStatus(Enum):  # pragma: no cover
    """
    Status of a subscription binding.

    Tracks the lifecycle state of a subscription from initial registration through
    activation, failure, or unsubscription.
    """

    NEW = 'NEW'
    PENDING = 'PENDING'
    ACTIVE = 'ACTIVE'  # subscription successful
    FAILED = 'FAILED'
    DEGRADED = 'DEGRADED'
    UNSUBSCRIBED = 'UNSUBSCRIBED'  # unsubscription successful
    EXPIRED = 'EXPIRED'


class SubscriptionUpdated(WsEvent):
    """Emitted when subscription status changes."""

    subscription: Subscription
    binding_key: str
    status: BindingStatus


class Binding(BaseModel):
    """
    Internal state tracking for a subscription binding.

    Maintains the desired intent (subscribe or unsubscribe), current status,
    and retry state for subscription operations.

    Attributes:
        subscription (Subscription): The subscription being tracked.
        intent (Literal[BindingStatus.ACTIVE, BindingStatus.UNSUBSCRIBED]): Desired state.
        status (BindingStatus): Current state. Default: BindingStatus.NEW.
        attempts (int): Number of attempts made. Default: 0.
        last_attempt (float): Timestamp of last attempt. Default: 0.
    """

    subscription: Subscription
    intent: Literal[BindingStatus.ACTIVE, BindingStatus.UNSUBSCRIBED]
    status: BindingStatus = BindingStatus.NEW
    attempts: int = 0
    last_attempt: float = 0

    @property
    def done(self) -> bool:
        """Whether the binding has reached its intended state."""
        return self.status == self.intent

    def reset(self):  # pragma: no cover
        """Reset retry state to allow new attempts."""
        self.attempts = 0
        self.last_attempt = 0


class SubscriptionHandle:
    """
    Handle for interacting with a subscription.

    Provides methods to query subscription state, wait for completion, and unsubscribe.
    Returned by subscribe/unsubscribe operations.
    """

    def __init__(self, controller: 'SubscriptionController', subscription: Subscription):
        self._controller = controller
        self._subscription = subscription

    @property
    def binding_key(self) -> str:
        """Get the unique key identifying this subscription."""
        return self._subscription.binding_key()

    @property
    def status(self) -> BindingStatus:
        """Get the current status of this subscription."""
        return self._controller.get_status(self.binding_key)

    @property
    def active(self) -> bool:
        """Whether the subscription is currently active."""
        return self.status == BindingStatus.ACTIVE

    @property
    def unsubscribed(self) -> bool:
        """Whether the subscription has been unsubscribed."""
        return self.status == BindingStatus.UNSUBSCRIBED

    @property
    def done(self) -> bool:
        """Whether the subscription has reached its intended state."""
        return self._controller.is_done(self.binding_key)

    def wait(self, timeout: float | None = None) -> bool:
        """
        Wait for the subscription to reach its intended state.

        Args:
            timeout (float | None): Maximum time to wait in seconds, or indefinitely if None. Default: None.

        Returns:
            bool: True if subscription reached intended state, False if timed out or failed.
        """
        return self._controller.wait_for(self.binding_key, timeout=timeout)

    def unsubscribe(self) -> 'SubscriptionHandle':
        """
        Unsubscribe from this subscription.

        Returns:
            SubscriptionHandle: This handle for chaining.
        """
        self._controller.unsubscribe(self._subscription)
        return self


class SubscriptionController:
    """
    Manages WebSocket subscriptions with automatic retries and state tracking.

    Handles subscription lifecycle including registration, activation, expiry, and unsubscription.
    Maintains binding state and coordinates with a resolver to match events to subscriptions.
    Thread-safe through internal condition variable.
    """

    def __init__(
        self,
        send_payload: Callable[[str], bool],
        emit_event: Callable[[WsEvent], None],
        subscription_resolver: SubscriptionResolver,
        subscription_retries: int = 5,
        subscription_timeout: float = 2,
    ):
        """
        Create a subscription controller.

        Args:
            send_payload (Callable[[str], bool]): Function to send payloads through the WebSocket.
                Returns True if sent successfully.
            emit_event (Callable[[WsEvent], None]): Function to emit events.
            subscription_resolver (SubscriptionResolver): Resolver to match events to subscriptions.
            subscription_retries (int, optional): Maximum retry attempts per subscription. Default: 5.
            subscription_timeout (float, optional): Seconds to wait between retry attempts. Default: 2.
        """
        self._send_payload = send_payload
        self._emit_event = emit_event
        self._subscription_resolver = subscription_resolver
        self._subscription_retries = subscription_retries
        self._subscription_timeout = subscription_timeout

        self._bindings: Dict[str, Binding] = {}
        self._condition = Condition(RLock())

    def _send(self, payload) -> bool:
        try:
            success = self._send_payload(payload)
            if not success:
                _LOGGER.info(f'{self}: Sending payload unsuccessful: {payload}')
            return success
        except Exception as e:
            _LOGGER.exception(f'{self}: Exception sending payload: {payload}\n{exception_to_string(e)}')
            return False

    def observe(self, event: WsEvent):
        """
        Process an event to update subscription state.

        Uses the resolver to determine if the event confirms subscription or unsubscription,
        then updates the corresponding binding status.

        Args:
            event (WsEvent): Event to process.
        """
        is_active, binding_key = self._subscription_resolver.resolve_binding_key(event)

        # None means the event is not related to a tracked subscription
        if binding_key is None:
            return

        with self._condition:
            if not self.has_subscription(binding_key):
                _LOGGER.warning(f'{self}: Observed a binding_key "{binding_key}" that is missing a subscription. Event: {event}')
                return

            if is_active:
                self._confirm_subscribed(binding_key)
            else:
                self._confirm_unsubscribed(binding_key)

    def _make_attempt(self, binding: Binding):
        subscription = binding.subscription
        if binding.intent == BindingStatus.ACTIVE:
            payload = subscription.subscribe_payload()
            self._send(payload)
            if not subscription.confirms_subscribe:
                _LOGGER.info(f'{self}: Subscribed: {payload} without confirmation.')
                self._confirm_subscribed(subscription.binding_key())

        elif binding.intent == BindingStatus.UNSUBSCRIBED:
            payload = subscription.unsubscribe_payload()
            self._send(payload)
            if not subscription.confirms_unsubscribe:
                _LOGGER.info(f'{self}: Unsubscribed: {payload} without confirmation.')
                self._confirm_unsubscribed(subscription.binding_key())

    def reconcile_binding(self, binding: Binding):
        """
        Reconcile a single binding by checking expiry and retrying if needed.

        Handles expiry checks, retry logic, and failure detection. Called periodically
        by the runtime to maintain subscription state.

        Args:
            binding (Binding): Binding to reconcile.
        """
        now = time.time()
        subscription = binding.subscription

        # if either done or failed, return early or check expiration if expiry_seconds is provided
        if binding.status in [binding.intent, BindingStatus.FAILED]:
            if subscription.expiry_seconds is None:
                return

            time_since_last_attempt = now - binding.last_attempt
            if time_since_last_attempt < subscription.expiry_seconds:
                return

            _LOGGER.info(f'{self}: Subscription expired: {subscription} after {time_since_last_attempt:.1f} seconds')
            self._update_status(binding, BindingStatus.EXPIRED)

        # if we've exceeded the number of retries, mark the subscription as failed
        if binding.attempts >= self._subscription_retries:
            _LOGGER.info(f'{self}: Subscription failed after {self._subscription_retries} attempts: {binding}')
            self._update_status(binding, BindingStatus.FAILED)
            return

        # wait until timeout has passed since last attempt
        if binding.last_attempt + self._subscription_timeout > now:
            return

        binding.last_attempt = now
        binding.attempts += 1
        self._make_attempt(binding)

    def reconcile_bindings(self):
        """Reconcile all bindings by checking expiry and retrying as needed."""
        with self._condition:
            for binding in self._bindings.values():
                self.reconcile_binding(binding)

    def subscribe(self, subscription: Subscription) -> SubscriptionHandle:
        """
        Register intent to subscribe.

        Creates or updates a binding with ACTIVE intent. The actual subscription
        attempt occurs during reconciliation.

        Args:
            subscription (Subscription): Subscription to activate.

        Returns:
            SubscriptionHandle: Handle for tracking and controlling this subscription.
        """
        binding_key = subscription.binding_key()

        with self._condition:
            binding = self._bindings.get(binding_key)

            if binding is None:
                self._bindings[binding_key] = Binding(subscription=subscription, intent=BindingStatus.ACTIVE)
                self._condition.notify_all()
                _LOGGER.info(f'{self}: Registered subscription intent: {binding_key}')

            elif binding.intent != BindingStatus.ACTIVE:
                binding.intent = BindingStatus.ACTIVE

                # If it had previously completed unsubscribe, it now needs work again.
                if binding.status == BindingStatus.UNSUBSCRIBED:
                    binding.reset()

                self._condition.notify_all()
                _LOGGER.info(f'{self}: Updated subscription intent: {binding_key} -> {BindingStatus.ACTIVE.value}')

            return SubscriptionHandle(self, subscription)

    def unsubscribe(self, subscription: Subscription) -> SubscriptionHandle:
        """
        Register intent to unsubscribe.

        Creates or updates a binding with UNSUBSCRIBED intent. The actual unsubscription
        attempt occurs during reconciliation.

        Args:
            subscription (Subscription): Subscription to deactivate.

        Returns:
            SubscriptionHandle: Handle for tracking this unsubscription.
        """
        binding_key = subscription.binding_key()

        with self._condition:
            binding = self._bindings.get(binding_key)

            if binding is None:
                self._bindings[binding_key] = Binding(subscription=subscription, intent=BindingStatus.UNSUBSCRIBED)
                self._condition.notify_all()
                _LOGGER.info(f'{self}: Registered unsubscription intent: {binding_key}')

            elif binding.intent != BindingStatus.UNSUBSCRIBED:
                binding.intent = BindingStatus.UNSUBSCRIBED

                # If it had previously completed subscribe, it now needs work again.
                if binding.status == BindingStatus.ACTIVE:
                    binding.reset()

                self._condition.notify_all()
                _LOGGER.info(f'{self}: Updated subscription intent: {binding_key} -> {BindingStatus.UNSUBSCRIBED.value}')

            return SubscriptionHandle(self, subscription)

    def invalidate_subscriptions(self):
        """Mark all subscriptions as degraded, typically after connection loss."""
        with self._condition:
            for binding_key, binding in self._bindings.items():
                if binding.status != BindingStatus.DEGRADED:
                    self._update_status(binding, BindingStatus.DEGRADED)

    def is_subscription_active(self, binding_key: str) -> Optional[bool]:  # pragma: no cover
        """Check if a subscription is currently active.

        Args:
            binding_key (str): Binding key to check.

        Returns:
            bool: True if subscription exists and is active, False otherwise.
        """
        with self._condition:
            if not self.has_subscription(binding_key):
                return False
            return self._bindings[binding_key].status == BindingStatus.ACTIVE

    def has_active_subscriptions(self) -> bool:
        """
        Check if any subscriptions are currently active.

        Returns:
            bool: True if any subscriptions are active, False otherwise.
        """
        with self._condition:
            for subscription in self._bindings:
                if self.is_subscription_active(subscription):
                    return True
        return False

    def has_subscription(self, binding_key: str) -> bool:  # pragma: no cover
        """Check if a subscription exists.

        Args:
            binding_key (str): Binding key to check.

        Returns:
            bool: True if subscription exists, False otherwise.
        """
        return binding_key in self._bindings

    def get_status(self, binding_key: str) -> BindingStatus | None:  # pragma: no cover
        """Get the status of a subscription.

        Args:
            binding_key (str): Binding key to query.

        Returns:
            BindingStatus | None: Current status, or None if subscription doesn't exist.
        """
        with self._condition:
            if not self.has_subscription(binding_key):
                return None
            return self._bindings[binding_key].status

    def is_done(self, binding_key: str) -> bool | None:  # pragma: no cover
        """Check if a subscription has reached its intended state.

        Args:
            binding_key (str): Binding key to check.

        Returns:
            bool | None: True if done, False if not done, None if subscription doesn't exist.
        """
        with self._condition:
            if not self.has_subscription(binding_key):
                return None
            return self._bindings[binding_key].done

    def get_active_subscriptions(self):
        """
        Get all active subscriptions.

        Returns:
            dict[str, Binding]: Deep copies of active bindings keyed by binding_key.
        """
        with self._condition:
            return {
                binding_key: copy.deepcopy(binding) for binding_key, binding in self._bindings.items() if self.is_subscription_active(binding_key)
            }

    def _update_status(self, binding: Binding, status: BindingStatus):
        binding_key = binding.subscription.binding_key()
        _LOGGER.info(f'{self}: Updated subscription status: {binding_key} {binding.status.value} -> {status.value}')
        binding.status = status
        binding.attempts = 0
        self._condition.notify_all()
        self._emit_event(events.SubscriptionUpdated(subscription=binding.subscription, binding_key=binding_key, status=status))

    def _confirm_subscribed(self, binding_key: str):
        if not self.has_subscription(binding_key):
            _LOGGER.warning(f'{self}: Unknown subscription {binding_key} - cannot update status to {BindingStatus.ACTIVE.value}')
            return

        binding = self._bindings[binding_key]

        if binding.status == BindingStatus.ACTIVE or binding.intent == BindingStatus.UNSUBSCRIBED:
            return

        self._update_status(binding, BindingStatus.ACTIVE)

    def _confirm_unsubscribed(self, binding_key: str):
        if not self.has_subscription(binding_key):
            _LOGGER.warning(f'{self}: Unknown subscription {binding_key} - cannot update status to {BindingStatus.UNSUBSCRIBED.value}')
            return

        binding = self._bindings[binding_key]

        if binding.status == BindingStatus.UNSUBSCRIBED or binding.intent == BindingStatus.ACTIVE:
            return

        self._update_status(binding, BindingStatus.UNSUBSCRIBED)

    def wait_for(self, binding_key: str, timeout: float | None = None) -> bool:
        """
        Wait for a subscription to reach its intended state.

        Blocks until the binding reaches its intent or fails. Uses a condition variable
        for efficient waiting.

        Args:
            binding_key (str): Binding key to wait for.
            timeout (float | None): Maximum time to wait in seconds. None means wait indefinitely. Default: None.

        Returns:
            bool: True if binding reached intended state, False if timed out, failed, or binding not found.
        """
        deadline = None if timeout is None else time.monotonic() + timeout

        with self._condition:
            while True:
                if not self.has_subscription(binding_key):
                    return False

                binding = self._bindings[binding_key]

                if binding.done:
                    return True

                if binding.status == BindingStatus.FAILED:
                    return False

                # wait for the remaining time
                remaining = None
                if timeout is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return False

                self._condition.wait(remaining)

    def __str__(self):  # pragma: no cover
        return f'{self.__class__.__qualname__}()'
