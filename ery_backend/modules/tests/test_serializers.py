from languages_plus.models import Language

from ery_backend.actions.factories import ActionFactory
from ery_backend.base.testcases import EryTestCase
from ery_backend.stages.factories import StageDefinitionFactory
from ery_backend.variables.factories import VariableDefinitionFactory
from ..factories import ModuleDefinitionFactory
from ..models import ModuleDefinition


class TestModuleDefinitionBXMLSerializer(EryTestCase):
    def setUp(self):
        self.module_definition = ModuleDefinitionFactory(
            start_stage=None, warden_stage=None, primary_language=Language.objects.first()
        )
        self.action = ActionFactory(module_definition=self.module_definition)
        self.start_stage = StageDefinitionFactory(module_definition=self.module_definition)
        self.warden_stage = StageDefinitionFactory(module_definition=self.module_definition)
        self.module_definition.start_stage = self.start_stage
        self.module_definition.warden_stage = self.warden_stage
        self.module_definition.save()
        self.variable = VariableDefinitionFactory(module_definition=self.module_definition)
        self.module_definition_serializer = ModuleDefinition.get_bxml_serializer()(self.module_definition)
        self.base_module = ModuleDefinitionFactory(start_stage=None, warden_stage=None)
        self.base_module_serializer = ModuleDefinition.get_bxml_serializer()(self.base_module)
        self.data = self.module_definition_serializer.data

    def test_exists(self):
        self.assertIsNotNone(self.module_definition_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.module_definition_serializer.data['start_stage'], self.module_definition.start_stage.name)
        self.assertEqual(self.module_definition_serializer.data['warden_stage'], self.module_definition.warden_stage.name)
        self.assertEqual(self.module_definition_serializer.data['comment'], self.module_definition.comment)
        self.assertEqual(self.module_definition_serializer.data['name'], self.module_definition.name)
        self.assertEqual(self.module_definition_serializer.data['min_team_size'], self.module_definition.min_team_size)
        self.assertEqual(self.module_definition_serializer.data['max_team_size'], self.module_definition.max_team_size)
        self.assertEqual(
            self.module_definition_serializer.data['primary_language'], self.module_definition.primary_language.iso_639_1
        )
