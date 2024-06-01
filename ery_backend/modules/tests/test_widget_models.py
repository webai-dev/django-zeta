from unittest import mock
import unittest

from languages_plus.models import Language

from django.core.exceptions import ValidationError
from django.db import IntegrityError

from ery_backend.actions.factories import ActionFactory, ActionStepFactory
from ery_backend.actions.models import ActionStep
from ery_backend.base.testcases import EryTestCase, create_test_hands
from ery_backend.frontends.models import Frontend
from ery_backend.frontends.sms_utils import set_widget_variable
from ery_backend.hands.factories import HandFactory
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.users.factories import UserFactory
from ery_backend.variables.factories import VariableDefinitionFactory, VariableChoiceItemFactory, HandVariableFactory
from ery_backend.variables.models import VariableDefinition
from ery_backend.widgets.factories import WidgetFactory, WidgetEventFactory, WidgetEventStepFactory
from ery_backend.widgets.models import Widget, WidgetEvent, WidgetEventStep
from ..factories import (
    ModuleDefinitionWidgetFactory,
    ModuleEventFactory,
    WidgetChoiceFactory,
    WidgetChoiceTranslationFactory,
    ModuleEventStepFactory,
)
from ..models import WidgetChoice, ModuleDefinitionWidget, ModuleEvent, ModuleEventStep


