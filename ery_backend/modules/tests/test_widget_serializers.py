from ery_backend.actions.factories import ActionFactory
from ery_backend.base.testcases import EryTestCase
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.users.factories import UserFactory
from ery_backend.variables.factories import VariableDefinitionFactory, VariableChoiceItemFactory
from ery_backend.variables.models import VariableDefinition
from ery_backend.widgets.factories import WidgetFactory
from ..factories import (
    ModuleDefinitionWidgetFactory,
    ModuleEventFactory,
    WidgetChoiceFactory,
    WidgetChoiceTranslationFactory,
    ModuleEventStepFactory,
)
from ..models import ModuleEvent, ModuleEventStep, ModuleDefinitionWidget, WidgetChoice, WidgetChoiceTranslation


class TestModuleDefinitionWidgetBXMLSerializer(EryTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.module_definition = ModuleDefinitionFactory()
        self.widget = WidgetFactory()
        self.variable_definition = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.str)
        self.module_definition_widget = ModuleDefinitionWidgetFactory(
            module_definition=self.module_definition, widget=self.widget, variable_definition=self.variable_definition
        )
        self.module_definition_widget_serializer = ModuleDefinitionWidget.get_bxml_serializer()(self.module_definition_widget)

    def test_exists(self):
        self.assertIsNotNone(self.module_definition_widget_serializer)

    def test_expected_attributes(self):
        self.module_definition_widget.refresh_from_db()
        self.assertEqual(self.module_definition_widget_serializer.data['name'], self.module_definition_widget.name)
        self.assertEqual(self.module_definition_widget_serializer.data['comment'], self.module_definition_widget.comment)
        self.assertEqual(
            self.module_definition_widget_serializer.data['required_widget'], self.module_definition_widget.required_widget
        )
        self.assertEqual(
            self.module_definition_widget_serializer.data['initial_value'], self.module_definition_widget.initial_value
        )
        self.assertEqual(
            self.module_definition_widget_serializer.data['random_mode'], self.module_definition_widget.random_mode
        )
        self.assertEqual(self.module_definition_widget_serializer.data['widget'], self.module_definition_widget.widget.slug)


class TestWidgetChoiceBXMLSerializer(EryTestCase):
    def setUp(self):
        self.variable_definition = VariableDefinitionFactory(
            data_type=VariableDefinition.DATA_TYPE_CHOICES.choice, default_value=None
        )
        self.variable_choice_item = VariableChoiceItemFactory(variable_definition=self.variable_definition, value='a')
        self.module_definition_widget = ModuleDefinitionWidgetFactory(variable_definition=self.variable_definition)
        self.widget_choice = WidgetChoiceFactory(widget=self.module_definition_widget, value='a')
        self.widget_choice_serializer = WidgetChoice.get_bxml_serializer()(self.widget_choice)

    def test_exists(self):
        self.assertIsNotNone(self.widget_choice_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.widget_choice_serializer.data['order'], self.widget_choice.order)
        self.assertEqual(self.widget_choice_serializer.data['value'], self.widget_choice.value)


class TestWidgetChoiceTranslationBXMLSerializer(EryTestCase):
    def setUp(self):
        self.widget_choice = WidgetChoiceFactory()
        self.widget_choice_translation = WidgetChoiceTranslationFactory(widget_choice=self.widget_choice)
        self.widget_choice_translation_serializer = WidgetChoiceTranslation.get_bxml_serializer()(
            self.widget_choice_translation
        )

    def test_exists(self):
        self.assertIsNotNone(self.widget_choice_translation_serializer)

    def test_expected_attributes(self):
        self.assertEqual(
            self.widget_choice_translation_serializer.data['language'], self.widget_choice_translation.language.iso_639_1
        )
        self.assertEqual(self.widget_choice_translation_serializer.data['caption'], self.widget_choice_translation.caption)


class TestModuleEventBXMLSerializer(EryTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.action = ActionFactory()
        self.module_definition = ModuleDefinitionFactory()
        self.variable_definition = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.str)
        self.module_definition_widget = ModuleDefinitionWidgetFactory(variable_definition=self.variable_definition)
        self.event = ModuleEventFactory(widget=self.module_definition_widget)
        self.event_serializer = ModuleEvent.get_bxml_serializer()(self.event)

    def test_exists(self):
        self.assertIsNotNone(self.event_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.event_serializer.data['event_type'], self.event.event_type)


class TestModuleEventStepBXMLSerializer(EryTestCase):
    def setUp(self):
        self.module_event_step = ModuleEventStepFactory(event_action_type=ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.run_action)
        self.module_event_step_serializer = ModuleEventStep.get_bxml_serializer()(self.module_event_step)

    def test_exists(self):
        self.assertIsNotNone(self.module_event_step_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.module_event_step_serializer.data['event_action_type'], self.module_event_step.event_action_type)
