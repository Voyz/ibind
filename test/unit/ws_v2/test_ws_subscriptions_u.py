from unittest.mock import MagicMock, patch

import pytest

from ibind.events import WsOpen, WsEvent
from ibind.ws_v2.ws_subscriptions import (
    Subscription,
    BindingStatus,
    Binding,
    SubscriptionHandle,
    SubscriptionController,
    SubscriptionUpdated,
)
from test.test_utils import capture_logs, mock_module_time


class MockEvent(WsEvent):
    """Mock event for testing subscription confirmation."""

    binding_key: str
    is_active: bool


class MockResolver:
    """Mock resolver that extracts binding_key and is_active from MockEvent."""

    def resolve_binding_key(self, event: WsEvent):
        if isinstance(event, MockEvent):
            return (event.is_active, event.binding_key)
        return (False, None)


class MockSubscription(Subscription):
    topic_value: str = 'test_topic'
    payload_value: str = 'sub_payload'

    @property
    def topic(self) -> str:
        return self.topic_value

    def subscribe_payload(self) -> str:
        return self.payload_value

    def unsubscribe_payload(self) -> str:
        return f'unsub_{self.payload_value}'


class MockSubscriptionNoConfirm(Subscription):
    topic_value: str = 'no_confirm'
    payload_value: str = 'no_confirm_payload'

    @property
    def topic(self) -> str:
        return self.topic_value

    def subscribe_payload(self) -> str:
        return self.payload_value

    def unsubscribe_payload(self) -> str:
        return f'unsub_{self.payload_value}'

    @property
    def confirms_subscribe(self) -> bool:
        return False

    @property
    def confirms_unsubscribe(self) -> bool:
        return True


@pytest.fixture
def mock_sub():
    return MockSubscription()


@pytest.fixture()
def binding_key(mock_sub):
    return mock_sub.binding_key()


@pytest.fixture
def test_subscription_with_expiry():
    return MockSubscription(expiry_seconds=10)


@pytest.fixture
def test_subscription_no_confirm():
    return MockSubscriptionNoConfirm()


@pytest.fixture
def mock_send_payload():
    return MagicMock(return_value=True)


@pytest.fixture
def mock_emit_event():
    return MagicMock()


@pytest.fixture
def emitter(mock_emit_event):
    return MagicMock(emit=mock_emit_event)


@pytest.fixture
def sc(mock_send_payload, emitter):
    return SubscriptionController(
        send_payload=mock_send_payload,
        emitter=emitter,
        subscription_resolver=MockResolver(),
        subscription_retries=3,
        subscription_timeout=1.0,
    )


class TestBinding:
    @capture_logs()
    def test_binding_done_when_status_matches_intent(self, mock_sub):
        """Binding.done returns True when status matches intent."""
        ## Arrange
        binding = Binding(subscription=mock_sub, intent=BindingStatus.ACTIVE)
        binding.status = BindingStatus.ACTIVE

        ## Act
        result = binding.done

        ## Assert
        assert result is True


