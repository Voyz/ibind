"""
Unit tests for SubscriptionController.

The SubscriptionController is a class that manages WebSocket subscriptions to various channels
in the Interactive Brokers (IBKR) API. It provides a high-level interface for subscribing
unsubscribing, and managing the lifecycle of data stream subscriptions.

Core Functionality Tested:
==========================

1. **Subscription Management**:
   - Subscribe to channels with retry logic and timeout handling
   - Unsubscribe from channels with optional confirmation
   - Modify existing subscription parameters
   - Recreation of lost subscriptions after connection issues

2. **State Tracking**:
   - Track active/inactive subscription status
   - Manage subscription metadata (data, confirmation requirements, processors)
   - Query subscription existence and status

3. **Configuration**:
   - Initialize with custom retry counts and timeouts
   - Support for different SubscriptionProcessor implementations
   - Thread-safe operations with internal locking

Key Components:
===============

- **SubscriptionController**: Main class managing subscription lifecycle
- **SubscriptionProcessor**: Abstract interface for creating subscribe/unsubscribe payloads
- **Subscription State**: Internal dictionary tracking channel status and metadata

Test Coverage:
==============

This test suite focuses on the **utility methods** and **initialization logic** that are
currently marked with 'pragma: no cover' but represent critical functionality for:

- Subscription state queries without side effects
- Parameter validation and initialization
- Error handling for invalid operations

The tests do NOT cover the complex WebSocket integration aspects (send/receive operations)
which are tested separately in integration tests.

"""

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


def test_is_subscription_active_with_active_subscription(subscription_controller):
    # Arrange
    subscription_controller._subscriptions['test_channel'] = {
        'status': True,
        'data': {'key': 'value'},
        'needs_confirmation': True,
        'subscription_processor': None
    }

    # Act
    result = subscription_controller.is_subscription_active('test_channel')

    # Assert
    assert result is True


def test_is_subscription_active_with_inactive_subscription(subscription_controller):
    # Arrange
    subscription_controller._subscriptions['test_channel'] = {
        'status': False,
        'data': {'key': 'value'},
        'needs_confirmation': True,
        'subscription_processor': None
    }

    # Act
    result = subscription_controller.is_subscription_active('test_channel')

    # Assert
    assert result is False

def test_is_subscription_active_with_missing_status(subscription_controller):
    # Arrange
    subscription_controller._subscriptions['test_channel'] = {
        'data': {'key': 'value'},
        'needs_confirmation': True,
        'subscription_processor': None
    }

    # Act
    result = subscription_controller.is_subscription_active('test_channel')

    # Assert
    assert result is None


def test_has_active_subscriptions_with_active_subscriptions(subscription_controller):
    # Arrange
    subscription_controller._subscriptions = {
        'active_channel': {
            'status': True,
            'data': None,
            'needs_confirmation': True,
            'subscription_processor': None
        },
        'inactive_channel': {
            'status': False,
            'data': None,
            'needs_confirmation': True,
            'subscription_processor': None
        }
    }

    # Act
    result = subscription_controller.has_active_subscriptions()

    # Assert
    assert result is True


def test_has_active_subscriptions_with_no_active_subscriptions(subscription_controller):
    # Arrange
    subscription_controller._subscriptions = {
        'inactive_channel_1': {
            'status': False,
            'data': None,
            'needs_confirmation': True,
            'subscription_processor': None
        },
        'inactive_channel_2': {
            'status': False,
            'data': None,
            'needs_confirmation': True,
            'subscription_processor': None
        }
    }

    # Act
    result = subscription_controller.has_active_subscriptions()

    # Assert
    assert result is False


def test_has_active_subscriptions_with_empty_subscriptions(subscription_controller):
    # Arrange
    subscription_controller._subscriptions = {}

    # Act
    result = subscription_controller.has_active_subscriptions()

    # Assert
    assert result is False


def test_has_subscription_with_existing_channel(subscription_controller):
    # Arrange
    subscription_controller._subscriptions['existing_channel'] = {
        'status': True,
        'data': None,
        'needs_confirmation': True,
        'subscription_processor': None
    }

    # Act
    result = subscription_controller.has_subscription('existing_channel')

    # Assert
    assert result is True


def test_has_subscription_with_empty_subscriptions(subscription_controller):
    # Arrange
    subscription_controller._subscriptions = {}

    # Act
    result = subscription_controller.has_subscription('any_channel')

    # Assert
    assert result is False


def test_init_with_default_parameters(mock_processor):
    # Arrange

    # Act
    controller = SubscriptionController(subscription_processor=mock_processor)

    # Assert
    assert controller._subscription_processor == mock_processor
    assert controller._subscription_retries == DEFAULT_SUBSCRIPTION_RETRIES
    assert controller._subscription_timeout == DEFAULT_SUBSCRIPTION_TIMEOUT
    assert controller._subscriptions == {}
    assert controller._operational_lock is not None


