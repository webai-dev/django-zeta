import random
import unittest

from django.core.exceptions import ValidationError
from languages_plus.models import Language
from rest_framework import serializers

from ery_backend.actions.models import Action, ActionStep
from ery_backend.actions.factories import ActionFactory, ActionStepFactory
from ery_backend.base.testcases import EryTestCase
from ery_backend.commands.factories import (
    CommandFactory,
    CommandTemplateFactory,
    CommandTemplateBlockFactory,
    CommandTemplateBlockTranslationFactory,
)
from ery_backend.conditions.models import Condition
from ery_backend.conditions.factories import ConditionFactory
from ery_backend.keywords.factories import KeywordFactory
from ery_backend.forms.factories import FormFactory, FormFieldFactory, FormButtonListFactory, FormItemFactory
from ery_backend.frontends.factories import FrontendFactory
from ery_backend.frontends.models import Frontend
from ery_backend.hands.factories import HandFactory
from ery_backend.modules.factories import (
    ModuleDefinitionProcedureFactory,
    ModuleDefinitionWidgetFactory,
    ModuleEventFactory,
    WidgetChoiceFactory,
    WidgetChoiceTranslationFactory,
)
from ery_backend.modules.models import (
    ModuleDefinitionProcedure,
    ModuleEvent,
    ModuleDefinitionWidget,
    WidgetChoice,
    ModuleEventStep,
)
from ery_backend.procedures.factories import ProcedureFactory
from ery_backend.robots.factories import RobotFactory, RobotRuleFactory
from ery_backend.robots.models import Robot, RobotRule
from ery_backend.stages.factories import (
    StageTemplateFactory,
    StageTemplateBlockFactory,
    StageDefinitionFactory,
    RedirectFactory,
)
from ery_backend.stages.models import StageTemplate, StageTemplateBlock, StageDefinition
from ery_backend.stints.factories import (
    StintFactory,
    StintDefinitionModuleDefinitionFactory,
    StintDefinitionVariableDefinitionFactory,
)
from ery_backend.stints.models import StintDefinitionModuleDefinition
from ery_backend.syncs.factories import EraFactory
from ery_backend.syncs.models import Era
from ery_backend.teams.factories import TeamFactory
from ery_backend.templates.factories import TemplateFactory
from ery_backend.themes.factories import ThemeFactory
from ery_backend.validators.factories import ValidatorFactory
from ery_backend.variables.factories import (
    VariableDefinitionFactory,
    VariableChoiceItemFactory,
    ModuleVariableFactory,
    VariableChoiceItemTranslationFactory,
)
from ery_backend.variables.models import VariableDefinition, VariableChoiceItem, ModuleVariable, TeamVariable, HandVariable
from ery_backend.widgets.factories import WidgetFactory, WidgetConnectionFactory

from ..factories import ModuleDefinitionFactory, ModuleFactory
from ..models import ModuleDefinition


