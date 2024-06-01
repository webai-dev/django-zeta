from ery_backend.base.testcases import EryTestCase
from ery_backend.modules.factories import ModuleDefinitionProcedureFactory
from ery_backend.modules.models import ModuleDefinitionProcedure

from ..factories import ProcedureFactory, ProcedureArgumentFactory
from ..models import Procedure, ProcedureArgument


class TestProcedureBXMLSerializer(EryTestCase):
    def setUp(self):
        self.procedure = ProcedureFactory()
        self.procedure_serializer = Procedure.get_bxml_serializer()(self.procedure)

    def test_exists(self):
        self.assertIsNotNone(self.procedure)

    def test_expected_attributes(self):
        self.assertEqual(self.procedure_serializer.data['name'], self.procedure.name)
        self.assertEqual(self.procedure_serializer.data['comment'], self.procedure.comment)
        self.assertEqual(self.procedure_serializer.data['code'], self.procedure.code)


class TestProcedureArgumentBXMLSerializer(EryTestCase):
    def setUp(self):
        self.procedure_argument = ProcedureArgumentFactory(default=45)
        self.procedure_argument_serializer = ProcedureArgument.get_bxml_serializer()(self.procedure_argument)

    def test_exists(self):
        self.assertIsNotNone(self.procedure_argument_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.procedure_argument_serializer.data['name'], self.procedure_argument.name)
        self.assertEqual(self.procedure_argument_serializer.data['comment'], self.procedure_argument.comment)
        self.assertEqual(self.procedure_argument_serializer.data['default'], self.procedure_argument.default)


class TestModuleDefinitionProcedureSerializer(EryTestCase):
    def setUp(self):
        self.module_definition_procedure = ModuleDefinitionProcedureFactory()
        self.module_definition_procedure_serializer = ModuleDefinitionProcedure.get_bxml_serializer()(
            self.module_definition_procedure
        )

    def test_exists(self):
        self.assertIsNotNone(self.module_definition_procedure_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.module_definition_procedure_serializer.data['name'], self.module_definition_procedure.name)
        self.assertEqual(
            self.module_definition_procedure_serializer.data['procedure'], self.module_definition_procedure.procedure.slug
        )
