from abc import ABC
from dataclasses import dataclass
from enum import Enum
from typing import Dict, TYPE_CHECKING, Optional, TypeVar, Generic

from ibind.support.logs import project_logger
from ibind.support.py_utils import wait_until, TimeoutLock, UNDEFINED, exception_to_string

if TYPE_CHECKING:  # pragma: no cover
    from ibind.base.ws_client import WsClient

_LOGGER = project_logger(__file__)

T = TypeVar("T", str, Enum)


class SubscriptionProcessor(ABC):  # pragma: no cover
    """
    An abstract base class for creating subscription and unsubscription payloads.

    This class defines the interface for creating payloads to subscribe and unsubscribe from channels.
    Concrete implementations should provide the specific logic for payload creation based on the channel
    and any additional data.

    Methods:
        make_subscribe_payload(channel: str, data: dict = None): Abstract method to create a subscription payload.
        make_unsubscribe_payload(channel: str, data: dict = None): Abstract method to create an unsubscription payload.
    """

    def make_subscribe_payload(self, channel: str, data: dict = None) -> str:
        raise NotImplementedError()

    def make_unsubscribe_payload(self, channel: str, data: dict = None) -> str:
        raise NotImplementedError()

    def make_subscription_uuid(self, channel: str, data: dict = None) -> str:
        raise NotImplementedError()


@dataclass
class Subscription(Generic[T]):
    channel: T
    data: dict = None
    status: bool = False
    needs_confirmation: bool = True
    subscription_processor: SubscriptionProcessor = None

    def copy(
            self,
            channel: Optional[T] = UNDEFINED,
            data: Optional[dict] = UNDEFINED,
            status: Optional[bool] = UNDEFINED,
            needs_confirmation: Optional[bool] = UNDEFINED,
            subscription_processor: Optional[SubscriptionProcessor] = UNDEFINED
    ):
        return Subscription(
            channel=channel if channel is not UNDEFINED else self.channel,
            data=data if data is not UNDEFINED else self.data,
            status=status if status is not UNDEFINED else self.status,
            needs_confirmation=needs_confirmation if needs_confirmation is not UNDEFINED else self.needs_confirmation,
            subscription_processor=subscription_processor if subscription_processor is not UNDEFINED else self.subscription_processor,
        )

    def _make_uuid(self):
        if self.subscription_processor == None:
            raise RuntimeError(f'SubscriptionProcessor not set for {self}')

        self._uuid = self.subscription_processor.make_subscription_uuid(self.channel, self.data)

    def uuid(self):
        try:
            return getattr(self, '_uuid')
        except AttributeError:
            self._make_uuid()
            return self._uuid

    def __repr__(self):
        return str(self)

    def __str__(self):
        return f'Subscription({self.channel!s}, {self.data}, status={self.status}, needs_confirmation={self.needs_confirmation})'


