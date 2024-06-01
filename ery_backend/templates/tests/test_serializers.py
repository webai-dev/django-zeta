from languages_plus.models import Language

from ery_backend.base.testcases import EryTestCase
from ery_backend.frontends.factories import FrontendFactory
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.stages.factories import StageTemplateFactory, StageDefinitionFactory
from ..factories import TemplateFactory, TemplateBlockFactory, TemplateBlockTranslationFactory, TemplateWidgetFactory
from ..models import Template, TemplateBlock, TemplateBlockTranslation


class TestTemplateBXMLSerializer(EryTestCase):
    def setUp(self):
        self.parental_template = TemplateFactory()
        self.frontend = FrontendFactory()
        self.template = TemplateFactory(parental_template=self.parental_template, frontend=self.frontend)
        self.module_definition = ModuleDefinitionFactory()
        self.stage_definition = StageDefinitionFactory()
        self.stage_template = StageTemplateFactory(stage_definition=self.stage_definition, template=self.template)
        self.template_widget_1 = TemplateWidgetFactory(template=self.template)
        self.template_widget_2 = TemplateWidgetFactory(template=self.template)
        self.template_serializer = Template.get_bxml_serializer()(self.template)

    def test_exists(self):
        self.assertIsNotNone(self.template_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.template_serializer.data['comment'], self.template.comment)
        self.assertEqual(self.template_serializer.data['name'], self.template.name)
        self.assertEqual(self.template_serializer.data['frontend'], self.frontend.name)
        self.assertEqual(self.template_serializer.data['parental_template'], self.parental_template.slug)
        self.assertEqual(self.template_serializer.data['primary_language'], self.template.primary_language.iso_639_1)


class TestTemplateBlockBXMLSerializer(EryTestCase):
    def setUp(self):
        self.template_block = TemplateBlockFactory()
        self.template_block_serializer = TemplateBlock.get_bxml_serializer()(self.template_block)

    def test_exists(self):
        self.assertIsNotNone(self.template_block_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.template_block_serializer.data['name'], self.template_block.name)


class TestTemplateBlockTranslationBXMLSerializer(EryTestCase):
    def setUp(self):
        self.template_block = TemplateBlockFactory()
        self.tb_translation = TemplateBlockTranslationFactory(
            template_block=self.template_block, language=Language.objects.get(pk='ab'), content="Test translation"
        )
        self.tb_translation_serializer = TemplateBlockTranslation.get_bxml_serializer()(self.tb_translation)

    def test_exists(self):
        self.assertIsNotNone(self.tb_translation_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.tb_translation_serializer.data['language'], self.tb_translation.language.iso_639_1)
        self.assertEqual(self.tb_translation_serializer.data['content'], self.tb_translation.content)