class TestModuleDefinitionWidget(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)

    def setUp(self):
        self.hand = create_test_hands(n=1, signal_pubsub=False).first()
        self.language = Language.objects.get(pk='aa')
        self.hand.stint.stint_specification.language = self.language
        self.hand.stint.stint_specification.save()
        self.user = self.hand.user
        self.module_definition = self.hand.current_module_definition
        self.stint = self.hand.stint
        self.widget = WidgetFactory()
        self.variable_definition = VariableDefinitionFactory(
            module_definition=self.module_definition,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.choice,
            name='test_vd1',
            default_value=None,
        )
        self.variable_choice_item_1 = VariableChoiceItemFactory(variable_definition=self.variable_definition, value='a')
        self.variable_choice_item_2 = VariableChoiceItemFactory(variable_definition=self.variable_definition, value='b')
        self.variable_choice_item_3 = VariableChoiceItemFactory(variable_definition=self.variable_definition, value='c')
        self.variable_definition_str = VariableDefinitionFactory(
            module_definition=self.module_definition, data_type=VariableDefinition.DATA_TYPE_CHOICES.str
        )
        self.module_definition_widget = ModuleDefinitionWidgetFactory(
            required_widget=True,
            initial_value='starting-val',
            random_mode=ModuleDefinitionWidget.RANDOM_CHOICES.desc,
            widget=self.widget,
            variable_definition=self.variable_definition,
            module_definition=self.module_definition,
        )
        self.widget_choice = WidgetChoiceFactory(widget=self.module_definition_widget, order=0, value='a')
        WidgetChoiceTranslationFactory(widget_choice=self.widget_choice, language=self.language)
        self.widget_choice2 = WidgetChoiceFactory(widget=self.module_definition_widget, order=1, value='b')
        WidgetChoiceTranslationFactory(widget_choice=self.widget_choice2, language=self.language)
        self.widget_choice3 = WidgetChoiceFactory(widget=self.module_definition_widget, order=2, value='c')
        WidgetChoiceTranslationFactory(widget_choice=self.widget_choice3, language=self.language)

    def test_exists(self):
        self.assertIsNotNone(self.module_definition_widget)

    def test_expected_attributes(self):
        self.assertTrue(self.module_definition_widget.required_widget)
        self.assertEqual(self.module_definition_widget.initial_value, 'starting-val')
        self.assertEqual(self.module_definition_widget.random_mode, ModuleDefinitionWidget.RANDOM_CHOICES.desc)
        self.assertEqual(self.module_definition_widget.widget, self.widget)

    @unittest.skip("Address in issue #813")
    def test_expected_save_errors(self):
        # switching variable_definition from nonchoice to choice
        variable_definition_str = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.str)
        module_definition_widget = ModuleDefinitionWidgetFactory(variable_definition=variable_definition_str)

        # switching variable_definition type from nonchoice to choice, without VariableChoiceItems
        module_definition_widget.variable_definition = variable_definition_str
        with self.assertRaises(ValidationError):
            # Otherwise EryValueError due to no choice items for default_value
            module_definition_widget.variable_definition.default_value = None
            module_definition_widget.variable_definition.save()
            module_definition_widget.variable_definition.data_type = VariableDefinition.DATA_TYPE_CHOICES.choice
            module_definition_widget.variable_definition.save()

    def test_get_choices_as_extra_variable(self):
        """
        Confirm WidgetChoices are converted to a dictionary with name(choices), value(choice info)
        """
        choices = self.module_definition_widget.get_choices(Language.objects.first())
        expected_results = self.module_definition_widget.get_choices_as_extra_variable(choices)
        self.assertEqual(expected_results, {'choices': choices})

    def test_is_multiple_choice(self):
        """
        Confirm correct boolean returned by input.is_multiple_choice.
        """
        # Should pass so long as WidgetChoices exist
        self.assertTrue(self.module_definition_widget.choices.exists())
        self.assertTrue(self.module_definition_widget.is_multiple_choice)

        # Should not fail still if there are no WidgetChoices as it is a VariableDefinition with data_type set to 'choice'
        self.module_definition_widget.choices.all().delete()

        # No widget choices, but variable choice items present
        self.assertTrue(self.module_definition_widget.is_multiple_choice)

        # Should fail still as there are no WidgetChoices and the VariableDefinition has not data_type set to 'choice'
        self.module_definition_widget.variable_definition = self.variable_definition_str
        # No widget choices, but variable choice items present
        self.assertFalse(self.module_definition_widget.is_multiple_choice)

    def test_get_choices(self):
        """
        Confirm expected results for each randomization option in ModuleDefinitionWidget.get_choices.
        """
        language = self.module_definition.primary_language

        # ascending results
        self.module_definition_widget.random_mode = ModuleDefinitionWidget.RANDOM_CHOICES.asc
        asc_results = [
            {'value': choice.value, 'caption': choice.get_translation(language)}
            for choice in [self.widget_choice, self.widget_choice2, self.widget_choice3]
        ]
        self.assertEqual(self.module_definition_widget.get_choices(language=language), asc_results)

        # descending results
        self.module_definition_widget.random_mode = ModuleDefinitionWidget.RANDOM_CHOICES.desc
        desc_results = [
            {'value': choice.value, 'caption': choice.get_translation(language)}
            for choice in [self.widget_choice3, self.widget_choice2, self.widget_choice]
        ]
        self.assertEqual(self.module_definition_widget.get_choices(language=language), desc_results)

        # shuffled results
        self.module_definition_widget.random_mode = ModuleDefinitionWidget.RANDOM_CHOICES.shuffle
        equals = True  # Asserts all results are always equal
        mdw = self.module_definition_widget
        for _ in range(100):
            result = mdw.get_choices(language=language) == mdw.get_choices(language=language)
            if not result:
                equals = False
                break
        self.assertFalse(equals)

        # random ascend/descend results
        self.module_definition_widget.random_mode = ModuleDefinitionWidget.RANDOM_CHOICES.random_asc_desc
        equals = False  # Assert results don't match any of expected results
        output = self.module_definition_widget.get_choices(language=language)
        if output in (asc_results, desc_results):
            equals = True
        self.assertTrue(equals)

    @staticmethod
    def get_translation(widget_choice, language):
        return widget_choice.translations.get(language=language)

    def test_get_choices_by_language(self):
        correct_lang = Language.objects.get(iso_639_1='aa')
        incorrect_lang = Language.objects.get(iso_639_1='ab')
        default_lang = self.module_definition.primary_language
        module_definition_widget = ModuleDefinitionWidgetFactory(
            variable_definition=self.variable_definition, random_mode=ModuleDefinitionWidget.RANDOM_CHOICES.random_asc_desc
        )
        widget_choice1 = WidgetChoiceFactory(widget=module_definition_widget, value='a', order=1)
        widget_choice1_correct = WidgetChoiceTranslationFactory(
            widget_choice=widget_choice1, caption='Correct One', language=correct_lang
        )
        WidgetChoiceTranslationFactory(widget_choice=widget_choice1, caption='Incorrect One', language=incorrect_lang)

        WidgetChoiceTranslationFactory(widget_choice=widget_choice1, caption='Default One', language=default_lang)
        # Get one choice of correct with correct translation caption (when other caption exists)
        choices = module_definition_widget.get_choices(language=correct_lang)
        self.assertIn({'value': widget_choice1.value, 'caption': widget_choice1_correct.caption}, choices)

        # Return value when desired translation does not exist to provide caption
        widget_choice2 = WidgetChoiceFactory(widget=module_definition_widget, value='b', order=2)
        WidgetChoiceTranslationFactory(widget_choice=widget_choice2, language=default_lang, caption='Also Correct')
        choices_2 = module_definition_widget.get_choices(language=self.language)
        self.assertIn({'value': widget_choice2.value, 'caption': widget_choice2.value}, choices_2)

    def test_expected_get_choices_errors(self):
        # Does not pass multiple choice check
        str_vd = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.str)
        no_choice_input = ModuleDefinitionWidgetFactory(
            variable_definition=str_vd, random_mode=ModuleDefinitionWidget.RANDOM_CHOICES.asc
        )
        with self.assertRaises(TypeError):
            no_choice_input.get_choices()

    def test_get_privilege_ancestor(self):
        self.assertEqual(
            self.module_definition_widget.get_privilege_ancestor(), self.module_definition_widget.module_definition
        )

    def test_get_privilege_ancestor_cls(self):
        self.assertEqual(
            self.module_definition_widget.get_privilege_ancestor_cls(),
            self.module_definition_widget.module_definition.__class__,
        )

    def test_get_privilege_ancestor_filter_path(self):
        self.assertEqual(self.module_definition_widget.get_privilege_ancestor_filter_path(), 'module_definition')

    def test_duplicate(self):
        input_2 = self.module_definition_widget.duplicate()
        self.assertIsNotNone(input_2)
        self.assertEqual(input_2.module_definition, self.module_definition_widget.module_definition)
        self.assertEqual(input_2.widget, self.module_definition_widget.widget)
        self.assertNotEqual(input_2, self.module_definition_widget)
        self.assertEqual(input_2.name, '{}Copy'.format(self.module_definition_widget.name))
        widget_choice_2 = WidgetChoice.objects.filter(widget=input_2, value='a').first()
        self.assertIsNotNone(widget_choice_2)
        self.assertEqual(self.widget_choice.value, widget_choice_2.value)
        # Children should not be equivalent
        self.assertNotEqual(self.widget_choice, widget_choice_2)
        # Parents should be equivalent
        self.assertEqual(self.widget_choice.widget.module_definition, widget_choice_2.widget.module_definition)

    def test_import(self):
        xml = open('ery_backend/modules/tests/data/module_definition-w-1.bxml', 'rb')
        widget = Widget.import_instance_from_xml(xml, name='InstanceNew')

        self.assertIsNotNone(widget)
        self.assertEqual(widget.name, 'InstanceNew')


