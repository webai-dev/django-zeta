from unittest import mock

from reversion.models import Version
from test_plus.test import TestCase


from ery_backend.hands.factories import HandFactory
from ery_backend.modules.factories import ModuleDefinitionWidgetFactory
from ery_backend.stints.models import Stint
from ery_backend.users.factories import UserFactory
from ery_backend.widgets.factories import WidgetFactory

from ..testcases import create_revisions, EryTestCase
from ..utils import str_is_num, verified_revert, opt_out


class TestStrMethods(TestCase):
    def test_str_is_num(self):
        # letter
        is_num, num = str_is_num('a')
        self.assertFalse(is_num)
        self.assertIsNone(num)

        # int
        is_num, num = str_is_num('1')
        self.assertTrue(is_num)
        self.assertEqual(num, 1)

        # float
        is_num, num = str_is_num('1.2')
        self.assertTrue(is_num)
        self.assertEqual(num, 1.2)

    def test_str_method_errors(self):
        # non string values
        with self.assertRaises(ValueError):
            str_is_num(1)


class TestVerifiedRevert(EryTestCase):
    def setUp(self):
        self.module_definition_widget = ModuleDefinitionWidgetFactory()

    def test_verified_revert(self):
        """
        Confirm version.revert works if foreign keys of serialized data refer to existing objects
        """
        create_revisions([{'obj': self.module_definition_widget, 'attr': 'comment'}], revision_n=1)
        version = Version.objects.get_for_object(self.module_definition_widget).first()
        verified_revert(version)

    def test_verified_revert_errors(self):
        """
        Confirm non-existent foreign key reference returns error.
        """
        original_widget = self.module_definition_widget.widget
        # save a reference to original widget
        create_revisions([{'obj': self.module_definition_widget, 'attr': 'comment'}], revision_n=1)
        self.module_definition_widget.widget = WidgetFactory()
        original_widget.delete()
        original_widget = None
        version = Version.objects.get_for_object(self.module_definition_widget).first()
        with self.assertRaises(ValueError):
            verified_revert(version)


class TestOptOut(EryTestCase):
    """
    Confirm opt_out methods works as expected.
    """

    @mock.patch('ery_backend.hands.models.Hand.pay')
    def test_opt_out(self, mock_pay):
        """
        Confirm user can log out stint with opt-out code
        """
        hand = HandFactory(user=UserFactory())
        hand.stint.status = Stint.STATUS_CHOICES.running
        hand.stint.save()
        opt_out(hand)
        self.assertEqual(hand.stint.status, Stint.STATUS_CHOICES.cancelled)
