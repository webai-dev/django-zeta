from unittest import mock

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import Count

from ery_backend.base.cache import get_func_cache_key_for_hand, set_tagged
from ery_backend.base.testcases import EryTestCase, create_test_hands
from ery_backend.conditions.factories import ConditionFactory
from ery_backend.conditions.models import Condition
from ery_backend.hands.factories import HandFactory
from ery_backend.logs.models import Log
from ery_backend.modules.factories import ModuleDefinitionFactory, ModuleDefinitionProcedureFactory
from ery_backend.procedures.factories import ProcedureFactory
from ery_backend.procedures.utils import get_procedure_functions
from ery_backend.scripts.grpc.engine_pb2 import Result, Value
from ery_backend.stages.factories import StageDefinitionFactory
from ery_backend.stints.factories import StintFactory
from ery_backend.syncs.factories import EraFactory
from ery_backend.users.factories import UserFactory
from ery_backend.validators.factories import ValidatorFactory
from ery_backend.variables.factories import (
    VariableDefinitionFactory,
    HandVariableFactory,
    TeamVariableFactory,
    ModuleVariableFactory,
)
from ery_backend.variables.models import VariableDefinition

from ..models import ActionStep
from ..factories import ActionFactory, ActionStepFactory


class TestAction(EryTestCase):
    def setUp(self):
        self.module_definition = ModuleDefinitionFactory()
        self.action = ActionFactory(module_definition=self.module_definition)

    def test_exists(self):
        self.assertIsNotNone(self.action)

    def test_expected_attributes(self):
        self.assertEqual(self.action.module_definition, self.module_definition)

    def test_is_circular(self):
        """
        Tested in actionstep. Circularity always checked at actionstep level, as creation
        of an action cannot lead to circularity
        """

    def test_get_privilege_ancestor(self):
        self.assertEqual(self.action.get_privilege_ancestor(), self.module_definition)

    def test_get_privilege_ancestor_cls(self):
        self.assertEqual(self.action.get_privilege_ancestor_cls(), self.module_definition.__class__)

    def test_get_privilege_ancestor_filter_path(self):
        self.assertEqual(self.action.get_privilege_ancestor_filter_path(), 'module_definition')

    def test_simple_duplicate(self):
        action_2 = self.action.duplicate()
        self.assertNotEqual(self.action, action_2)
        self.assertEqual(f'{self.action.name}_copy', action_2.name)
        self.assertEqual(self.action.comment, action_2.comment)
        self.assertEqual(self.action.module_definition, action_2.module_definition)

    def test_duplicate(self):
        condition = ConditionFactory(
            module_definition=self.module_definition,
            left_type=Condition.TYPE_CHOICES.expression,
            right_type=Condition.TYPE_CHOICES.expression,
            left_expression=1,
            right_expression=1,
            relation=Condition.RELATION_CHOICES.equal,
        )
        subaction = ActionFactory(module_definition=self.module_definition)
        era = EraFactory(module_definition=self.module_definition)
        variable_definition = VariableDefinitionFactory(module_definition=self.module_definition)
        actionstep_1 = ActionStepFactory(
            action=self.action,
            action_type=ActionStep.ACTION_TYPE_CHOICES.log,
            subaction=None,
            era=None,
            variable_definition=None,
            condition=condition,
        )
        ActionStepFactory(
            action=self.action,
            action_type=ActionStep.ACTION_TYPE_CHOICES.run_code,
            subaction=None,
            era=None,
            variable_definition=None,
            condition=condition,
            code='00100',
        )
        ActionStepFactory(
            action=self.action,
            action_type=ActionStep.ACTION_TYPE_CHOICES.subaction,
            subaction=subaction,
            era=None,
            variable_definition=None,
            condition=condition,
        )
        ActionStepFactory(
            action=self.action,
            action_type=ActionStep.ACTION_TYPE_CHOICES.set_era,
            subaction=None,
            era=era,
            variable_definition=None,
            condition=condition,
        )
        ActionStepFactory(
            action=self.action,
            action_type=ActionStep.ACTION_TYPE_CHOICES.set_variable,
            subaction=None,
            era=None,
            variable_definition=variable_definition,
            condition=condition,
        )
        action_2 = self.action.duplicate()
        module_definition_2 = action_2.module_definition
        self.assertIsNotNone(action_2)
        self.assertEqual(action_2.name, '{}_copy'.format(self.action.name))
        # parents should be equal
        self.assertEqual(self.action.module_definition, module_definition_2)

        actionstep1_2 = ActionStep.objects.filter(
            action=action_2, condition=condition, log_message=actionstep_1.log_message
        ).first()
        self.assertIsNotNone(actionstep1_2)
        # children should not be equal
        self.assertNotIn(actionstep1_2, self.action.steps.all())
        actionstep2_2 = ActionStep.objects.filter(action=action_2, condition=condition, code='00100').first()
        self.assertIsNotNone(actionstep2_2)
        actionstep3_2 = ActionStep.objects.filter(action=action_2, condition=condition, subaction=subaction).first()
        self.assertIsNotNone(actionstep3_2)
        actionstep4_2 = ActionStep.objects.filter(action=action_2, condition=condition, era=era).first()
        self.assertIsNotNone(actionstep4_2)
        actionstep5_2 = ActionStep.objects.filter(
            action=action_2, condition=condition, variable_definition=variable_definition
        ).first()

        self.assertIsNotNone(actionstep5_2)

    @mock.patch('ery_backend.conditions.models.Condition.evaluate')
    @mock.patch('ery_backend.actions.models.ActionStep._interpret_value')
    def test_run(self, mock_interpret, mock_evaluate):
        """
        Run mutltiple action steps
            1) Logs a single message
            2) Sets a variable
            3) Sets an era
            4) Stage progression
        """
        mock_interpret.return_value = '4matchhere'
        stint = StintFactory()
        hand_1 = HandFactory(stint=stint, user=UserFactory())
        validator = ValidatorFactory(code=None, nullable=True)
        action = ActionFactory(module_definition=hand_1.current_module_definition)
        era = EraFactory(name='next_era', module_definition=hand_1.current_module_definition)
        variable_definition = VariableDefinitionFactory(
            module_definition=action.module_definition,
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            validator=validator,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.str,
        )
        hv_1 = HandVariableFactory(hand=hand_1, variable_definition=variable_definition, value='1matchhere')
        ActionStepFactory(
            action=action,
            action_type=ActionStep.ACTION_TYPE_CHOICES.log,
            subaction=None,
            era=None,
            variable_definition=None,
            order=1,
            log_message='test-log-executed',
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
        )
        ActionStepFactory(
            action=action,
            action_type=ActionStep.ACTION_TYPE_CHOICES.set_variable,
            subaction=None,
            era=None,
            variable_definition=variable_definition,
            order=2,
            for_each=ActionStep.FOR_EACH_CHOICES.hand_in_stint,
            value='4matchhere',
        )

        ActionStepFactory(
            action=action,
            action_type=ActionStep.ACTION_TYPE_CHOICES.set_era,
            subaction=None,
            era=era,
            variable_definition=None,
            order=3,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
        )

        mock_evaluate.return_value = True
        action.run(hand_1)
        self.assertEqual(hand_1.era, era)
        # check log created
        Log.objects.get(message='test-log-executed', log_type=Log.LOG_TYPE_CHOICES.info)

        # confirm no other log objects created
        self.assertEqual(Log.objects.count(), 1)

        # check variables saved correctly
        hv_1.refresh_from_db()
        self.assertEqual(hv_1.value, '4matchhere')

        # check era set correctly
        self.assertEqual(hand_1.era, era)