def test_init_with_custom_parameters(mock_processor):
    # Arrange
    custom_retries = 10
    custom_timeout = 5.0

    # Act
    controller = SubscriptionController(
        subscription_processor=mock_processor,
        subscription_retries=custom_retries,
        subscription_timeout=custom_timeout
    )

    # Assert
    assert controller._subscription_processor == mock_processor
    assert controller._subscription_retries == custom_retries
    assert controller._subscription_timeout == custom_timeout
    assert controller._subscriptions == {}
    assert controller._operational_lock is not None


def test_init_with_zero_retries(mock_processor):

    # Act
    controller = SubscriptionController(
        subscription_processor=mock_processor,
        subscription_retries=0,
        subscription_timeout=1.0
    )

    # Assert
    assert controller._subscription_retries == 0
    assert controller._subscription_timeout == 1.0


def test_modify_subscription_status_only(controller_with_test_subscription):

    # Act
    controller_with_test_subscription.modify_subscription('test_channel', status=True)

    # Assert
    subscription = controller_with_test_subscription._subscriptions['test_channel']
    assert subscription['status'] is True
    assert subscription['data'] == {'original': 'data'}
    assert subscription['needs_confirmation'] is True
    assert subscription['subscription_processor'] is not None


def test_modify_subscription_data_only(controller_with_test_subscription):
    # Arrange
    new_data = {'modified': 'data'}

    # Act
    controller_with_test_subscription.modify_subscription('test_channel', data=new_data)

    # Assert
    subscription = controller_with_test_subscription._subscriptions['test_channel']
    assert subscription['status'] is False
    assert subscription['data'] == new_data
    assert subscription['needs_confirmation'] is True
    assert subscription['subscription_processor'] is not None


def test_modify_subscription_needs_confirmation_only(controller_with_test_subscription):

    # Act
    controller_with_test_subscription.modify_subscription('test_channel', needs_confirmation=False)

    # Assert
    subscription = controller_with_test_subscription._subscriptions['test_channel']
    assert subscription['status'] is False
    assert subscription['data'] == {'original': 'data'}
    assert subscription['needs_confirmation'] is False
    assert subscription['subscription_processor'] is not None


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


def test_modify_subscription_multiple_parameters(controller_with_test_subscription):
    # Arrange
    new_data = {'new': 'data'}
    new_processor = MagicMock(spec=SubscriptionProcessor)

    # Act
    controller_with_test_subscription.modify_subscription(
        'test_channel',
        status=True,
        data=new_data,
        needs_confirmation=False,
        subscription_processor=new_processor
    )

    # Assert
    subscription = controller_with_test_subscription._subscriptions['test_channel']
    assert subscription['status'] is True
    assert subscription['data'] == new_data
    assert subscription['needs_confirmation'] is False
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


def test_attempt_unsubscribing_repeated_success_first_try(subscription_controller, monkeypatch):
    # Arrange
    test_channel = 'test_channel'
    test_payload = 'unsubscribe_payload'

    # Mock WebSocket client behavior
    subscription_controller.running = True
    mock_send_payload = MagicMock(return_value=True)
    monkeypatch.setattr(subscription_controller, '_send_payload', mock_send_payload)

    # Mock wait_until to simulate immediate success
    mock_wait_until = MagicMock(return_value=True)
    monkeypatch.setattr('ibind.base.subscription_controller.wait_until', mock_wait_until)

    # Act
    result = subscription_controller._attempt_unsubscribing_repeated(test_channel, test_payload)

    # Assert
    assert result is True
    mock_send_payload.assert_called_once_with(test_payload)
    mock_wait_until.assert_called_once()


def test_attempt_unsubscribing_repeated_success_after_retries(subscription_controller, monkeypatch):
    # Arrange
    test_channel = 'test_channel'
    test_payload = 'unsubscribe_payload'
    subscription_controller._subscription_retries = 3

    subscription_controller.running = True
    mock_send_payload = MagicMock(return_value=True)
    monkeypatch.setattr(subscription_controller, '_send_payload', mock_send_payload)

    # Mock wait_until to fail twice, then succeed
    mock_wait_until = MagicMock(side_effect=[False, False, True])
    monkeypatch.setattr('ibind.base.subscription_controller.wait_until', mock_wait_until)

    # Act
    result = subscription_controller._attempt_unsubscribing_repeated(test_channel, test_payload)

    # Assert
    assert result is True
    assert mock_send_payload.call_count == 3
    assert mock_wait_until.call_count == 3


def test_attempt_unsubscribing_repeated_failure_after_max_retries(subscription_controller, monkeypatch):
    # Arrange
    test_channel = 'test_channel'
    test_payload = 'unsubscribe_payload'
    subscription_controller._subscription_retries = 2

    subscription_controller.running = True
    mock_send_payload = MagicMock(return_value=True)
    monkeypatch.setattr(subscription_controller, '_send_payload', mock_send_payload)

    # Mock wait_until to always fail
    mock_wait_until = MagicMock(return_value=False)
    monkeypatch.setattr('ibind.base.subscription_controller.wait_until', mock_wait_until)

    # Act
    result = subscription_controller._attempt_unsubscribing_repeated(test_channel, test_payload)

    # Assert
    assert result is False
    assert mock_send_payload.call_count == 2
    assert mock_wait_until.call_count == 2