class TestModule(EryTestCase):
    def setUp(self):
        self.stint = StintFactory()
        self.module = ModuleFactory(stint=self.stint)
        self.modulevariable = ModuleVariableFactory(module=self.module)
        self.modulevariable2 = ModuleVariableFactory(module=self.module)

    def test_exists(self):
        self.assertIsNotNone(self.module)

    def test_expected_attributes(self):
        self.assertEqual(self.module.stint, self.stint)
        self.assertIn(self.modulevariable, self.module.variables.all())
        self.assertIn(self.modulevariable2, self.module.variables.all())

    @staticmethod
    def test_make_variables():
        """
        Confirms module.make_variables returns a variable as intended at all levels
        """
        stint = StintFactory()
        module_definition = ModuleDefinitionFactory()
        sdmd = StintDefinitionModuleDefinition.objects.create(
            stint_definition=stint.stint_specification.stint_definition, module_definition=module_definition
        )
        module = ModuleFactory(stint=stint, stint_definition_module_definition=sdmd)
        team = TeamFactory(stint=stint)
        hand = HandFactory(stint=stint)
        var_def_mv = VariableDefinitionFactory(
            module_definition=module_definition, scope=VariableDefinition.SCOPE_CHOICES.module
        )
        var_def_tv = VariableDefinitionFactory(
            module_definition=module_definition, scope=VariableDefinition.SCOPE_CHOICES.team
        )
        var_def_hv = VariableDefinitionFactory(
            module_definition=module_definition, scope=VariableDefinition.SCOPE_CHOICES.hand
        )
        module.make_variables(teams=stint.teams.all(), hands=stint.hands.all())
        ModuleVariable.objects.get(module=module, variable_definition=var_def_mv)
        TeamVariable.objects.get(team=team, variable_definition=var_def_tv)
        HandVariable.objects.get(hand=hand, variable_definition=var_def_hv)

    def test_make_variables_exclusion_list(self):
        """
        Ensure that module.make_variables can exclude variable_definition from normal creation flow if
        connected to given stint_definition_variable_definitions
        """
        stint = StintFactory()
        stint_definition = stint.stint_specification.stint_definition
        sdmd1 = StintDefinitionModuleDefinitionFactory(stint_definition=stint_definition, order=1)
        sdmd2 = StintDefinitionModuleDefinitionFactory(stint_definition=stint_definition, order=2)
        module = ModuleFactory(stint=stint, stint_definition_module_definition=sdmd1)
        team = TeamFactory(stint=stint)
        hand = HandFactory(stint=stint)
        var_def_mv1 = VariableDefinitionFactory(
            module_definition=sdmd1.module_definition, scope=VariableDefinition.SCOPE_CHOICES.module
        )
        var_def_mv2 = VariableDefinitionFactory(
            module_definition=sdmd2.module_definition,
            scope=VariableDefinition.SCOPE_CHOICES.module,
            data_type=var_def_mv1.data_type,
        )
        var_def_tv1 = VariableDefinitionFactory(
            module_definition=sdmd1.module_definition, scope=VariableDefinition.SCOPE_CHOICES.team
        )
        var_def_tv2 = VariableDefinitionFactory(
            module_definition=sdmd2.module_definition,
            scope=VariableDefinition.SCOPE_CHOICES.team,
            data_type=var_def_tv1.data_type,
        )
        var_def_hv1 = VariableDefinitionFactory(
            module_definition=sdmd1.module_definition, scope=VariableDefinition.SCOPE_CHOICES.hand
        )
        var_def_hv2 = VariableDefinitionFactory(
            module_definition=sdmd2.module_definition,
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            data_type=var_def_hv1.data_type,
        )

        StintDefinitionVariableDefinitionFactory(
            stint_definition=stint_definition, variable_definitions=[var_def_mv1, var_def_mv2]
        )
        StintDefinitionVariableDefinitionFactory(
            stint_definition=stint_definition, variable_definitions=[var_def_tv1, var_def_tv2]
        )
        StintDefinitionVariableDefinitionFactory(
            stint_definition=stint_definition, variable_definitions=[var_def_hv1, var_def_hv2]
        )
        sdvds = stint_definition.stint_definition_variable_definitions
        module.make_variables(hands=stint.hands.all(), teams=stint.teams.all(), stint_definition_variable_definitions=sdvds)
        with self.assertRaises(ModuleVariable.DoesNotExist):
            ModuleVariable.objects.get(module=module, variable_definition=var_def_mv1)
        with self.assertRaises(ModuleVariable.DoesNotExist):
            ModuleVariable.objects.get(module=module, variable_definition=var_def_mv2)

        with self.assertRaises(TeamVariable.DoesNotExist):
            TeamVariable.objects.get(team=team, variable_definition=var_def_tv1)
        with self.assertRaises(TeamVariable.DoesNotExist):
            TeamVariable.objects.get(team=team, variable_definition=var_def_tv2)

        with self.assertRaises(HandVariable.DoesNotExist):
            HandVariable.objects.get(hand=hand, variable_definition=var_def_hv1)
        with self.assertRaises(HandVariable.DoesNotExist):
            HandVariable.objects.get(hand=hand, variable_definition=var_def_hv2)