class TestActionStep(EryTestCase):
    def setUp(self):

        # creates two teams, with 1st two hands on 1st team
        hands = create_test_hands(n=3, team_size=2, signal_pubsub=False)
        self.hand_1 = hands.all()[0]
        self.hand_2 = hands.all()[1]
        self.hand_3 = hands.all()[2]
        self.module_definition = self.hand_1.current_module.stint_definition_module_definition.module_definition
        self.current_team = self.hand_1.current_team
        self.variable_definition = VariableDefinitionFactory(module_definition=self.module_definition, is_output_data=False)
        self.era = EraFactory(module_definition=self.module_definition)
        self.action = ActionFactory(module_definition=self.module_definition)
        self.subaction = ActionFactory(module_definition=self.module_definition)
        self.stage = StageDefinitionFactory(module_definition=self.module_definition)
        self.message = "A step in the right direction?"
        self.log_message = "Error Error. Fatal Internal Error."
        self.action_step = ActionStepFactory(
            action=self.action,
            invert_condition=True,
            for_each='hand_in_stint',
            action_type=ActionStep.ACTION_TYPE_CHOICES.log,
            value=self.message,
            code='1011001010101000101011',
            era=self.era,
            log_message=self.log_message,
            subaction=self.subaction,
            variable_definition=self.variable_definition,
        )

        circular_action = ActionFactory(module_definition=self.module_definition)
        self.circular_action_step_1 = ActionStepFactory(action_type=ActionStep.ACTION_TYPE_CHOICES.log, action=circular_action)
        self.circular_action_step_2 = ActionStepFactory(action_type=ActionStep.ACTION_TYPE_CHOICES.log, action=circular_action)
        self.circular_action_step_3 = ActionStepFactory(action_type=ActionStep.ACTION_TYPE_CHOICES.log, action=circular_action)
        self.circular_action_step_4 = ActionStepFactory(action_type=ActionStep.ACTION_TYPE_CHOICES.log, action=circular_action)
        self.circular_action_step_5 = ActionStepFactory(action_type=ActionStep.ACTION_TYPE_CHOICES.log, action=circular_action)
        self.circular_action_step_6 = ActionStepFactory(action_type=ActionStep.ACTION_TYPE_CHOICES.log, action=circular_action)

        self.base_action_step = ActionStepFactory(
            action=self.action, action_type=ActionStep.ACTION_TYPE_CHOICES.log, log_message=self.log_message
        )

    def test_exists(self):
        self.assertIsNotNone(self.action_step)

    def test_expected_attributes(self):
        self.assertEqual(self.action_step.action, self.action)
        self.assertTrue(self.action_step.invert_condition)
        self.assertEqual(self.action_step.for_each, 'hand_in_stint')
        self.assertEqual(self.action_step.action_type, 'log')
        self.assertEqual(self.action_step.value, self.message)
        self.assertEqual(self.action_step.code, '1011001010101000101011')
        self.assertEqual(self.action_step.era, self.era)
        self.assertEqual(self.action_step.log_message, self.log_message)
        self.assertEqual(self.action_step.subaction, self.subaction)
        self.assertEqual(self.action_step.variable_definition, self.variable_definition)

    def test_get_privilege_ancestor(self):
        self.assertEqual(self.action_step.get_privilege_ancestor(), self.action_step.action.module_definition)

    def test_get_privilege_ancestor_cls(self):
        self.assertEqual(self.action_step.get_privilege_ancestor_cls(), self.action_step.action.module_definition.__class__)

    def test_get_privilege_ancestor_filter_path(self):
        self.assertEqual(self.action_step.get_privilege_ancestor_filter_path(), 'action__module_definition')

    # XXX: Address in issue #813
    def test_validation_errors(self):
        with self.assertRaises(ValidationError):
            ActionStepFactory(action_type=ActionStep.ACTION_TYPE_CHOICES.run_code, code=None)
        # with self.assertRaises(ValidationError):
        #     ActionStepFactory(action_type=ActionStep.ACTION_TYPE_CHOICES.set_era, era=None)
        with self.assertRaises(ValidationError):
            ActionStepFactory(action_type=ActionStep.ACTION_TYPE_CHOICES.log, log_message=None)
        # with self.assertRaises(ValidationError):
        #     ActionStepFactory(action_type=ActionStep.ACTION_TYPE_CHOICES.subaction, subaction=None)
        # with self.assertRaises(ValidationError):
        #     ActionStepFactory(action_type=ActionStep.ACTION_TYPE_CHOICES.set_variable, variable_definition=None)
        # with self.assertRaises(ValidationError):
        #     ActionStepFactory(action_type=ActionStep.ACTION_TYPE_CHOICES.set_variable, value=None)

    @mock.patch('ery_backend.conditions.models.Condition.evaluate', autospec=True)
    def test_condition_required(self, mock_evaluate):  # pylint: disable=no-self-use
        """
        Confirm action_step runs condition.evaluate when condition is not None.
        """
        hand = create_test_hands(n=1, signal_pubsub=False).first()
        module_definition = hand.current_module.stint_definition_module_definition.module_definition
        condition = ConditionFactory(module_definition=module_definition)
        action = ActionFactory(module_definition=module_definition)
        as_1 = ActionStepFactory(
            action=action,
            condition=condition,
            action_type=ActionStep.ACTION_TYPE_CHOICES.log,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
        )
        as_1.run(hand)
        mock_evaluate.assert_called_with(condition, hand, None)

    # XXX: Address in issue #677
    # def test_circularity(self):
    #     module_definition_1 = ModuleDefinitionFactory()
    #     action_c0 = ActionFactory(module_definition=module_definition_1, name='action_c0')
    #     action_c1 = ActionFactory(module_definition=module_definition_1, name='action_c1')
    #     action_c2 = ActionFactory(module_definition=module_definition_1, name='action_c2')
    #     action_d0 = ActionFactory(module_definition=module_definition_1, name='action_d0')

    #     # same action/subaction
    #     with self.assertRaises(ValidationError):
    #         ActionStepFactory(action=action_c0, subaction=action_c0)

    #     # while ActionStep.save() should execute in the same way as ActionStepFactory(), the latter is not picked up
    #     # in coverage. The first is thus implemented here, where:
    #     # Actionstep(AS) is declared which has a subaction with AS containing subaction with (AS) that leads to circularity
    #     ActionStepFactory(action=action_c0, subaction=action_c1)
    #     ActionStepFactory(action=action_c1, subaction=action_c2)

    #     test_actionstep2 = ActionStep(action=action_c2, subaction=action_c0,
    #                                   condition=ConditionFactory(left_type=Condition.TYPE_CHOICES.expression,
    #                                                              right_type=Condition.TYPE_CHOICES.expression,
    #                                                              left_expression=1, right_expression=1,
    #                                                              relation=Condition.RELATION_CHOICES.equal,
    #                                                              module_definition=self.module_definition))
    #     with self.assertRaises(ValidationError):
    #         test_actionstep2.save()

    #     # links two branches, but not cyclically, since c2 does not have Actionstep leading back to d branch
    #     ActionStepFactory(action=action_d0, subaction=action_c0)

    #     # link c2 to d0, causing a circle
    #     with self.assertRaises(ValidationError):
    #         ActionStepFactory(action=action_c2, subaction=action_d0)

    #     # linking top of branch to middle and end, and end to middle, but not middle to end should not trigger
    #     # _is_circular
    #     action_e0 = ActionFactory(module_definition=module_definition_1, name='action_e0')
    #     action_e1 = ActionFactory(module_definition=module_definition_1, name='action_e1')
    #     action_e2 = ActionFactory(module_definition=module_definition_1, name='action_e2')
    #     ActionStepFactory(action=action_e0, subaction=action_e1)
    #     ActionStepFactory(action=action_e0, subaction=action_e2)
    #     ActionStepFactory(action=action_e2, subaction=action_e1)

    def test_ordering(self):
        action = ActionFactory(module_definition=self.module_definition)
        action_step4 = ActionStepFactory(action=action, action_type="set_variable", order=4)
        action_step1 = ActionStepFactory(action=action, action_type="set_variable", order=1)
        action_step2 = ActionStepFactory(action=action, action_type="set_variable", order=2)
        action_steps = ActionStep.objects.filter(action=action)
        self.assertEqual(len(action_steps), 3)
        self.assertEqual(action_steps[0], action_step1)
        self.assertEqual(action_steps[1], action_step2)
        self.assertEqual(action_steps[2], action_step4)

    @mock.patch('ery_backend.conditions.models.Condition.evaluate')
    def test_era_synchronization(self, mock_evaluate):
        """
        Confirm changing eras for two hand of the same team with a size of 2 triggers team
        era change.
        """
        mock_evaluate.return_value = True
        team = self.hand_1.current_team
        era_1 = EraFactory(module_definition=self.module_definition)
        # hand era change triggers team era change
        action = ActionFactory(module_definition=self.module_definition)
        ActionStepFactory(
            action=action,
            action_type=ActionStep.ACTION_TYPE_CHOICES.set_era,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
            era=era_1,
        )
        action.run(self.hand_1)
        self.hand_1.refresh_from_db()  # Get typecasted expressions
        team.refresh_from_db()
        self.assertEqual(self.hand_1.era, era_1)
        self.assertNotEqual(team.era, era_1)
        # hand_3 era change shouldn't change team era, due to separate team.
        action.run(self.hand_3)
        self.hand_3.refresh_from_db()
        team.refresh_from_db()
        self.assertEqual(self.hand_3.era, era_1)
        self.assertNotEqual(team.era, era_1)
        action.run(self.hand_2)
        self.hand_2.refresh_from_db()
        team.refresh_from_db()
        self.assertEqual(self.hand_2.era, era_1)
        self.assertEqual(team.era, era_1)

    @mock.patch('ery_backend.conditions.models.Condition.evaluate')
    @mock.patch('ery_backend.scripts.ledger_client.send_payment')
    def test_pay_users(self, mock_payment, mock_evaluate):
        """
        Confirm ledger_client.send_payment called through actionstep execution.
        """
        mock_evaluate.return_value = True

        # delete extra hands
        self.hand_1.stint.hands.exclude(id=self.hand_1.id).all().delete()
        ss = self.hand_1.stint.stint_specification
        ss.min_earnings = None
        ss.max_earnings = None
        ss.save()
        action = ActionFactory(module_definition=self.module_definition)
        pay_vd = VariableDefinitionFactory(
            module_definition=self.module_definition,
            is_payoff=True,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.float,
            scope=VariableDefinition.SCOPE_CHOICES.hand,
        )
        HandVariableFactory(hand=self.hand_1, variable_definition=pay_vd, value=5)
        as_1 = ActionStepFactory(
            action=action,
            action_type=ActionStep.ACTION_TYPE_CHOICES.pay_users,
            for_each=ActionStep.FOR_EACH_CHOICES.hand_in_stint,
        )
        expected_payoff = self.hand_1.get_payoff()
        action.run(self.hand_1)
        mock_payment.assert_called_with(expected_payoff, self.hand_1, as_1)

    def test_pay_users_errors(self):
        action = ActionFactory(module_definition=self.module_definition)
        # confirm errors triggered on incorrect scope
        with self.assertRaises(ValidationError):
            ActionStepFactory(
                action=action,
                action_type=ActionStep.ACTION_TYPE_CHOICES.pay_users,
                for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
            )


