from ery_backend.base.testcases import EryTestCase
from ery_backend.users.factories import UserFactory

from ..models import Notification
from ..utils import create_user_notification, create_group_notification


class TestNotificationCreation(EryTestCase):
    """
    Confirm notifications created with message and fake url.
    """

    def setUp(self):
        self.user = UserFactory()

    def test_create_user_notification(self):
        message = 'Someone took the cookie from the cookie jar!'
        url = 'ery_backend/cookiestoragearea'
        create_user_notification(self.user, message, url)

        self.assertEqual(Notification.objects.filter(user=self.user, content__message=message, url=url).count(), 1)

    def test_create_group_notification_errors(self):
        """
        Verify type validation.
        """
        # users is not a list
        with self.assertRaises(TypeError):
            create_group_notification(self.user, 'test message', 'test url')
        # message is incorrect type
        with self.assertRaises(TypeError):
            create_group_notification([self.user], 345, 'test url')
        # url is incorrect type
        with self.assertRaises(TypeError):
            create_group_notification([self.user], 'test message', 345)

    def test_create_group_notification(self):
        user_2 = UserFactory()
        # url
        notifications = create_group_notification([self.user, user_2], 'test message 2', 'fakelinkhere')
        self.assertIsInstance(notifications, list)
        self.assertEqual(
            Notification.objects.filter(user=self.user, content__message='test message 2', url='fakelinkhere').count(), 1
        )
        self.assertEqual(
            Notification.objects.filter(user=user_2, content__message='test message 2', url='fakelinkhere').count(), 1
        )