class TestSubscriptionHandle:
    @capture_logs()
    def test_status(self, sc, mock_sub):
        """SubscriptionHandle.status returns the current binding status."""
        ## Arrange
        sc.subscribe(mock_sub)
        handle = SubscriptionHandle(sc, mock_sub)

        ## Assert
        assert handle.status == BindingStatus.NEW

    @capture_logs()
    def test_active_when_status_active(self, sc, mock_sub, binding_key):
        """SubscriptionHandle.active returns True when status is ACTIVE."""
        ## Arrange
        sc.subscribe(mock_sub)
        with sc._condition:
            sc._confirm_subscribed(binding_key)
        handle = SubscriptionHandle(sc, mock_sub)

        ## Assert
        assert handle.active is True

    @capture_logs()
    def test_active_when_status_not_active(self, sc, mock_sub):
        """SubscriptionHandle.active returns False when status is not ACTIVE."""
        ## Arrange
        sc.subscribe(mock_sub)
        handle = SubscriptionHandle(sc, mock_sub)

        ## Assert
        assert handle.active is False

    @capture_logs()
    def test_unsubscribed_when_status_unsubscribed(self, sc, mock_sub, binding_key):
        """SubscriptionHandle.unsubscribed returns True when status is UNSUBSCRIBED."""
        ## Arrange
        sc.unsubscribe(mock_sub)
        with sc._condition:
            sc._confirm_unsubscribed(binding_key)
        handle = SubscriptionHandle(sc, mock_sub)

        ## Assert
        assert handle.unsubscribed is True

    @capture_logs()
    def test_done_delegates_to_controller(self, sc, mock_sub, binding_key):
        """SubscriptionHandle.done delegates to controller.is_done."""
        ## Arrange
        sc.subscribe(mock_sub)
        with sc._condition:
            sc._confirm_subscribed(binding_key)
        handle = SubscriptionHandle(sc, mock_sub)

        ## Assert
        assert handle.done is True

    @capture_logs()
    def test_wait_delegates_to_controller(self, sc, mock_sub, binding_key):
        """SubscriptionHandle.wait delegates to controller.wait_for."""
        ## Arrange
        sc.subscribe(mock_sub)
        with sc._condition:
            sc._confirm_subscribed(binding_key)
        handle = SubscriptionHandle(sc, mock_sub)

        ## Act
        result = handle.wait(timeout=1.0)

        ## Assert
        assert result is True

    @capture_logs()
    def test_unsubscribe_delegates_to_controller(self, sc, mock_sub, binding_key):
        """SubscriptionHandle.unsubscribe delegates to controller.unsubscribe."""
        ## Arrange
        sc.subscribe(mock_sub)
        handle = SubscriptionHandle(sc, mock_sub)

        ## Act
        result = handle.unsubscribe()

        ## Assert
        assert result is handle
        assert sc.get_status(binding_key) == BindingStatus.NEW