class TestActionStepRun(EryTestCase):
    def setUp(self):
        hands = create_test_hands(n=3, team_size=2, signal_pubsub=False).annotate(team_size=Count('current_team__hands'))
        self.hand = hands.filter(team_size=2).first()
        self.action = ActionFactory(module_definition=self.hand.stage.stage_definition.module_definition)

    def test_log(self):
        # log creation (also tests for_each implementation)
        as1 = ActionStepFactory(
            action=self.action,
            action_type=ActionStep.ACTION_TYPE_CHOICES.log,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
        )
        as1.run(self.hand)

        # 1 current hand
        self.assertEqual(Log.objects.filter(stint=self.hand.stint, log_type=Log.LOG_TYPE_CHOICES.info).count(), 1)

        Log.objects.all().delete()
        as1.for_each = ActionStep.FOR_EACH_CHOICES.hand_in_team
        as1.run(self.hand)

        # 2 hands linked to current team
        self.assertEqual(Log.objects.filter(stint=self.hand.stint, log_type=Log.LOG_TYPE_CHOICES.info).count(), 2)

        Log.objects.all().delete()
        as1.for_each = ActionStep.FOR_EACH_CHOICES.hand_in_stint
        as1.run(self.hand)
        # 3 hands linked to stint
        self.assertEqual(Log.objects.filter(stint=self.hand.stint, log_type=Log.LOG_TYPE_CHOICES.info).count(), 3)

        Log.objects.all().delete()
        as1.for_each = ActionStep.FOR_EACH_CHOICES.team_in_stint
        as1.run(self.hand)
        # 1 team linked to stint
        self.assertEqual(Log.objects.filter(stint=self.hand.stint, log_type=Log.LOG_TYPE_CHOICES.info).count(), 2)

    def test_set_era(self):
        era = EraFactory(module_definition=self.hand.stage.stage_definition.module_definition)
        as1 = ActionStepFactory(
            action=self.action,
            action_type=ActionStep.ACTION_TYPE_CHOICES.set_era,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
            era=era,
        )
        # confirm set_era works
        self.assertNotEqual(self.hand.era, era)
        as1.run(self.hand)
        self.assertEqual(self.hand.era, era)

    @mock.patch('ery_backend.actions.models.ActionStep._interpret_value')
    def test_subaction(self, mock_interpret):
        """
        Notes:
            * set_variable tested elsewhere
        """
        mock_interpret.return_value = 45

        # confirm subaction works
        # 2 different subactions used to set era and stage, executed as subactions in 3rd and 4th generation of action1.run
        module_definition = self.hand.stage.stage_definition.module_definition
        dual_action_1 = ActionFactory(module_definition=module_definition)
        dual_action_2 = ActionFactory(module_definition=module_definition)
        dual_action_3 = ActionFactory(module_definition=module_definition)
        dual_action_4 = ActionFactory(module_definition=module_definition)
        ActionStepFactory(
            action=dual_action_1,
            action_type=ActionStep.ACTION_TYPE_CHOICES.subaction,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
            subaction=dual_action_3,
        )
        ActionStepFactory(
            action=dual_action_2,
            action_type=ActionStep.ACTION_TYPE_CHOICES.subaction,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
            subaction=dual_action_3,
        )
        era = EraFactory(module_definition=module_definition)
        ActionStepFactory(
            action=dual_action_3,
            action_type=ActionStep.ACTION_TYPE_CHOICES.set_era,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
            era=era,
        )
        ActionStepFactory(
            action=dual_action_3,
            action_type=ActionStep.ACTION_TYPE_CHOICES.subaction,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
            subaction=dual_action_4,
        )
        ActionStepFactory(
            action=dual_action_4,
            action_type=ActionStep.ACTION_TYPE_CHOICES.log,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
            log_message='Such and such',
        )
        dual_action_1.run(hand=self.hand)
        self.assertEqual(self.hand.era, era)


