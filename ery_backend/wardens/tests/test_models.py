import datetime as dt

import pytz

from ery_backend.base.testcases import EryTestCase
from ery_backend.stints.factories import StintFactory
from ery_backend.users.factories import UserFactory

from ..factories import WardenFactory


class TestWarden(EryTestCase):
    def setUp(self):
        self.stint = StintFactory()
        self.now_time = dt.datetime.now(pytz.UTC)
        self.user = UserFactory()
        self.warden = WardenFactory(stint=self.stint, user=self.user, last_seen=self.now_time,)

    def test_exists(self):
        self.assertIsNotNone(self.warden)

    def test_expected_attributes(self):
        self.assertEqual(self.warden.stint, self.stint)
        self.assertEqual(self.warden.user, self.user)
        self.assertEqual(self.warden.last_seen, self.now_time)