class TestInterface:
    @capture_logs()
    def test_subscribe_creates_new_binding(self, sc, mock_sub, binding_key):
        """SubscriptionController.subscribe creates a new binding with ACTIVE intent."""
        ## Act
        handle = sc.subscribe(mock_sub)

        ## Assert
        assert isinstance(handle, SubscriptionHandle)
        assert sc.has_subscription(binding_key)
        binding = sc._bindings[binding_key]
        assert binding.intent == BindingStatus.ACTIVE
        assert binding.status == BindingStatus.NEW

    @capture_logs()
    def test_subscribe_updates_existing_binding_intent(self, sc, mock_sub, binding_key):
        """SubscriptionController.subscribe updates intent on existing binding."""
        ## Arrange
        sc.unsubscribe(mock_sub)
        binding = sc._bindings[binding_key]
        assert binding.intent == BindingStatus.UNSUBSCRIBED

        ## Act
        sc.subscribe(mock_sub)

        ## Assert
        assert binding.intent == BindingStatus.ACTIVE

    @capture_logs()
    def test_subscribe_resets_unsubscribed_binding(self, sc, mock_sub, binding_key):
        """SubscriptionController.subscribe resets binding when previously UNSUBSCRIBED."""
        ## Arrange
        sc.unsubscribe(mock_sub)
        with sc._condition:
            sc._confirm_unsubscribed(binding_key)
        binding = sc._bindings[binding_key]
        binding.attempts = 5
        binding.last_attempt = 100.0

        ## Act
        sc.subscribe(mock_sub)

        ## Assert
        binding = sc._bindings[binding_key]
        assert binding.attempts == 0
        assert binding.last_attempt == 0

    @capture_logs()
    def test_subscribe_resets_failed_binding(self, sc, mock_sub, binding_key):
        """SubscriptionController.subscribe resets and sets NEW status when binding is FAILED."""
        ## Arrange
        sc.subscribe(mock_sub)
        binding = sc._bindings[binding_key]
        binding.status = BindingStatus.FAILED
        binding.attempts = 5
        binding.last_attempt = 100.0

        ## Act
        sc.subscribe(mock_sub)

        ## Assert
        binding = sc._bindings[binding_key]
        assert binding.status == BindingStatus.NEW
        assert binding.attempts == 0
        assert binding.last_attempt == 0

    @capture_logs()
    def test_unsubscribe_creates_new_binding(self, sc, mock_sub, binding_key):
        """SubscriptionController.unsubscribe creates a new binding with UNSUBSCRIBED intent."""
        ## Act
        handle = sc.unsubscribe(mock_sub)

        ## Assert
        assert isinstance(handle, SubscriptionHandle)
        assert sc.has_subscription(binding_key)
        binding = sc._bindings[binding_key]
        assert binding.intent == BindingStatus.UNSUBSCRIBED
        assert binding.status == BindingStatus.NEW

    @capture_logs()
    def test_unsubscribe_updates_existing_binding_intent(self, sc, mock_sub, binding_key):
        """SubscriptionController.unsubscribe updates intent on existing binding."""
        ## Arrange
        sc.subscribe(mock_sub)

        ## Act
        sc.unsubscribe(mock_sub)

        ## Assert
        binding = sc._bindings[binding_key]
        assert binding.intent == BindingStatus.UNSUBSCRIBED

    @capture_logs()
    def test_unsubscribe_resets_active_binding(self, sc, mock_sub, binding_key):
        """SubscriptionController.unsubscribe resets binding when previously ACTIVE."""
        ## Arrange
        sc.subscribe(mock_sub)
        with sc._condition:
            sc._confirm_subscribed(binding_key)
        binding = sc._bindings[binding_key]
        binding.attempts = 5
        binding.last_attempt = 100.0

        ## Act
        sc.unsubscribe(mock_sub)

        ## Assert
        binding = sc._bindings[binding_key]
        assert binding.attempts == 0
        assert binding.last_attempt == 0

    @capture_logs()
    def test_unsubscribe_resets_failed_binding(self, sc, mock_sub, binding_key):
        """SubscriptionController.unsubscribe resets and sets NEW status when binding is FAILED."""
        ## Arrange
        sc.unsubscribe(mock_sub)
        binding = sc._bindings[binding_key]
        binding.status = BindingStatus.FAILED
        binding.attempts = 5
        binding.last_attempt = 100.0

        ## Act
        sc.unsubscribe(mock_sub)

        ## Assert
        binding = sc._bindings[binding_key]
        assert binding.status == BindingStatus.NEW
        assert binding.attempts == 0
        assert binding.last_attempt == 0

    @capture_logs()
    def test_has_active_subscriptions(self, sc, mock_sub, binding_key):
        """SubscriptionController.has_active_subscriptions returns True when any subscription is active."""
        ## Arrange
        sc.subscribe(mock_sub)
        with sc._condition:
            sc._confirm_subscribed(binding_key)

        ## Act
        result = sc.has_active_subscriptions()

        ## Assert
        assert result is True

    @capture_logs()
    def test_has_active_subscriptions_returns_false_when_none_active(self, sc, mock_sub):
        """SubscriptionController.has_active_subscriptions returns False when no subscriptions are active."""
        ## Arrange
        sc.subscribe(mock_sub)

        ## Act
        result = sc.has_active_subscriptions()

        ## Assert
        assert result is False

    @capture_logs()
    def test_get_active_subscriptions(self, sc, mock_sub, binding_key):
        """SubscriptionController.get_active_subscriptions returns dict of active bindings."""
        ## Arrange
        sc.subscribe(mock_sub)
        with sc._condition:
            sc._confirm_subscribed(binding_key)

        ## Act
        result = sc.get_active_subscriptions()

        ## Assert
        assert binding_key in result
        assert result[binding_key].status == BindingStatus.ACTIVE

    @capture_logs()
    def test_invalidate_subscriptions(self, sc, mock_sub, binding_key):
        """SubscriptionController.invalidate_subscriptions marks all bindings as DEGRADED."""
        ## Arrange
        sc.subscribe(mock_sub)
        with sc._condition:
            sc._confirm_subscribed(binding_key)

        ## Act
        sc.invalidate_subscriptions()

        ## Assert
        assert sc.get_status(binding_key) == BindingStatus.DEGRADED


