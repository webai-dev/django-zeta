from languages_plus.models import Language

from ery_backend.actions.factories import ActionFactory
from ery_backend.base.testcases import EryTestCase
from ery_backend.conditions.factories import ConditionFactory
from ery_backend.templates.factories import TemplateFactory
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.themes.factories import ThemeFactory
from ery_backend.variables.factories import VariableDefinitionFactory
from ery_backend.variables.models import VariableDefinition
from ..factories import (
    StageDefinitionFactory,
    StageTemplateFactory,
    StageTemplateBlockFactory,
    StageTemplateBlockTranslationFactory,
    RedirectFactory,
)
from ..models import StageDefinition, StageTemplate, StageTemplateBlock, StageTemplateBlockTranslation, Redirect


class TestStageTemplateBlockTranslationBXMLSerializer(EryTestCase):
    def setUp(self):
        self.stage_template_block = StageTemplateBlockFactory()
        self.stb_translation = StageTemplateBlockTranslationFactory(
            stage_template_block=self.stage_template_block,
            language=Language.objects.get(pk='ab'),
            content="Compound names on fleek",
        )
        self.stb_translation_serializer = StageTemplateBlockTranslation.get_bxml_serializer()(self.stb_translation)

    def test_exists(self):
        self.assertIsNotNone(self.stb_translation_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.stb_translation_serializer.data['language'], self.stb_translation.language.iso_639_1)
        self.assertEqual(self.stb_translation_serializer.data['content'], self.stb_translation.content)
        self.assertEqual(self.stb_translation_serializer.data['frontend'], self.stb_translation.frontend.name)


class TestStageTemplateBlockBXMLSerializer(EryTestCase):
    def setUp(self):
        self.module_definition = ModuleDefinitionFactory()
        self.variable_factory = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.str)
        self.stage_definition = StageDefinitionFactory(module_definition=self.module_definition)
        self.stage_template = StageTemplateFactory(stage_definition=self.stage_definition)
        self.stage_template_block = StageTemplateBlockFactory(stage_template=self.stage_template)
        self.stage_template_block_serializer = StageTemplateBlock.get_bxml_serializer()(self.stage_template_block)

    def test_exists(self):
        self.assertIsNotNone(self.stage_template_block_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.stage_template_block_serializer.data['name'], self.stage_template_block.name)


class TestStageTemplateBXMLSerializer(EryTestCase):
    def setUp(self):
        self.module_definition = ModuleDefinitionFactory()
        self.variable_factory = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.str)
        self.template = TemplateFactory()
        self.theme = ThemeFactory()
        self.stage_definition = StageDefinitionFactory(module_definition=self.module_definition)
        self.stage_template = StageTemplateFactory(
            stage_definition=self.stage_definition, template=self.template, theme=self.theme
        )
        self.stage_template_block = StageTemplateBlockFactory(stage_template=self.stage_template)
        self.stage_template_data = StageTemplate.get_bxml_serializer()(self.stage_template).data

    def test_exists(self):
        self.assertIsNotNone(self.stage_template_data)

    def test_expected_attributes(self):
        """
        Note: All sets tested in test_models/test_duplicate
        """
        self.assertEqual(self.stage_template_data['template'], self.template.slug)
        self.assertEqual(self.stage_template_data['theme'], self.theme.slug)


class TestStageDefinitionSerializer(EryTestCase):
    def setUp(self):
        self.template = TemplateFactory()
        self.template_2 = TemplateFactory()
        self.module_definition = ModuleDefinitionFactory()
        self.action = ActionFactory(module_definition=self.module_definition)
        self.stage = StageDefinitionFactory(module_definition=self.module_definition, pre_action=self.action)
        self.stage_serializer_data = StageDefinition.get_bxml_serializer()(self.stage).data

    def test_exists(self):
        self.assertIsNotNone(self.stage_serializer_data)

    def test_expected_attributes(self):
        """
        Note: All sets tested in test_models/test_duplicate
        """
        self.assertEqual(self.stage_serializer_data['pre_action'], self.stage.pre_action.name)
        self.assertEqual(self.stage_serializer_data['comment'], self.stage.comment)
        self.assertEqual(self.stage_serializer_data['name'], self.stage.name)
        self.assertEqual(self.stage_serializer_data['end_stage'], self.stage.end_stage)


class TestRedirectSerializer(EryTestCase):
    def setUp(self):
        self.stage_definition = StageDefinitionFactory()
        self.next_stage_definition = StageDefinitionFactory(module_definition=self.stage_definition.module_definition)
        self.condition = ConditionFactory(module_definition=self.stage_definition.module_definition)
        self.redirect = RedirectFactory(
            stage_definition=self.stage_definition, condition=self.condition, next_stage_definition=self.next_stage_definition
        )
        self.redirect_serializer_data = Redirect.get_bxml_serializer()(self.redirect).data

    def test_exists(self):
        self.assertIsNotNone(self.redirect_serializer_data)

    def test_expected_attributes(self):
        self.assertEqual(self.redirect_serializer_data['next_stage_definition'], self.next_stage_definition.name)
        self.assertEqual(self.redirect_serializer_data['condition'], self.condition.name)
        self.assertEqual(self.redirect_serializer_data['order'], self.redirect.order)
