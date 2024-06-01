from ery_backend.base.testcases import EryTestCase
from ery_backend.modules.factories import ModuleDefinitionFactory, ModuleDefinitionProcedureFactory
from ery_backend.procedures.factories import ProcedureFactory

from ..utils import get_procedure_functions


class TestGetProcedureFunctions(EryTestCase):
    def setUp(self):
        self.procedure_1 = ProcedureFactory()
        self.procedure_2 = ProcedureFactory()
        self.module_definition = ModuleDefinitionFactory()
        self.alias_1_a = ModuleDefinitionProcedureFactory(procedure=self.procedure_1, module_definition=self.module_definition)
        self.alias_1_b = ModuleDefinitionProcedureFactory(procedure=self.procedure_1, module_definition=self.module_definition)
        self.alias_2 = ModuleDefinitionProcedureFactory(procedure=self.procedure_2, module_definition=self.module_definition)
        self.procedures = [self.procedure_1, self.procedure_2]

    def test_get_procedure_functions(self):
        functions = get_procedure_functions(self.module_definition, 'engine')
        for procedure in self.procedures:
            self.assertIn(f'{procedure.js_name} = {procedure.generate_js_function()}', functions)
        for alias in [self.alias_1_a, self.alias_1_b]:
            self.assertIn(f'var {alias.name} = {self.procedure_1.js_name}', functions)
        self.assertIn(f'var {self.alias_2.name} = {self.procedure_2.js_name}', functions)