class TestObserve:
    @capture_logs()
    def test_observe_confirms_subscribed(self, sc, mock_sub, binding_key):
        """SubscriptionController.observe confirms subscription when resolver returns active."""
        ## Arrange
        sc.subscribe(mock_sub)
        event = MockEvent(binding_key=binding_key, is_active=True)

        ## Act
        sc.observe(event)

        ## Assert
        assert sc.get_status(binding_key) == BindingStatus.ACTIVE

    @capture_logs()
    def test_observe_confirms_unsubscribed(self, sc, mock_sub, binding_key):
        """SubscriptionController.observe confirms unsubscription when resolver returns inactive."""
        ## Arrange
        sc.subscribe(mock_sub)
        with sc._condition:
            sc._confirm_subscribed(binding_key)
        sc.unsubscribe(mock_sub)
        event = MockEvent(binding_key=binding_key, is_active=False)

        ## Act
        sc.observe(event)

        ## Assert
        assert sc.get_status(binding_key) == BindingStatus.UNSUBSCRIBED

    @capture_logs()
    def test_observe_ignores_unrelated_events(self, sc, mock_sub, binding_key):
        """SubscriptionController.observe ignores events with no binding key."""
        ## Arrange
        sc.subscribe(mock_sub)
        event = WsOpen()

        ## Act
        sc.observe(event)

        ## Assert
        assert sc.get_status(binding_key) == BindingStatus.NEW, 'observe should not have updated the binding'

    @capture_logs(logger_level='WARNING', expected_errors=['Observed a binding_key'], partial_match=True)
    def test_observe_warns_on_missing_subscription(self, sc):
        """SubscriptionController.observe logs warning when binding key has no subscription."""
        ## Arrange
        event = MockEvent(binding_key='unknown_key', is_active=True)

        ## Act
        sc.observe(event)