class TestModuleDefinitionWidgetNumericTypes(EryTestCase):
    @staticmethod
    def test_numeric_types():
        """
        Confirm ModuleDefinitionWidget.variable_definition can be of type int or float.
        """
        ModuleDefinitionWidgetFactory(variable_definition__data_type=VariableDefinition.DATA_TYPE_CHOICES.float)
        ModuleDefinitionWidgetFactory(variable_definition__data_type=VariableDefinition.DATA_TYPE_CHOICES.int)

    def test_numeric_values(self):
        """
        Confirm type checking for ModuleDefinitionWidget.variable_definition values.
        """
        hand = create_test_hands(n=1, signal_pubsub=False).first()
        float_vd = VariableDefinitionFactory(
            data_type=VariableDefinition.DATA_TYPE_CHOICES.float, scope=VariableDefinition.SCOPE_CHOICES.hand
        )
        float_input = ModuleDefinitionWidgetFactory(variable_definition=float_vd)
        HandVariableFactory(hand=hand, variable_definition=float_vd, value=None)
        with self.assertRaises(ValueError):
            set_widget_variable(hand, float_input, 'clearlynotafloat')
        set_widget_variable(hand, float_input, 3.2)

        int_vd = VariableDefinitionFactory(
            data_type=VariableDefinition.DATA_TYPE_CHOICES.int, scope=VariableDefinition.SCOPE_CHOICES.hand
        )
        int_input = ModuleDefinitionWidgetFactory(variable_definition=int_vd)
        HandVariableFactory(hand=hand, variable_definition=int_vd, value=None)
        with self.assertRaises(ValueError):
            set_widget_variable(hand, int_input, 'clearlynotanint')
        set_widget_variable(hand, int_input, 3)


