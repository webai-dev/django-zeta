import datetime as dt

from ery_backend.base.testcases import EryTestCase
from ery_backend.users.factories import UserFactory

from ..factories import NotificationFactory, NotificationContentFactory
from ..models import NotificationPriority


class TestNotification(EryTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.content = NotificationContentFactory()
        self.notification = NotificationFactory(user=self.user, content=self.content, read=False)

    def test_expected_attributes(self):
        self.assertEqual(self.notification.user, self.user)
        self.assertEqual(self.notification.content, self.content)
        self.assertFalse(self.notification.read)


class TestNotificationContent(EryTestCase):
    def setUp(self):
        self.message = 'placeholder'
        self.content = NotificationContentFactory(message=self.message, priority=NotificationPriority['LOW'].value)

    def test_expected_attributes(self):
        self.assertEqual(self.content.message, self.message)
        self.assertEqual(self.content.date, dt.date.today())
        self.assertEqual(self.content.priority, NotificationPriority['LOW'].value)