class TestReconcile:
    @capture_logs()
    def test_reconcile_binding_sends_subscribe_payload(self, sc, mock_sub, mock_send_payload, binding_key):
        """SubscriptionController.reconcile_binding sends subscribe payload for ACTIVE intent."""
        ## Arrange
        sc.subscribe(mock_sub)
        binding = sc._bindings[binding_key]

        ## Act
        sc.reconcile_binding(binding)

        ## Assert
        mock_send_payload.assert_called_once_with('sub_payload')
        assert binding.attempts == 1
        assert binding.status == BindingStatus.NEW

    @capture_logs()
    def test_reconcile_binding_sends_unsubscribe_payload(self, sc, test_subscription_no_confirm, mock_send_payload):
        """SubscriptionController.reconcile_binding sends unsubscribe payload for UNSUBSCRIBED intent."""
        ## Arrange
        sc.unsubscribe(test_subscription_no_confirm)
        binding = sc._bindings[test_subscription_no_confirm.binding_key()]

        ## Act
        with sc._condition:
            sc.reconcile_binding(binding)

        ## Assert
        mock_send_payload.assert_called_once_with('unsub_no_confirm_payload')
        assert binding.attempts == 1

    @capture_logs()
    def test_reconcile_binding_auto_confirms_when_no_confirm_subscribe(self, sc, test_subscription_no_confirm, mock_send_payload):
        """SubscriptionController.reconcile_binding auto-confirms when confirms_subscribe is False."""
        ## Arrange
        sc.subscribe(test_subscription_no_confirm)
        binding = sc._bindings[test_subscription_no_confirm.binding_key()]

        ## Act
        with sc._condition:
            sc.reconcile_binding(binding)

        ## Assert
        assert binding.status == BindingStatus.ACTIVE

    @capture_logs()
    def test_reconcile_binding_no_auto_confirm_when_confirms_unsubscribe_true(self, sc, test_subscription_no_confirm, mock_send_payload):
        """SubscriptionController.reconcile_binding does not auto-confirm when confirms_unsubscribe is True."""
        ## Arrange
        sc.unsubscribe(test_subscription_no_confirm)
        binding = sc._bindings[test_subscription_no_confirm.binding_key()]

        ## Act
        sc.reconcile_binding(binding)

        ## Assert
        assert binding.status == BindingStatus.NEW
        assert binding.attempts == 1

    @capture_logs()
    def test_reconcile_binding_auto_confirms_when_no_confirm_unsubscribe(self, sc, mock_sub, mock_send_payload, binding_key):
        """SubscriptionController.reconcile_binding auto-confirms when confirms_unsubscribe is False."""
        ## Arrange
        sc.unsubscribe(mock_sub)
        binding = sc._bindings[binding_key]

        ## Act
        with sc._condition:
            sc.reconcile_binding(binding)

        ## Assert
        assert binding.status == BindingStatus.UNSUBSCRIBED

    @capture_logs()
    def test_reconcile_binding_respects_timeout(self, sc, mock_sub, binding_key):
        """SubscriptionController.reconcile_binding waits for timeout before retrying."""
        ## Arrange
        sc.subscribe(mock_sub)
        binding = sc._bindings[binding_key]

        ## Act
        with mock_module_time('ibind.ws_v2.ws_subscriptions', time_sequence=[1000.0, 1000.5]):
            sc.reconcile_binding(binding)
            first_attempt = binding.attempts
            sc.reconcile_binding(binding)

        ## Assert
        assert binding.attempts == first_attempt

    @capture_logs()
    def test_reconcile_binding_retries_after_timeout(self, sc, mock_sub, mock_send_payload, binding_key):
        """SubscriptionController.reconcile_binding retries after timeout expires."""
        ## Arrange
        sc.subscribe(mock_sub)
        binding = sc._bindings[binding_key]

        ## Act
        with mock_module_time('ibind.ws_v2.ws_subscriptions', time_sequence=[1000.0, 1000.0, 1002.0]):
            sc.reconcile_binding(binding)
            sc.reconcile_binding(binding)  # this call should return without making an attempt
            sc.reconcile_binding(binding)

        ## Assert
        assert binding.attempts == 2, 'should only attempt twice'
        assert mock_send_payload.call_count == 2

    @capture_logs()
    def test_reconcile_binding_marks_failed_after_max_retries(self, sc, mock_sub, binding_key):
        """SubscriptionController.reconcile_binding marks binding as FAILED after max retries."""
        ## Arrange
        sc.subscribe(mock_sub)
        binding = sc._bindings[binding_key]

        ## Act
        with mock_module_time('ibind.ws_v2.ws_subscriptions', time_sequence=[1000.0, 1001.1, 1002.2, 1003.3, 1004.4]):
            for i in range(4):
                with sc._condition:
                    sc.reconcile_binding(binding)

        ## Assert
        assert binding.status == BindingStatus.FAILED

    @capture_logs()
    def test_reconcile_binding_marks_expired_when_no_activity(self, sc, test_subscription_with_expiry):
        """SubscriptionController.reconcile_binding marks binding as EXPIRED when expiry time passes."""
        ## Arrange
        with mock_module_time('ibind.ws_v2.ws_subscriptions', time_sequence=[1000.0, 1011.0]):
            sc.subscribe(test_subscription_with_expiry)
            binding = sc._bindings[test_subscription_with_expiry.binding_key()]
            with sc._condition:
                sc.reconcile_binding(binding)
            with sc._condition:
                sc._confirm_subscribed(test_subscription_with_expiry.binding_key())

            ## Act
            with sc._condition:
                sc.reconcile_binding(binding)

        ## Assert
        assert binding.status == BindingStatus.EXPIRED

    @capture_logs()
    def test_reconcile_binding_does_not_expire_without_expiry_seconds(self, sc, mock_sub, binding_key):
        """SubscriptionController.reconcile_binding does not expire when expiry_seconds is None."""
        ## Arrange
        sc.subscribe(mock_sub)
        binding = sc._bindings[binding_key]
        sc.reconcile_binding(binding)
        with sc._condition:
            sc._confirm_subscribed(binding_key)

        ## Act
        with mock_module_time('ibind.ws_v2.ws_subscriptions', time_sequence=[1000.0, 1002.0]):
            sc.reconcile_binding(binding)

        ## Assert
        assert binding.status == BindingStatus.ACTIVE

    @capture_logs()
    def test_reconcile_binding_does_not_expire_before_expiry_time(self, sc, test_subscription_with_expiry):
        """SubscriptionController.reconcile_binding does not expire before expiry_seconds elapses."""
        ## Arrange
        with mock_module_time('ibind.ws_v2.ws_subscriptions', time_sequence=[1000.0, 1005.0]):
            sc.subscribe(test_subscription_with_expiry)
            binding = sc._bindings[test_subscription_with_expiry.binding_key()]
            with sc._condition:
                sc.reconcile_binding(binding)
            with sc._condition:
                sc._confirm_subscribed(test_subscription_with_expiry.binding_key())

            ## Act
            with sc._condition:
                sc.reconcile_binding(binding)

        ## Assert
        assert binding.status == BindingStatus.ACTIVE

    @capture_logs()
    def test_reconcile_bindings_processes_all_bindings(self, sc):
        """SubscriptionController.reconcile_bindings processes all registered bindings."""
        ## Arrange
        sub1 = MockSubscription(topic_value='topic1', payload_value='payload1')
        sub2 = MockSubscription(topic_value='topic2', payload_value='payload2')
        sc.subscribe(sub1)
        sc.subscribe(sub2)

        ## Act
        sc.reconcile_bindings()

        ## Assert
        binding1 = sc._bindings[sub1.binding_key()]
        binding2 = sc._bindings[sub2.binding_key()]
        assert binding1.attempts == 1
        assert binding2.attempts == 1