class TestWidgetChoice(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.language = Language.objects.get(pk='en')

    def setUp(self):
        self.variable_definition = VariableDefinitionFactory(
            data_type=VariableDefinition.DATA_TYPE_CHOICES.choice, default_value=None
        )
        self.variable_choice_item = VariableChoiceItemFactory(variable_definition=self.variable_definition, value='a')
        self.module_definition_widget = ModuleDefinitionWidgetFactory(variable_definition=self.variable_definition)
        self.widget_choice = WidgetChoiceFactory(widget=self.module_definition_widget, value='a', order=2,)

    def test_exists(self):
        self.assertIsNotNone(self.widget_choice)

    def test_expected_attributes(self):
        self.assertEqual(self.widget_choice.widget, self.module_definition_widget)
        self.assertEqual(self.widget_choice.value, 'a')
        self.assertEqual(self.widget_choice.order, 2)

    def test_get_info(self):
        WidgetChoiceTranslationFactory(widget_choice=self.widget_choice, caption='this one', language=self.language)
        self.assertEqual(
            self.widget_choice.get_info(self.language),
            {'value': self.widget_choice.value, 'caption': self.widget_choice.get_translation(self.language)},
        )

    def test_get_privileged_ancestor(self):
        self.assertEqual(self.widget_choice.get_privilege_ancestor(), self.widget_choice.widget.module_definition)

    def test_get_privilege_ancestor_cls(self):
        self.assertEqual(
            self.widget_choice.get_privilege_ancestor_cls(), self.widget_choice.widget.module_definition.__class__
        )

    def test_get_privilege_ancestor_filter_path(self):
        self.assertEqual(self.widget_choice.get_privilege_ancestor_filter_path(), 'widget__module_definition')

    @unittest.skip("XXX: Address in issue #813")
    def test_expected_save_errors(self):
        """
        Confirm expected errors on save.
        """
        variable_definition = VariableDefinitionFactory(
            data_type=VariableDefinition.DATA_TYPE_CHOICES.choice, name='test_vd', default_value=None
        )
        # No VariableChoiceItems
        with self.assertRaises(ValidationError):
            module_definition_widget = ModuleDefinitionWidget.objects.create(
                variable_definition=variable_definition,
                module_definition=variable_definition.module_definition,
                name='TestMDWidget',
            )

        # Outside of subset
        VariableChoiceItemFactory(variable_definition=variable_definition, value='a')
        module_definition_widget = ModuleDefinitionWidgetFactory(variable_definition=variable_definition)
        with self.assertRaises(ValueError):
            WidgetChoiceFactory(widget=module_definition_widget, value='b')

    def test_get_translation(self):
        """
        Confirm get_translation returns expected translation or value if Does Not Exist.
        """
        # Confirm intended translation returned if exists
        WidgetChoiceTranslationFactory(widget_choice=self.widget_choice, caption='this one', language=self.language)
        preferred = WidgetChoiceTranslationFactory(
            widget_choice=self.widget_choice, caption='not this one', language=Language.objects.get(pk='aa')
        )
        self.assertEqual(self.widget_choice.get_translation(language=Language.objects.get(pk='aa')), preferred.caption)

        # Confirm value returned if requested Does Not Exist
        self.assertEqual(self.widget_choice.get_translation(Language.objects.get(pk='ab')), self.widget_choice.value)

    def test_unique_together(self):
        variable_definition = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.str)
        module_definition_widget = ModuleDefinitionWidgetFactory(
            variable_definition=variable_definition, module_definition=variable_definition.module_definition
        )
        WidgetChoiceFactory(widget=module_definition_widget, value='a', order=1)
        with self.assertRaises(IntegrityError):
            WidgetChoiceFactory(widget=module_definition_widget, value='a')

    def test_caseinsensitive_uniqueness(self):
        """
        Confirm value uniqueness is case insensitive within input.
        """
        variable_definition = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.str)
        widget = ModuleDefinitionWidgetFactory(variable_definition=variable_definition)
        WidgetChoiceFactory(widget=widget, value='TomAto', order=1)
        with self.assertRaises(IntegrityError):
            WidgetChoiceFactory(widget=widget, value='Tomato', order=2)


