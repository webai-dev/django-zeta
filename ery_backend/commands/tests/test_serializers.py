from ery_backend.base.testcases import EryTestCase
from ery_backend.templates.factories import TemplateFactory

from ..factories import (
    CommandFactory,
    CommandTemplateFactory,
    CommandTemplateBlockFactory,
    CommandTemplateBlockTranslationFactory,
)

from ..models import Command, CommandTemplate, CommandTemplateBlockTranslation


class TestCommandBXMLSerializer(EryTestCase):
    def setUp(self):
        self.command = CommandFactory()
        self.command_serializer = Command.get_bxml_serializer()(instance=self.command)

    def test_exists(self):
        self.assertIsNotNone(self.command_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.command_serializer.data['name'], self.command.name)
        self.assertEqual(self.command_serializer.data['action'], self.command.action.name)
        self.assertEqual(self.command_serializer.data['trigger_pattern'], self.command.trigger_pattern)
        self.assertEqual(self.command_serializer.data['comment'], self.command.comment)


class TestCommandTemplateSerializer(EryTestCase):
    def setUp(self):
        self.template = TemplateFactory()
        self.command_template = CommandTemplateFactory(template=self.template)
        self.command_template_serializer = CommandTemplate.get_bxml_serializer()(instance=self.command_template)

    def test_exists(self):
        self.assertIsNotNone(self.command_template_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.command_template_serializer.data['template'], self.template.slug)


class TestCommandTemplateBlockSerializer(EryTestCase):
    def setUp(self):
        self.ctb = CommandTemplateBlockFactory()
        self.ctb_serializer = CommandTemplateBlockTranslation.get_bxml_serializer()(instance=self.ctb)

    def test_exists(self):
        self.assertIsNotNone(self.ctb_serializer)


class TestCommandTemplateBlockTranslationSerializer(EryTestCase):
    def setUp(self):
        self.ctb_translation = CommandTemplateBlockTranslationFactory()
        self.ctb_translation_serializer = CommandTemplateBlockTranslation.get_bxml_serializer()(instance=self.ctb_translation)

    def test_exists(self):
        self.assertIsNotNone(self.ctb_translation_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.ctb_translation_serializer.data['content'], self.ctb_translation.content)
        self.assertEqual(self.ctb_translation_serializer.data['language'], 'en')