class TestSend:
    @capture_logs(logger_level='INFO', expected_errors=['Sending payload unsuccessful'], partial_match=True)
    def test_send_logs_when_send_fails(self, sc, mock_sub, mock_send_payload, binding_key):
        """SubscriptionController._send logs when send_payload returns False."""
        ## Arrange
        mock_send_payload.return_value = False
        sc.subscribe(mock_sub)
        binding = sc._bindings[binding_key]

        ## Act
        sc.reconcile_binding(binding)

    @capture_logs(logger_level='ERROR', expected_errors=['Exception sending payload'], partial_match=True)
    def test_send_logs_exception(self, sc, mock_sub, mock_send_payload, binding_key):
        """SubscriptionController._send logs exceptions from send_payload."""
        ## Arrange
        mock_send_payload.side_effect = RuntimeError('send error')
        sc.subscribe(mock_sub)
        binding = sc._bindings[binding_key]

        ## Act
        sc.reconcile_binding(binding)


class TestWaitFor:
    @capture_logs()
    def test_wait_for_returns_true_when_done(self, sc, mock_sub, binding_key):
        """SubscriptionController.wait_for returns True when binding is done."""
        ## Arrange
        sc.subscribe(mock_sub)
        with sc._condition:
            sc._confirm_subscribed(binding_key)

        ## Act
        result = sc.wait_for(binding_key, timeout=1.0)

        ## Assert
        assert result is True

    @capture_logs()
    def test_wait_for_returns_false_when_failed(self, sc, mock_sub, binding_key):
        """SubscriptionController.wait_for returns False when binding is FAILED."""
        ## Arrange
        sc.subscribe(mock_sub)
        binding = sc._bindings[binding_key]
        binding.status = BindingStatus.FAILED

        ## Act
        result = sc.wait_for(binding_key, timeout=1.0)

        ## Assert
        assert result is False

    @capture_logs()
    def test_wait_for_returns_false_when_missing(self, sc):
        """SubscriptionController.wait_for returns False when binding does not exist."""
        ## Act
        result = sc.wait_for('nonexistent', timeout=0.1)

        ## Assert
        assert result is False

    @capture_logs()
    def test_wait_for_returns_false_on_timeout(self, sc, mock_sub, binding_key):
        """SubscriptionController.wait_for returns False when timeout expires."""
        ## Arrange
        sc.subscribe(mock_sub)

        ## Act
        result = sc.wait_for(binding_key, timeout=0.001)

        ## Assert
        assert result is False

    @capture_logs()
    def test_wait_for_waits_and_unblocks_on_notification(self, sc, mock_sub, binding_key):
        """SubscriptionController.wait_for waits for notification and returns when status changes."""
        ## Arrange
        sc.subscribe(mock_sub)
        event = MockEvent(binding_key=binding_key, is_active=True)

        original_wait = sc._condition.wait
        wait_call_count = 0

        def mock_wait(timeout=None):
            nonlocal wait_call_count
            wait_call_count += 1
            if wait_call_count == 1:
                sc.observe(event)
            else:
                original_wait(timeout)

        ## Act
        with patch.object(sc._condition, 'wait', side_effect=mock_wait):
            result = sc.wait_for(binding_key, timeout=5.0)

        ## Assert
        assert result is True
        assert wait_call_count == 1
        assert sc.get_status(binding_key) == BindingStatus.ACTIVE