class TestWidgetChoiceTranslation(EryTestCase):
    def setUp(self):
        self.widget_choice = WidgetChoiceFactory()
        self.widget_choice_translation = WidgetChoiceTranslationFactory(
            widget_choice=self.widget_choice, caption='Choice Un', language=Language.objects.first()
        )

    def test_exists(self):
        self.assertIsNotNone(self.widget_choice_translation)

    def test_expected_attributes(self):
        self.assertEqual(self.widget_choice_translation.widget_choice, self.widget_choice)
        self.assertEqual(self.widget_choice_translation.language, Language.objects.first())
        self.assertEqual(self.widget_choice_translation.caption, 'Choice Un')

    def test_unique_togther(self):
        variable_definition = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.choice)
        widget = ModuleDefinitionWidgetFactory(variable_definition=variable_definition)
        widget_choice = WidgetChoiceFactory(widget=widget)
        WidgetChoiceTranslationFactory(widget_choice=widget_choice, language=Language.objects.first())
        with self.assertRaises(IntegrityError):
            WidgetChoiceTranslationFactory(widget_choice=widget_choice, language=Language.objects.first())


class TestModuleEvent(EryTestCase):
    def setUp(self):
        self.module_definition = ModuleDefinitionFactory()
        self.variable_definition = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.str)
        self.module_definition_widget = ModuleDefinitionWidgetFactory(
            variable_definition=self.variable_definition, module_definition=self.module_definition
        )
        self.module_event = ModuleEventFactory(
            name=ModuleEvent.REACT_EVENT_CHOICES.onSubmit, widget=self.module_definition_widget
        )

    def test_exists(self):
        self.assertIsNotNone(self.module_event)

    def test_expected_attributes(self):
        self.module_event.refresh_from_db()

        self.assertEqual(self.module_event.name, ModuleEvent.REACT_EVENT_CHOICES.onSubmit)
        self.assertEqual(self.module_event.widget, self.module_definition_widget)

    def test_get_privilege_ancestor(self):
        self.assertEqual(self.module_event.get_privilege_ancestor(), self.module_event.widget.module_definition)

    def test_get_privilege_ancestor_cls(self):
        self.assertEqual(self.module_event.get_privilege_ancestor_cls(), self.module_event.widget.module_definition.__class__)

    def test_get_privilege_ancestor_filter_path(self):
        self.assertEqual(self.module_event.get_privilege_ancestor_filter_path(), 'widget__module_definition')

    def test_format(self):
        """Confirm adheres to React naming conventions"""
        with self.assertRaises(ValidationError):
            ModuleEventFactory(name='all_the_way_left')
        with self.assertRaises(ValidationError):
            ModuleEventFactory(name='1LeftWithNumbers')
        with self.assertRaises(ValidationError):
            ModuleEventFactory(name='left With Spaces')

    def test_unique_together(self):
        """Two widget_events cannot have the same name, event_type for the same widget"""
        # This is fine
        web = Frontend.objects.get(name='Web')
        widget = WidgetFactory(frontend=web)
        module_widget = ModuleDefinitionWidgetFactory(widget=widget)

        ModuleEventFactory(name='starting', widget=module_widget, event_type=ModuleEvent.REACT_EVENT_CHOICES.onChange)
        ModuleEventFactory(name='starting', widget=module_widget, event_type=ModuleEvent.REACT_EVENT_CHOICES.onClick)

        # Also fine
        widget_a = WidgetFactory(frontend=web)
        widget_b = WidgetFactory(frontend=web)
        module_widget_a = ModuleDefinitionWidgetFactory(widget=widget_a)
        module_widget_b = ModuleDefinitionWidgetFactory(widget=widget_b)
        ModuleEventFactory(name='starting', widget=module_widget_a, event_type=ModuleEvent.REACT_EVENT_CHOICES.onChange)
        ModuleEventFactory(name='starting', widget=module_widget_b, event_type=ModuleEvent.REACT_EVENT_CHOICES.onChange)

        # This is not
        widget_a = WidgetFactory(frontend=web)
        module_widget_a = ModuleDefinitionWidgetFactory(widget=widget_a)
        ModuleEventFactory(name='starting', widget=module_widget_a, event_type=ModuleEvent.REACT_EVENT_CHOICES.onChange)
        with self.assertRaises(IntegrityError):
            ModuleEventFactory(name='starting', widget=module_widget_a, event_type=ModuleEvent.REACT_EVENT_CHOICES.onChange)