# XXX: Address in issue #538
# class TestQuit(EryTestCase):
#     def setUp(self):
#         self.hand = create_test_hands(n=1).first()
#         md = self.hand.current_module.stint_definition_module_definition.module_definition
#         self.action = ActionFactory(module_definition=md)

#     def test_default_generation(self):
#         md = ModuleDefinitionFactory()
#         self.assertTrue(md.command_set.filter(name='quit').exists())
#         self.assertIsNotNone(get_command('qUit', md))

#     @mock.patch('ery_backend.hands.models.Hand.pay')
#     def test_quit(self, mock_pay):
#         """
#         Confirm user can opt out.
#         """
#         as_1 = ActionStepFactory(action=self.action, action_type=ActionStep.ACTION_TYPE_CHOICES.quit,
#                                  for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only)
#         as_1.run(self.hand)
#         self.assertEqual(self.hand.status, Hand.STATUS_CHOICES.quit)
#         self.assertEqual(self.hand.stint.status, Stint.STATUS_CHOICES.cancelled)

#     def test_quit_error(self):
#         """
#         Confirm quit can only be used for current hand.
#         """
#         with self.assertRaises(ValidationError):
#             ActionStepFactory(action=self.action, action_type=ActionStep.ACTION_TYPE_CHOICES.quit,
#                               for_each=ActionStep.FOR_EACH_CHOICES.hand_in_stint)