class TestConfirmSubscribed:
    @capture_logs()
    def test_confirm_subscribed_updates_status(self, sc, mock_sub, binding_key):
        """SubscriptionController._confirm_subscribed updates status to ACTIVE."""
        ## Arrange
        sc.subscribe(mock_sub)

        ## Act
        with sc._condition:
            sc._confirm_subscribed(binding_key)

        ## Assert
        assert sc.get_status(binding_key) == BindingStatus.ACTIVE

    @capture_logs()
    def test_confirm_subscribed_ignores_when_already_active(self, sc, mock_sub, binding_key):
        """SubscriptionController._confirm_subscribed does not update when already ACTIVE."""
        ## Arrange
        sc.subscribe(mock_sub)
        with sc._condition:
            sc._confirm_subscribed(binding_key)
        binding = sc._bindings[binding_key]
        binding.attempts = 5

        ## Act
        with sc._condition:
            sc._confirm_subscribed(binding_key)

        ## Assert
        assert binding.attempts == 5

    @capture_logs()
    def test_confirm_subscribed_ignores_when_intent_unsubscribed(self, sc, mock_sub, binding_key):
        """SubscriptionController._confirm_subscribed does not update when intent is UNSUBSCRIBED."""
        ## Arrange
        sc.subscribe(mock_sub)
        sc.unsubscribe(mock_sub)
        binding = sc._bindings[binding_key]
        original_status = binding.status

        ## Act
        sc._confirm_subscribed(binding_key)

        ## Assert
        assert binding.status == original_status

    @capture_logs(logger_level='WARNING', expected_errors=['Unknown subscription'], partial_match=True)
    def test_confirm_subscribed_warns_when_missing(self, sc):
        """SubscriptionController._confirm_subscribed logs warning when binding does not exist."""
        ## Act
        sc._confirm_subscribed('nonexistent')


class TestConfirmUnsubscribed:
    @capture_logs()
    def test_confirm_unsubscribed_updates_status(self, sc, mock_sub, binding_key):
        """SubscriptionController._confirm_unsubscribed updates status to UNSUBSCRIBED."""
        ## Arrange
        sc.unsubscribe(mock_sub)

        ## Act
        with sc._condition:
            sc._confirm_unsubscribed(binding_key)

        ## Assert
        assert sc.get_status(binding_key) == BindingStatus.UNSUBSCRIBED

    @capture_logs()
    def test_confirm_unsubscribed_ignores_when_already_unsubscribed(self, sc, mock_sub, binding_key):
        """SubscriptionController._confirm_unsubscribed does not update when already UNSUBSCRIBED."""
        ## Arrange
        sc.unsubscribe(mock_sub)
        with sc._condition:
            sc._confirm_unsubscribed(binding_key)
        binding = sc._bindings[binding_key]
        binding.attempts = 5

        ## Act
        with sc._condition:
            sc._confirm_unsubscribed(binding_key)

        ## Assert
        assert binding.attempts == 5

    @capture_logs()
    def test_confirm_unsubscribed_ignores_when_intent_active(self, sc, mock_sub, binding_key):
        """SubscriptionController._confirm_unsubscribed does not update when intent is ACTIVE."""
        ## Arrange
        sc.subscribe(mock_sub)
        binding = sc._bindings[binding_key]
        original_status = binding.status

        ## Act
        sc._confirm_unsubscribed(binding_key)

        ## Assert
        assert binding.status == original_status

    @capture_logs(logger_level='WARNING', expected_errors=['Unknown subscription'], partial_match=True)
    def test_confirm_unsubscribed_warns_when_missing(self, sc):
        """SubscriptionController._confirm_unsubscribed logs warning when binding does not exist."""
        ## Act
        sc._confirm_unsubscribed('nonexistent')