class TestModuleEventStep(EryTestCase):
    def setUp(self):
        self.module_definition = ModuleDefinitionFactory()
        self.action = ActionFactory(module_definition=self.module_definition)
        self.variable_definition = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.str)
        self.module_definition_widget = ModuleDefinitionWidgetFactory(
            variable_definition=self.variable_definition, module_definition=self.module_definition
        )
        self.module_event = ModuleEventFactory(widget=self.module_definition_widget)
        self.event_step = ModuleEventStepFactory(
            module_event=self.module_event,
            action=self.action,
            order=4,
            event_action_type=ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.run_action,
        )

    def test_exists(self):
        self.assertIsNotNone(self.module_event)

    def test_expected_attributes(self):
        self.event_step.refresh_from_db()
        self.assertEqual(self.event_step.action, self.action)
        self.assertEqual(self.event_step.module_event, self.module_event)
        self.assertEqual(self.event_step.event_action_type, ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.run_action)
        self.assertEqual(self.event_step.order, 4)

    # XXX: Address in issue #813
    # def test_expected_errors(self):
    #     # Cannot be save_var type if no variable_definition
    #     widget = ModuleDefinitionWidgetFactory(variable_definition=None)
    #     module_event = ModuleEventFactory(widget=widget)
    #     with self.assertRaises(ValidationError):
    #         ModuleEventStepFactory(
    #             module_event=module_event, event_action_type=ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.save_var)

    #     # Cannot be run_action type if no action
    #     with self.assertRaises(ValidationError):
    #         ModuleEventStepFactory(
    #             action=None, event_action_type=ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.run_action,
    #             module_event=module_event)

    def test_get_privilege_ancestor(self):
        self.assertEqual(self.event_step.get_privilege_ancestor(), self.event_step.module_event.widget.module_definition)

    def test_get_privilege_ancestor_cls(self):
        self.assertEqual(
            self.event_step.get_privilege_ancestor_cls(), self.event_step.module_event.widget.module_definition.__class__
        )

    def test_get_privilege_ancestor_filter_path(self):
        self.assertEqual(self.event_step.get_privilege_ancestor_filter_path(), 'module_event__widget__module_definition')

    def test_save_var(self):
        hand_vd = VariableDefinitionFactory(
            scope=VariableDefinition.SCOPE_CHOICES.hand, data_type=VariableDefinition.DATA_TYPE_CHOICES.str, validator=None
        )
        hand_var = HandVariableFactory(variable_definition=hand_vd, hand=HandFactory(user=UserFactory()))
        md_widget = ModuleDefinitionWidgetFactory(
            module_definition=hand_var.hand.current_module_definition, variable_definition=hand_vd
        )
        module_event = ModuleEventFactory(widget=md_widget, name=ModuleEvent.REACT_EVENT_CHOICES.onClick,)
        ModuleEventStepFactory(module_event=module_event, event_action_type=ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.save_var)
        module_event.trigger(hand_var.hand, value='nine')
        hand_var.refresh_from_db()
        self.assertEqual(hand_var.value, 'nine')

    @mock.patch('ery_backend.actions.models.ActionStep._interpret_value')
    def test_run_action(self, mock_interpret):
        hand = HandFactory(user=UserFactory())
        value = 'answers found here'
        mock_interpret.return_value = value
        hand_vd = VariableDefinitionFactory(
            scope=VariableDefinition.SCOPE_CHOICES.hand, data_type=VariableDefinition.DATA_TYPE_CHOICES.str, validator=None
        )
        hand_var = HandVariableFactory(variable_definition=hand_vd, hand=hand)
        action = ActionFactory(module_definition=hand_var.hand.current_module_definition)
        ActionStepFactory(
            action=action,
            action_type=ActionStep.ACTION_TYPE_CHOICES.set_variable,
            value=f"'{value}'",
            condition=None,
            variable_definition=hand_vd,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
        )
        self.assertNotEqual(value, hand_var.value)
        md_widget = ModuleDefinitionWidgetFactory(module_definition=hand_var.hand.current_module_definition)

        event = ModuleEventFactory(widget=md_widget, event_type=ModuleEvent.REACT_EVENT_CHOICES.onClick)
        ModuleEventStepFactory(
            event_action_type=ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.run_action, action=action, module_event=event
        )
        event.trigger(hand_var.hand)
        hand_var.refresh_from_db()
        self.assertEqual(hand_var.value, value)

    def test_execution_order(self):
        """
        Steps should be executed in order.
        """
        hand = create_test_hands(module_definition_n=1, stage_n=3, redirects=True).first()
        stagedef_1, stagedef_2, _ = list(hand.current_module_definition.stage_definitions.order_by('id').all())
        module_event = ModuleEventFactory()
        me_step_1 = ModuleEventStepFactory(
            event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.back, module_event=module_event
        )
        me_step_2 = ModuleEventStepFactory(
            event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.submit, module_event=module_event
        )
        self.assertTrue(me_step_1.order < me_step_2.order)
        self.assertEqual(hand.stage.stage_definition, stagedef_1)
        module_event.trigger(hand)
        hand.refresh_from_db()
        self.assertEqual(hand.stage.stage_definition, stagedef_2)
        me_step_1.order = 3
        me_step_1.save()
        me_step_2.order = 2
        me_step_2.save()
        self.assertTrue(me_step_1.order > me_step_2.order)
        hand.set_stage(stage_definition=stagedef_1)
        hand.refresh_from_db()
        self.assertEqual(hand.stage.stage_definition, stagedef_1)
        module_event.trigger(hand)
        hand.refresh_from_db()
        self.assertEqual(hand.stage.stage_definition, stagedef_2)


