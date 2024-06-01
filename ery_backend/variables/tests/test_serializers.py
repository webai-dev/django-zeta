import json

from languages_plus.models import Language

from ery_backend.base.testcases import EryTestCase
from ery_backend.validators.factories import ValidatorFactory
from ..factories import VariableDefinitionFactory, VariableChoiceItemFactory, VariableChoiceItemTranslationFactory
from ..models import VariableDefinition, VariableChoiceItem, VariableChoiceItemTranslation


class TestVariableDefinitionSerializer(EryTestCase):
    def setUp(self):
        self.validator = ValidatorFactory(code=None)
        self.variable_definition = VariableDefinitionFactory(validator=self.validator)
        self.variable_definition_serializer = VariableDefinition.get_bxml_serializer()(self.variable_definition)

    def test_exists(self):
        self.assertIsNotNone(self.variable_definition_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.variable_definition_serializer.data['name'], self.variable_definition.name)
        self.assertEqual(self.variable_definition_serializer.data['comment'], self.variable_definition.comment)
        self.assertEqual(self.variable_definition_serializer.data['validator'], self.variable_definition.validator.slug)
        serialized_default_value = self.variable_definition_serializer.data['default_value']
        serialized_default_value = json.loads(serialized_default_value)
        self.assertEqual(serialized_default_value, self.variable_definition.default_value)
        self.assertEqual(self.variable_definition_serializer.data['specifiable'], self.variable_definition.specifiable)
        self.assertEqual(self.variable_definition_serializer.data['is_payoff'], self.variable_definition.is_payoff)
        self.assertEqual(self.variable_definition_serializer.data['is_output_data'], self.variable_definition.is_output_data)
        self.assertEqual(self.variable_definition_serializer.data['scope'], self.variable_definition.scope)
        self.assertEqual(self.variable_definition_serializer.data['data_type'], self.variable_definition.data_type)


class TestVariableChoiceItemSerializer(EryTestCase):
    def setUp(self):
        self.variable_definition = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.choice)
        self.variable_choice_item = VariableChoiceItemFactory(variable_definition=self.variable_definition)
        self.variable_choice_item_serializer = VariableChoiceItem.get_bxml_serializer()(self.variable_choice_item)

    def test_exists(self):
        self.assertIsNotNone(self.variable_choice_item_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.variable_choice_item_serializer.data['value'], self.variable_choice_item.value)


class TestVariableChoiceItemTranslationSerializer(EryTestCase):
    def setUp(self):
        self.vci = VariableChoiceItemFactory(variable_definition__data_type=VariableDefinition.DATA_TYPE_CHOICES.choice)
        self.language = Language.objects.first()
        self.vci_translation = VariableChoiceItemTranslationFactory(
            variable_choice_item=self.vci, language=self.language, caption="test caption"
        )
        self.vci_translation_serializer = VariableChoiceItemTranslation.get_bxml_serializer()(self.vci_translation)

    def test_exists(self):
        self.assertIsNotNone(self.vci_translation_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.vci_translation_serializer.data['caption'], "test caption")
        self.assertEqual(self.vci_translation_serializer.data['language'], self.language.pk)