class TestGetToSave(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        hand = create_test_hands().first()
        cls.module_definition = hand.current_module.module_definition
        cls.stint = hand.stint

    def test_get_to_save_when_specified(self):
        """
        When to_save is specified, get_to_save should return it
        """
        vd = VariableDefinitionFactory(module_definition=self.module_definition)
        action = ActionFactory(module_definition=self.module_definition)
        action_step = ActionStepFactory(to_save=[vd], action=action)
        self.assertEqual(action_step.get_to_save(self.stint).all()[0], vd)

    def test_get_to_save_unspecified(self):
        """
        When to_save is None, get_to_save should return VariableDefinitions
        filtered with is_output_data=True
        """

        action = ActionFactory(module_definition=self.module_definition)

        vds = [
            VariableDefinitionFactory(is_output_data=False, module_definition=action.module_definition),
            VariableDefinitionFactory(is_output_data=True, module_definition=action.module_definition),
        ]

        action_step = ActionStepFactory(to_save=None, action=action)
        got = list(action_step.get_to_save(self.stint))
        self.assertEqual(got[0].pk, vds[1].pk)


class TestActionStepEngine(EryTestCase):
    """
    Confirm processes that call EryEngine send calls and set values as expected.
    """

    def setUp(self):
        self.hand = create_test_hands(n=1, signal_pubsub=False).first()
        self.module_definition = self.hand.current_module.stint_definition_module_definition.module_definition

        preset_vd = VariableDefinitionFactory(
            name='presetvar',
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.int,
            is_output_data=False,
            module_definition=self.module_definition,
        )

        test_vd = VariableDefinitionFactory(
            name='testvar',
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.int,
            is_output_data=False,
            module_definition=self.module_definition,
        )
        self.preset_var = HandVariableFactory(hand=self.hand, variable_definition=preset_vd, value=5)
        self.action = ActionFactory(module_definition=self.module_definition)
        self.action_step = ActionStepFactory(
            action=self.action,
            order=0,
            action_type=ActionStep.ACTION_TYPE_CHOICES.set_variable,
            value='presetvar * 45',
            variable_definition=test_vd,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
        )
        self.handvar = HandVariableFactory(hand=self.hand, variable_definition=test_vd, value=None)

    @mock.patch('ery_backend.scripts.engine_client._run_javascript_op')
    @mock.patch('ery_backend.scripts.engine_client.make_javascript_op')
    def test_interpret_value(self, mock_op, mock_engine):
        """
        Confirm EryEngine receives expected parameters during interpretation of VariableDefinition value.
        """
        mock_engine.return_value = Result(value=Value(number_value=self.preset_var.value * 45))
        interpreted_value = self.action_step._interpret_value(self.hand)  # pylint:disable=protected-access
        mock_op.assert_called_with(str(self.action_step), 'presetvar * 45', self.hand, self.hand.stint.get_context(self.hand))
        self.assertEqual(interpreted_value, self.preset_var.value * 45)

    @mock.patch('ery_backend.scripts.engine_client._run_javascript_op')
    def test_interpret_value_caching(self, mock_engine):
        """
        Confirm EryEngine receives expected parameters during interpretation of VariableDefinition value.
        """
        mock_engine.return_value = Result(value=Value(string_value='fake value'))
        cache_key = get_func_cache_key_for_hand(self.action_step.value, self.hand)
        # confirm key is created and stored in cache
        self.action_step._interpret_value(self.hand)  # pylint:disable=protected-access
        self.assertEqual(cache.get(cache_key), Result(value=Value(string_value='fake value')).SerializeToString())

    @mock.patch('ery_backend.scripts.engine_client._run_javascript_op')
    def test_interpret_value_cache_use(self, mock_engine):
        mock_engine.return_value = Result(value=Value(string_value='fake value'))
        cache_key = get_func_cache_key_for_hand(self.action_step.value, self.hand)
        # manually cache result
        set_tagged(cache_key, Result(value=Value(string_value='fake value')).SerializeToString(), [])
        # Fails if a call is actually made to engine
        self.assertEqual(self.action_step._interpret_value(self.hand), 'fake value')  # pylint:disable=protected-access

    @mock.patch('ery_backend.scripts.engine_client._run_javascript_op')
    @mock.patch('ery_backend.scripts.engine_client.make_javascript_op')
    def test_save_variable(self, mock_op, mock_engine):
        """
        Confirm variable value is set to interpreted variable definition value (based on hand context).
        """
        set_var_definition = self.handvar.variable_definition

        mock_engine.return_value = Result(value=Value(number_value=45))
        self.action_step.run(self.hand)
        self.handvar.refresh_from_db()
        self.assertEqual(self.handvar.value, 45)

        # team wide
        set_var_definition.scope = VariableDefinition.SCOPE_CHOICES.team
        teamvar = TeamVariableFactory(team=self.hand.current_team, variable_definition=set_var_definition, value=None)
        self.action_step.run(self.hand)
        teamvar.refresh_from_db()
        self.assertEqual(teamvar.value, 45)
        # module wide
        set_var_definition.scope = VariableDefinition.SCOPE_CHOICES.module
        modulevar = ModuleVariableFactory(module=self.hand.current_module, variable_definition=set_var_definition, value=None)
        self.action_step.run(self.hand)
        modulevar.refresh_from_db()
        self.assertEqual(modulevar.value, 45)

    @mock.patch('ery_backend.scripts.engine_client.evaluate')
    def test_run(self, mock_eval):
        """
        Confirm engine is called for AS of action_type=run_code
        """
        code_actionstep = ActionStepFactory(
            action=self.action,
            order=1,
            action_type=ActionStep.ACTION_TYPE_CHOICES.run_code,
            value='presetvar * 45',
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
        )
        code_actionstep.run(self.hand)
        mock_eval.assert_called_with(f'run_code_on_{self.hand}', self.hand, code_actionstep.code)


class TestProcedureIntegration(EryTestCase):
    """
    Confirm procedures are prefixed into code intended or actionstep execution.
    """

    def setUp(self):
        self.hand = create_test_hands(n=1, signal_pubsub=False).first()
        self.md = self.hand.current_module.stint_definition_module_definition.module_definition
        set_random_stage = ProcedureFactory(name='set_random_stage', code='return Math.floor(Math.random()* stages.length);')
        ModuleDefinitionProcedureFactory(name='set_random_stage', procedure=set_random_stage, module_definition=self.md)

        stages_index = VariableDefinitionFactory(
            module_definition=self.md,
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.int,
            validator=None,
        )
        HandVariableFactory(hand=self.hand, variable_definition=stages_index, value=42)
        self.as_1 = ActionStepFactory(
            action__module_definition=self.md,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
            action_type=ActionStep.ACTION_TYPE_CHOICES.set_variable,
            variable_definition=stages_index,
            value='set_random_stage()',
        )

    @mock.patch('ery_backend.scripts.engine_client._run_javascript_op')
    @mock.patch('ery_backend.scripts.engine_client.make_javascript_op')
    def test_function_in_setvar(self, mock_make, mock_run):
        mock_run.return_value = Result(value=Value(number_value=42))
        self.as_1.run(self.hand)
        mock_make.assert_called_with(
            str(self.as_1),
            f"{get_procedure_functions(self.md, 'engine')}\n{self.as_1.value}",
            self.hand,
            self.hand.stint.get_context(self.hand),
        )