class SubscriptionController():
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
            subscription_processor: SubscriptionProcessor,
            subscription_retries: int = 5,
            subscription_timeout: float = 2,
    ):

        self._subscription_processor = subscription_processor
        self._subscription_retries = subscription_retries
        self._subscription_timeout = subscription_timeout

        self._subscriptions: Dict[str, Subscription] = {}
        self._operational_lock = TimeoutLock(60)

    def _send_payload(self: 'WsClient', payload) -> bool:
        try:
            success = self.send(payload)
            if not success:
                _LOGGER.info(f'{self}: Sending payload unsuccessful: {payload}')
            return success
        except Exception as e:
            _LOGGER.exception(f'{self}: Exception sending payload: {payload}\n{exception_to_string(e)}')
            return False

    def _attempt_subscribing_once(self, subscription: Subscription, payload: str) -> bool:
        success = self._send_payload(payload)
        if not success:
            _LOGGER.info(f'{self}: Subscription failed: {payload}')
            return False

        _LOGGER.info(f'{self}: Subscribed: {payload} without confirmation.')
        subscription.status = True
        return True

    def _attempt_subscribing_repeated(self: 'WsClient', subscription: Subscription, payload: str) -> bool:
        # attempt to subscribe several times
        for attempt in range(self._subscription_retries):
            # if the client got shut down in the meantime, we just stop trying
            if not self.running:
                return False

            if attempt > 0:
                _LOGGER.info(f'{self}: Subscribing reattempt ({attempt + 1}/{self._subscription_retries}) {payload}')

            if not self._send_payload(payload):
                continue

            # we assume that once the subscription is successful its status will be set to True

            if wait_until(lambda: self.is_subscription_active(subscription.uuid()) == True, timeout=self._subscription_timeout):
                _LOGGER.info(f'{self}: Subscribed: {payload}')
                return True

        # if all failed, notify and return
        _LOGGER.error(f'{self}: Subscribing failed after {self._subscription_retries} attempts: {payload}')
        return False

    def _attempt_subscribing(self, subscription: Subscription) -> bool:

        # format the payload
        payload = subscription.subscription_processor.make_subscribe_payload(subscription.channel, subscription.data)

        if not subscription.needs_confirmation:
            # if we don't need confirmation, we send the request and mark subscription as successful
            return self._attempt_subscribing_once(subscription, payload)
        else:
            # otherwise, repeatedly attempt to subscribe and expect for a confirmation
            return self._attempt_subscribing_repeated(subscription, payload)

    def subscribe_with_subscription(self, subscription: Subscription) -> bool:
        """
        Subscribes to a specified channel.

        Attempts to subscribe to a given channel using the WsClient. The method handles the subscription
        logic, including sending the subscription payload and managing subscription retries and timeouts.
        The subscription status is tracked within the class.

        Parameters:
            channel (str): The name of the channel to subscribe to.
            data (dict, optional): Additional data to be included in the subscription request. Defaults to None.
            needs_confirmation (bool, optional): Specifies whether the subscription requires confirmation.
                                                 Defaults to True.
            subscription_processor (SubscriptionProcessor, optional): The subscription processor to use instead of the
                                                                      default one if provided. Defaults to None.

        Returns:
            bool: True if the subscription was successful, False otherwise.

        Note:
            - If 'needs_confirmation' is False, the method sends the subscription request and assumes success.
            - If 'needs_confirmation' is True, the method waits for confirmation in order to mark the subscription as successful.
        """
        with self._operational_lock:
            subscription = subscription.copy()
            if subscription.subscription_processor is None:
                subscription.subscription_processor = self._subscription_processor

            if self.is_subscription_active(subscription.uuid()):  # do nothing if subscription is present and active
                return True

            # store a new subscription
            self._subscriptions[subscription.uuid()] = subscription

            return self._attempt_subscribing(subscription)

    def _attempt_unsubscribing_once(self, subscription: Subscription, payload: str) -> bool:
        self._send_payload(payload)
        _LOGGER.info(f'{self}: Unsubscribed: {payload} without confirmation.')
        return True

    def _attempt_unsubscribing_repeated(self: 'WsClient', subscription: Subscription, payload: str) -> bool:
        # attempt to unsubscribe several times
        for attempt in range(self._subscription_retries):
            # if the client got shut down in the meantime, we just stop trying
            if not self.running:
                return False

            if attempt > 0:
                _LOGGER.info(f'{self}: Unsubscribing reattempt ({attempt + 1}/{self._subscription_retries}) {payload}')

            if not self._send_payload(payload):
                continue

            # we assume that once the unsubscription is successful its status will be set to False
            if wait_until(lambda: self.is_subscription_active(subscription.uuid()) == False, timeout=self._subscription_timeout):
                _LOGGER.info(f'{self}: Unsubscribed: {payload}')
                return True

        # if all failed, notify and return
        _LOGGER.error(f'{self}: Unsubscribing failed after {self._subscription_retries} attempts: {payload}')
        return False

    def _attempt_unsubscribing(
            self,
            subscription: Subscription
    ) -> bool:

        # format the payload
        payload = subscription.subscription_processor.make_unsubscribe_payload(subscription.channel, subscription.data)

        if not subscription.needs_confirmation:
            # if we don't need confirmation, we send the request and mark unsubscription as successful
            return self._attempt_unsubscribing_once(subscription, payload)
        else:
            # otherwise, repeatedly attempt to unsubscribe and expect for a confirmation
            return self._attempt_unsubscribing_repeated(subscription, payload)

    def unsubscribe_with_subscription(
            self,
            subscription: Subscription
    ) -> bool:
        """
        Unsubscribes from a specified channel.

        Attempts to unsubscribe from a given channel using the WsClient. The method manages the
        unsubscription logic, including sending the unsubscription payload and handling retries and timeouts.
        The subscription status is updated accordingly within the class.

        Parameters:
            channel (str): The name of the channel to unsubscribe from.
            data (dict, optional): Additional data to be included in the unsubscription request. Defaults to None.
            needs_confirmation (bool, optional): Specifies whether the unsubscription requires confirmation.
                                                 Defaults to False.
            subscription_processor (SubscriptionProcessor, optional): The subscription processor to use instead of the
                                                                      default one if provided. Defaults to None.

        Returns:
            bool: True if the unsubscription was successful, False otherwise.

        Note:
            - If 'needs_confirmation' is False, the method sends the unsubscription request and assumes success.
            - If 'needs_confirmation' is True, the method waits for confirmation before marking the unsubscription as successful.
        """
        with self._operational_lock:
            subscription = subscription.copy()
            if subscription.subscription_processor is None:
                subscription.subscription_processor = self._subscription_processor

            # if not self.is_subscription_active(channel):  # do nothing if subscription is not present or not active
            #     return True

            confirmed = self._attempt_unsubscribing(subscription)

            if confirmed:  # remove the subscription
                self._subscriptions.pop(subscription.uuid(), None)

            return confirmed

    def modify_subscription(
            self,
            uuid: str,
            status: bool = UNDEFINED,
            data: dict = UNDEFINED,
            needs_confirmation: bool = UNDEFINED,
            subscription_processor: SubscriptionProcessor = UNDEFINED,
    ):

        """
        Modifies an existing subscription.

        Updates the properties of an existing subscription. If a property is set to UNDEFINED, it remains unchanged.

        Parameters:
            uuid (str): The channel whose subscription is to be modified.
            status (bool, optional): The new status of the subscription. Set as UNDEFINED to leave unchanged.
            data (dict, optional): The new data associated with the subscription. Set as UNDEFINED to leave unchanged.
            needs_confirmation (bool, optional): Specifies whether the subscription requires confirmation.
                                                 Set as UNDEFINED to leave unchanged.
            subscription_processor (SubscriptionProcessor, optional): The subscription processor to use instead of the
                                                                      default one if provided. Defaults to None.

        Raises:
            KeyError: If the specified channel does not have an existing subscription.
        """
        try:
            if status is not UNDEFINED:
                self._subscriptions[uuid].status = status

            if data is not UNDEFINED:
                self._subscriptions[uuid].data = data

            if needs_confirmation is not UNDEFINED:
                self._subscriptions[uuid].needs_confirmation = needs_confirmation

            if subscription_processor is not UNDEFINED:
                self._subscriptions[uuid].subscription_processor = subscription_processor

        except KeyError as e:
            raise KeyError(f'Subscription {uuid} does not exist. Current subscriptions: {list(self._subscriptions.keys())}') from e

    def recreate_subscriptions(self):
        """
        Re-subscribes to all currently stored subscriptions.

        Iterates over all currently stored subscriptions and attempts to re-subscribe to each. Useful in scenarios
        where a connection reset or similar event necessitates re-establishing subscriptions.
        """
        with self._operational_lock:
            active_subscriptions = {}
            inactive_subscriptions = {}
            for uuid, subscription in self._subscriptions.items():
                if subscription.status == False:
                    inactive_subscriptions[uuid] = subscription
                else:
                    active_subscriptions[uuid] = subscription

            if len(inactive_subscriptions) == 0:
                return

            _LOGGER.info(f'{self}: Recreating {len(inactive_subscriptions)}/{len(self._subscriptions)} subscriptions: {inactive_subscriptions}')
            self._subscriptions = active_subscriptions

            not_resubscribed = {}

            for uuid, subscription in inactive_subscriptions.items():

                success = self.subscribe_with_subscription(subscription)
                if not success:
                    not_resubscribed[uuid] = subscription.copy(status=False)

            if not_resubscribed != {}:
                _LOGGER.error(f'{self}: Failed to re-subscribe {len(not_resubscribed)} channels: {not_resubscribed}')

            # carry over unsuccessful subscriptions
            self._subscriptions = {**self._subscriptions, **not_resubscribed}

    def invalidate_subscriptions(self):
        for subscription in self._subscriptions.values():

            if subscription.status:
                subscription.status = False
                _LOGGER.info(f'{self}: Invalidated subscription: {subscription.uuid()}')

    def get_subscription(self, uuid: str) -> Optional[Subscription]:
        try:
            return self._subscriptions[uuid]
        except KeyError:
            return None

    def is_subscription_active(self, uuid: str) -> Optional[bool]:  # pragma: no cover
        subscription = self.get_subscription(uuid)
        if subscription is None:
            return None

        return subscription.status

    def has_active_subscriptions(self) -> bool:  # pragma: no cover
        for subscription in self._subscriptions.values():
            if self.is_subscription_active(subscription.uuid()):
                return True
        return False

    def has_subscription(self, uuid: str) -> bool:  # pragma: no cover
        return uuid in self._subscriptions
