import pytest
from unittest.mock import MagicMock

from ibind.base.subscription_controller import (
    SubscriptionController,
    SubscriptionProcessor,
    DEFAULT_SUBSCRIPTION_RETRIES,
    DEFAULT_SUBSCRIPTION_TIMEOUT
)
from ibind.support.py_utils import UNDEFINED


@pytest.fixture
def mock_processor():
    """Create a mock SubscriptionProcessor for testing."""
    return MagicMock(spec=SubscriptionProcessor)


@pytest.fixture
def subscription_controller(mock_processor):
    """Create a SubscriptionController with default test configuration."""
    return SubscriptionController(
        subscription_processor=mock_processor,
        subscription_retries=3,
        subscription_timeout=1.0
    )


@pytest.fixture
def controller_with_test_subscription(mock_processor):
    """Create a SubscriptionController with a predefined test subscription."""
    controller = SubscriptionController(subscription_processor=mock_processor)
    controller._subscriptions['test_channel'] = {
        'status': False,
        'data': {'original': 'data'},
        'needs_confirmation': True,
        'subscription_processor': mock_processor
    }
    return controller


@pytest.fixture
def subscription_configs():
    """Common subscription configurations for testing."""
    return {
        'active': lambda processor=None: {
            'status': True,
            'data': {'key': 'value'},
            'needs_confirmation': True,
            'subscription_processor': processor
        },
        'inactive': lambda processor=None: {
            'status': False,
            'data': {'key': 'value'},
            'needs_confirmation': True,
            'subscription_processor': processor
        }
    }


@pytest.mark.parametrize("subscription_data,expected", [
    ({'status': True, 'data': {'key': 'value'}, 'needs_confirmation': True, 'subscription_processor': None}, True),
    ({'status': False, 'data': {'key': 'value'}, 'needs_confirmation': True, 'subscription_processor': None}, False),
    ({'data': {'key': 'value'}, 'needs_confirmation': True, 'subscription_processor': None}, None),  # missing status
])
def test_is_subscription_active(subscription_controller, subscription_data, expected):
    # Arrange
    subscription_controller._subscriptions['test_channel'] = subscription_data

    # Act
    result = subscription_controller.is_subscription_active('test_channel')

    # Assert
    assert result is expected


@pytest.mark.parametrize("subscriptions_config,expected", [
    # Has active subscriptions
    ({
        'active_channel': {'status': True, 'data': None, 'needs_confirmation': True, 'subscription_processor': None},
        'inactive_channel': {'status': False, 'data': None, 'needs_confirmation': True, 'subscription_processor': None}
    }, True),
    # No active subscriptions
    ({
        'inactive_channel_1': {'status': False, 'data': None, 'needs_confirmation': True, 'subscription_processor': None},
        'inactive_channel_2': {'status': False, 'data': None, 'needs_confirmation': True, 'subscription_processor': None}
    }, False),
    # Empty subscriptions
    ({}, False),
])
def test_has_active_subscriptions(subscription_controller, subscriptions_config, expected):
    # Arrange
    subscription_controller._subscriptions = subscriptions_config

    # Act
    result = subscription_controller.has_active_subscriptions()

    # Assert
    assert result is expected


@pytest.mark.parametrize("subscriptions_config,channel,expected", [
    # Existing channel
    ({'existing_channel': {'status': True, 'data': None, 'needs_confirmation': True, 'subscription_processor': None}}, 'existing_channel', True),
    # Empty subscriptions
    ({}, 'any_channel', False),
])
def test_has_subscription(subscription_controller, subscriptions_config, channel, expected):
    # Arrange
    subscription_controller._subscriptions = subscriptions_config

    # Act
    result = subscription_controller.has_subscription(channel)

    # Assert
    assert result is expected


@pytest.mark.parametrize("modifications,expected_status,expected_data,expected_confirmation,expected_processor_is_new", [
    # Status only
    ({'status': True}, True, {'original': 'data'}, True, False),
    # Data only
    ({'data': {'modified': 'data'}}, False, {'modified': 'data'}, True, False),
    # Needs confirmation only
    ({'needs_confirmation': False}, False, {'original': 'data'}, False, False),
    # Processor only - we'll test the processor separately since it's a MagicMock
    # Multiple parameters
    ({'status': True, 'data': {'new': 'data'}, 'needs_confirmation': False}, True, {'new': 'data'}, False, False),
])
def test_modify_subscription_parameters(controller_with_test_subscription, modifications, expected_status, expected_data, expected_confirmation, expected_processor_is_new):
    # Arrange
    original_processor = controller_with_test_subscription._subscriptions['test_channel']['subscription_processor']
    if 'subscription_processor' in modifications:
        new_processor = MagicMock(spec=SubscriptionProcessor)
        modifications['subscription_processor'] = new_processor

    # Act
    controller_with_test_subscription.modify_subscription('test_channel', **modifications)

    # Assert
    subscription = controller_with_test_subscription._subscriptions['test_channel']
    assert subscription['status'] is expected_status
    assert subscription['data'] == expected_data
    assert subscription['needs_confirmation'] is expected_confirmation

    if 'subscription_processor' in modifications:
        assert subscription['subscription_processor'] == modifications['subscription_processor']
    else:
        assert subscription['subscription_processor'] == original_processor


