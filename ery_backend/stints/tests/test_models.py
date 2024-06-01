# pylint:disable=too-many-lines
import datetime
import json
import unittest
from unittest import mock
import random

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.db.utils import IntegrityError

import grpc
from languages_plus.models import Language

from ery_backend.actions.exceptions import EryActionError
from ery_backend.actions.factories import ActionFactory, ActionStepFactory
from ery_backend.actions.models import ActionStep
from ery_backend.assets.factories import ImageAssetFactory
from ery_backend.base.exceptions import EryValidationError
from ery_backend.base.testcases import EryTestCase, create_test_stintdefinition, create_test_hands, random_dt_value
from ery_backend.datasets.factories import DatasetFactory
from ery_backend.keywords.factories import KeywordFactory
from ery_backend.frontends.factories import FrontendFactory
from ery_backend.frontends.models import Frontend
from ery_backend.hands.factories import HandFactory
from ery_backend.hands.models import Hand
from ery_backend.labs.factories import LabFactory
from ery_backend.logs.models import Log
from ery_backend.modules.factories import ModuleDefinitionFactory, ModuleFactory
from ery_backend.modules.models import Module
from ery_backend.stages.factories import StageDefinitionFactory, RedirectFactory
from ery_backend.stages.models import StageTemplate, StageTemplateBlock
from ery_backend.stint_specifications.factories import StintSpecificationFactory, StintSpecificationVariableFactory
from ery_backend.syncs.factories import EraFactory
from ery_backend.teams.factories import TeamFactory
from ery_backend.templates.factories import TemplateFactory
from ery_backend.templates.models import Template
from ery_backend.themes.factories import ThemeFactory
from ery_backend.users.factories import UserFactory
from ery_backend.validators.factories import ValidatorFactory
from ery_backend.variables.factories import (
    ModuleVariableFactory,
    HandVariableFactory,
    TeamVariableFactory,
    VariableDefinitionFactory,
)
from ery_backend.variables.models import VariableDefinition, HandVariable, ModuleVariable, TeamVariable
from ery_backend.widgets.factories import WidgetFactory
from ery_backend.widgets.models import Widget, WidgetEvent

from ..factories import StintDefinitionFactory, StintFactory, StintDefinitionVariableDefinitionFactory
from ..models import StintDefinition, StintDefinitionModuleDefinition, Stint