class TestBackProgression(EryTestCase):
    def setUp(self):
        self.hand = create_test_hands(stage_n=2, signal_pubsub=False).first()
        self.initial_stage = self.hand.stage
        self.last_stage_def = self.hand.current_module_definition.stage_definitions.last()
        self.hand.set_stage(stage_definition=self.last_stage_def)
        self.hand.refresh_from_db()
        self.assertEqual(self.hand.stage.stage_definition, self.last_stage_def)
        breadcrumb = self.hand.create_breadcrumb(self.hand.stage)
        self.hand.set_breadcrumb(breadcrumb)
        self.module_widget = ModuleDefinitionWidgetFactory(module_definition=self.hand.current_module_definition)
        self.module_event = ModuleEventFactory(widget=self.module_widget)
        ModuleEventStepFactory(
            module_event=self.module_event, event_action_type=ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.back
        )

    def test_back_progression(self):
        self.module_widget.trigger_events(self.module_event.name, self.module_event.event_type, self.hand)
        self.hand.refresh_from_db()
        self.assertEqual(self.hand.stage, self.initial_stage)


class TestForwardProgression(EryTestCase):
    def setUp(self):
        self.hand = create_test_hands(stage_n=2, redirects=True, signal_pubsub=False).first()
        self.last_stage_def = self.hand.current_module_definition.stage_definitions.last()
        self.module_widget = ModuleDefinitionWidgetFactory(module_definition=self.hand.current_module_definition)
        self.module_event = ModuleEventFactory(widget=self.module_widget)
        ModuleEventStepFactory(
            module_event=self.module_event, event_action_type=ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.submit
        )

    @mock.patch('ery_backend.hands.models.Hand.pay')
    def test_forward_progression(self, mock_pay):
        self.module_widget.trigger_events(self.module_event.name, self.module_event.event_type, self.hand)
        self.hand.refresh_from_db()
        self.assertEqual(self.hand.stage.stage_definition, self.last_stage_def)


