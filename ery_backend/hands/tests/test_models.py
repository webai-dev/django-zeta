import datetime as dt
from unittest import mock
import unittest

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

import pytz

from ery_backend.actions.factories import ActionFactory, ActionStepFactory
from ery_backend.actions.models import ActionStep
from ery_backend.base.testcases import EryTestCase, create_test_hands
from ery_backend.base.utils import get_default_language
from ery_backend.frontends.models import Frontend
from ery_backend.hands.models import Hand
from ery_backend.logs.models import Log
from ery_backend.modules.factories import ModuleDefinitionFactory, ModuleFactory
from ery_backend.modules.models import Module
from ery_backend.robots.factories import RobotFactory
from ery_backend.syncs.factories import EraFactory
from ery_backend.stages.factories import StageFactory, StageDefinitionFactory, StageBreadcrumbFactory
from ery_backend.stages.models import StageBreadcrumb, StageDefinition
from ery_backend.stints.factories import StintFactory
from ery_backend.stints.models import StintDefinitionModuleDefinition, Stint
from ery_backend.stint_specifications.factories import StintModuleSpecificationFactory
from ery_backend.teams.factories import TeamFactory, TeamHandFactory
from ery_backend.users.factories import UserFactory
from ery_backend.variables.factories import VariableDefinitionFactory, HandVariableFactory
from ery_backend.variables.models import VariableDefinition

from ..factories import HandFactory


