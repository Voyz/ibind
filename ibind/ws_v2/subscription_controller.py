import copy
import time
from enum import Enum
from typing import Dict, Optional, Callable, Protocol, Tuple, Hashable, Literal

from pydantic import BaseModel, ConfigDict

from ibind.support.logs import project_logger
from ibind.support.py_utils import TimeoutLock, exception_to_string
from ws_v2.events import WsEvent

_LOGGER = project_logger(__file__)


class Subscription(BaseModel):
    model_config = ConfigDict(frozen=True)
    key: Hashable

    @property
    def topic(self) -> str:
        raise NotImplementedError

    def subscribe_payload(self) -> str:
        raise NotImplementedError

    def unsubscribe_payload(self) -> str:
        raise NotImplementedError

    @property
    def confirms_subscribe(self) -> bool:
        return True

    @property
    def confirms_unsubscribe(self) -> bool:
        return False

    def binding_key(self):
        return self.subscribe_payload()

    def __hash__(self):
        if hasattr(self, '_hash'):
            return self._hash
        _hash = hash(self.binding_key())
        setattr(self, '_hash', _hash)
        return _hash

    def __str__(self):
        return f'{self.__class__.__qualname__}({self.binding_key()})'


class SubscriptionResolver(Protocol):
    def resolve_binding_key(self, event) -> Tuple[bool, str]:
        ...


class BindingStatus(Enum):
    NEW = "NEW"
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    DEGRADED = "DEGRADED"
    UNSUBSCRIBED = "UNSUBSCRIBED"
    RECONNECTING = "RECONNECTING"


class Binding(BaseModel):
    subscription: Subscription
    intent: Literal[BindingStatus.ACTIVE, BindingStatus.UNSUBSCRIBED]
    status: BindingStatus = BindingStatus.NEW
    attempts: int = 0
    last_attempt: float = 0


class SubscriptionController:
    """
    Mixin which manages subscriptions to different channels using the WsClient.

    This class handles the logic for subscribing and unsubscribing to various channels. It maintains a
    record of active subscriptions and provides methods to modify them. The class relies on a
    SubscriptionProcessor to create subscription and unsubscription payloads.

    Constructor Parameters:
        subscription_processor (SubscriptionProcessor): The processor to create subscription payloads.
        subscription_retries (int, optional): The number of retries for subscription requests. Defaults to 5.
        subscription_timeout (float, optional): The timeout in seconds for subscription requests. Defaults to 2.
    """

    def __init__(
        self,
        send_payload: Callable[[str], bool],
        subscription_resolver: SubscriptionResolver,
        subscription_retries: int = 5,
        subscription_timeout: float = 2,
    ):
        self._send_payload = send_payload
        self._subscription_resolver = subscription_resolver
        self._subscription_retries = subscription_retries
        self._subscription_timeout = subscription_timeout

        self._bindings: Dict[str, Binding] = {}
        self._operational_lock = TimeoutLock(60)

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
        is_active, binding_key = self._subscription_resolver.resolve_binding_key(event)

        # None means the event is not related to a tracked subscription
        if binding_key is None:
            return

        with self._operational_lock:
            if not self.has_subscription(binding_key):
                _LOGGER.warning(f'{self}: Observed a binding_key "{binding_key}" that is missing a subscription. Event: {event}')
                return

            if is_active:
                self._confirm_subscribed(binding_key)
            else:
                self._confirm_unsubscribed(binding_key)

    def parse_binding(self, binding: Binding):
        # wait until timeout has passed since last attempt
        if binding.last_attempt + self._subscription_timeout > time.time():
            return
        binding.last_attempt = time.time()

        # if we've exceeded the number of retries, mark the subscription as failed
        if binding.attempts >= self._subscription_retries:
            _LOGGER.info(f'{self}: Subscription failed after {self._subscription_retries} attempts: {binding}')
            binding.status = BindingStatus.FAILED
            binding.attempts = 0
            return

        binding.attempts += 1

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

    def parse_bindings(self):
        with self._operational_lock:
            for binding in self._bindings.values():
                if binding.status == binding.intent:
                    continue

                self.parse_binding(binding)

    def subscribe(self, subscription: Subscription) -> bool:
        with self._operational_lock:
            if self.is_subscription_active(subscription.binding_key()):  # do nothing if subscription is present and active
                return True

            # store a new binding
            if self.has_subscription(subscription.binding_key()):
                return

            self._bindings[subscription.binding_key()] = Binding(subscription=subscription, intent=BindingStatus.ACTIVE)
            _LOGGER.info(f'{self}: Registered subscription intent: {subscription.binding_key()}')

    def unsubscribe(self, subscription: Subscription) -> bool:
        with self._operational_lock:
            if self.has_subscription(subscription.binding_key()):
                binding = self._bindings[subscription.binding_key()]
                if binding.status == BindingStatus.UNSUBSCRIBED:
                    return
                self._bindings[subscription.binding_key()].intent = BindingStatus.UNSUBSCRIBED
            else:
                binding = Binding(subscription=subscription, intent=BindingStatus.UNSUBSCRIBED)
                self._bindings[subscription.binding_key()] = binding
            _LOGGER.info(f'{self}: Registered unsubscription intent: {subscription.binding_key()}')

    def invalidate_subscriptions(self):
        for binding_key, binding in self._bindings.items():
            if binding.status == BindingStatus.ACTIVE:
                binding.status = BindingStatus.DEGRADED
                _LOGGER.info(f'{self}: Invalidated subscription: {binding}')

    def is_subscription_active(self, binding_key: str) -> Optional[bool]:  # pragma: no cover
        if not self.has_subscription(binding_key):
            return False
        return self._bindings[binding_key].status == BindingStatus.ACTIVE

    def has_active_subscriptions(self) -> bool:  # pragma: no cover
        with self._operational_lock:
            for subscription in self._bindings:
                if self.is_subscription_active(subscription):
                    return True
        return False

    def has_subscription(self, binding_key: str) -> bool:  # pragma: no cover
        with self._operational_lock:
            return binding_key in self._bindings

    def get_active_subscriptions(self):
        with self._operational_lock:
            return {
                binding_key: copy.deepcopy(binding)
                for binding_key, binding in self._bindings.items()
                if self.is_subscription_active(binding_key)
            }

    def _confirm_subscribed(self, binding_key: str):
        if not self.has_subscription(binding_key):
            _LOGGER.warning(f'{self}: Unknown subscription {binding_key} - cannot update status to {BindingStatus.ACTIVE.value}')
            return

        binding = self._bindings[binding_key]

        if binding.status == BindingStatus.ACTIVE or binding.intent == BindingStatus.UNSUBSCRIBED:
            return

        binding.status = BindingStatus.ACTIVE
        binding.attempts = 0
        _LOGGER.info(f'{self}: Updated subscription status: {binding_key} -> {BindingStatus.ACTIVE.value}')

    def _confirm_unsubscribed(self, binding_key: str):
        if not self.has_subscription(binding_key):
            _LOGGER.warning(f'{self}: Unknown subscription {binding_key} - cannot update status to {BindingStatus.UNSUBSCRIBED.value}')
            return

        binding = self._bindings[binding_key]

        if binding.status == BindingStatus.UNSUBSCRIBED or binding.intent == BindingStatus.ACTIVE:
            return

        binding.status = BindingStatus.UNSUBSCRIBED
        binding.attempts = 0
        _LOGGER.info(f'{self}: Updated subscription status: {binding_key} -> {BindingStatus.UNSUBSCRIBED.value}')

    def __str__(self):
        return f'{self.__class__.__qualname__}()'