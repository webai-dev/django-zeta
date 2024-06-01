import os

from ery_backend.base.testcases import EryLiveServerTestCase, grant_owner_to_obj
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.modules.models import ModuleDefinition
from ery_backend.users.factories import UserFactory
from ery_backend.variables.factories import VariableDefinitionFactory
from ery_backend.variables.models import VariableDefinition


class TestModuleDefinition(EryLiveServerTestCase):
    def setUp(self):
        self.tony_el_tigre = UserFactory(username='rawrrrr')
        # client must be logged in
        self.client = self.get_loggedin_client(self.tony_el_tigre)

    def test_export_moduledefinition_w_variables(self):
        """
        Export ModuleDefinition w variables having bool, list, and dict values. Receives a bxml file.
        """
        # moduledefinition containing variable definitions with list and dict values
        module_definition_w_variables = ModuleDefinitionFactory(name='Moduledefinitionwvariables')

        VariableDefinitionFactory(
            module_definition=module_definition_w_variables,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.bool,
            default_value=False,
            is_payoff=False,
        )
        VariableDefinitionFactory(
            module_definition=module_definition_w_variables,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.list,
            default_value=['List', 'right', 'here'],
            is_payoff=False,
        )
        VariableDefinitionFactory(
            module_definition=module_definition_w_variables,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.dict,
            default_value={'Dict': 'here'},
            is_payoff=False,
        )
        grant_owner_to_obj(module_definition_w_variables, self.tony_el_tigre)
        response = self.client.get(f'/export/module_definition/{module_definition_w_variables.gql_id}')
        # properly named bxml file
        self.assertEqual(
            response.get('Content-Disposition'), f'attachment; filename={module_definition_w_variables.name}.bxml'
        )

        # alexia confirms serialized module definition is of correct name inside of file
        self.assertIn(f'{module_definition_w_variables.name}', response.content.decode('utf-8'))

    def test_import_moduledefinition_w_variables(self):
        """
        Import ModuleDefinition w varirables having bool, list, and dict values.
        """
        xml_address = f'{os.getcwd()}/ery_backend/modules/tests/data/module_definition_with_variables.bxml'
        xml_file = open(xml_address, 'rb')
        module_definition = ModuleDefinition.import_instance_from_xml(xml_file)
        self.assertTrue(module_definition.variabledefinition_set.filter(data_type='bool').exists())
        self.assertTrue(module_definition.variabledefinition_set.filter(data_type='list').exists())
        self.assertTrue(module_definition.variabledefinition_set.filter(data_type='dict').exists())
