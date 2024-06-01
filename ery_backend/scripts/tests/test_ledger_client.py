from ery_backend.actions.factories import ActionFactory, ActionStepFactory
from ery_backend.actions.models import ActionStep
from ery_backend.base.testcases import EryTestCase, create_test_hands
from ery_backend.users.factories import UserFactory

from ..grpc.ledger_pb2 import Peer, Transferal, StintInfo, Payment
from ..ledger_client import _make_peer, _make_transferal, _make_stint_info, _make_payment


class TestLedgerClient(EryTestCase):
    def setUp(self):
        self.debitor = UserFactory(username='Grandad')
        self.creditor = UserFactory(username='APoodleNamedSlickback')
        self.hand = create_test_hands(n=1, signal_pubsub=False).first()
        self.stint = self.hand.stint
        action = ActionFactory(module_definition=self.hand.current_module.stint_definition_module_definition.module_definition)
        self.as_1 = ActionStepFactory(
            action=action,
            for_each=ActionStep.FOR_EACH_CHOICES.hand_in_stint,
            action_type=ActionStep.ACTION_TYPE_CHOICES.pay_users,
        )

    def test_make_peer(self):
        """
        Confirm debtors and creditors created correctly.
        """
        expected_debitor = Peer(id=self.debitor.id, name=self.debitor.username)
        expected_creditor = Peer(id=self.creditor.id, name=self.creditor.username)
        returned_debitor = _make_peer(self.debitor)  # pylint:disable=protected-access
        returned_creditor = _make_peer(self.creditor)  # pylint:disable=protected-access

        self.assertEqual(expected_debitor, returned_debitor)
        self.assertEqual(expected_creditor, returned_creditor)

    def test_make_transferal(self):
        """
        Confirm transferal created correctly.
        """
        # pylint:disable=protected-access
        expected_transferal = Transferal(
            creditor=_make_peer(self.creditor),
            debitor=_make_peer(self.debitor),
            amount=20,
            description=f"Payment for {self.stint}.",
        )
        # pylint:disable=protected-access
        returned_transferal = _make_transferal(amount=20, creditor=self.creditor, debitor=self.debitor, stint=self.stint)
        self.assertEqual(expected_transferal, returned_transferal)

    def test_make_stint_info(self):
        """
        Confirm StintInfo created correctly.
        """
        # Without action
        expected_stint_info = StintInfo(
            stint_id=self.stint.id,
            stint_specification_id=self.stint.stint_specification_id,
            module_id=self.hand.current_module.id,
            hand_id=self.hand.id,
        )
        returned_stint_info = _make_stint_info(self.hand)

        self.assertEqual(expected_stint_info, returned_stint_info)

        # With action
        expected_stint_info = StintInfo(
            stint_id=self.stint.id,
            stint_specification_id=self.stint.stint_specification.id,
            module_id=self.hand.current_module.id,
            action_id=self.as_1.action.id,
            action_step_id=self.as_1.id,
            hand_id=self.hand.id,
        )
        # pylint:disable=protected-access
        returned_stint_info = _make_stint_info(self.hand, self.as_1)

        self.assertEqual(expected_stint_info, returned_stint_info)

    def test_make_payment(self):
        """
        Confirm Payment created correctly.
        """
        # pylint:disable=protected-access
        transferal = _make_transferal(creditor=self.hand.user, debitor=self.stint.started_by, amount=20, stint=self.stint)

        stint_info = _make_stint_info(self.hand, self.as_1)  # pylint:disable=protected-access

        expected_payment = Payment(transfer=transferal, stint=stint_info, immediate_payment_method=Payment.PHONE_RECHARGE)

        # pylint:disable=protected-access
        returned_payment = _make_payment(amount=20, hand=self.hand, action_step=self.as_1)
        # XXX: Address in issue #508. Due to lack of enum options, this should be retested when more than just
        # XXX: PHONE_RECHARGE exists as an option.
        self.assertEqual(expected_payment, returned_payment)
