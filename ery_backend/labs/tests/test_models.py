from unittest import mock

from ery_backend.base.exceptions import EryValueError
from ery_backend.base.testcases import EryTestCase, create_test_stintdefinition, create_test_hands
from ery_backend.hands.factories import HandFactory
from ery_backend.frontends.models import Frontend
from ery_backend.stints.factories import StintFactory
from ery_backend.stints.models import Stint
from ery_backend.stint_specifications.factories import StintSpecificationFactory
from ery_backend.users.factories import UserFactory
from ..factories import LabFactory


class TestLab(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.comment_1 = 'Gee, Brain, you really think this will work? Pinky! It\'s ALIVE'
        cls.user = UserFactory()
        cls.frontend = Frontend.objects.get(name='Web')

    def setUp(self):
        self.current_stint = StintFactory()
        self.lab = LabFactory(name='PinkyBrain_episode_1', current_stint=self.current_stint, comment=self.comment_1)

    def test_exists(self):
        self.assertIsNotNone(self.lab)

    def test_expected_attributes(self):
        self.assertEqual(self.lab.current_stint, self.current_stint)
        self.assertEqual(self.lab.name, 'PinkyBrain_episode_1')
        self.assertEqual(self.lab.comment, self.comment_1)
        self.assertIsNotNone(self.lab.secret)

    def test_set_stint(self):
        """
        Confirm current_stint updated via StintSpecification.realize.
        """
        sd = create_test_stintdefinition(self.frontend)
        new_specification = StintSpecificationFactory(opt_in_code='Jeepers', stint_definition=sd)
        self.lab.set_stint(new_specification.id, self.user)
        # current_stint should be updated
        self.assertEqual(self.lab.current_stint.stint_specification, new_specification)
        # no hands should exist in current_stint
        self.assertEqual(self.lab.current_stint.hands.count(), 0)
        self.assertEqual(self.lab.current_stint.lab, self.lab)

    def test_start(self):
        """
        Confirms lab.start works as expected.
        """
        sd = create_test_stintdefinition(self.frontend)
        ss = StintSpecificationFactory(opt_in_code='I Want In', stint_definition=sd)

        self.lab.current_stint = None
        self.lab.save()
        self.assertIsNone(self.lab.current_stint)

        self.lab.set_stint(ss.id, self.user)
        self.lab.start(2, self.user, signal_pubsub=False)

        # start method should preallocate hands (as specified by hand_n) for stint
        self.assertEqual(self.lab.current_stint.hands.count(), 2)
        self.assertIsNotNone(self.lab.current_stint.hands.get(user__username=f'__lab__:{self.lab.secret}:1'))
        self.assertIsNotNone(self.lab.current_stint.hands.get(user__username=f'__lab__:{self.lab.secret}:2'))

        # started_by should be set on sint
        self.assertEqual(self.lab.current_stint.started_by, self.user)

    @mock.patch('ery_backend.hands.models.Hand.pay')
    def test_stop(self, mock_pay):
        """
        Confirms lab.stop works as expected.
        """
        self.assertIsNotNone(self.lab.current_stint)
        stint = self.lab.current_stint
        HandFactory(stint=stint, user=self.user)
        self.lab.stop(self.user)
        self.assertIsNone(self.lab.current_stint)
        self.assertEqual(stint.status, Stint.STATUS_CHOICES.cancelled)

    def test_change_no_cancel(self):
        """
        Confirms lab.change works as expected.
        """
        current_stint = self.lab.current_stint
        self.assertEqual(current_stint.status, None)
        stint_1 = StintFactory(lab=self.lab)
        self.lab.change(stint_1.id)
        # previous current should not be cancelled, as it was not running
        current_stint.refresh_from_db()
        self.assertEqual(current_stint.status, None)

        # new expected current stint
        self.assertEqual(self.lab.current_stint, stint_1)

    @mock.patch('ery_backend.hands.models.Hand.pay')
    def test_change_cancel(self, mock_pay):
        """
        Confirms lab.change works as expected.
        """
        stint_specification = create_test_hands(n=1, signal_pubsub=False).first().stint.stint_specification
        # changes status to running
        self.lab.set_stint(stint_specification.id, self.user)
        self.lab.start(1, self.user, signal_pubsub=False)
        starting_stint = self.lab.current_stint
        self.assertEqual(self.lab.current_stint.status, Stint.STATUS_CHOICES.running)
        stint_1 = StintFactory(lab=self.lab)
        self.lab.change(stint_1.id)
        # previous current_stint should be cancelled
        starting_stint.refresh_from_db()
        self.assertEqual(starting_stint.status, Stint.STATUS_CHOICES.cancelled)

        # new expected current stint
        self.assertEqual(self.lab.current_stint, stint_1)

    def test_expected_change_error(self):
        stint_1 = StintFactory()
        with self.assertRaises(EryValueError):
            self.lab.change(stint_1.id)
