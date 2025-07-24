import unittest
from unittest.mock import MagicMock

from ibind.base.subscription_controller import SubscriptionController, SubscriptionProcessor
from ibind.support.py_utils import UNDEFINED


class TestSubscriptionControllerUtilityMethodsU(unittest.TestCase):
    """
    Tests for utility methods in SubscriptionController.

    These methods are currently marked with 'pragma: no cover' but represent
    simple data access patterns that can be easily unit tested. The utility
    methods provide basic subscription state queries without side effects.
    """

    def setUp(self):
        # Create a mock SubscriptionProcessor
        self.mock_processor = MagicMock(spec=SubscriptionProcessor)
        self.controller = SubscriptionController(
            subscription_processor=self.mock_processor,
            subscription_retries=3,
            subscription_timeout=1.0
        )

    def test_is_subscription_active_with_active_subscription(self):
        # Set up an active subscription
        self.controller._subscriptions['test_channel'] = {
            'status': True,
            'data': {'key': 'value'},
            'needs_confirmation': True,
            'subscription_processor': None
        }

        result = self.controller.is_subscription_active('test_channel')
        self.assertTrue(result)

    def test_is_subscription_active_with_inactive_subscription(self):
        # Set up an inactive subscription
        self.controller._subscriptions['test_channel'] = {
            'status': False,
            'data': {'key': 'value'},
            'needs_confirmation': True,
            'subscription_processor': None
        }

        result = self.controller.is_subscription_active('test_channel')
        self.assertFalse(result)

    def test_is_subscription_active_with_nonexistent_channel(self):
        result = self.controller.is_subscription_active('nonexistent_channel')
        self.assertIsNone(result)

    def test_is_subscription_active_with_missing_status(self):
        # Set up subscription without status field
        self.controller._subscriptions['test_channel'] = {
            'data': {'key': 'value'},
            'needs_confirmation': True,
            'subscription_processor': None
        }

        result = self.controller.is_subscription_active('test_channel')
        self.assertIsNone(result)

    def test_has_active_subscriptions_with_active_subscriptions(self):
        # Set up mix of active and inactive subscriptions
        self.controller._subscriptions = {
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

        result = self.controller.has_active_subscriptions()
        self.assertTrue(result)

    def test_has_active_subscriptions_with_no_active_subscriptions(self):
        # Set up only inactive subscriptions
        self.controller._subscriptions = {
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

        result = self.controller.has_active_subscriptions()
        self.assertFalse(result)

    def test_has_active_subscriptions_with_empty_subscriptions(self):
        self.controller._subscriptions = {}

        result = self.controller.has_active_subscriptions()
        self.assertFalse(result)

    def test_has_subscription_with_existing_channel(self):
        self.controller._subscriptions['existing_channel'] = {
            'status': True,
            'data': None,
            'needs_confirmation': True,
            'subscription_processor': None
        }

        result = self.controller.has_subscription('existing_channel')
        self.assertTrue(result)

    def test_has_subscription_with_nonexistent_channel(self):
        result = self.controller.has_subscription('nonexistent_channel')
        self.assertFalse(result)

    def test_has_subscription_with_empty_subscriptions(self):
        self.controller._subscriptions = {}

        result = self.controller.has_subscription('any_channel')
        self.assertFalse(result)


class TestSubscriptionControllerInitU(unittest.TestCase):
    """
    Tests for SubscriptionController constructor and initialization.

    These tests verify that the controller properly initializes all instance variables
    with both default and custom parameters.
    """

    def test_init_with_default_parameters(self):
        mock_processor = MagicMock(spec=SubscriptionProcessor)

        controller = SubscriptionController(subscription_processor=mock_processor)

        # Verify all instance variables are set correctly
        self.assertEqual(controller._subscription_processor, mock_processor)
        self.assertEqual(controller._subscription_retries, 5)  # default
        self.assertEqual(controller._subscription_timeout, 2)  # default
        self.assertEqual(controller._subscriptions, {})
        self.assertIsNotNone(controller._operational_lock)

    def test_init_with_custom_parameters(self):
        mock_processor = MagicMock(spec=SubscriptionProcessor)
        custom_retries = 10
        custom_timeout = 5.0

        controller = SubscriptionController(
            subscription_processor=mock_processor,
            subscription_retries=custom_retries,
            subscription_timeout=custom_timeout
        )

        # Verify custom parameters are set correctly
        self.assertEqual(controller._subscription_processor, mock_processor)
        self.assertEqual(controller._subscription_retries, custom_retries)
        self.assertEqual(controller._subscription_timeout, custom_timeout)
        self.assertEqual(controller._subscriptions, {})
        self.assertIsNotNone(controller._operational_lock)

    def test_init_with_zero_retries(self):
        mock_processor = MagicMock(spec=SubscriptionProcessor)

        controller = SubscriptionController(
            subscription_processor=mock_processor,
            subscription_retries=0,
            subscription_timeout=1.0
        )

        self.assertEqual(controller._subscription_retries, 0)
        self.assertEqual(controller._subscription_timeout, 1.0)


class TestModifySubscriptionU(unittest.TestCase):
    """
    Tests for modify_subscription method parameter handling.

    These tests focus on the simple parameter assignment logic and KeyError handling
    without testing the complex WebSocket integration aspects.
    """

    def setUp(self):
        self.mock_processor = MagicMock(spec=SubscriptionProcessor)
        self.controller = SubscriptionController(subscription_processor=self.mock_processor)

        # Set up a test subscription
        self.test_channel = 'test_channel'
        self.controller._subscriptions[self.test_channel] = {
            'status': False,
            'data': {'original': 'data'},
            'needs_confirmation': True,
            'subscription_processor': self.mock_processor
        }

    def test_modify_subscription_status_only(self):
        self.controller.modify_subscription(self.test_channel, status=True)

        # Verify only status was modified
        subscription = self.controller._subscriptions[self.test_channel]
        self.assertTrue(subscription['status'])
        self.assertEqual(subscription['data'], {'original': 'data'})
        self.assertTrue(subscription['needs_confirmation'])
        self.assertEqual(subscription['subscription_processor'], self.mock_processor)

    def test_modify_subscription_data_only(self):
        new_data = {'modified': 'data'}
        self.controller.modify_subscription(self.test_channel, data=new_data)

        # Verify only data was modified
        subscription = self.controller._subscriptions[self.test_channel]
        self.assertFalse(subscription['status'])
        self.assertEqual(subscription['data'], new_data)
        self.assertTrue(subscription['needs_confirmation'])
        self.assertEqual(subscription['subscription_processor'], self.mock_processor)

    def test_modify_subscription_needs_confirmation_only(self):
        self.controller.modify_subscription(self.test_channel, needs_confirmation=False)

        # Verify only needs_confirmation was modified
        subscription = self.controller._subscriptions[self.test_channel]
        self.assertFalse(subscription['status'])
        self.assertEqual(subscription['data'], {'original': 'data'})
        self.assertFalse(subscription['needs_confirmation'])
        self.assertEqual(subscription['subscription_processor'], self.mock_processor)

    def test_modify_subscription_processor_only(self):
        new_processor = MagicMock(spec=SubscriptionProcessor)
        self.controller.modify_subscription(self.test_channel, subscription_processor=new_processor)

        # Verify only subscription_processor was modified
        subscription = self.controller._subscriptions[self.test_channel]
        self.assertFalse(subscription['status'])
        self.assertEqual(subscription['data'], {'original': 'data'})
        self.assertTrue(subscription['needs_confirmation'])
        self.assertEqual(subscription['subscription_processor'], new_processor)

    def test_modify_subscription_multiple_parameters(self):
        new_data = {'new': 'data'}
        new_processor = MagicMock(spec=SubscriptionProcessor)

        self.controller.modify_subscription(
            self.test_channel,
            status=True,
            data=new_data,
            needs_confirmation=False,
            subscription_processor=new_processor
        )

        # Verify all parameters were modified
        subscription = self.controller._subscriptions[self.test_channel]
        self.assertTrue(subscription['status'])
        self.assertEqual(subscription['data'], new_data)
        self.assertFalse(subscription['needs_confirmation'])
        self.assertEqual(subscription['subscription_processor'], new_processor)

    def test_modify_subscription_with_undefined_parameters(self):
        original_subscription = self.controller._subscriptions[self.test_channel].copy()

        # Call with all UNDEFINED parameters - nothing should change
        self.controller.modify_subscription(
            self.test_channel,
            status=UNDEFINED,
            data=UNDEFINED,
            needs_confirmation=UNDEFINED,
            subscription_processor=UNDEFINED
        )

        # Verify nothing was modified
        self.assertEqual(self.controller._subscriptions[self.test_channel], original_subscription)

    def test_modify_subscription_nonexistent_channel_raises_keyerror(self):
        nonexistent_channel = 'nonexistent_channel'

        with self.assertRaises(KeyError) as context:
            self.controller.modify_subscription(nonexistent_channel, status=True)

        # Verify the error message contains channel info
        error_message = str(context.exception)
        self.assertIn(nonexistent_channel, error_message)
        self.assertIn('does not exist', error_message)
        self.assertIn('Current subscriptions:', error_message)
