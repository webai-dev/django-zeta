import datetime as dt
from unittest import mock

import pytz

from ery_backend.base.testcases import EryTestCase
from ery_backend.hands.factories import HandFactory
from ery_backend.hands.models import Hand
from ery_backend.hands.utils import update_timeouts
from ery_backend.modules.factories import ModuleFactory
from ery_backend.stints.factories import StintFactory
from ery_backend.stints.models import Stint
from ery_backend.stint_specifications.factories import StintModuleSpecificationFactory
from ery_backend.users.factories import UserFactory


class TestUpdateTimeouts(EryTestCase):
    def setUp(self):
        self.stint = StintFactory(status=Stint.STATUS_CHOICES.running)
        self.stint_specification = self.stint.stint_specification
        self.current_module = ModuleFactory()
        self.hand = HandFactory(
            stint=self.stint,
            status=Hand.STATUS_CHOICES.active,
            last_seen=dt.datetime.now(pytz.UTC) - dt.timedelta(seconds=5),
            current_module=self.current_module,
            user=UserFactory(),
        )

    def test_update_timeouts_without_quit(self):
        # confirm active hand that has timed out in one running stint is caught and EXPOSED
        StintModuleSpecificationFactory(
            hand_timeout=5,
            stint_specification=self.stint_specification,
            module_definition=self.current_module.stint_definition_module_definition.module_definition,
            stop_on_quit=False,
        )
        update_timeouts()
        self.hand.refresh_from_db()
        self.assertEqual(self.hand.status, Hand.STATUS_CHOICES.timedout)
        # stint's status should not be changed
        self.assertEqual(self.stint.status, Stint.STATUS_CHOICES.running)

    @mock.patch('ery_backend.hands.models.Hand.pay')
    def test_update_timeouts_with_quit(self, mock_pay):
        # confirm active hand that has timed out in one running stint is caught and EXPOSED
        StintModuleSpecificationFactory(
            hand_timeout=5,
            stint_specification=self.stint_specification,
            module_definition=self.current_module.stint_definition_module_definition.module_definition,
            stop_on_quit=True,
        )
        update_timeouts()
        self.hand.refresh_from_db()
        self.assertEqual(self.hand.status, Hand.STATUS_CHOICES.timedout)
        # stint's status should be changed
        self.stint.refresh_from_db()
        self.assertEqual(self.stint.status, Stint.STATUS_CHOICES.cancelled)