class TestTriggerEvents(EryTestCase):
    """
    Confirm ModuleEvents and contained WidgetEvents are run as a result of running ModuleWidget.trigger_events.
    """

    def setUp(self):
        self.widget = WidgetFactory()
        self.mw = ModuleDefinitionWidgetFactory(widget=self.widget)
        self.hand = HandFactory()

    @mock.patch('ery_backend.modules.widgets.ModuleEvent.trigger', autospec=True)
    @mock.patch('ery_backend.widgets.models.WidgetEvent.trigger', autospec=True)
    def test_one_of_each_event(self, mock_trigger, mock_module_trigger):
        """
        One ModuleEvent and one WidgetEvent
        """
        module_widget_event_1 = ModuleEventFactory(widget=self.mw)
        widget_event_1 = WidgetEventFactory(
            widget=self.widget, event_type=module_widget_event_1.event_type, name=module_widget_event_1.name
        )
        self.mw.trigger_events(module_widget_event_1.name, module_widget_event_1.event_type, hand=self.hand, value=23)
        mock_trigger.assert_called_with(widget_event_1, self.hand)
        mock_module_trigger.assert_called_with(module_widget_event_1, self.hand, value=23)

    @mock.patch('ery_backend.modules.widgets.ModuleEvent.trigger', autospec=True)
    @mock.patch('ery_backend.widgets.models.WidgetEvent.trigger', autospec=True)
    def test_many_steps(self, mock_trigger, mock_module_trigger):
        on_click_widget_event = WidgetEventFactory(widget=self.widget, event_type=WidgetEvent.REACT_EVENT_CHOICES.onClick)
        WidgetEventStepFactory(
            widget_event=on_click_widget_event, event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.run_code
        )
        WidgetEventStepFactory(
            widget_event=on_click_widget_event, event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.submit
        )
        on_change_widget_event = WidgetEventFactory(
            widget=self.widget, event_type=WidgetEvent.REACT_EVENT_CHOICES.onChange, name=on_click_widget_event.name
        )
        WidgetEventStepFactory(
            widget_event=on_change_widget_event, event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.run_code
        )

        on_click_module_event = ModuleEventFactory(
            widget=self.mw, event_type=ModuleEvent.REACT_EVENT_CHOICES.onClick, name=on_click_widget_event.name
        )
        ModuleEventStepFactory(
            module_event=on_click_module_event, event_action_type=ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.save_var
        )
        ModuleEventStepFactory(
            module_event=on_click_module_event, event_action_type=ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.submit
        )

        on_change_module_event = ModuleEventFactory(
            widget=self.mw, event_type=ModuleEvent.REACT_EVENT_CHOICES.onChange, name=on_click_widget_event.name
        )
        ModuleEventStepFactory(
            module_event=on_change_module_event, event_action_type=ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.submit
        )

        self.mw.trigger_events(on_click_widget_event.name, ModuleEvent.REACT_EVENT_CHOICES.onClick, hand=self.hand, value=23)
        mock_trigger.assert_any_call(on_click_widget_event, self.hand)
        # Wrong event
        with self.assertRaises(AssertionError):
            mock_trigger.assert_any_call(on_change_widget_event, self.hand)

        mock_module_trigger.assert_any_call(on_click_module_event, self.hand, value=23)
        # Wrong event
        with self.assertRaises(AssertionError):
            mock_module_trigger.assert_any_call(on_change_module_event, self.hand, value=23)

        # With event call change, other events objs should work
        self.mw.trigger_events(on_click_widget_event.name, ModuleEvent.REACT_EVENT_CHOICES.onChange, hand=self.hand, value=23)
        mock_trigger.assert_any_call(on_change_widget_event, self.hand)
        mock_module_trigger.assert_any_call(on_change_module_event, self.hand, value=23)