class TestHand(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.user = UserFactory()
        cls.robot = RobotFactory()
        cls.era = EraFactory()
        cls.stint = StintFactory()
        module_definition = ModuleDefinitionFactory()
        sdmd = StintDefinitionModuleDefinition.objects.create(
            stint_definition=cls.stint.stint_specification.stint_definition, module_definition=module_definition
        )
        cls.current_module = ModuleFactory(stint=cls.stint, stint_definition_module_definition=sdmd)
        cls.stage = StageFactory()
        cls.now_time = dt.datetime.now(pytz.utc)
        cls.current_team = TeamFactory()
        # allows checking all expected attributes without validation error
        cls.hand_2 = HandFactory(user=None, robot=None)
        TeamHandFactory(team=cls.current_team, hand=cls.hand_2)
        cls.web = Frontend.objects.get(name='Web')
        cls.language = get_default_language()

    def setUp(self):
        self.hand = HandFactory(
            user=self.user,
            robot=None,
            era=self.era,
            stage=self.stage,
            last_seen=self.now_time,
            stint=self.stint,
            current_module=self.current_module,
            status=Hand.STATUS_CHOICES.active,
            current_payoff=21,
            current_team=self.current_team,
        )
        TeamHandFactory(team=self.current_team, hand=self.hand)
        self.current_breadcrumb = StageBreadcrumbFactory(hand=self.hand, stage=self.stage)

    def test_exists(self):
        self.assertIsNotNone(self.hand)

    def test_expected_attributes(self):
        self.hand.current_breadcrumb = self.current_breadcrumb
        self.hand.save()
        self.hand.refresh_from_db()

        self.assertTrue(self.hand.user)
        self.assertFalse(self.hand_2.user)
        self.assertEqual(self.hand.user, self.user)
        self.assertEqual(self.hand.era, self.era)
        self.assertEqual(self.hand.stage, self.stage)
        self.assertEqual(self.hand.last_seen, self.now_time)
        self.assertEqual(self.hand.stint, self.stint)
        self.assertEqual(self.hand.current_team, self.current_team)
        self.assertEqual(self.hand.current_module, self.current_module)
        self.assertEqual(self.hand.status, Hand.STATUS_CHOICES.active)
        self.assertEqual(self.hand.current_payoff, 21)
        self.assertEqual(self.hand.current_breadcrumb, self.current_breadcrumb)
        self.assertEqual(self.hand.frontend, self.web)
        self.assertEqual(self.hand.language, self.language)

    def test_unique_together(self):
        with self.assertRaises(IntegrityError):
            HandFactory(user=self.user, stint=self.stint)

    def test_validation_errors(self):
        # User and robot
        with self.assertRaises(ValidationError):
            HandFactory(user=self.user, robot=self.robot)

    def test_set_era(self):
        era = EraFactory()
        self.assertNotEqual(self.hand.era, era)
        self.hand.set_era(era)
        self.assertEqual(self.hand.era, era)
        # Log should not be created
        self.assertEqual(Log.objects.count(), 0)

    def test_set_stage(self):
        """
        Confirm stage set correctly based on Stage and StageDefinition.
        """
        stage = StageFactory(stage_definition=StageDefinitionFactory(module_definition=self.hand.current_module_definition))
        self.assertNotEqual(self.hand.stage, stage)
        self.hand.set_stage(stage)
        self.assertEqual(self.hand.stage, stage)
        # Log should not be created
        self.assertEqual(Log.objects.count(), 0)

    def test_preaction_on_set_stage(self):
        """
        Confirm preaction is executed on render if preaction_started is false
        """
        message = "By Gorge it worked!"
        hand = create_test_hands(n=1, signal_pubsub=False).first()
        initial_stage = hand.stage
        initial_crumb = hand.current_breadcrumb
        md = hand.current_module_definition
        pre_action = ActionFactory(module_definition=md)
        stage_definition = StageDefinitionFactory(
            module_definition=md, pre_action=pre_action, breadcrumb_type=StageDefinition.BREADCRUMB_TYPE_CHOICES.all
        )
        ActionStepFactory(
            action=pre_action,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
            action_type=ActionStep.ACTION_TYPE_CHOICES.log,
            log_message=message,
        )
        hand.set_stage(stage_definition=stage_definition)
        hand.refresh_from_db()
        new_stage = hand.stage
        new_crumb = hand.create_breadcrumb(new_stage)
        hand.set_breadcrumb(new_crumb)
        hand.refresh_from_db()
        self.assertEqual(len(list(Log.objects.filter(message=message).all())), 1)

        # 2nd execution should not trigger preaction
        hand.set_stage(initial_stage)
        hand.set_breadcrumb(initial_crumb)
        hand.set_stage(new_stage)
        hand.set_breadcrumb(new_crumb)
        self.assertEqual(len(list(Log.objects.filter(message=message).all())), 1)

    def test_log(self):
        # Verify creation of a non-system log
        message = 'This is a test log'
        log_type = Log.LOG_TYPE_CHOICES.warning
        self.hand.log(message=message, log_type=Log.LOG_TYPE_CHOICES.warning, system_only=False)
        self.assertTrue(
            Log.objects.filter(
                message=message,
                log_type=log_type,
                stint=self.hand.stint,
                team=self.hand.current_team,
                module=self.hand.current_module,
                hand=self.hand,
            ).exists()
        )

        # Verify system log is not created as Log object
        message = 'This is a system test log'
        self.hand.log(message=message, log_type=Log.LOG_TYPE_CHOICES.warning, system_only=True)
        self.assertFalse(
            Log.objects.filter(
                message=message,
                log_type=log_type,
                stint=self.hand.stint,
                team=self.hand.current_team,
                module=self.hand.current_module,
                hand=self.hand,
            ).exists()
        )


class TestSetStatus(EryTestCase):
    def setUp(self):
        self.hands = create_test_hands(n=3, signal_pubsub=False)

    @unittest.skip("Restore in issue #477")
    @mock.patch('ery_backend.hands.models.Hand.pay')
    def test_general_set_status(self, mock_pay):
        """
        Confirm status cannot be set to arbitary values.
        """
        # should not work for arbitrary status choices
        hand = self.hands.first()
        with self.assertRaises(ValueError):
            hand.set_status('pickled')

        hand.set_status(Hand.STATUS_CHOICES.finished)
        hand.refresh_from_db()
        self.assertEqual(hand.status, Hand.STATUS_CHOICES.finished)

    @unittest.skip("Restore in issue #477")
    @mock.patch('ery_backend.hands.models.Hand.pay')
    def test_hands_continuation_finish_all(self, mock_pay):
        """
        Confirm stint finished when all hands are finished.
        """
        hand_1, hand_2, hand_3 = self.hands.all()
        hand_1.set_status(Hand.STATUS_CHOICES.finished)
        hand_2.set_status(Hand.STATUS_CHOICES.finished)
        self.assertEqual(hand_3.stint.status, Stint.STATUS_CHOICES.running)
        # if hand is finishing a stint that all other hands have finished, set status to finished
        hand_3.set_status(Hand.STATUS_CHOICES.finished)
        self.assertEqual(hand_3.stint.status, Stint.STATUS_CHOICES.finished)

    @mock.patch('ery_backend.hands.models.Hand.pay')
    def test_hands_continuation_finish_one(self, mock_pay):
        """
        Confirm stint cancelled when one hand has finished, another is unable to finish, and no others can
        proceed.
        """
        hand_1, hand_2, hand_3 = self.hands.all()
        hand_1.set_status(Hand.STATUS_CHOICES.timedout)
        hand_2.set_status(Hand.STATUS_CHOICES.finished)
        # stint should be cancelled
        hand_3.set_status(Hand.STATUS_CHOICES.finished)
        self.assertEqual(hand_3.stint.status, Stint.STATUS_CHOICES.cancelled)

    @mock.patch('ery_backend.hands.models.Hand.pay')
    def test_hands_continuation_quit(self, mock_pay):
        """
        Confirm stint cancelled when one hand quits and no others can proceed.
        """
        hand_1, hand_2, hand_3 = self.hands.all()
        hand_1.set_status(Hand.STATUS_CHOICES.finished)
        hand_2.set_status(Hand.STATUS_CHOICES.finished)
        # stint should be cancelled
        hand_3.set_status(Hand.STATUS_CHOICES.quit)
        self.assertEqual(hand_3.stint.status, Stint.STATUS_CHOICES.cancelled)

    @mock.patch('ery_backend.hands.models.Hand.pay')
    def test_hands_continuation_cancelled(self, mock_pay):
        """
        Confirm stint cancelled when one hand is cancelled and no others can proceed.
        """
        hand_1, hand_2, hand_3 = self.hands.all()
        hand_1.set_status(Hand.STATUS_CHOICES.finished)
        hand_2.set_status(Hand.STATUS_CHOICES.finished)
        # stint should be cancelled
        hand_3.set_status(Hand.STATUS_CHOICES.cancelled)
        self.assertEqual(hand_3.stint.status, Stint.STATUS_CHOICES.cancelled)

    @mock.patch('ery_backend.hands.models.Hand.pay')
    def test_hands_continuation_timedout(self, mock_pay):
        """
        Confirm stint cancelled when one hand times out and no others can proceed.
        """
        hand_1, hand_2, hand_3 = self.hands.all()
        hand_1.set_status(Hand.STATUS_CHOICES.finished)
        hand_2.set_status(Hand.STATUS_CHOICES.finished)
        # stint should be cancelled
        hand_3.set_status(Hand.STATUS_CHOICES.timedout)
        self.assertEqual(hand_3.stint.status, Stint.STATUS_CHOICES.cancelled)

    def test_log(self):
        # Verify creation of a non-system log
        hand = self.hands.first()
        message = 'This is a test log'
        log_type = Log.LOG_TYPE_CHOICES.warning
        hand.log(message=message, log_type=Log.LOG_TYPE_CHOICES.warning, system_only=False)
        self.assertTrue(
            Log.objects.filter(
                message=message,
                log_type=log_type,
                stint=hand.stint,
                team=hand.current_team,
                module=hand.current_module,
                hand=hand,
            ).exists()
        )

        # Verify system log is not created as Log object
        message = 'This is a system test log'
        hand.log(message=message, log_type=Log.LOG_TYPE_CHOICES.warning, system_only=True)
        self.assertFalse(
            Log.objects.filter(
                message=message,
                log_type=log_type,
                stint=hand.stint,
                team=hand.current_team,
                module=hand.current_module,
                hand=hand,
            ).exists()
        )


@unittest.skip("Restore in issue #477")
class TestEndStageBehavior(EryTestCase):
    def setUp(self):
        self.hands = list(create_test_hands(n=2, signal_pubsub=False).all())
        self.md = self.hands[0].current_module.stint_definition_module_definition.module_definition

    @mock.patch('ery_backend.conditions.models.Condition.evaluate')
    @mock.patch('ery_backend.hands.models.Hand.pay')
    def test_end_stage(self, mock_pay, mock_evaluate):
        """
        End stage should update status if no next module.
        """
        mock_evaluate.return_value = True
        stage_def = StageDefinitionFactory(module_definition=self.md, end_stage=True)
        action = ActionFactory(module_definition=self.md)
        ActionStepFactory(
            action=action,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
            action_type=ActionStep.ACTION_TYPE_CHOICES.go_to_stage,
            next_stage=stage_def,
        )
        action.run(self.hands[0])
        self.hands[0].refresh_from_db()
        self.assertEqual(self.hands[0].status, Hand.STATUS_CHOICES.finished)

        stint = self.hands[0].stint
        self.assertEqual(stint.status, Stint.STATUS_CHOICES.running)

        action.run(self.hands[1])
        self.hands[1].refresh_from_db()
        self.assertEqual(self.hands[1].status, Hand.STATUS_CHOICES.finished)

        stint.refresh_from_db()
        # if hand is last, should change stint status
        stint.refresh_from_db()
        self.assertEqual(stint.status, Stint.STATUS_CHOICES.finished)


class TestGetPayoff(EryTestCase):
    def setUp(self):
        self.hand = create_test_hands(n=1, signal_pubsub=False).first()
        self.hand.stint.stint_specification.min_earnings = 15
        self.hand.stint.stint_specification.max_earnings = 30
        self.hand.stint.stint_specification.save()
        md_1 = self.hand.current_module.stint_definition_module_definition.module_definition
        md_2 = ModuleDefinitionFactory()
        sdmd = StintDefinitionModuleDefinition.objects.create(
            stint_definition=self.hand.stint.stint_specification.stint_definition, module_definition=md_2, order=1
        )
        self.alt_mod = ModuleFactory(stint_definition_module_definition=sdmd)
        self.spec = StintModuleSpecificationFactory(
            min_earnings=0, max_earnings=20, stint_specification=self.hand.stint.stint_specification, module_definition=md_1
        )
        self.hand_vd_1 = VariableDefinitionFactory(
            data_type=VariableDefinition.DATA_TYPE_CHOICES.float,
            is_payoff=True,
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            validator=None,
            module_definition=md_1,
        )
        self.hand_vd_2 = VariableDefinitionFactory(
            data_type=VariableDefinition.DATA_TYPE_CHOICES.float,
            is_payoff=True,
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            validator=None,
            module_definition=md_1,
        )
        self.hand_vd_3 = VariableDefinitionFactory(
            data_type=VariableDefinition.DATA_TYPE_CHOICES.float,
            is_payoff=True,
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            validator=None,
            module_definition=md_2,
        )

    def test_get_payoff(self):
        """
        Confirm payoffs within boundaries returned as expected.
        """
        # module passed
        self.spec.max_earnings = 20
        self.spec.save()
        HandVariableFactory(value=4, hand=self.hand, variable_definition=self.hand_vd_1, module=self.hand.current_module)
        HandVariableFactory(value=5, hand=self.hand, variable_definition=self.hand_vd_2, module=self.hand.current_module)
        # alt-mod should not affect result
        HandVariableFactory(value=15, hand=self.hand, variable_definition=self.hand_vd_3, module=self.alt_mod)
        self.assertEqual(self.hand.get_payoff(self.hand.current_module), 9)

        # no module passed
        self.assertEqual(self.hand.get_payoff(), 24)

    def test_get_payoff_min(self):
        """
        Confirm all min value boundaries work as expected.
        """
        # module passed
        self.spec.min_earnings = 3
        self.hand.stint.stint_specification.min_earnings = 15
        self.hand.stint.stint_specification.save()
        self.spec.save()
        HandVariableFactory(value=1, hand=self.hand, variable_definition=self.hand_vd_1, module=self.hand.current_module)
        HandVariableFactory(value=1, hand=self.hand, variable_definition=self.hand_vd_2, module=self.hand.current_module)
        # alt-mod should not affect result
        HandVariableFactory(value=2, hand=self.hand, variable_definition=self.hand_vd_3, module=self.alt_mod)
        self.assertEqual(self.hand.get_payoff(self.hand.current_module), 3)

        # no module passed
        self.assertEqual(self.hand.get_payoff(), 15)

    def test_get_payoff_max(self):
        """
        Confirm all max value boundaries works as expected.
        """
        # module passed
        self.spec.max_earnings = 10
        self.spec.save()
        HandVariableFactory(value=12, hand=self.hand, variable_definition=self.hand_vd_1, module=self.hand.current_module)
        HandVariableFactory(value=3, hand=self.hand, variable_definition=self.hand_vd_2, module=self.hand.current_module)
        # alt-mod should not affect result
        HandVariableFactory(value=20, hand=self.hand, variable_definition=self.hand_vd_3, module=self.alt_mod)
        self.assertEqual(self.hand.get_payoff(self.hand.current_module), 10)

        self.hand.stint.stint_specification.max_earnings = 20
        self.hand.stint.stint_specification.save()
        self.assertEqual(self.hand.get_payoff(), 20)


class TestHandPayment(EryTestCase):
    @mock.patch('ery_backend.scripts.ledger_client.send_payment')
    def test_pay(self, mock_send):
        """
        Confirm method works
        """
        hand = create_test_hands(n=1, signal_pubsub=False).first()
        md = hand.current_module.stint_definition_module_definition.module_definition
        action = ActionFactory(module_definition=md)
        as_1 = ActionStepFactory(
            action=action,
            for_each=ActionStep.FOR_EACH_CHOICES.hand_in_stint,
            action_type=ActionStep.ACTION_TYPE_CHOICES.pay_users,
        )
        pay_vd = VariableDefinitionFactory(
            module_definition=md,
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.float,
            validator=None,
            is_payoff=True,
        )
        pay_vd_2 = VariableDefinitionFactory(
            module_definition=md,
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.float,
            validator=None,
            is_payoff=True,
        )
        HandVariableFactory(variable_definition=pay_vd, value=5, hand=hand)
        stint = hand.stint
        ss = stint.stint_specification
        ss.min_earnings = 1
        ss.max_earnings = 10
        ss.save()

        payoff = hand.get_payoff()
        hand.pay(as_1)
        mock_send.assert_called_with(payoff, hand, as_1)

        HandVariableFactory(variable_definition=pay_vd_2, value=1, hand=hand)
        hand.pay(as_1)

        # handvariables should be cleared after payment
        for hand_variable in hand.variables.filter(variable_definition__is_payoff=True).all():
            self.assertEqual(hand_variable.value, 0)


class TestHandNextModule(EryTestCase):
    def setUp(self):
        self.hand = create_test_hands(n=1, team_size=1, frontend_type='Web', signal_pubsub=False).first()
        self.stint_definition = self.hand.stint.stint_specification.stint_definition
        self.module_definition_1 = self.stint_definition.stint_definition_module_definitions.get(order=0).module_definition
        self.module_definition_2 = ModuleDefinitionFactory()

    def test_get_next_module(self):
        sdmd = StintDefinitionModuleDefinition.objects.create(
            stint_definition=self.stint_definition, module_definition=self.module_definition_2, order=1
        )
        ModuleFactory(stint_definition_module_definition=sdmd, stint=self.hand.stint)

        self.assertEqual(self.hand.get_next_module(), Module.objects.get(stint_definition_module_definition=sdmd))

    @mock.patch('ery_backend.hands.models.Hand.pay')
    def test_opt_out(self, mock_pay):
        self.hand.status = Hand.STATUS_CHOICES.active
        self.hand.save()
        self.hand.opt_out()
        self.hand.refresh_from_db()
        self.assertTrue(self.hand.status, Hand.STATUS_CHOICES.quit)

    @unittest.skip("Address in issue #403")
    def test_update_last_seen(self):
        current_time = dt.datetime.now(pytz.UTC)
        # mock_app_render.return_value = 'anythingatall'
        # test method works
        self.hand.update_last_seen()
        self.assertTrue(self.hand.last_seen > current_time)

        # test method executed on stage.render
        new_current_time = dt.datetime.now().replace(tzinfo=pytz.UTC)
        self.hand.stage.stage_definition.render(hand=self.hand)
        self.assertTrue(self.hand.last_seen > new_current_time)

    def test_repeated_modules(self):
        sdmd_1 = StintDefinitionModuleDefinition.objects.create(
            stint_definition=self.stint_definition, module_definition=self.module_definition_1, order=1
        )
        sdmd_2 = StintDefinitionModuleDefinition.objects.create(
            stint_definition=self.stint_definition, module_definition=self.module_definition_2, order=2
        )
        module_2 = ModuleFactory(stint_definition_module_definition=sdmd_1, stint=self.hand.stint)
        module_3 = ModuleFactory(stint_definition_module_definition=sdmd_2, stint=self.hand.stint)

        self.assertEqual(self.hand.get_next_module(), module_2)

        self.hand.set_module(module_2)
        self.hand.refresh_from_db()
        # return expected module after repeated module
        self.assertEqual(self.hand.get_next_module(), module_3)

    def test_no_more_modules(self):
        # should return none if current Module is last. by default, only 1 sdmd
        self.assertIsNone(self.hand.get_next_module())


class TestBreadcrumb(EryTestCase):
    def setUp(self):
        self.hand = create_test_hands(n=1, signal_pubsub=False).first()

    def test_create_breadcrumb(self):
        """
        Confirm breadcrumbs can be created.
        """
        # delete correctly autocreated crumb
        self.hand.current_breadcrumb = None
        self.hand.save()

        start_crumb = self.hand.create_breadcrumb(self.hand.stage)
        self.hand.set_breadcrumb(start_crumb)
        self.assertTrue(
            StageBreadcrumb.objects.filter(
                hand=self.hand, stage=self.hand.stage, previous_breadcrumb=None, next_breadcrumb=None
            ).exists()
        )

        none_stagedefinition = StageDefinitionFactory(
            breadcrumb_type=StageDefinition.BREADCRUMB_TYPE_CHOICES.none, module_definition=self.hand.current_module_definition
        )
        none_stage = StageFactory(stage_definition=none_stagedefinition)
        # do not add forward/backward option if stage_definition does not allow
        none_crumb = self.hand.create_breadcrumb(none_stage)
        self.hand.set_breadcrumb(none_crumb)
        back_stagedefinition = StageDefinitionFactory(
            breadcrumb_type=StageDefinition.BREADCRUMB_TYPE_CHOICES.back, module_definition=self.hand.current_module_definition
        )
        back_stage = StageFactory(stage_definition=back_stagedefinition)
        back_crumb = self.hand.create_breadcrumb(back_stage)
        self.hand.set_breadcrumb(back_crumb)
        none_crumb.refresh_from_db()
        self.assertIsNone(none_crumb.next_breadcrumb)
        self.assertIsNone(none_crumb.previous_breadcrumb)

        # all_crumb should get forward and backward crumb
        all_stagedefinition = StageDefinitionFactory(
            breadcrumb_type=StageDefinition.BREADCRUMB_TYPE_CHOICES.all, module_definition=self.hand.current_module_definition
        )
        all_stage = StageFactory(stage_definition=all_stagedefinition)
        all_crumb = self.hand.create_breadcrumb(all_stage)
        self.hand.set_breadcrumb(all_crumb)

        # back_crumb should get a backward crumb
        self.assertEqual(back_crumb.previous_breadcrumb, none_crumb)
        self.assertIsNone(back_crumb.next_breadcrumb)

        final_stagedefinition = StageDefinitionFactory(
            breadcrumb_type=StageDefinition.BREADCRUMB_TYPE_CHOICES.none, module_definition=self.hand.current_module_definition
        )
        final_stage = StageFactory(stage_definition=final_stagedefinition)
        final_crumb = self.hand.create_breadcrumb(final_stage)

        self.assertEqual(all_crumb.previous_breadcrumb, back_crumb)
        self.assertEqual(all_crumb.next_breadcrumb, final_crumb)

    def test_breadcrumb_on_init(self):
        """
        Confirm breadcrumb created automagically on stint start
        """
        self.assertTrue(
            StageBreadcrumb.objects.filter(
                hand=self.hand, stage=self.hand.stage, previous_breadcrumb=None, next_breadcrumb=None
            ).exists()
        )