class TestModuleDefinition(EryTestCase):
    def setUp(self):
        self.warden_stage = StageDefinitionFactory()
        self.start_stage = StageDefinitionFactory(name='startstage')
        self.module_definition = ModuleDefinitionFactory(
            name='ModuleDefinitionTwo',
            comment='This test module definition',
            min_team_size=30,
            max_team_size=40,
            start_stage=self.start_stage,
            warden_stage=self.warden_stage,
            primary_language=Language.objects.first(),
        )
        self.start_stage.module_definition = self.module_definition
        self.start_stage.save()
        if self.module_definition.start_era:
            self.fail("Autogeneration fixed. Update code")
        self.module_definition.start_era = EraFactory(
            name=f'{self.module_definition.name}-start', module_definition=self.module_definition
        )
        self.base_module_definition = ModuleDefinitionFactory(start_stage=None, warden_stage=None)

        ValidatorFactory(name='module_definition-vd-1', code=None)
        ValidatorFactory(name='module_definition-vd-2', regex=None)

    def test_exists(self):
        self.assertIsNotNone(self.module_definition)

    def test_expected_attributes(self):
        self.assertEqual(self.module_definition.name, 'ModuleDefinitionTwo')
        self.assertEqual(self.module_definition.comment, 'This test module definition')
        self.assertEqual(self.module_definition.min_team_size, 30)
        self.assertEqual(self.module_definition.max_team_size, 40)
        self.assertEqual(self.module_definition.start_stage, self.start_stage)
        self.assertEqual(self.module_definition.warden_stage, self.warden_stage)
        self.assertEqual(
            self.module_definition.start_era, Era.objects.get(name='{}-start'.format(self.module_definition.name))
        )
        self.assertIsNotNone(self.module_definition.slug)
        self.assertEqual(self.module_definition.primary_language, Language.objects.first())

        mdw_1 = ModuleDefinitionWidgetFactory(module_definition=self.module_definition)
        mdw_2 = ModuleDefinitionWidgetFactory(module_definition=self.module_definition)
        widgets = self.module_definition.module_widgets.all()
        for module_definition_widget in (mdw_1, mdw_2):
            self.assertIn(module_definition_widget, widgets)
        self.assertEqual(len(widgets), 2)

    def test_validation_errors(self):
        with self.assertRaises(ValidationError):
            ModuleDefinitionFactory(min_team_size=12, max_team_size=4)

    def test_uniqueness(self):
        # Same name is ok for different modules...
        md_1 = ModuleDefinitionFactory(name='NameOne')
        md_2 = ModuleDefinitionFactory(name='NameOne')

        self.assertNotEqual(md_1, md_2)

    def test_base_import(self):
        TemplateFactory(slug='defaulttemplate-asd123')
        ThemeFactory(slug='defaulttheme-asd123')
        base_xml = open('ery_backend/modules/tests/data/module_definition-0.bxml', 'rb')
        module_definition = ModuleDefinition.import_instance_from_xml(base_xml, name='InstanceNew')
        self.assertEqual(module_definition.name, 'InstanceNew')

    def test_many_children_import(self):
        TemplateFactory(slug='defaulttemplate-asd123')
        ThemeFactory(slug='defaulttheme-asd123')
        web = Frontend.objects.get(name='Web')
        TemplateFactory(slug='moduledefinitiontemplate1-smzEnmHy', frontend=web)
        base_xml = open('ery_backend/modules/tests/data/module_definition_commands.bxml', 'rb')
        module_definition = ModuleDefinition.import_instance_from_xml(base_xml, name='InstanceNew')
        self.assertIsNotNone(module_definition)
        command_zero = module_definition.command_set.get(name='commandzero')
        self.assertEqual(command_zero.command_templates.count(), 2)
        command_zero_template = command_zero.command_templates.first()
        self.assertEqual(command_zero_template.blocks.count(), 1)

    def test_full_import(self):
        # Preloads
        xml = open('ery_backend/modules/tests/data/module_definition-1.bxml', 'rb')
        ProcedureFactory(slug='ajbidjsleap')
        ValidatorFactory(name='moduledefinitionvd2', slug='moduledefinitionvd2-uTeIlVsg', regex=None)
        ValidatorFactory(name='moduledefinitionvd1', slug='moduledefinitionvd1-IoZsobtv', regex=None)
        frontend = FrontendFactory(name='module_definition-frontend-1')
        TemplateFactory(slug='defaulttemplate-asd123')
        ThemeFactory(slug='defaulttheme-asd123')
        parental_template = TemplateFactory(name='moduledefinitiontemplate2', slug='moduledefinitiontemplate2-mXsMkPUQ')
        template = TemplateFactory(
            name='moduledefinitiontemplate1',
            slug='moduledefinitiontemplate1-smzEnmHy',
            parental_template=parental_template,
            frontend=frontend,
        )
        ThemeFactory(name='moduledefinitiontheme1', slug='moduledefinitiontheme1-fftsSJcD')
        widget_1 = WidgetFactory(name='ModuleDefinitionWOne', slug='moduledefinitioniw1-PkaJygiV')
        widget_2 = WidgetFactory(name='ModuleDefinitionWTwo', slug='moduledefinitioniw2-IxmJDlAU')
        module_definition = ModuleDefinition.import_instance_from_xml(xml, "TestModuleDefinitionFullImport")

        # Expected actions
        action_1 = Action.objects.filter(module_definition=module_definition, name='module_definition-action-1').first()
        self.assertIsNotNone(action_1)
        action_2 = Action.objects.filter(module_definition=module_definition, name='module_definition-action-2').first()
        self.assertIsNotNone(action_2)
        action_3 = Action.objects.filter(module_definition=module_definition, name='module_definition-action-3').first()
        self.assertIsNotNone(action_3)

        # Expected variables
        variable_definition_1 = VariableDefinition.objects.filter(
            module_definition=module_definition, name='moduledefinitionvar1'
        ).first()
        self.assertIsNotNone(variable_definition_1)
        variable_definition_2 = VariableDefinition.objects.filter(
            module_definition=module_definition, name='moduledefinitionvar2'
        ).first()
        self.assertIsNotNone(variable_definition_2)

        # Expected variable_choice_items
        variable_choice_item_1 = VariableChoiceItem.objects.filter(
            value='a', variable_definition=variable_definition_2
        ).first()
        self.assertIsNotNone(variable_choice_item_1)
        variable_choice_item_2 = VariableChoiceItem.objects.filter(
            value='b', variable_definition=variable_definition_2
        ).first()
        self.assertIsNotNone(variable_choice_item_2)

        # Expected eras
        era_2 = Era.objects.filter(
            module_definition=module_definition, name='module_definition-era-2', action=action_1
        ).first()
        self.assertIsNotNone(era_2)

        # Expected module_definition_widgets
        module_definition_widget_1 = ModuleDefinitionWidget.objects.filter(
            module_definition=module_definition, name='ModuleDefinitionWidgetOne', widget=widget_1
        ).first()
        self.assertIsNotNone(module_definition_widget_1)
        module_definition_widget_2 = ModuleDefinitionWidget.objects.filter(
            module_definition=module_definition, name='ModuleDefinitionWidgetTwo', widget=widget_2
        ).first()
        self.assertIsNotNone(module_definition_widget_2)

        # Expected module_events
        event_1 = ModuleEvent.objects.filter(
            event_type=ModuleEvent.REACT_EVENT_CHOICES.onSubmit, widget=module_definition_widget_1
        ).first()
        self.assertIsNotNone(event_1)
        event_2 = ModuleEvent.objects.filter(
            event_type=ModuleEvent.REACT_EVENT_CHOICES.onChange, widget=module_definition_widget_1
        ).first()
        self.assertIsNotNone(event_2)

        # Expected module_events steps
        self.assertTrue(
            event_1.steps.filter(
                event_action_type=ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.run_action, action=action_1
            ).exists()
        )
        self.assertTrue(
            event_2.steps.filter(
                event_action_type=ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.run_action, action=action_2
            ).exists()
        )

        # Expected choice input item
        widget_choice_1 = WidgetChoice.objects.filter(widget=module_definition_widget_1).first()
        self.assertIsNotNone(widget_choice_1)

        # Expected stages
        stage_definition_1 = StageDefinition.objects.filter(
            module_definition=module_definition, name='ModuleDefinitionStageOne', pre_action=None
        ).first()
        self.assertIsNotNone(stage_definition_1)
        stage_definition_2 = StageDefinition.objects.filter(
            module_definition=module_definition, name='ModuleDefinitionStageTwo', pre_action=action_2
        ).first()
        self.assertIsNotNone(stage_definition_2)
        stage_definition_3 = StageDefinition.objects.filter(
            module_definition=module_definition, name='ModuleDefinitionStageThree', pre_action=action_2
        ).first()
        self.assertIsNotNone(stage_definition_3)

        # Expected stagetemplates
        stage_template_1 = StageTemplate.objects.filter(stage_definition=stage_definition_1, template=template).first()
        self.assertIsNotNone(stage_template_1)
        stage_template_2 = StageTemplate.objects.filter(
            stage_definition=stage_definition_1, template=parental_template
        ).first()
        self.assertIsNotNone(stage_template_2)

        # Expected stagetemplateblocks
        stage_template_block_1 = StageTemplateBlock.objects.filter(
            stage_template=stage_template_1, name='SandraHolden'
        ).first()

        self.assertIsNotNone(stage_template_block_1)
        stage_template_block_2 = StageTemplateBlock.objects.filter(
            stage_template=stage_template_1, name='TriciaBriggs'
        ).first()

        self.assertIsNotNone(stage_template_block_2)

        # Expected module single children
        self.assertEqual(module_definition.start_stage, stage_definition_1)
        self.assertEqual(module_definition.warden_stage, stage_definition_2)

        # Expected conditions
        condition_expression = Condition.objects.filter(
            module_definition=module_definition, left_type=Condition.TYPE_CHOICES.expression, name='module_definition-cond-2'
        ).first()
        self.assertIsNotNone(condition_expression)
        condition_variable = Condition.objects.filter(
            module_definition=module_definition, left_type=Condition.TYPE_CHOICES.variable, name='module_definition-cond-1'
        ).first()
        self.assertIsNotNone(condition_variable)
        self.assertEqual(condition_variable.left_variable_definition, variable_definition_1)
        self.assertEqual(condition_variable.right_variable_definition, variable_definition_2)

        condition_sub_condition = Condition.objects.filter(
            module_definition=module_definition, left_type='sub_condition', name='module_definition-cond-3'
        ).first()
        self.assertIsNotNone(condition_sub_condition)
        # Expected action steps
        actionstep1_2 = ActionStep.objects.filter(
            action=action_2, variable_definition=variable_definition_1, condition=condition_variable
        ).first()
        self.assertIsNotNone(actionstep1_2)

        actionstep1_3 = ActionStep.objects.filter(action=action_2, era=era_2, condition=condition_variable).first()
        self.assertIsNotNone(actionstep1_3)

        actionstep1_4 = ActionStep.objects.filter(action=action_2, subaction=action_3, condition=condition_variable).first()
        self.assertIsNotNone(actionstep1_4)

        # Expected robots
        robot = Robot.objects.filter(name='robotone', module_definition=module_definition).first()
        self.assertIsNotNone(robot)

        # Expected rules
        robot_rule = robot.rules.filter(
            rule_type=RobotRule.RULE_TYPE_CHOICES.static, robot=robot, static_value='a', widget=module_definition_widget_2
        ).first()
        self.assertIsNotNone(robot_rule)

        # Expected commands
        command = module_definition.command_set.filter(name='commandzero')
        self.assertTrue(command.exists())
        command = command.first()

        # Expected command_templates
        self.assertEqual(command.command_templates.count(), 2)
        self.assertTrue(command.command_templates.filter(blocks__name='Content').exists())
        self.assertEqual(
            command.command_templates.get(blocks__name='Content').blocks.get(name='Content').translations.count(), 1
        )
        self.assertTrue(command.command_templates.filter(blocks__name='OtherContent').exists())
        self.assertEqual(
            command.command_templates.get(blocks__name='OtherContent').blocks.get(name='OtherContent').translations.count(), 1
        )

        # Expected procedures_aliases
        self.assertTrue(ModuleDefinitionProcedure.objects.filter(name='import_procedure_one').exists())
        self.assertTrue(ModuleDefinitionProcedure.objects.filter(name='importprocedureone').exists())

    def test_expected_relationmissing_import_error(self):
        """
            User creates custom xml, but with related fk that does not exist in current db.
        """
        base_xml = open('ery_backend/modules/tests/data/module_definition-relationmissing.bxml', 'rb')
        with self.assertRaises(serializers.ValidationError):
            ModuleDefinition.import_instance_from_xml(base_xml)

    def test_base_duplicate(self):
        module_2 = self.base_module_definition.duplicate()
        self.assertNotEqual(self.base_module_definition, module_2)
        self.assertEqual('{}Copy'.format(self.base_module_definition.name), module_2.name)

    def test_full_duplicate(self):
        procedure = ProcedureFactory(name='procedure')
        alias = ModuleDefinitionProcedureFactory(
            name='procedure', procedure=procedure, module_definition=self.base_module_definition
        )
        alias2 = ModuleDefinitionProcedureFactory(
            name='proc', procedure=procedure, module_definition=self.base_module_definition
        )
        preload_keywords = [KeywordFactory() for _ in range(3)]
        for keyword in preload_keywords:
            self.base_module_definition.keywords.add(keyword)
        ValidatorFactory(name='validator-0', regex=None)
        frontend = FrontendFactory(name='frontend-0')
        parental_template = TemplateFactory(name='template-1', frontend=None)
        preload_template = TemplateFactory(name='template-0', parental_template=parental_template, frontend=frontend)
        ThemeFactory(name='theme-0')
        preload_forms = [FormFactory(module_definition=self.base_module_definition) for _ in range(1, 3)]
        for preload_form in preload_forms:
            child_count = random.randint(1, 3)
            preload_field_items = [FormItemFactory(form=preload_form, child_type=False) for _ in range(child_count)]
            _ = [
                FormFieldFactory(form_item=preload_field_items[i], add_choices=True, add_choices__translations=True)
                for i in range(child_count)
            ]
            preload_buttonlist_items = [FormItemFactory(form=preload_form, child_type=False) for _ in range(child_count)]
            _ = [FormButtonListFactory(form_item=preload_buttonlist_items[i], add_buttons=True) for i in range(child_count)]

        preload_action_1 = ActionFactory(module_definition=self.base_module_definition, name='action-0')
        preload_action_2 = ActionFactory(module_definition=self.base_module_definition, name='action-2')
        preload_action_3 = ActionFactory(module_definition=self.base_module_definition, name='to_save_check')
        preload_var_definition = VariableDefinitionFactory(
            module_definition=self.base_module_definition,
            name='bypwilklqf',
            data_type=VariableDefinition.DATA_TYPE_CHOICES.choice,
            default_value='b',
        )
        to_save_var_definitions = []
        for _ in range(3):
            vd = VariableDefinitionFactory(module_definition=self.base_module_definition)
            to_save_var_definitions.append(vd)
        preload_var_choice = VariableChoiceItemFactory(variable_definition=preload_var_definition, value='a')
        preload_var_choice.save()
        language_1 = Language.objects.get(iso_639_1='ab')
        VariableChoiceItemTranslationFactory(
            variable_choice_item=preload_var_choice, language=language_1, caption='test caption'
        )
        preload_era = EraFactory(module_definition=self.base_module_definition, name='era-0', action=preload_action_1)
        preload_widget = WidgetFactory(name='WidgetZ')
        preload_module_definition_widget = ModuleDefinitionWidgetFactory(
            module_definition=self.base_module_definition,
            name='ModuleDefinitionWidgetZero',
            widget=preload_widget,
            variable_definition=preload_var_definition,
        )
        robot = RobotFactory(module_definition=self.base_module_definition, name='robotone')
        RobotRuleFactory(
            robot=robot,
            rule_type=RobotRule.RULE_TYPE_CHOICES.static,
            static_value='a',
            widget=preload_module_definition_widget,
        )

        ModuleEventFactory(
            widget=preload_module_definition_widget,
            event_type=ModuleEvent.REACT_EVENT_CHOICES.onChange,
            include_event_steps=True,
        )
        preload_widget_choice = WidgetChoiceFactory(widget=preload_module_definition_widget, value='a')
        WidgetChoiceTranslationFactory(widget_choice=preload_widget_choice, language=language_1, caption="test caption")
        preload_stage_definition = StageDefinitionFactory(
            module_definition=self.base_module_definition, name='StageZero', pre_action=preload_action_2
        )
        RedirectFactory(
            stage_definition=preload_stage_definition,
            condition=ConditionFactory(
                module_definition=preload_stage_definition.module_definition,
                left_type=Condition.TYPE_CHOICES.expression,
                right_type=Condition.TYPE_CHOICES.expression,
                left_variable_definition=None,
                right_variable_definition=None,
                left_expression=1,
                right_expression=1,
            ),
        )
        preload_stage_template = StageTemplateFactory(stage_definition=preload_stage_definition, template=preload_template)
        StageTemplateBlockFactory(stage_template=preload_stage_template, name='TestStbOne')
        preload_condition_expression = ConditionFactory(
            module_definition=self.base_module_definition,
            left_type=Condition.TYPE_CHOICES.expression,
            right_type=Condition.TYPE_CHOICES.expression,
            left_expression=1,
            right_expression=1,
            relation=Condition.RELATION_CHOICES.equal,
        )
        preload_condition_variable = ConditionFactory(
            module_definition=self.base_module_definition,
            left_type=Condition.TYPE_CHOICES.variable,
            left_variable_definition=preload_var_definition,
            right_type=Condition.TYPE_CHOICES.variable,
            right_variable_definition=preload_var_definition,
            relation=Condition.RELATION_CHOICES.equal,
        )
        preload_condition_subcondition_1 = ConditionFactory(
            module_definition=self.base_module_definition,
            left_type='sub_condition',
            left_sub_condition=preload_condition_variable,
            right_type='sub_condition',
            right_sub_condition=preload_condition_variable,
            operator=Condition.BINARY_OPERATOR_CHOICES.op_and,
        )
        preload_condition_subcondition_2 = ConditionFactory(
            module_definition=self.base_module_definition,
            left_type='sub_condition',
            left_sub_condition=preload_condition_subcondition_1,
            right_type='sub_condition',
            right_sub_condition=preload_condition_subcondition_1,
            left_variable_definition=None,
            right_variable_definition=None,
            operator=Condition.BINARY_OPERATOR_CHOICES.op_and,
        )
        preload_condition_subcondition_3 = ConditionFactory(
            module_definition=self.base_module_definition,
            left_type='sub_condition',
            left_sub_condition=preload_condition_subcondition_2,
            right_type='sub_condition',
            right_sub_condition=preload_condition_subcondition_2,
            left_variable_definition=None,
            right_variable_definition=None,
            operator=Condition.BINARY_OPERATOR_CHOICES.op_and,
        )

        ActionStepFactory(
            action=preload_action_1,
            subaction=preload_action_2,
            condition=preload_condition_expression,
            era=None,
            variable_definition=None,
            action_type='subaction',
        )
        ActionStepFactory(
            action=preload_action_1,
            subaction=None,
            condition=preload_condition_variable,
            era=None,
            variable_definition=preload_var_definition,
            action_type='set_variable_definition',
        )
        ActionStepFactory(
            action=preload_action_1,
            subaction=None,
            condition=preload_condition_expression,
            era=preload_era,
            variable_definition=None,
            action_type='set_era',
        )
        ActionStepFactory(
            action=preload_action_1,
            subaction=None,
            condition=preload_condition_expression,
            era=None,
            variable_definition=None,
            action_type='log',
            log_message='test-log',
        )
        to_save_step = ActionStepFactory(
            action=preload_action_3,
            subaction=None,
            condition=None,
            era=None,
            variable_definition=None,
            action_type=ActionStep.ACTION_TYPE_CHOICES.save_data,
            log_message=None,
        )
        to_save_step.to_save.add(*to_save_var_definitions)
        command = CommandFactory(
            module_definition=self.base_module_definition,
            action__module_definition=self.base_module_definition,
            action__name='command_action',
        )
        command_template = CommandTemplateFactory(command=command)
        ctb_1 = CommandTemplateBlockFactory(command_template=command_template, name='Content')
        CommandTemplateBlockTranslationFactory(command_template_block=ctb_1)
        CommandTemplateBlockFactory(command_template=command_template, name='OtherContent')
        self.base_module_definition.start_stage = preload_stage_definition
        self.base_module_definition.warden_stage = preload_stage_definition
        self.base_module_definition.save()

        module_definition = self.base_module_definition.duplicate()
        # Expected actions
        action_1 = Action.objects.filter(module_definition=module_definition, name='action-0').first()
        self.assertIsNotNone(action_1)
        action_2 = Action.objects.filter(module_definition=module_definition, name='action-2').first()
        action_3 = Action.objects.filter(module_definition=module_definition, name='to_save_check').first()
        self.assertIsNotNone(action_2)
        self.assertEqual(action_1.name, 'action-0')
        self.assertEqual(action_2.name, 'action-2')
        self.assertEqual(action_3.name, 'to_save_check')

        # Expected variables
        variable_definition = VariableDefinition.objects.filter(module_definition=module_definition, name='bypwilklqf').first()
        self.assertIsNotNone(variable_definition)

        # Expected variable_choice_items
        variable_choice_item = VariableChoiceItem.objects.filter(value='a', variable_definition=variable_definition,).first()
        self.assertIsNotNone(variable_choice_item)

        self.assertEqual(variable_choice_item.translations.get(language=language_1).caption, "test caption")

        # Expected eras
        era = Era.objects.filter(module_definition=module_definition, name='era-0', action=action_1).first()
        self.assertIsNotNone(era)

        # Expected inputs
        module_definition_widget = ModuleDefinitionWidget.objects.filter(
            module_definition=module_definition, name='ModuleDefinitionWidgetZero', widget=preload_widget
        ).first()
        self.assertIsNotNone(module_definition_widget)

        # Expected module_events
        event = ModuleEvent.objects.filter(
            widget=module_definition_widget, event_type=ModuleEvent.REACT_EVENT_CHOICES.onChange
        ).first()
        self.assertIsNotNone(event)

        # Expected choice input items
        widget_choice = WidgetChoice.objects.filter(widget=module_definition_widget).first()
        self.assertIsNotNone(widget_choice)
        self.assertEqual(widget_choice.translations.get(language=language_1).caption, "test caption")
        # Expected stages
        stage_definition = StageDefinition.objects.filter(
            module_definition=module_definition, name='StageZero', pre_action=action_2
        ).first()
        self.assertIsNotNone(stage_definition)

        # Expected stagetemplates
        stage_template = StageTemplate.objects.filter(stage_definition=stage_definition, template=preload_template).first()
        self.assertIsNotNone(stage_template)

        # Expected stagetemplateblocks
        stage_template_block = StageTemplateBlock.objects.filter(stage_template=stage_template, name='TestStbOne').first()

        self.assertIsNotNone(stage_template_block)

        # Expected module single children
        self.assertEqual(module_definition.start_stage, stage_definition)
        self.assertEqual(module_definition.warden_stage, stage_definition)

        # Expected conditions
        condition_expression = Condition.objects.filter(
            module_definition=module_definition,
            left_type=Condition.TYPE_CHOICES.expression,
            name=preload_condition_expression.name,
        ).first()
        self.assertIsNotNone(condition_expression)
        condition_variable = Condition.objects.filter(
            module_definition=module_definition,
            left_type=Condition.TYPE_CHOICES.variable,
            name=preload_condition_variable.name,
        ).first()
        self.assertIsNotNone(condition_variable)
        condition_subcondition_1 = Condition.objects.filter(
            module_definition=module_definition,
            left_type='sub_condition',
            name=preload_condition_subcondition_1.name,
            left_sub_condition=condition_variable,
        ).first()
        self.assertIsNotNone(condition_subcondition_1)

        condition_subcondition_2 = Condition.objects.filter(
            module_definition=module_definition,
            left_type='sub_condition',
            name=preload_condition_subcondition_2.name,
            left_sub_condition=condition_subcondition_1,
        ).first()
        self.assertIsNotNone(condition_subcondition_2)

        condition_subcondition_3 = Condition.objects.filter(
            module_definition=module_definition,
            left_type='sub_condition',
            name=preload_condition_subcondition_3.name,
            left_sub_condition=condition_subcondition_2,
        ).first()

        self.assertIsNotNone(condition_subcondition_3)
        # Expected action steps
        actionstep1_2 = ActionStep.objects.filter(action=action_1, subaction=action_2, condition=condition_expression).first()
        self.assertIsNotNone(actionstep1_2)

        actionstep1_3 = ActionStep.objects.filter(
            action=action_1, variable_definition=variable_definition, condition=condition_variable
        ).first()
        self.assertIsNotNone(actionstep1_3)

        actionstep1_4 = ActionStep.objects.filter(action=action_1, era=era, condition=condition_expression).first()
        self.assertIsNotNone(actionstep1_4)

        actionstep1_5 = ActionStep.objects.filter(
            action=action_1, log_message='test-log', condition=condition_expression
        ).first()
        self.assertIsNotNone(actionstep1_5)
        actionstep3_1 = ActionStep.objects.filter(
            action=action_3, action_type=ActionStep.ACTION_TYPE_CHOICES.save_data
        ).first()
        self.assertIsNotNone(actionstep3_1)

        # Expected command
        command = module_definition.command_set.filter(name=command.name)
        self.assertTrue(command.exists())
        command = command.first()

        # Expected command templates
        self.assertEqual(command.command_templates.count(), 1)
        self.assertTrue(command.command_templates.first().blocks.filter(name='Content').exists())
        self.assertEqual(command.command_templates.first().blocks.get(name='Content').translations.count(), 1)
        self.assertTrue(command.command_templates.first().blocks.filter(name='OtherContent').exists())

        # Expected robots
        new_robot = module_definition.robots.filter(name='robotone').first()
        self.assertIsNotNone(new_robot)
        self.assertTrue(
            new_robot.rules.filter(rule_type=RobotRule.RULE_TYPE_CHOICES.static, widget=module_definition_widget).exists()
        )

        # Procedures
        self.assertTrue(module_definition.moduledefinitionprocedure_set.filter(name=alias.name).exists())
        self.assertTrue(module_definition.moduledefinitionprocedure_set.filter(name=alias2.name).exists())

        # Expected keywords
        for keyword in preload_keywords:
            self.assertIn(keyword, module_definition.keywords.all())

        # Expected form
        for form in preload_forms:
            new_form = module_definition.forms.get(name=form.name)
            # Items
            for item in form.items.all():
                # Fields
                if hasattr(item, 'field'):
                    self.assertIsNotNone(
                        new_form.items.get(order=item.order, field__name=item.field.name, tab_order=item.tab_order)
                    )
                    new_field = new_form.items.get(field__name=item.field.name, field__widget=item.field.widget.id).field
                    # Choices
                    for choice in item.field.choices.all():
                        new_choice = new_field.choices.get(value=choice.value, order=choice.order)
                        # Translations
                        for translation_language, translation_caption in choice.translations.values_list(
                            'language', 'caption'
                        ):
                            self.assertTrue(
                                new_choice.translations.filter(
                                    language=translation_language, caption=translation_caption
                                ).exists()
                            )
                # Button Lists
                elif hasattr(item, 'button_list'):
                    self.assertIsNotNone(
                        new_form.items.get(order=item.order, button_list__name=item.button_list.name, tab_order=item.tab_order)
                    )
                    new_button_list = new_form.items.get(button_list__name=item.button_list.name).button_list
                    # Buttons
                    for button_name, disable_name, hide_name in item.button_list.buttons.values_list(
                        'name', 'disable__name', 'hide__name'
                    ).all():
                        self.assertTrue(
                            new_button_list.buttons.filter(
                                name=button_name, disable__name=disable_name, hide__name=hide_name
                            ).exists()
                        )

    def test_touch(self):
        """Confirm that verisons are incremented on each save"""
        ver = self.module_definition.version
        self.module_definition.name = "NewNameModuleDef"
        self.module_definition.save()
        self.assertEqual(self.module_definition.version, ver + 1)

        action = ActionFactory(module_definition=self.module_definition, name='action-0')
        self.assertEqual(self.module_definition.version, ver + 2)

        action.name = "newNameAction"
        action.save()
        self.assertEqual(self.module_definition.version, ver + 3)

        actionstep = ActionStepFactory(action=action, action_type='save_vars')
        self.assertEqual(self.module_definition.version, ver + 5)

        actionstep.action_type = 'log'
        actionstep.save()
        self.assertEqual(self.module_definition.version, ver + 6)

    def test_has_stage(self):
        """
        Confirm stage lookups work properly.
        """
        self.assertTrue(self.module_definition.has_stage(self.module_definition.start_stage.name))
        self.assertFalse(self.module_definition.has_stage('orange_soda_factory'))