class TestStintDefinition(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.frontend = Frontend.objects.get(name='Web')
        cls.default_template = TemplateFactory(slug='defaulttemplate-asd123')
        cls.default_theme = ThemeFactory(slug='defaulttheme-asd123')

    def setUp(self):
        self.module_definition = ModuleDefinitionFactory()
        self.cover_image = ImageAssetFactory()
        self.stint_definition = StintDefinitionFactory(
            name='StintDefinitionTwentyFive', comment='This test stint', cover_image=self.cover_image
        )
        self.stintdefinitionmoduledefinition = StintDefinitionModuleDefinition(
            stint_definition=self.stint_definition, module_definition=self.module_definition
        )
        self.stintdefinitionmoduledefinition.save()
        self.stint_specification = StintSpecificationFactory()

    def test_exists(self):
        self.assertIsNotNone(self.stint_definition)

    def test_expected_attributes(self):
        self.assertEqual(self.stint_definition.name, 'StintDefinitionTwentyFive')
        self.assertEqual(self.stint_definition.comment, 'This test stint')
        self.assertIn(self.module_definition, self.stint_definition.module_definitions.all())
        self.assertEqual(self.stint_definition.cover_image, self.cover_image)

    def test_ready(self):
        sd = StintDefinitionFactory()
        # fails if not at least one module_definition
        self.assertFalse(sd.ready)

        md = ModuleDefinitionFactory()
        sdmd = StintDefinitionModuleDefinition(stint_definition=sd, module_definition=md)
        sdmd.save()

        # still fails if no moduledefinition contains start_stage and start_era
        self.assertIsNone(md.start_stage)
        self.assertFalse(sd.ready)

        # passed with ready module definition (start_stage and start_era)
        md.start_stage = StageDefinitionFactory()
        if md.start_era:
            self.fail("Autogeneration fixed. Update code")
        md.start_era = EraFactory(module_definition=md)
        md.save()
        self.assertTrue(sd.ready)

    def test_ordering(self):
        stintdef = StintDefinitionFactory()
        moduledef1 = ModuleDefinitionFactory(name="ModuleOne")
        moduledef2 = ModuleDefinitionFactory(name="ModuleTwo")
        moduledef3 = ModuleDefinitionFactory(name="ModuleThree")
        stintdefmoduledef_1 = StintDefinitionModuleDefinition.objects.create(
            stint_definition=stintdef, module_definition=moduledef2, order=1
        )
        stintdefmoduledef_0 = StintDefinitionModuleDefinition.objects.create(
            stint_definition=stintdef, module_definition=moduledef3, order=0
        )
        stintdefmoduledef_2 = StintDefinitionModuleDefinition.objects.create(
            stint_definition=stintdef, module_definition=moduledef1, order=2
        )
        stint_modules = StintDefinitionModuleDefinition.objects.all()
        found_stint_modules = list()
        for s in stint_modules:
            name = s.module_definition.name
            if name in ('ModuleOne', 'ModuleTwo', 'ModuleThree'):
                found_stint_modules.append(s)
        self.assertEqual(len(found_stint_modules), 3)
        self.assertEqual(found_stint_modules[0], stintdefmoduledef_0)
        self.assertEqual(found_stint_modules[1], stintdefmoduledef_1)
        self.assertEqual(found_stint_modules[2], stintdefmoduledef_2)

        # Note: I've confirmed as of 2/8/19 that this ordering does not apply to stint_definition.module_definitions.

    def test_base_import(self):
        base_xml = open('ery_backend/stints/tests/data/stint-0.bxml', 'rb')
        stint_definition = StintDefinition.import_instance_from_xml(base_xml, name='instance_new')
        self.assertEqual(stint_definition.name, 'instance_new')

    def test_full_import(self):
        xml = open('ery_backend/stints/tests/data/stint-1.bxml', 'rb')
        ValidatorFactory(code=None, name='moduledefinitionvd1', slug='moduledefinitionvd1-IoZsobtv')
        ValidatorFactory(code=None, name='moduledefinitionvd2', slug='moduledefinitionvd2-uTeIlVsg')
        frontend = FrontendFactory(name='module_definition-frontend-1')
        parental_template = TemplateFactory(
            name='module_definition-template-2', frontend=None, slug='moduledefinitiontemplate2-mXsMkPUQ'
        )
        TemplateFactory(
            name='module_definition-template-1',
            parental_template=parental_template,
            frontend=frontend,
            slug='moduledefinitiontemplate1-smzEnmHy',
        )
        ThemeFactory(name='module_definition-theme-1')
        WidgetFactory(name='ModuleDefinitionWOne', slug='moduledefinitionw1-PkaJygiV')
        WidgetFactory(name='ModuleDefinitionWTwo', slug='moduledefinitionw2-IxmJDlAU')
        stint_definition = StintDefinition.import_instance_from_xml(xml)
        self.assertIsNotNone(stint_definition)
        # Confirm complex stint definition recreated as intended
        module_definition = stint_definition.module_definitions.first()
        self.assertEqual(module_definition.variabledefinition_set.count(), 2)
        self.assertEqual(
            module_definition.variabledefinition_set.get(name='moduledefinitionvar2').variablechoiceitem_set.count(), 2
        )
        self.assertEqual(module_definition.era_set.count(), 3)
        self.assertEqual(module_definition.module_widgets.count(), 2)
        self.assertEqual(module_definition.module_widgets.get(name='ModuleDefinitionWidgetOne').choices.count(), 2)
        self.assertEqual(module_definition.stage_definitions.count(), 3)
        self.assertEqual(module_definition.stage_definitions.get(name='ModuleDefinitionStageOne').stage_templates.count(), 2)
        self.assertEqual(
            StageTemplateBlock.objects.filter(
                stage_template=StageTemplate.objects.get(template=Template.objects.get(name='module_definition-template-1'))
            ).count(),
            2,
        )
        self.assertEqual(
            module_definition.start_stage, module_definition.stage_definitions.get(name='ModuleDefinitionStageOne')
        )
        self.assertEqual(
            module_definition.warden_stage, module_definition.stage_definitions.get(name='ModuleDefinitionStageTwo')
        )
        self.assertEqual(module_definition.condition_set.count(), 4)
        self.assertEqual(
            module_definition.condition_set.get(name='module_definition-cond-1').left_variable_definition,
            module_definition.variabledefinition_set.get(name='moduledefinitionvar1'),
        )
        self.assertEqual(
            module_definition.condition_set.get(name='module_definition-cond-1').right_variable_definition,
            module_definition.variabledefinition_set.get(name='moduledefinitionvar2'),
        )
        self.assertEqual(module_definition.action_set.get(name='module_definition-action-3').steps.count(), 1)
        self.assertEqual(module_definition.action_set.get(name='module_definition-action-2').steps.count(), 3)
        # Expected specifications
        test_specification = stint_definition.specifications.filter(name='testspecification')
        backup_specification = stint_definition.specifications.filter(name='backupspecification')
        self.assertTrue(test_specification.exists())
        self.assertTrue(backup_specification.exists())
        self.assertEqual(test_specification.first().backup_stint_specification, backup_specification.first())

    def test_base_duplicate(self):
        self.stintdefinitionmoduledefinition.delete()
        base_stint_definition = self.stint_definition
        stint_definition_2 = base_stint_definition.duplicate()
        self.assertNotEqual(base_stint_definition, stint_definition_2)
        self.assertEqual('{}_copy'.format(base_stint_definition.name), stint_definition_2.name)

    def test_full_duplicate(self):
        # User is same as original
        for _ in range(3):
            keyword = KeywordFactory()
            self.stint_definition.keywords.add(keyword)
        backup_ss = StintSpecificationFactory(stint_definition=self.stint_definition)
        combo_objs = [{'frontend': frontend, 'language': Language.objects.get(pk='en')} for frontend in Frontend.objects.all()]
        ss = StintSpecificationFactory(
            stint_definition=self.stint_definition, backup_stint_specification=backup_ss, add_languagefrontends=combo_objs
        )
        ss_variables = []
        for _ in range(10):
            variable_definition = VariableDefinitionFactory(module_definition=self.module_definition)
            ss_variables.append(
                StintSpecificationVariableFactory(variable_definition=variable_definition, stint_specification=ss)
            )

        stint_definition_2 = self.stint_definition.duplicate()
        self.assertNotEqual(self.stint_definition, stint_definition_2)
        cloned_specification = stint_definition_2.specifications.filter(name=ss.name)
        cloned_backup_specification = stint_definition_2.specifications.filter(name=backup_ss.name)
        self.assertTrue(cloned_specification.exists())
        self.assertTrue(cloned_backup_specification.exists())
        self.assertEqual(cloned_specification.first().backup_stint_specification, cloned_backup_specification.first())
        module_definition_2 = stint_definition_2.module_definitions.first()
        self.assertIsNotNone(module_definition_2)
        # Children should not be the same
        self.assertNotEqual(self.module_definition, module_definition_2)
        self.assertEqual(stint_definition_2.keywords.count(), 3)

    # XXX: Address in issue #820
    # @staticmethod
    # def test_simple_import():
    #     """
    #     Used to test deserialization of xml generated via SimpleStintDefinitionSerializer
    #          (represents ModuleDefinitions linked to StintDefinition as slugs, rather than serializing full
    #           module definition info)
    #     """
    #     xml = open('ery_backend/stints/tests/data/simple-stint-0.bxml', 'rb')
    #     preload_module_definition_0 = ModuleDefinitionFactory(slug='moduledefinition0-tTPTcTkz')
    #     preload_module_definition_1 = ModuleDefinitionFactory(slug='moduledefinition1-PBdzLcxg')
    #     stint_definition = StintDefinition.import_instance_from_xml(xml, simple=True)

    #     StintDefinitionModuleDefinition.objects.get(
    #         stint_definition=stint_definition, module_definition=preload_module_definition_0
    #     )
    #     StintDefinitionModuleDefinition.objects.get(
    #         stint_definition=stint_definition, module_definition=preload_module_definition_1
    #     )

    def test_realize(self):
        # create stint
        stintdef = create_test_stintdefinition(self.frontend)
        stint = stintdef.realize(self.stint_specification)

        # Check attributes
        self.assertEqual(stint.stint_specification, self.stint_specification)

    def test_expected_realize_errors(self):
        """
        StintDefinition is not ready (has no connected ModuleDefinitions w/ stage)
        """
        with self.assertRaises(EryValidationError):
            self.stint_definition.realize(self.stint_specification)


class TestStint(EryTestCase):
    """
    These tests function regardless or because of stint.start in setup.
    """

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.frontend = Frontend.objects.get(name='Web')

    def setUp(self):
        stint_definition = create_test_stintdefinition(self.frontend)
        self.stint_specification = StintSpecificationFactory(
            team_size=2, min_team_size=2, max_team_size=2, stint_definition=stint_definition
        )
        self.lab = LabFactory()
        self.stint = StintFactory(stint_specification=self.stint_specification, lab=self.lab,)
        for _ in range(2):
            HandFactory(stint=self.stint, user=UserFactory())
        self.stint.start(UserFactory(), signal_pubsub=False)

        self.module = self.stint.modules.first()
        self.module_vd = VariableDefinitionFactory(
            scope=VariableDefinition.SCOPE_CHOICES.module, name='mvd', data_type=VariableDefinition.DATA_TYPE_CHOICES.str
        )
        self.module_variable_1 = ModuleVariableFactory(
            module=self.module, variable_definition=self.module_vd, value='kindermatchhere'
        )
        self.team_1 = self.stint.teams.first()
        self.team_vd = VariableDefinitionFactory(
            scope=VariableDefinition.SCOPE_CHOICES.team, name='tvd', data_type=VariableDefinition.DATA_TYPE_CHOICES.str
        )
        self.team_variable_1 = TeamVariableFactory(
            team=self.team_1, variable_definition=self.team_vd, value='teamsmatchheretogether', module=self.module
        )
        self.hand = self.stint.hands.first()
        self.user = self.hand.user
        self.hand_vd = VariableDefinitionFactory(
            scope=VariableDefinition.SCOPE_CHOICES.hand, name='hvd', data_type=VariableDefinition.DATA_TYPE_CHOICES.str
        )
        self.hand_variable_1 = HandVariableFactory(
            hand=self.hand, variable_definition=self.hand_vd, value='pleasedontmatchhere', module=self.module
        )

    def test_exists(self):
        self.assertIsNotNone(self.stint)

    def test_expected_attributes(self):
        self.assertEqual(self.stint.stint_specification, self.stint_specification)
        self.assertIn(self.team_1, self.stint.teams.all())
        self.assertEqual(self.stint.lab, self.lab)
        self.assertEqual(self.stint.status, Stint.STATUS_CHOICES.running)

    @mock.patch('ery_backend.hands.models.Hand.pay')
    def test_activity(self, mock_pay):
        """
        Confirm stint activity is set based on state.
        """
        self.stint.set_status(Stint.STATUS_CHOICES.running)
        self.assertTrue(self.stint.active)
        self.stint.set_status(Stint.STATUS_CHOICES.panicked)
        self.stint.save()
        self.assertFalse(self.stint.active)

    @mock.patch('ery_backend.hands.models.Hand.pay')
    def test_set_status(self, mock_pay):
        """
        Confirm status can be sucessfully updated.
        """
        stint = StintFactory(status=Stint.STATUS_CHOICES.starting)
        stint.set_status(Stint.STATUS_CHOICES.panicked)
        stint.refresh_from_db()
        self.assertEqual(stint.status, Stint.STATUS_CHOICES.panicked)

        # Should raise error on incorrect status
        with self.assertRaises(ValueError):
            self.stint.set_status('CRAZY')

    def test_get_context(self):
        context = self.stint.get_context(hand=self.hand, team=self.team_1)

        # Test default conext (generated within initial dict)
        self.assertEqual(context["module"], self.hand.current_module.stint_definition_module_definition.module_definition.slug)
        self.assertEqual(context["era"], self.hand.era.slug)
        self.assertEqual(context["nteams"], self.stint.teams.count())
        self.assertEqual(context["language"], self.hand.language.iso_639_1)

        # Test ModuleVariable objects

        # Team should overwrite context[name] = value
        self.team_vd.name = 'svd'
        self.team_vd.save()
        context = self.stint.get_context(hand=self.hand, team=self.team_1)
        self.assertEqual(context['variables'][self.team_vd.name], (self.team_vd.id, 'teamsmatchheretogether'))

        # Hand should overwrite context[name] = value
        self.hand_vd.name = 'svd'
        self.hand_vd.save()
        context = self.stint.get_context(hand=self.hand, team=self.team_1)
        self.assertEqual(context['variables'][self.hand_vd.name], (self.hand_vd.id, 'pleasedontmatchhere'))

    def test_expected_get_variable_errors(self):
        team_2 = TeamFactory()

        hand_2 = HandFactory()
        hand_2.current_team = TeamFactory()

        # must have hand
        with self.assertRaises(EryValidationError):
            self.stint.get_variable(self.hand_variable_1.variable_definition, team=self.team_1)

        # must have hand or team
        with self.assertRaises(EryValidationError):
            self.stint.get_variable(self.team_variable_1.variable_definition)

        # handVariable
        with self.assertRaises(ObjectDoesNotExist):
            # hand that does not have said variable
            self.stint.get_variable(self.hand_variable_1.variable_definition, hand=HandFactory())

        # teamVariable
        with self.assertRaises(ObjectDoesNotExist):
            # hand not part of team with said variable
            self.stint.get_variable(self.team_variable_1.variable_definition, hand=hand_2)
            # team does not have said variable
        with self.assertRaises(ObjectDoesNotExist):
            self.stint.get_variable(self.team_variable_1.variable_definition, team=team_2)

        # moduleVariable
        with self.assertRaises(ObjectDoesNotExist):
            # hand's current module does not have said variable
            hand_2.current_module = ModuleFactory(stint=self.stint)
            hand_2.stint = self.stint
            hand_2.save()
            self.stint.get_variable(self.module_variable_1.variable_definition, hand=hand_2)

    def test_set_variable(self):
        self.stint.set_variable(self.module_variable_1.variable_definition, 'dudelightamatch', hand=self.hand)
        self.module_variable_1.refresh_from_db()
        self.assertEqual(self.module_variable_1.value, 'dudelightamatch')
        message = 'set_variable for: {}, of type: {}, = {}'.format(
            self.module_variable_1.variable_definition.name, self.module_variable_1.__class__, 'dudelightamatch'
        )
        self.assertIsNone(Log.objects.filter(message=message).first())

    def test_get_variable(self):
        # HandVariable
        self.assertEqual(
            self.stint.get_variable(self.hand_variable_1.variable_definition, hand=self.hand), self.hand_variable_1
        )

        # TeamVariable
        self.assertEqual(
            self.stint.get_variable(self.team_variable_1.variable_definition, team=self.team_1), self.team_variable_1
        )
        self.assertEqual(
            self.stint.get_variable(self.team_variable_1.variable_definition, hand=self.hand), self.team_variable_1
        )

        # ModuleVariable
        self.assertEqual(
            self.stint.get_variable(self.module_variable_1.variable_definition, hand=self.hand), self.module_variable_1
        )

    @mock.patch('ery_backend.hands.models.Hand.pay')
    def test_stop(self, mock_pay):
        """
        Confirm stint.stop sets stopped_by user (if exists) and end time.
        """
        user = UserFactory()
        self.stint.stop(user)
        self.stint.refresh_from_db()
        self.assertEqual(self.stint.stopped_by, user)

        # No error should occur on lack of stopped_by. This just means Stint stopped automatically.
        self.stint.set_status(Stint.STATUS_CHOICES.running)
        self.stint.stop()

        self.assertIsInstance(self.stint.ended, datetime.datetime)

    def test_log(self):
        # Verify creation of a non-system log
        message = 'This is a test log'
        log_type = Log.LOG_TYPE_CHOICES.warning
        self.stint.log(message=message, log_type=Log.LOG_TYPE_CHOICES.warning, system_only=False)
        self.assertTrue(Log.objects.filter(message=message, log_type=log_type, stint=self.stint).exists())

        # Verify system log is not created as Log object
        message = 'This is a system test log'
        self.stint.log(message=message, log_type=Log.LOG_TYPE_CHOICES.warning, system_only=True)
        self.assertFalse(Log.objects.filter(message=message, log_type=log_type, stint=self.stint).exists())


class TestPanicStint(EryTestCase):
    """
    Confirm Stint panicks in expected situations.
    """

    def setUp(self):
        self.hand = create_test_hands(n=1, signal_pubsub=False).first()
        self.action = ActionFactory(module_definition=self.hand.current_module_definition)

    @mock.patch('ery_backend.stints.models.Stint.set_status', autospec=True)
    def test_actionstep_with_deleted_era(self, mock_set_status):
        """
        ActionStep of type set_era run on a hand, but no longer has an era due to era deletion.
        """
        era = EraFactory(module_definition=self.hand.current_module_definition)
        action_step = ActionStepFactory(
            era=era,
            action_type=ActionStep.ACTION_TYPE_CHOICES.set_era,
            action=self.action,
            condition=None,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
        )
        era.delete()

        with self.assertRaises(EryActionError):
            action_step.run(self.hand)
        mock_set_status.assert_any_call(self.hand.stint, Stint.STATUS_CHOICES.panicked)

    @mock.patch('ery_backend.stints.models.Stint.set_status', autospec=True)
    def test_actionstep_with_deleted_hand(self, mock_set_status):
        """
        Hand deleted between obtaining starting actionstep and attempting to set era
        """
        action_step = ActionStepFactory(
            era=EraFactory(),
            action_type=ActionStep.ACTION_TYPE_CHOICES.set_era,
            action=self.action,
            condition=None,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
        )

        self.hand.current_breadcrumb.delete()  # trigger cascade causing hand deletion
        with self.assertRaises(EryActionError):
            action_step.run(self.hand)
        mock_set_status.assert_any_call(self.hand.stint, Stint.STATUS_CHOICES.panicked)

    @unittest.skip("XXX: Reinstate when re-implementing pay")
    @mock.patch('ery_backend.hands.models.Hand.pay')
    def test_pay_called_once_with_deleted_currentmoduledefinition(self, mock_pay):
        # Hand.pay occurs once here (during set_stage), before failure to query StageDefinition on
        # hand.stage.stage_definition.allow_back.
        stage_definition = self.hand.stage.stage_definition
        stage_definition.redirect_on_submit = True
        stage_definition.save()
        end_stage_definition = StageDefinitionFactory(module_definition=self.hand.current_module_definition, end_stage=True)
        RedirectFactory(stage_definition=stage_definition, next_stage_definition=end_stage_definition)
        self.hand.submit()
        self.hand.current_module.stint_definition_module_definition.module_definition.delete()
        self.assertEqual(mock_pay.call_count, 1)

    @mock.patch('ery_backend.stints.models.Stint.set_status', autospec=True)
    @mock.patch('ery_backend.scripts.engine_client.evaluate')
    def test_actionstep_setvar_with_deleted_vardefinition(self, mock_eval, mock_set_status):
        variable_definition = VariableDefinitionFactory(
            module_definition=self.hand.current_module_definition, scope=VariableDefinition.SCOPE_CHOICES.hand
        )
        HandVariableFactory(variable_definition=variable_definition, hand=self.hand)
        action_step = ActionStepFactory(
            variable_definition=variable_definition,
            action_type=ActionStep.ACTION_TYPE_CHOICES.set_variable,
            action=self.action,
            condition=None,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
        )
        variable_definition.delete()
        with self.assertRaises(EryActionError):
            action_step.run(self.hand)
        mock_set_status.assert_any_call(self.hand.stint, Stint.STATUS_CHOICES.panicked)

    @mock.patch('ery_backend.stints.models.Stint.set_status', autospec=True)
    @mock.patch('ery_backend.scripts.engine_client._run_javascript_op')
    def test_panic_on_noengine(self, mock_run_op, mock_set_status):
        """
        Verify EryActionError when engine is stalled ";)".
        """
        mock_run_op.side_effect = grpc.RpcError()
        variable_definition = VariableDefinitionFactory(
            module_definition=self.hand.current_module_definition, scope=VariableDefinition.SCOPE_CHOICES.hand
        )
        action_step = ActionStepFactory(
            variable_definition=variable_definition,
            action_type=ActionStep.ACTION_TYPE_CHOICES.set_variable,
            action=self.action,
            condition=None,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
        )
        with self.assertRaises(EryActionError):
            action_step.run(self.hand)
        mock_set_status.assert_any_call(self.hand.stint, Stint.STATUS_CHOICES.panicked)

    def tearDown(self):
        """
        Failure to remove hand's stage manually leads to IntegrityError during
        test_actionstep_stage_progression_with_deleted_currentmoduledefinition. Stage maintain
        reference to Stagebreadcrumb, which tearDown attempts to delete first.
        """
        stage = self.hand.stage
        stage.delete()


class TestStartStint(EryTestCase):
    """
    These tests require Stint.start to be (or not to be) called.
    """

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.frontend = Frontend.objects.get(name='Web')

    def setUp(self):
        stint_definition = create_test_stintdefinition(self.frontend)
        self.stint_specification = StintSpecificationFactory(
            team_size=2, min_team_size=2, max_team_size=2, stint_definition=stint_definition, late_arrival=False
        )
        self.stint = self.stint_specification.realize(UserFactory())

    def test_ready(self):
        # should fail due to lack of one team with two hands
        self.assertFalse(self.stint.ready)

        for _ in range(2):
            HandFactory(stint=self.stint)
        self.assertTrue(self.stint.ready)

    def test_start_hand(self):
        # without module
        stintdefinition_moduledefinitions = self.stint_specification.stint_definition.stint_definition_module_definitions.all()
        module = stintdefinition_moduledefinitions.first().realize(self.stint)
        hand = HandFactory(stint=module.stint, era=None, stage=None, current_breadcrumb=None, current_module=None, status=None)
        self.assertIsNone(hand.stage)
        self.assertIsNone(hand.era)
        self.assertIsNone(hand.current_module)
        self.assertIsNone(hand.status)
        self.assertIsNone(hand.current_breadcrumb)

        stage_definition = module.module_definition.start_stage
        era = module.module_definition.start_era
        module.stint.start_hand(hand)
        hand.refresh_from_db()
        self.assertEqual(hand.stage.stage_definition, stage_definition)
        self.assertEqual(hand.era, era)
        self.assertEqual(hand.current_breadcrumb.stage, hand.stage)
        self.assertEqual(hand.current_module, module)
        self.assertEqual(hand.status, hand.STATUS_CHOICES.active)

    @mock.patch('google.cloud.pubsub.PublisherClient.create_topic')
    @mock.patch('google.cloud.pubsub.PublisherClient.publish')
    def test_start_pubsub(self, mock_publish, mock_create):
        """
        Confirms pubsub message published as expected during start.
        """
        for _ in range(8):
            HandFactory(stint=self.stint, user=UserFactory())
        user = UserFactory()
        with self.assertRaises(TypeError):  # Comes from wrapping future.exception() in a mock
            self.stint.start(user)
        deployment = getattr(settings, "DEPLOYMENT", "staging")
        project_name = getattr(settings, "PROJECT_NAME", "eryservices-176219")
        mock_publish.assert_called_with(
            f'projects/{project_name}/topics/{deployment}-robot',
            json.dumps({'action': 'STINT_START', 'stint_id': self.stint.id}).encode('UTF-8'),
        )

    def test_start(self):
        for _ in range(8):
            HandFactory(stint=self.stint, user=UserFactory())
        user = UserFactory()
        self.stint.start(user, signal_pubsub=False)
        self.assertIsInstance(self.stint.started, datetime.datetime)
        # correct # of modules
        expected_module_definitions = self.stint.stint_specification.stint_definition.module_definitions
        self.assertEqual(expected_module_definitions.count(), self.stint.modules.count())
        # correct modules of correct order
        i = 0
        for module in self.stint.modules.all():
            self.assertEqual(module.stint_definition_module_definition.module_definition, expected_module_definitions.all()[i])
            i += 1
        # 4 teams generated from 8 hands
        self.assertEqual(self.stint.teams.count(), 4)
        team_1 = self.stint.teams.all()[0]
        team_2 = self.stint.teams.all()[1]
        team_3 = self.stint.teams.all()[2]
        team_4 = self.stint.teams.all()[3]
        # each team has 2 hands
        for team in [team_1, team_2, team_3, team_4]:
            self.assertEqual(team.hands.count(), 2)
        # teams do not share hands
        test_hand = team_1.hands.first()
        for team in [team_2, team_3, team_4]:
            self.assertNotIn(test_hand, team.hands.all())
        starting_module_definition = self.stint.modules.first().stint_definition_module_definition.module_definition
        # team has correct era
        self.assertEqual(self.stint.teams.first().era, starting_module_definition.start_era)
        # hand has correct module, era, status, and stage
        self.assertEqual(test_hand.current_module, self.stint.modules.first())
        self.assertEqual(test_hand.stage.stage_definition, starting_module_definition.start_stage)
        self.assertEqual(test_hand.era, starting_module_definition.start_era)
        self.assertEqual(test_hand.status, Hand.STATUS_CHOICES.active)

        # started_by should be set
        self.assertEqual(self.stint.started_by, user)

    def test_start_includes_stint_definition_variable_definitions(self):
        """
        Ensure that stint.start produces appropriate variables when there are
        :class:`~ery_backend.stints.models.StintDefinitionVariableDefinition` instances
        """
        stint_definition = create_test_stintdefinition(Frontend.objects.get(name="Web"))

        module_sdvd = StintDefinitionVariableDefinitionFactory(
            stint_definition=stint_definition,
            variable_definitions__count=random.randint(1, 5),
            variable_definitions__scope=VariableDefinition.SCOPE_CHOICES.module,
        )

        team_sdvd = StintDefinitionVariableDefinitionFactory(
            stint_definition=stint_definition,
            variable_definitions__count=random.randint(1, 5),
            variable_definitions__scope=VariableDefinition.SCOPE_CHOICES.team,
        )

        hand_sdvd = StintDefinitionVariableDefinitionFactory(
            stint_definition=stint_definition,
            variable_definitions__count=random.randint(1, 5),
            variable_definitions__scope=VariableDefinition.SCOPE_CHOICES.hand,
        )

        stint = stint_definition.realize(stint_specification=StintSpecificationFactory(stint_definition=stint_definition))

        for _ in range(random.randint(1, 10)):
            HandFactory(stint=stint)

        stint.start(UserFactory(), signal_pubsub=False)

        ModuleVariable.objects.get(stint_definition_variable_definition=module_sdvd)

        self.assertEqual(
            TeamVariable.objects.filter(stint_definition_variable_definition=team_sdvd).count(), stint.teams.count()
        )

        self.assertEqual(
            HandVariable.objects.filter(stint_definition_variable_definition=hand_sdvd).count(), stint.hands.count()
        )

    def test_start_includes_stintspecificationvariables(self):
        module_definition_count = random.randint(2, 5)
        sd = create_test_stintdefinition(Frontend.objects.get(name='Web'), module_definition_n=module_definition_count)
        ss = StintSpecificationFactory(stint_definition=sd)
        stint = sd.realize(ss)
        HandFactory(stint=stint, current_module=None)  # Stint needs hand to realize vars on start
        module_definitions = [sdmd.module_definition for sdmd in sd.stint_definition_module_definitions.all()]
        ssv_count = random.randint(1, 10)
        variable_definitions = [VariableDefinitionFactory(module_definition=module_definitions[0]) for _ in range(ssv_count)]
        ssvs = [
            StintSpecificationVariableFactory(stint_specification=ss, variable_definition=variable_definitions[ssv_counter])
            for ssv_counter in range(ssv_count)
        ]
        sdvd_ssv_count = random.randint(1, 10)
        sdvds = [
            StintDefinitionVariableDefinitionFactory(stint_definition=sd, variable_definitions__count=module_definition_count)
            for _ in range(sdvd_ssv_count)
        ]
        sdvd_first_vds = []
        md_order = dict(sd.stint_definition_module_definitions.values_list('module_definition', 'order'))
        for sdvd in sdvds:
            ordered_vds = sorted(list(sdvd.variable_definitions.all()), key=lambda x: md_order[x.module_definition.id])
            sdvd_first_vds.append(ordered_vds[0])
        sdvd_ssvs = [
            StintSpecificationVariableFactory(stint_specification=ss, variable_definition=sdvd_first_vds[sdvd_counter],)
            for sdvd_counter in range(sdvd_ssv_count)
        ]
        stint.start(UserFactory(), signal_pubsub=False)
        scope_map = {
            VariableDefinition.SCOPE_CHOICES.hand: HandVariable,
            VariableDefinition.SCOPE_CHOICES.team: TeamVariable,
            VariableDefinition.SCOPE_CHOICES.module: ModuleVariable,
        }
        for ssv in ssvs:
            vd = ssv.variable_definition
            variable = scope_map[vd.scope].objects.get(variable_definition=vd)
            self.assertEqual(variable.value, ssv.value)

        for sdvd_ssv_counter in range(sdvd_ssv_count):
            vd = sdvd_ssvs[sdvd_ssv_counter].variable_definition
            variable = scope_map[vd.scope].objects.get(stint_definition_variable_definition=sdvds[sdvd_ssv_counter])
            self.assertEqual(variable.value, sdvd_ssvs[sdvd_ssv_counter].value)

    def test_start_includes_datasetvariables(self):
        module_definition_count = random.randint(2, 5)
        sd = create_test_stintdefinition(Frontend.objects.get(name='Web'), module_definition_n=module_definition_count)
        ss = StintSpecificationFactory(stint_definition=sd)
        stint = sd.realize(ss)
        HandFactory(stint=stint, current_module=None)  # Stint needs hand to realize vars on start
        module_definitions = [sdmd.module_definition for sdmd in sd.stint_definition_module_definitions.all()]
        ssv_count = random.randint(1, 10)
        variable_definitions = [VariableDefinitionFactory(module_definition=module_definitions[0]) for _ in range(ssv_count)]
        dataset_info = {}  # a random number of vds from ssvs and sdvd_ssvs
        for i in range(random.randint(1, ssv_count)):
            vd = variable_definitions[i]
            dataset_info[vd.name] = vd.data_type
        ssvs = [
            StintSpecificationVariableFactory(stint_specification=ss, variable_definition=variable_definitions[ssv_counter])
            for ssv_counter in range(ssv_count)
        ]
        sdvd_ssv_count = random.randint(1, 10)
        sdvds = [
            StintDefinitionVariableDefinitionFactory(stint_definition=sd, variable_definitions__count=module_definition_count)
            for _ in range(sdvd_ssv_count)
        ]
        sdvd_first_vds = []
        md_order = dict(sd.stint_definition_module_definitions.values_list('module_definition', 'order'))
        for sdvd in sdvds:
            ordered_vds = sorted(list(sdvd.variable_definitions.all()), key=lambda x: md_order[x.module_definition.id])
            sdvd_first_vds.append(ordered_vds[0])
        for i in range(random.randint(1, sdvd_ssv_count)):
            vd = sdvd_first_vds[i]
            dataset_info[vd.name] = vd.data_type

        sdvd_ssvs = [
            StintSpecificationVariableFactory(stint_specification=ss, variable_definition=sdvd_first_vds[sdvd_counter],)
            for sdvd_counter in range(sdvd_ssv_count)
        ]
        dataset_dict = {}
        for key in dataset_info:
            data_type = dataset_info[key]
            value = random_dt_value(data_type)
            if data_type in (VariableDefinition.DATA_TYPE_CHOICES.list, VariableDefinition.DATA_TYPE_CHOICES.dict):
                value = json.dumps(value)
            dataset_dict[key] = value
        dataset_row = [dataset_dict]
        dataset = DatasetFactory(to_dataset=dataset_row)
        ss.dataset = dataset
        ss.save()
        stint.start(UserFactory(), signal_pubsub=False)
        scope_map = {
            VariableDefinition.SCOPE_CHOICES.hand: HandVariable,
            VariableDefinition.SCOPE_CHOICES.team: TeamVariable,
            VariableDefinition.SCOPE_CHOICES.module: ModuleVariable,
        }
        for ssv in ssvs:  # dataset value should be prioritized over only matching ssvs
            vd = ssv.variable_definition
            variable = scope_map[vd.scope].objects.get(variable_definition=vd)
            dataset_value = vd.name in dataset_row[0]
            expected_value = dataset_row[0][vd.name] if dataset_value else ssv.value
            if dataset_value and vd.data_type in (
                VariableDefinition.DATA_TYPE_CHOICES.list,
                VariableDefinition.DATA_TYPE_CHOICES.dict,
            ):
                expected_value = json.loads(expected_value)
            self.assertEqual(variable.value, expected_value)

        for sdvd_ssv_counter in range(sdvd_ssv_count):
            vd = sdvd_ssvs[sdvd_ssv_counter].variable_definition
            variable = scope_map[vd.scope].objects.get(stint_definition_variable_definition=sdvds[sdvd_ssv_counter])
            dataset_value = vd.name in dataset_row[0]
            expected_value = dataset_row[0][vd.name] if dataset_value else sdvd_ssvs[sdvd_ssv_counter].value
            if dataset_value and vd.data_type in (
                VariableDefinition.DATA_TYPE_CHOICES.list,
                VariableDefinition.DATA_TYPE_CHOICES.dict,
            ):
                expected_value = json.loads(expected_value)
            self.assertEqual(variable.value, expected_value)

    def test_expected_start_errors(self):
        """
        Confirm user cannot re-start a stint.
        """
        for _ in range(2):
            HandFactory(stint=self.stint, user=UserFactory())
        user = UserFactory()
        self.stint.start(user, signal_pubsub=False)
        with self.assertRaises(EryValidationError):
            self.stint.start(user, signal_pubsub=False)

    def test_expected_stop_errors(self):
        """
        User should not be able to stop a stint that hasn't been started
        """
        with self.assertRaises(EryValidationError):
            self.stint.stop(UserFactory())


# XXX: Failures in this testcase addressed in #339
@unittest.skip
class TestStintPayoffs(EryTestCase):
    """
    Confirm hands are correctly paid on corresponding status changes.
    """

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.submit_widget = Widget.objects.get(name='SubmitButton')

    def setUp(self):
        self.hands = create_test_hands(n=3, signal_pubsub=False)
        self.stint = self.hands.first().stint
        self.stint.stint_specification.min_earnings = 0
        self.stint.stint_specification.save()

        self.md = self.hands.first().current_module.stint_definition_module_definition.module_definition
        payoff_vd = VariableDefinitionFactory(
            module_definition=self.md,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.float,
            is_payoff=True,
            scope=VariableDefinition.SCOPE_CHOICES.hand,
        )
        for hand in self.hands.all():
            HandVariableFactory(hand=hand, variable_definition=payoff_vd, value=5)

    @mock.patch('ery_backend.conditions.models.Condition.evaluate')
    @mock.patch('ery_backend.scripts.ledger_client.send_payment')
    def test_end_payoff(self, mock_pay, mock_evaluate):
        """
        Confirm hands given remaining pay as they finish Stint.
        """
        mock_evaluate.return_value = True
        hand_1 = self.hands.all()[0]
        hand_2 = self.hands.all()[2]
        hand_3 = self.hands.all()[1]
        stage_def = StageDefinitionFactory(module_definition=self.md, end_stage=True)
        self.assertNotEqual(hand_1.stage.stage_definition, stage_def)
        RedirectFactory(stage_definition=hand_1.stage.stage_definition, next_stage_definition=stage_def)
        self.submit_widget.trigger_events(WidgetEvent.EVENT_CHOICES.onClick, hand_1)
        self.assertEqual(hand_1.stage.stage_definition, stage_def)

        hand_1.refresh_from_db()
        hand_2.refresh_from_db()
        hand_3.refresh_from_db()
        self.assertEqual(hand_1.current_payoff, 5)
        self.assertEqual(hand_2.current_payoff, 0)
        self.assertEqual(hand_3.current_payoff, 0)

        self.submit_widget.trigger_events(WidgetEvent.EVENT_CHOICES.onClick, hand_2)
        hand_1.refresh_from_db()
        hand_2.refresh_from_db()
        hand_3.refresh_from_db()
        self.assertEqual(hand_1.current_payoff, 5)
        self.assertEqual(hand_2.current_payoff, 5)
        self.assertEqual(hand_3.current_payoff, 0)
        self.submit_widget.trigger_events(WidgetEvent.EVENT_CHOICES.onClick, hand_3)
        hand_1.refresh_from_db()
        hand_2.refresh_from_db()
        hand_3.refresh_from_db()
        self.assertEqual(hand_1.current_payoff, 5)
        self.assertEqual(hand_2.current_payoff, 5)
        self.assertEqual(hand_3.current_payoff, 5)

    @mock.patch('ery_backend.conditions.models.Condition.evaluate')
    @mock.patch('ery_backend.scripts.ledger_client.send_payment')
    def test_cancel_payoff(self, mock_pay, mock_evaluate):
        """
        Confirm hands given remaining pay (minimum in this case) on cancellation of Stint.
        """
        self.stint.stint_specification.min_earnings = 6
        self.stint.stint_specification.save()
        self.stint.set_status(Stint.STATUS_CHOICES.cancelled)
        for hand in self.hands.all():
            hand.refresh_from_db()
            self.assertEqual(hand.current_payoff, 6)

    @mock.patch('ery_backend.conditions.models.Condition.evaluate')
    @mock.patch('ery_backend.scripts.ledger_client.send_payment')
    def test_panic_payoff(self, mock_pay, mock_evaluate):
        """
        Confirm hands given remaining pay (minimum in this case) if stint crashes.
        """
        self.stint.stint_specification.min_earnings = 6
        self.stint.stint_specification.save()
        self.stint.set_status(Stint.STATUS_CHOICES.panicked)
        for hand in self.hands.all():
            hand.refresh_from_db()
            self.assertEqual(hand.current_payoff, 6)


class TestStopStint(EryTestCase):
    @staticmethod
    def batch_refresh(hands):
        for hand in hands:
            hand.refresh_from_db()

    @mock.patch('ery_backend.scripts.ledger_client.send_payment')
    def setUp(self, mock_pay):
        self.stint = create_test_hands(n=4, signal_pubsub=False).first().stint
        self.hand_1, self.hand_2, self.hand_3, self.hand_4 = self.stint.hands.all()
        self.hand_1.set_status(Hand.STATUS_CHOICES.active)
        self.hand_2.set_status(Hand.STATUS_CHOICES.timedout)
        self.hand_3.set_status(Hand.STATUS_CHOICES.quit)
        self.hand_4.set_status(Hand.STATUS_CHOICES.finished)

    @mock.patch('ery_backend.scripts.ledger_client.send_payment')
    def test_stint_stop_on_panic(self, mock_pay):
        """
        Confirm stint.stop executed on status change to panic.
        """
        self.stint.set_status(Stint.STATUS_CHOICES.panicked)
        self.batch_refresh([self.hand_1, self.hand_2, self.hand_3, self.hand_4])
        # hand active -> cancelled
        self.assertEqual(self.hand_1.status, Hand.STATUS_CHOICES.cancelled)
        # hands with any other status should not be changed.
        self.assertEqual(self.hand_2.status, Hand.STATUS_CHOICES.timedout)
        self.assertEqual(self.hand_3.status, Hand.STATUS_CHOICES.quit)
        self.assertEqual(self.hand_4.status, Hand.STATUS_CHOICES.finished)

    @mock.patch('ery_backend.scripts.ledger_client.send_payment')
    def test_stint_stop_on_cancel(self, mock_pay):
        """
        Confirm stint.stop executed on status change to cancel.
        """
        self.stint.set_status(Stint.STATUS_CHOICES.cancelled)
        self.batch_refresh([self.hand_1, self.hand_2, self.hand_3, self.hand_4])
        # hand active -> cancelled
        self.assertEqual(self.hand_1.status, Hand.STATUS_CHOICES.cancelled)
        # hands with any other status should not be changed.
        self.assertEqual(self.hand_2.status, Hand.STATUS_CHOICES.timedout)
        self.assertEqual(self.hand_3.status, Hand.STATUS_CHOICES.quit)
        self.assertEqual(self.hand_4.status, Hand.STATUS_CHOICES.finished)

    @mock.patch('ery_backend.scripts.ledger_client.send_payment')
    def test_stint_stop_on_finish(self, mock_pay):
        """
        Confirm stint.stop executed on status change to finished.
        """
        self.stint.set_status(Stint.STATUS_CHOICES.finished)
        self.batch_refresh([self.hand_1, self.hand_2, self.hand_3, self.hand_4])
        # hand active -> cancelled
        self.assertEqual(self.hand_1.status, Hand.STATUS_CHOICES.cancelled)
        # hands with any other status should not be changed.
        self.assertEqual(self.hand_2.status, Hand.STATUS_CHOICES.timedout)
        self.assertEqual(self.hand_3.status, Hand.STATUS_CHOICES.quit)
        self.assertEqual(self.hand_4.status, Hand.STATUS_CHOICES.finished)


class TestStintDefinitionModuleDefinition(EryTestCase):
    def setUp(self):
        self.stint_definition = StintDefinitionFactory()
        self.module_definition = ModuleDefinitionFactory()

    def test_realize(self):
        """
        Confirm module is created via module_definition.realize and variable is generated belonging to that module.
        Full testing of variable creation in realize is assumed via testing of module.make_variables
        """
        self.module_definition.variabledefinition_set.all().delete()
        stint_specification = StintSpecificationFactory(stint_definition=self.stint_definition)
        sdmd = StintDefinitionModuleDefinition.objects.create(
            stint_definition=self.stint_definition, module_definition=self.module_definition
        )
        stint = StintFactory(stint_specification=stint_specification)
        variable_definition = VariableDefinitionFactory(
            module_definition=self.module_definition, scope=VariableDefinition.SCOPE_CHOICES.module
        )
        sdmd.realize(stint)
        module = Module.objects.get(stint_definition_module_definition=sdmd, stint=stint)
        ModuleVariable.objects.get(module=module, variable_definition=variable_definition)

    @unittest.skip("XXX: Address in issue #815")
    def test_unique_together(self):
        """
        Confirm StintDefinitionModuleDefinition is unique per StintDefinition/order.
        """
        stint_definition = StintDefinitionFactory()
        module_definition_1 = ModuleDefinitionFactory()
        module_definition_2 = ModuleDefinitionFactory()
        StintDefinitionModuleDefinition.objects.create(
            stint_definition=stint_definition, module_definition=module_definition_1, order=1
        )

        # Can't have two SDMDs with same stint_definition/order
        with self.assertRaises(IntegrityError):
            StintDefinitionModuleDefinition.objects.create(
                stint_definition=stint_definition, module_definition=module_definition_2, order=1
            )

        # Can have two SDMDs with same stint_definition/module_definition
        StintDefinitionModuleDefinition.objects.create(
            stint_definition=stint_definition, module_definition=module_definition_1, order=2
        )


class TestRender(EryTestCase):
    def setUp(self):
        self.hand = create_test_hands(frontend_type='Web', signal_pubsub=False).first()

    @mock.patch('ery_backend.stints.models.Stint.render')
    def test_render(self, mock_stint_content):
        """
        Confirm render calls expected methods for expected frontends.
        """
        self.hand.stint.render(self.hand)
        mock_stint_content.assert_called_once()


class TestJoinUser(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.frontend = Frontend.objects.get(name='Web')

    def setUp(self):
        stint_definition = create_test_stintdefinition(self.frontend, module_definition_n=4)
        self.stint_specification = StintSpecificationFactory(
            team_size=2, min_team_size=1, max_team_size=2, stint_definition=stint_definition
        )
        self.stint = self.stint_specification.realize(UserFactory())
        self.pre_existing_hand = HandFactory(user=UserFactory(), frontend=self.frontend, stint=self.stint)

    def test_join_user_basic_info(self):
        """
        Confirm module, era, stage, and breadcrumbs created as expected.
        """
        self.stint.start(UserFactory(), signal_pubsub=False)
        self.pre_existing_hand.refresh_from_db()
        new_user = UserFactory()
        self.stint.join_user(new_user, frontend=self.frontend)
        new_hand = self.stint.hands.filter(user=new_user, frontend=self.frontend).first()
        self.assertIsNotNone(new_hand)
        self.assertEqual(self.pre_existing_hand.stage.stage_definition, new_hand.stage.stage_definition)
        self.assertEqual(self.pre_existing_hand.era, new_hand.era)
        self.assertEqual(self.pre_existing_hand.current_module, new_hand.current_module)
        self.assertIsNone(new_hand.current_breadcrumb.previous_breadcrumb)
        self.assertIsNone(new_hand.current_breadcrumb.next_breadcrumb)
        self.assertEqual(new_hand.current_breadcrumb.stage, new_hand.stage)
        self.assertEqual(new_hand.status, Hand.STATUS_CHOICES.active)

    def test_join_user_variables(self):
        """
        Confirm hand variables created as expected.
        """
        variables = []
        for module_definition in self.stint.stint_specification.stint_definition.module_definitions.all():
            variables.append(
                VariableDefinitionFactory(module_definition=module_definition, scope=VariableDefinition.SCOPE_CHOICES.hand)
            )
        self.stint.start(UserFactory(), signal_pubsub=False)
        for variable_def in variables:
            self.assertTrue(
                HandVariable.objects.filter(hand=self.pre_existing_hand, variable_definition=variable_def).exists()
            )
        new_user = UserFactory()
        self.stint.join_user(new_user, frontend=self.frontend)
        new_hand = self.stint.hands.filter(user=new_user, frontend=self.frontend).first()
        for variable_def in variables:
            self.assertTrue(HandVariable.objects.filter(hand=new_hand, variable_definition=variable_def).exists())


class TestStintDefinitionVariableDefinition(EryTestCase):
    @staticmethod
    def test_sdvd_factory_is_clean():
        """Running clean on a factory built StintVariableLink must produce no errors"""
        sdvd = StintDefinitionVariableDefinitionFactory()
        sdvd.clean()

    def test_factory_uses_supplied_variable_definitions(self):
        """
        Make sure the StintDefinitionVariableDefinition adds the supplied variable definitions when requested.
        """
        vds = [VariableDefinitionFactory(), VariableDefinitionFactory(), VariableDefinitionFactory()]
        sdvd = StintDefinitionVariableDefinitionFactory(variable_definitions=vds)
        self.assertEqual(sorted(list(sdvd.variable_definitions.values_list('pk', flat=True))), [v.pk for v in vds])

    @unittest.skip("Address in issue #813")
    def test_sdvd_requires_module_in_stintdefinition(self):
        """
        Make sure the VariableDefinitions in the StintDefinitionVariableDefinition belong to a ModuleDefinition that is
        included in the StintDefinition.stintdefintionmoduledefintion_set
        """
        sdvd = StintDefinitionVariableDefinitionFactory()
        module_definition_ids = set(
            sdvd.stint_definition.stint_definition_module_definitions.values_list('module_definition__id', flat=True)
        )

        for v in sdvd.variable_definitions.all():
            self.assertIn(
                v.module_definition.pk,
                module_definition_ids,
                msg="variable_definitions must belong to a ModuleDefinition that is included in the StintDefinition",
            )

        vd = VariableDefinitionFactory()

        if vd.module_definition.pk in module_definition_ids:
            raise ValueError("Random test data generation failed.")

        sdvd.variable_definitions.add(vd)
        self.assertRaises(ValueError, sdvd.clean)

    @unittest.skip("Address in issue #813")
    def test_sdvd_requires_distinct_module_definitions(self):
        """
        Make sure the ModuleDefinitions for each VariableDefinition in StintDefinitionVariableDefinition are distinct
        """
        sdvd = StintDefinitionVariableDefinitionFactory()
        vds = list(sdvd.variable_definitions.all())
        module_definitions = set()

        for v in vds:
            self.assertNotIn(
                v.module_definition.pk,
                module_definitions,
                msg="{} appeared more than once in factory StintDefinitionVariableDefinition".format(v.module_definition),
            )

            module_definitions.add(v.module_definition.pk)

        vd = VariableDefinitionFactory(module_definition=vds[0].module_definition)
        sdvd.variable_definitions.add(vd)
        self.assertRaises(ValueError, sdvd.clean)

    @unittest.skip("XXX: Address in issue #678")
    def test_sdvd_requires_identical_variable_types(self):
        sdvd = StintDefinitionVariableDefinitionFactory(variable_definitions__count=random.randint(2, 5))
        vds = list(sdvd.variable_definitions.all())

        # Force a mismatched type
        choices = [data_type for data_type, _ in VariableDefinition.DATA_TYPE_CHOICES]
        choices.remove(vds[0].data_type)
        vds[0].data_type = random.choice(choices)
        vds[0].save()

        msg = "Expected mismatch among these types: {}".format(" &".join([v.data_type for v in vds]))

        with self.assertRaises(ValueError, msg=msg):
            sdvd.clean()


# XXX: Address in issue #525
# class TestToDataset(EryTestCase):
#     dsclient = ery_datastore_client

#     def test_query_run_entity_from_datastore():

#     def test_query_write_entity_from_datastore():

#     def test_query_team_from_datastore():

#     def test_query_hand_from_datastore():

#     def test_asign_hand_as_team_member():

#     def test_save_as_dataset()