def test_modify_subscription_processor_only(controller_with_test_subscription):
    # Arrange
    new_processor = MagicMock(spec=SubscriptionProcessor)

    # Act
    controller_with_test_subscription.modify_subscription('test_channel', subscription_processor=new_processor)

    # Assert
    subscription = controller_with_test_subscription._subscriptions['test_channel']
    assert subscription['status'] is False
    assert subscription['data'] == {'original': 'data'}
    assert subscription['needs_confirmation'] is True
    assert subscription['subscription_processor'] == new_processor


def test_modify_subscription_with_undefined_parameters(controller_with_test_subscription):
    # Arrange
    original_subscription = controller_with_test_subscription._subscriptions['test_channel'].copy()

    # Act
    controller_with_test_subscription.modify_subscription(
        'test_channel',
        status=UNDEFINED,
        data=UNDEFINED,
        needs_confirmation=UNDEFINED,
        subscription_processor=UNDEFINED
    )

    # Assert
    assert controller_with_test_subscription._subscriptions['test_channel'] == original_subscription


def test_modify_subscription_nonexistent_channel_raises_keyerror(subscription_controller):
    # Arrange
    nonexistent_channel = 'nonexistent_channel'

    # Act & Assert
    with pytest.raises(KeyError) as exc_info:
        subscription_controller.modify_subscription(nonexistent_channel, status=True)

    error_message = str(exc_info.value)
    assert nonexistent_channel in error_message
    assert 'does not exist' in error_message
    assert 'Current subscriptions:' in error_message


# Tests for _attempt_unsubscribing_repeated method retry logic.
#
# These tests cover the complex retry loop logic that handles WebSocket
# unsubscription attempts with confirmation waiting and failure handling.


@pytest.mark.parametrize("wait_until_results,retries,expected_result,expected_send_calls,expected_wait_calls", [
    ([True], 5, True, 1, 1),                    # Success first try
    ([False, False, True], 3, True, 3, 3),     # Success after retries
    ([False, False], 2, False, 2, 2),          # Failure after max retries
])
def test_attempt_unsubscribing_repeated_retry_logic(subscription_controller, monkeypatch, wait_until_results, retries, expected_result, expected_send_calls, expected_wait_calls):
    # Arrange
    test_channel = 'test_channel'
    test_payload = 'unsubscribe_payload'
    subscription_controller._subscription_retries = retries

    subscription_controller.running = True
    mock_send_payload = MagicMock(return_value=True)
    monkeypatch.setattr(subscription_controller, '_send_payload', mock_send_payload)

    mock_wait_until = MagicMock(side_effect=wait_until_results)
    monkeypatch.setattr('ibind.base.subscription_controller.wait_until', mock_wait_until)

    # Act
    result = subscription_controller._attempt_unsubscribing_repeated(test_channel, test_payload)

    # Assert
    assert result is expected_result
    assert mock_send_payload.call_count == expected_send_calls
    assert mock_wait_until.call_count == expected_wait_calls


# Tests for recreate_subscriptions method
#
# These tests cover the subscription recreation logic that handles restoring
# inactive subscriptions after connection issues or system restarts.


@pytest.mark.parametrize("initial_subscriptions,subscribe_success,expected_subscribe_calls", [
    # No inactive subscriptions - all active
    ({
        'active_1': {'status': True, 'data': {'key': 'value1'}, 'needs_confirmation': True, 'subscription_processor': None},
        'active_2': {'status': True, 'data': {'key': 'value2'}, 'needs_confirmation': False, 'subscription_processor': None}
    }, True, 0),
    # Only inactive subscriptions - all should be recreated
    ({
        'inactive_1': {'status': False, 'data': {'key': 'value1'}, 'needs_confirmation': True, 'subscription_processor': None},
        'inactive_2': {'status': False, 'data': {'key': 'value2'}, 'needs_confirmation': False, 'subscription_processor': None}
    }, True, 2),
    # Mixed active/inactive - only inactive should be recreated
    ({
        'active': {'status': True, 'data': {'active': 'data'}, 'needs_confirmation': True, 'subscription_processor': None},
        'inactive': {'status': False, 'data': {'inactive': 'data'}, 'needs_confirmation': False, 'subscription_processor': None}
    }, True, 1),
])
def test_recreate_subscriptions_basic_functionality(subscription_controller, monkeypatch, initial_subscriptions, subscribe_success, expected_subscribe_calls):
    # Arrange
    subscription_controller._subscriptions = initial_subscriptions

    mock_subscribe = MagicMock(return_value=subscribe_success)
    monkeypatch.setattr(subscription_controller, 'subscribe', mock_subscribe)

    # Act
    subscription_controller.recreate_subscriptions()

    # Assert
    assert mock_subscribe.call_count == expected_subscribe_calls

    # If no subscriptions were recreated, verify original subscriptions remain
    if expected_subscribe_calls == 0:
        assert len(subscription_controller._subscriptions) == len(initial_subscriptions)
        for channel, sub in initial_subscriptions.items():
            assert subscription_controller._subscriptions[channel]['status'] == sub['status']