@unittest.skip("Address in issue #817")
class TestAutoGeneratedStartEra(EryTestCase):
    """
    Confirm era autogenerated on ModuleDefinition creation.
    """

    def test_auto_generation(self):
        module_definition = ModuleDefinition()
        module_definition.name = 'TestModuleDefinition'
        module_definition.primary_frontend = FrontendFactory()
        module_definition.default_template = TemplateFactory()
        module_definition.default_theme = ThemeFactory()
        self.assertIsNone(module_definition.start_era)
        module_definition.save()
        self.assertTrue(isinstance(module_definition.start_era, Era))

        # new era should not be generated on another save
        era_n = Era.objects.count()
        module_definition.save()
        self.assertEqual(era_n, Era.objects.count())


class TestGetWidgets(EryTestCase):
    def setUp(self):
        self.module_definition = ModuleDefinitionFactory()
        self.frontend1 = FrontendFactory()
        self.frontend2 = FrontendFactory()

    def test_get_widgets(self):
        """Confirm method is frontend specific"""
        nested_frontend1_widgets, nested_frontend2_widgets = [], []
        mw_1 = ModuleDefinitionWidgetFactory(
            module_definition=self.module_definition, widget=WidgetFactory(frontend=self.frontend1)
        )
        nested_frontend1_widgets += [
            WidgetConnectionFactory(originator=mw_1.widget, target=WidgetFactory(frontend=self.frontend1)).target
            for _ in range(random.randint(1, 10))
        ]
        nested_frontend1_widgets += [
            WidgetConnectionFactory(
                originator=random.choice(nested_frontend1_widgets), target=WidgetFactory(frontend=self.frontend1)
            ).target
            for _ in range(random.randint(1, 10))
        ]
        mw_2 = ModuleDefinitionWidgetFactory(
            module_definition=self.module_definition, widget=WidgetFactory(frontend=self.frontend1)
        )
        mw_3 = ModuleDefinitionWidgetFactory(
            module_definition=self.module_definition, widget=WidgetFactory(frontend=self.frontend2)
        )
        mw_4 = ModuleDefinitionWidgetFactory(
            module_definition=self.module_definition, widget=WidgetFactory(frontend=self.frontend2)
        )
        nested_frontend2_widgets += [
            WidgetConnectionFactory(originator=mw_4.widget, target=WidgetFactory(frontend=self.frontend2)).target
            for _ in range(random.randint(1, 10))
        ]
        nested_frontend2_widgets += [
            WidgetConnectionFactory(
                originator=random.choice(nested_frontend2_widgets), target=WidgetFactory(frontend=self.frontend2)
            ).target
            for _ in range(random.randint(1, 10))
        ]
        mw_5 = ModuleDefinitionWidgetFactory(
            module_definition=self.module_definition, widget=WidgetFactory(frontend=self.frontend2)
        )
        frontend1_widgets = self.module_definition.get_widgets(self.frontend1)
        frontend2_widgets = self.module_definition.get_widgets(self.frontend2)
        for module_definition_widget in (mw_1, mw_2):
            self.assertIn(module_definition_widget.widget, frontend1_widgets)
        for module_definition_widget in (mw_3, mw_4, mw_5):
            self.assertIn(module_definition_widget.widget, frontend2_widgets)
        for nested_frontend1_widget in nested_frontend1_widgets:
            self.assertIn(nested_frontend1_widget, frontend1_widgets)
        for nested_frontend2_widget in nested_frontend2_widgets:
            self.assertIn(nested_frontend2_widget, frontend2_widgets)
