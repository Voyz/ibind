import copy
import time
from enum import Enum
from typing import Dict, Optional, Callable

from pydantic import BaseModel, ConfigDict

from ibind.support.logs import project_logger
from ibind.support.py_utils import TimeoutLock, exception_to_string

_LOGGER = project_logger(__file__)


class Subscription(BaseModel):
    model_config = ConfigDict(frozen=True)

    @property
    def key(self) -> str:
        raise NotImplementedError

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

    def make_hash(self):
        return self.subscribe_payload()

    def __hash__(self):
        if hasattr(self, '_hash'):
            return self._hash
        _hash = hash(self.make_hash())
        setattr(self, '_hash', _hash)
        return _hash

    def __str__(self):
        return f'{self.__class__.__qualname__}({self.make_hash()})'


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
    intent: BindingStatus
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
        subscription_retries: int = 5,
        subscription_timeout: float = 2,
    ):
        self._send_payload = send_payload
        self._subscription_retries = subscription_retries
        self._subscription_timeout = subscription_timeout

        # self._subscriptions: Dict[str, dict] = {}
        self._bindings: Dict[Subscription, Binding] = {}
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

    def parse_binding(self, subscription: Subscription, binding: Binding):
        if binding.status == binding.intent:
            return

        if binding.last_attempt + self._subscription_timeout > time.time():
            return

        binding.last_attempt = time.time()

        if binding.attempts >= self._subscription_retries:
            _LOGGER.info(f'{self}: Subscription failed after {self._subscription_retries} attempts: {subscription}')
            binding.status = BindingStatus.FAILED
            binding.attempts = 0
            return

        if binding.intent == BindingStatus.ACTIVE:
            payload = binding.subscription.subscribe_payload()
            self._send(payload)
            if not subscription.confirms_subscribe:
                _LOGGER.info(f'{self}: Subscribed: {payload} without confirmation.')
                self.set_subscription_active(subscription)
        elif binding.intent == BindingStatus.UNSUBSCRIBED:
            payload = binding.subscription.unsubscribe_payload()
            self._send(payload)
            if not subscription.confirms_unsubscribe:
                _LOGGER.info(f'{self}: Unsubscribed: {payload} without confirmation.')
                self.set_subscription_unsubscribed(subscription)

    def parse_bindings(self):
        for subscription, binding in self._bindings.items():
            self.parse_binding(subscription, binding)

    def subscribe(self, subscription: Subscription) -> bool:
        with self._operational_lock:
            if self.is_subscription_active(subscription):  # do nothing if subscription is present and active
                return True

            # store a new binding
            if not self.has_subscription(subscription):
                self._bindings[subscription] = Binding(subscription=subscription, intent=BindingStatus.ACTIVE)

    def unsubscribe(self, subscription: Subscription) -> bool:
        with self._operational_lock:
            if not self.has_subscription(subscription):
                binding = Binding(subscription=subscription, intent=BindingStatus.UNSUBSCRIBED)
                self._bindings[subscription] = binding
            else:
                self._bindings[subscription].intent = BindingStatus.UNSUBSCRIBED

    # def invalidate_subscriptions(self):
    #     for channel in self._subscriptions:
    #         if self._subscriptions[channel].get('status', False):
    #             self._subscriptions[channel]['status'] = False
    #             _LOGGER.info(f'{self}: Invalidated subscription: {channel}')

    def invalidate_subscriptions(self):
        for subscription, binding in self._bindings.items():
            if binding.status == BindingStatus.ACTIVE:
                binding.status = BindingStatus.DEGRADED
                _LOGGER.info(f'{self}: Invalidated subscription: {subscription}')

    # def is_subscription_active(self, channel: str) -> Optional[bool]:  # pragma: no cover
    #     return self._subscriptions.get(channel, {}).get('status', None)

    def is_subscription_active(self, subscription: Subscription) -> Optional[bool]:  # pragma: no cover
        if not self.has_subscription(subscription):
            return False
        return self._bindings.get(subscription).status == BindingStatus.ACTIVE

    # def has_active_subscriptions(self) -> bool:  # pragma: no cover
    #     for channel in self._subscriptions:
    #         if self.is_subscription_active(channel):
    #             return True
    #     return False

    def has_active_subscriptions(self) -> bool:  # pragma: no cover
        for subscription in self._bindings:
            if self.is_subscription_active(subscription):
                return True
        return False

    # def has_subscription(self, channel: str) -> bool:  # pragma: no cover
    #     return channel in self._subscriptions

    def has_subscription(self, subscription: Subscription) -> bool:  # pragma: no cover
        return subscription in self._bindings

    # def get_active_subscriptions(self):
    #     return {channel: copy.deepcopy(subscription) for channel, subscription in self._subscriptions.items() if self.is_subscription_active(channel)}

    def get_active_subscriptions(self):
        return {
            subscription: copy.deepcopy(binding)
            for subscription, binding in self._bindings.items()
            if self.is_subscription_active(subscription)
        }

    def set_subscription_active(self, subscription: Subscription):
        if not self.has_subscription(subscription):
            _LOGGER.warning(f'{self}: Unknown subscription {subscription} - cannot update status to {BindingStatus.ACTIVE.value}')
            return

        binding = self._bindings[subscription]

        if binding.status == BindingStatus.ACTIVE or binding.intent == BindingStatus.UNSUBSCRIBED:
            return

        binding.status = BindingStatus.ACTIVE
        binding.attempts = 0
        _LOGGER.info(f'{self}: Updated subscription status: {subscription} -> {BindingStatus.ACTIVE.value}')

    def set_subscription_unsubscribed(self, subscription: Subscription):
        if not self.has_subscription(subscription):
            _LOGGER.warning(f'{self}: Unknown subscription {subscription} - cannot update status to {BindingStatus.UNSUBSCRIBED.value}')
            return

        binding = self._bindings[subscription]

        if binding.status == BindingStatus.UNSUBSCRIBED or binding.intent == BindingStatus.ACTIVE:
            return

        binding.status = BindingStatus.UNSUBSCRIBED
        binding.attempts = 0
        _LOGGER.info(f'{self}: Updated subscription status: {subscription} -> {BindingStatus.UNSUBSCRIBED.value}')

    def __str__(self):
        return f'{self.__class__.__qualname__}()'