class TestSubscriptionUpdatedEvent:
    @capture_logs()
    def test_subscription_updated_emitted_on_status_change(self, sc, mock_sub, binding_key, mock_emit_event):
        """SubscriptionController emits SubscriptionUpdated event when status changes."""
        ## Arrange
        sc.subscribe(mock_sub)

        ## Act
        with sc._condition:
            sc._confirm_subscribed(binding_key)

        ## Assert
        mock_emit_event.assert_called_once()
        event = mock_emit_event.call_args[0][0]
        assert isinstance(event, SubscriptionUpdated)
        assert event.subscription == mock_sub
        assert event.binding_key == binding_key
        assert event.status == BindingStatus.ACTIVE

    @capture_logs()
    def test_subscription_updated_emitted_on_unsubscribe(self, sc, mock_sub, binding_key, mock_emit_event):
        """SubscriptionController emits SubscriptionUpdated event when unsubscribing."""
        ## Arrange
        sc.subscribe(mock_sub)
        with sc._condition:
            sc._confirm_subscribed(binding_key)
        sc.unsubscribe(mock_sub)
        mock_emit_event.reset_mock()

        ## Act
        with sc._condition:
            sc._confirm_unsubscribed(binding_key)

        ## Assert
        mock_emit_event.assert_called_once()
        event = mock_emit_event.call_args[0][0]
        assert isinstance(event, SubscriptionUpdated)
        assert event.subscription == mock_sub
        assert event.binding_key == binding_key
        assert event.status == BindingStatus.UNSUBSCRIBED

    @capture_logs()
    def test_subscription_updated_emitted_on_failed_status(self, sc, mock_sub, binding_key, mock_emit_event):
        """SubscriptionController emits SubscriptionUpdated event when subscription fails."""
        ## Arrange
        sc.subscribe(mock_sub)
        binding = sc._bindings[binding_key]
        mock_emit_event.reset_mock()

        ## Act
        with mock_module_time('ibind.ws_v2.ws_subscriptions', time_sequence=[1000.0, 1001.1, 1002.2, 1003.3, 1004.4]):
            for i in range(4):
                with sc._condition:
                    sc.reconcile_binding(binding)

        ## Assert
        assert binding.status == BindingStatus.FAILED
        mock_emit_event.assert_called_once()
        event = mock_emit_event.call_args[0][0]
        assert isinstance(event, SubscriptionUpdated)
        assert event.status == BindingStatus.FAILED

    @capture_logs()
    def test_subscription_updated_emitted_on_expired_status(self, sc, test_subscription_with_expiry, mock_emit_event):
        """SubscriptionController emits SubscriptionUpdated event when subscription expires."""
        ## Arrange
        with mock_module_time('ibind.ws_v2.ws_subscriptions', time_sequence=[1000.0, 1011.0]):
            sc.subscribe(test_subscription_with_expiry)
            binding = sc._bindings[test_subscription_with_expiry.binding_key()]
            with sc._condition:
                sc.reconcile_binding(binding)
            with sc._condition:
                sc._confirm_subscribed(test_subscription_with_expiry.binding_key())
            mock_emit_event.reset_mock()

            ## Act
            with sc._condition:
                sc.reconcile_binding(binding)

        ## Assert
        assert binding.status == BindingStatus.EXPIRED
        mock_emit_event.assert_called_once()
        event = mock_emit_event.call_args[0][0]
        assert isinstance(event, SubscriptionUpdated)
        assert event.status == BindingStatus.EXPIRED

    @capture_logs()
    def test_subscription_updated_emitted_on_degraded_status(self, sc, mock_sub, binding_key, mock_emit_event):
        """SubscriptionController emits SubscriptionUpdated event when subscription is invalidated."""
        ## Arrange
        sc.subscribe(mock_sub)
        with sc._condition:
            sc._confirm_subscribed(binding_key)
        mock_emit_event.reset_mock()

        ## Act
        sc.invalidate_subscriptions()

        ## Assert
        mock_emit_event.assert_called_once()
        event = mock_emit_event.call_args[0][0]
        assert isinstance(event, SubscriptionUpdated)
        assert event.status == BindingStatus.DEGRADED
