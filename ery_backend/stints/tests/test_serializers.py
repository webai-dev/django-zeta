from ery_backend.base.testcases import EryTestCase
from ery_backend.modules.factories import ModuleDefinitionFactory
from ..factories import StintDefinitionFactory
from ..models import StintDefinition, StintDefinitionModuleDefinition


class TestStintDefinitionBXMLSerializer(EryTestCase):
    def setUp(self):
        self.stint_definition = StintDefinitionFactory()
        self.module_definition = ModuleDefinitionFactory()
        self.module_definition_2 = ModuleDefinitionFactory()
        self.stint_module = StintDefinitionModuleDefinition(
            stint_definition=self.stint_definition, module_definition=self.module_definition, order=1
        )
        self.stint_module.save()
        self.stint_module_2 = StintDefinitionModuleDefinition(
            stint_definition=self.stint_definition, module_definition=self.module_definition_2, order=2
        )
        self.stint_module_2.save()
        self.stint_definition_serializer = StintDefinition.get_bxml_serializer()(self.stint_definition)

    def test_exists(self):
        self.assertIsNotNone(self.stint_definition_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.stint_definition_serializer.data['comment'], self.stint_definition.comment)
        self.assertEqual(self.stint_definition_serializer.data['name'], self.stint_definition.name)


class TestStintDefinitionModuleDefinitionBXMLSerializer(EryTestCase):
    def setUp(self):
        self.stint_definition = StintDefinitionFactory()
        self.module_definition = ModuleDefinitionFactory()
        link = StintDefinitionModuleDefinition(
            stint_definition=self.stint_definition, module_definition=self.module_definition
        )
        link.save()
        self.link_serializer = StintDefinitionModuleDefinition.get_bxml_serializer()(link)
        self.link_serializer_data = self.link_serializer.data

    def test_exists(self):
        self.assertIsNotNone(self.link_serializer)

    def test_expected_attributes(self):
        self.assertIsNotNone(self.link_serializer_data['module_definition'])