@pytest.mark.parametrize("failure_scenario", ["partial", "all"])
def test_recreate_subscriptions_with_failures(subscription_controller, monkeypatch, failure_scenario):
    # Arrange
    mock_processor = MagicMock()
    original_subscriptions = {
        'inactive_channel_1': {
            'status': False,
            'data': {'key': 'value1'},
            'needs_confirmation': True,
            'subscription_processor': mock_processor
        },
        'inactive_channel_2': {
            'status': False,
            'data': {'key': 'value2'},
            'needs_confirmation': False,
            'subscription_processor': None
        }
    }
    subscription_controller._subscriptions = original_subscriptions.copy()

    # Configure subscribe behavior based on failure scenario
    if failure_scenario == "partial":
        def mock_subscribe_side_effect(channel, *args, **kwargs):
            return channel != 'inactive_channel_2'  # Fail only channel_2
        mock_subscribe = MagicMock(side_effect=mock_subscribe_side_effect)
    else:  # all failures
        mock_subscribe = MagicMock(return_value=False)

    monkeypatch.setattr(subscription_controller, 'subscribe', mock_subscribe)

    # Act
    subscription_controller.recreate_subscriptions()

    # Assert
    assert mock_subscribe.call_count == 2

    if failure_scenario == "partial":
        # Failed subscription should be preserved with status=False
        assert 'inactive_channel_2' in subscription_controller._subscriptions
        assert subscription_controller._subscriptions['inactive_channel_2']['status'] is False
    else:
        # All failed subscriptions should be preserved
        assert len(subscription_controller._subscriptions) == 2
        for channel, original_sub in original_subscriptions.items():
            assert channel in subscription_controller._subscriptions
            restored_sub = subscription_controller._subscriptions[channel]
            assert restored_sub['status'] is False
            assert restored_sub['data'] == original_sub['data']


def test_recreate_subscriptions_preserves_subscription_processor(subscription_controller, monkeypatch):
    # Arrange
    original_processor = MagicMock()
    subscription_controller._subscriptions = {
        'test_channel': {
            'status': False,
            'data': {'test': 'data'},
            'needs_confirmation': True,
            'subscription_processor': original_processor
        }
    }

    # Mock the subscribe method to fail
    mock_subscribe = MagicMock(return_value=False)
    monkeypatch.setattr(subscription_controller, 'subscribe', mock_subscribe)

    # Act
    subscription_controller.recreate_subscriptions()

    # Assert
    # Failed subscription should preserve the original processor
    restored_sub = subscription_controller._subscriptions['test_channel']
    assert restored_sub['subscription_processor'] is original_processor


def test_recreate_subscriptions_handles_missing_processor_key(subscription_controller, monkeypatch):
    # Arrange
    subscription_controller._subscriptions = {
        'test_channel': {
            'status': False,
            'data': {'test': 'data'},
            'needs_confirmation': True
            # Note: no 'subscription_processor' key
        }
    }

    # Mock the subscribe method to fail
    mock_subscribe = MagicMock(return_value=False)
    monkeypatch.setattr(subscription_controller, 'subscribe', mock_subscribe)

    # Act
    subscription_controller.recreate_subscriptions()

    # Assert
    # Should handle missing processor gracefully
    assert mock_subscribe.call_count == 1
    # subscribe should have been called with None for processor
    mock_subscribe.assert_called_with('test_channel', {'test': 'data'}, True, None)

    # Failed subscription should preserve None processor
    restored_sub = subscription_controller._subscriptions['test_channel']
    assert restored_sub['subscription_processor'] is None


@pytest.fixture
def controller_with_mixed_subscriptions():
    """Create a SubscriptionController with mixed active and inactive subscriptions."""
    controller = SubscriptionController(subscription_processor=MagicMock())
    controller._subscriptions = {
        'active_1': {
            'status': True,
            'data': {'active': 'data1'},
            'needs_confirmation': True,
            'subscription_processor': MagicMock()
        },
        'inactive_1': {
            'status': False,
            'data': {'inactive': 'data1'},
            'needs_confirmation': False,
            'subscription_processor': None
        },
        'active_2': {
            'status': True,
            'data': {'active': 'data2'},
            'needs_confirmation': False,
            'subscription_processor': MagicMock()
        },
        'inactive_2': {
            'status': False,
            'data': {'inactive': 'data2'},
            'needs_confirmation': True,
            'subscription_processor': MagicMock()
        }
    }
    return controller


