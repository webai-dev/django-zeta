from ery_backend.actions.factories import ActionFactory, ActionStepFactory
from ery_backend.actions.models import ActionStep
from ery_backend.base.testcases import EryTestCase, create_test_hands
from ery_backend.conditions.factories import ConditionFactory
from ery_backend.conditions.models import Condition
from ery_backend.variables.factories import VariableDefinitionFactory, HandVariableFactory
from ery_backend.variables.models import VariableDefinition


class TestHandPayment(EryTestCase):
    """
    Confirm hand recieves payment as expected from ledger.
    """

    def test_payment(self):
        hand = create_test_hands(n=1).first()
        # set payoff var for hand
        md = hand.current_module.stint_definition_module_definition.module_definition
        condition = ConditionFactory(
            module_definition=md,
            left_type=Condition.TYPE_CHOICES.expression,
            right_type=Condition.TYPE_CHOICES.expression,
            left_expression=1,
            right_expression=1,
        )
        action = ActionFactory(module_definition=md)
        ActionStepFactory(
            action=action,
            for_each=ActionStep.FOR_EACH_CHOICES.hand_in_stint,
            action_type=ActionStep.ACTION_TYPE_CHOICES.pay_users,
            condition=condition,
        )
        payoff_vd = VariableDefinitionFactory(
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            module_definition=md,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.float,
            validator=None,
            is_payoff=True,
        )
        payoff = HandVariableFactory(variable_definition=payoff_vd, value=5, hand=hand)
        # confirm user can recieve payoff from payoff var
        stint = hand.stint
        ss = stint.stint_specification
        ss.min_earnings = 1
        ss.max_earnings = 10
        ss.save()

        action.run(hand)
        # Test failure should be generated via error message from Ledger
        hand.refresh_from_db()
        self.assertEqual(hand.current_payoff, payoff.value)
