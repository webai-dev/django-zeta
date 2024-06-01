import graphene
from graphql_relay.node.node import from_global_id

from ery_backend.base.testcases import GQLTestCase
from ery_backend.conditions.models import Condition
from ery_backend.forms.models import Form, FormField
from ery_backend.frontends.factories import FrontendFactory
from ery_backend.procedures.factories import ProcedureFactory
from ery_backend.roles.utils import grant_role, revoke_role
from ery_backend.stages.models import StageDefinition
from ery_backend.templates.factories import TemplateFactory
from ery_backend.themes.factories import ThemeFactory
from ery_backend.users.schema import ViewerQuery
from ery_backend.variables.factories import ModuleVariableFactory
from ery_backend.variables.models import VariableDefinition
from ery_backend.variables.schema import ModuleVariableQuery
from ery_backend.widgets.models import Widget


# This file must come after stagedef imports to avoid undefined gql type
from ery_backend.mutations import ModuleDefinitionMutation, ModuleDefinitionProcedureMutation

from ..models import ModuleDefinition, ModuleDefinitionProcedure
from ..factories import ModuleDefinitionFactory, ModuleFactory, ModuleDefinitionProcedureFactory
from ..schema import ModuleDefinitionQuery, ModuleQuery, ModuleDefinitionProcedureQuery


class TestQuery(
    ModuleDefinitionQuery, ModuleQuery, ModuleVariableQuery, ModuleDefinitionProcedureQuery, ViewerQuery, graphene.ObjectType
):
    pass


class TestMutation(ModuleDefinitionMutation, ModuleDefinitionProcedureMutation, graphene.ObjectType):
    pass


class TestReadModuleDefinition(GQLTestCase):
    """Ensure we can produce and query ModuleDefinition objects."""

    node_name = "ModuleDefinitionNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_read_all_requires_user(self):
        """all_module_definitions query without a user should not be
        authorized
        """

        query = """{allModuleDefinitions {edges {node {name modified}}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        """module_definition query without user should not be authorized"""

        module_definition = ModuleDefinitionFactory()
        td = {"mid": module_definition.gql_id}
        query = """query MD($mid: ID!){moduleDefinition(id: $mid){name id}}"""

        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_applies_user_filtering(self):
        """all_module_definitions query should limit results according to user
        privileges
        """

        query = """{allModuleDefinitions {edges {node {name id}}}}"""
        mds = [
            ModuleDefinitionFactory(name="TestReadAllAppliesUserFilteringOne"),
            ModuleDefinitionFactory(name="TestReadAllAppliesUserFilteringTwo"),
            ModuleDefinitionFactory(name="TestReadAllAppliesUserFilteringThree"),
        ]

        # Nobody
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allModuleDefinitions"]["edges"]), 0)

        # Viewer
        for m in mds:
            grant_role(self.viewer["role"], m, self.viewer["user"])
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allModuleDefinitions"]["edges"]), 3)

        # Editor
        for m in mds[1:]:
            grant_role(self.editor["role"], m, self.editor["user"])
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allModuleDefinitions"]["edges"]), 2)

        # Owner
        grant_role(self.owner["role"], mds[2], self.owner["user"])
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allModuleDefinitions"]["edges"]), 1)

    def test_read_is_accurate(self):
        """moduleDefinition query attributes match as expected"""
        module = ModuleDefinitionFactory(
            name="TestReadIsAccurate", comment="this is a test", mxgraph_xml="json encoded xml here"
        )

        grant_role(self.viewer["role"], module, self.viewer["user"])
        td = {"mid": module.gql_id}
        query = """query ModuleDefinition($mid: ID!){moduleDefinition(id: $mid){
            id name minTeamSize maxTeamSize comment mxgraphXml}}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.fail_on_errors(result)

        data = result["data"]["moduleDefinition"]
        self.assertEqual(data["id"], td["mid"])
        self.assertEqual(data["name"], module.name)
        self.assertEqual(data["minTeamSize"], module.min_team_size)
        self.assertEqual(data["maxTeamSize"], module.max_team_size)
        self.assertEqual(data["comment"], module.comment)
        self.assertEqual(data["mxgraphXml"], module.mxgraph_xml)

    def test_no_soft_deletes_in_all_query(self):
        """
        Confirm soft_deleted objects are not returned in query.
        """
        query = """{allModuleDefinitions { edges{ node{ id }}}}"""
        module_definition = ModuleDefinitionFactory()
        grant_role(self.viewer["role"], module_definition, self.viewer["user"])

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(len(result["data"]["allModuleDefinitions"]["edges"]), 1)

        module_definition.soft_delete()
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(len(result["data"]["allModuleDefinitions"]["edges"]), 0)

    def test_no_soft_deletes_in_single_query(self):
        """
        Confirms soft_deleted object not returned in query.
        """
        query = """query ModuleDefinitionQuery($moduleDefinitionid: ID!){
            moduleDefinition(id: $moduleDefinitionid){ id }}
            """
        module_definition = ModuleDefinitionFactory()
        grant_role(self.viewer["role"], module_definition, self.viewer["user"])

        result = self.gql_client.execute(
            query,
            variable_values={"moduleDefinitionid": module_definition.gql_id},
            context_value=self.gql_client.get_context(user=self.viewer["user"]),
        )
        self.fail_on_errors(result)

        module_definition.soft_delete()
        result = self.gql_client.execute(
            query,
            variable_values={"moduleDefinitionid": module_definition.gql_id},
            context_value=self.gql_client.get_context(user=self.viewer["user"]),
        )
        self.assertEqual('ModuleDefinition matching query does not exist.', result['errors'][0]['message'])


class TestCreateModuleDefinition(GQLTestCase):
    node_name = "ModuleDefinitionNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_create_requires_login(self):
        """User must be logged in to create ModuleDefinitions"""

        query = """mutation{
                    createModuleDefinition(input: {
                        name: "Test Create Requires Login",
                        comment: "Don't create this.",
                        minTeamSize: 3,
                        maxTeamSize: 7
                     }){ moduleDefinitionEdge { node { id name }}}}
                """

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_create_produces_moduledefinition(self):
        """Logged in users can create ModuleDefinitions, with accurate data and
        permissions.
        """
        test_data = {
            "name": "TestCreateProducesModuleDefinition",
            "comment": "This is a Unit Test.  FTW.",
            "primaryFrontend": FrontendFactory().gql_id,
            "defaultTemplate": TemplateFactory().gql_id,
            "defaultTheme": ThemeFactory().gql_id,
            "minTeamSize": 3,
            "maxTeamSize": 7,
        }

        mutation = """
mutation CreateModuleDefinition(
    $name: String,
    $comment: String,
    $primaryFrontend: ID,
    $defaultTemplate: ID,
    $defaultTheme: ID
    $minTeamSize: Int,
    $maxTeamSize: Int
) {
    createModuleDefinition(input: {
        name: $name,
        comment: $comment,
        primaryFrontend: $primaryFrontend,
        defaultTemplate: $defaultTemplate,
        defaultTheme: $defaultTheme,
        minTeamSize: $minTeamSize,
        maxTeamSize: $maxTeamSize
    }) {
        moduleDefinitionEdge {
            node {
                id
                name
            }
        }
    }
}"""

        mutation_response = self.gql_client.execute(
            mutation, variable_values=test_data, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(mutation_response)

        self.assertEqual(
            mutation_response["data"]["createModuleDefinition"]["moduleDefinitionEdge"]["node"]["name"], test_data["name"]
        )

        td = {"mid": mutation_response["data"]["createModuleDefinition"]["moduleDefinitionEdge"]["node"]["id"]}

        query = """
query ModuleDefinition($mid: ID!) {
    moduleDefinition(id: $mid) {
        id
        name
        minTeamSize
        maxTeamSize
        comment
    }
}"""
        owner_lookup = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )

        self.fail_on_errors(owner_lookup)

        for field in ("name", "comment", "minTeamSize", "maxTeamSize"):
            self.assertEqual(
                owner_lookup["data"]["moduleDefinition"][field], test_data[field], msg="{} mismatch on lookup".format(field)
            )


class TestUpdateModuleDefinition(GQLTestCase):
    node_name = "ModuleDefinitionNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_update_requires_privileges(self):
        """Unprivileged users can't update modules"""
        md = ModuleDefinitionFactory()
        grant_role(self.viewer["role"], md, self.viewer["user"])

        test_data = {"mid": md.gql_id, "name": "TestUpdateRequiresPrivileges", "maxTeamSize": md.max_team_size + 1}

        query = """mutation UpdateModuleDefinition($mid: ID!, $name: String, $maxTeamSize: Int){
                updateModuleDefinition(input: {
                    id: $mid,
                    name: $name,
                    maxTeamSize: $maxTeamSize})
                {moduleDefinition{id, name}}}"""

        result = self.gql_client.execute(
            query, variable_values=test_data, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        test_data.pop("mid")
        test_data["max_team_size"] = test_data.pop("maxTeamSize")

        md.refresh_from_db()
        for field in test_data:
            self.assertNotEqual(getattr(md, field), test_data[field])

    def test_update_works_correctly(self):
        """Updated fields are updated"""
        md = ModuleDefinitionFactory()
        grant_role(self.editor["role"], md, self.editor["user"])

        min_team_size = md.min_team_size

        test_data = {"mid": md.gql_id, "name": "TestUpdateWorksCorrectly", "maxTeamSize": md.max_team_size + 3}

        query = """mutation UpdateModuleDefinition($mid: ID!, $name: String, $maxTeamSize: Int){
                updateModuleDefinition(input: {
                    id: $mid,
                    name: $name,
                    maxTeamSize: $maxTeamSize})
                {moduleDefinition{id}}}"""

        result = self.gql_client.execute(
            query, variable_values=test_data, context_value=self.gql_client.get_context(user=self.editor["user"])
        )
        self.fail_on_errors(result)

        md.refresh_from_db()

        test_data.pop("mid")
        test_data["max_team_size"] = test_data.pop("maxTeamSize")
        for field in test_data:
            self.assertEqual(getattr(md, field, None), test_data[field], msg=f"mismatch on {field}")

        self.assertEqual(md.min_team_size, min_team_size, msg="min team size has unexpected change")


class TestDeleteModuleDefinition(GQLTestCase):
    node_name = "ModuleDefinitionNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_delete_requires_privileges(self):
        md = ModuleDefinitionFactory()
        mid = md.pk
        test_data = {"gql_id": md.gql_id}

        grant_role(self.viewer["role"], md, self.viewer["user"])
        query = """mutation DeleteModuleDefinition($gql_id: ID!){
                    deleteModuleDefinition(input: {id: $gql_id}){
                    id}}"""

        result = self.gql_client.execute(query, variable_values=test_data)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            query, variable_values=test_data, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        verification = ModuleDefinition.objects.get(pk=mid)
        self.assertEqual(verification.name, md.name)

    def test_delete_works(self):
        md = ModuleDefinitionFactory()
        test_data = {"gql_id": md.gql_id}

        grant_role(self.owner["role"], md, self.owner["user"])

        query = """mutation DeleteModuleDefinition($gql_id: ID!){
            deleteModuleDefinition(input: {id: $gql_id}){
            id}}"""

        result = self.gql_client.execute(
            query, variable_values=test_data, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertTrue(result["data"]["deleteModuleDefinition"]["id"])

        md.refresh_from_db()
        self.assertEqual(md.state, md.STATE_CHOICES.deleted)


class TestReadModule(GQLTestCase):
    """Ensure reading Module works"""

    node_name = "ModuleNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def test_read_all_requires_login(self):
        """allModules query without a user is unauthorized"""
        query = """{allModules{edges{ node{ id }}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        module = ModuleFactory()
        td = {"moduleid": module.gql_id}

        query = """query ModuleQuery($moduleid: ID!){module(id: $moduleid){ id }}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        query = """{allModules{ edges{ node{ id }}}}"""
        modules = [ModuleFactory() for _ in range(3)]

        # No roles
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allModules"]["edges"]), 0)

        # Viewer
        for obj in modules:
            grant_role(self.viewer["role"], obj.stint.get_privilege_ancestor(), self.viewer["user"])
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allModules"]["edges"]), 3)

        # Editor
        for obj in modules[1:]:
            grant_role(self.editor["role"], obj.stint.get_privilege_ancestor(), self.editor["user"])
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allModules"]["edges"]), 2)

        # Owner
        grant_role(self.owner["role"], modules[2].stint.get_privilege_ancestor(), self.owner["user"])
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allModules"]["edges"]), 1)


class TestReadRelationships(GQLTestCase):
    """
    Confirm user can access related models as intended.
    """

    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def setUp(self):
        self.module = ModuleFactory()
        grant_role(self.viewer["role"], self.module.get_privilege_ancestor(), self.viewer["user"])
        self.td = {"gqlId": self.module.gql_id}
        self.context = self.gql_client.get_context(user=self.viewer["user"])

    def test_variables(self):
        mv_1 = ModuleVariableFactory(module=self.module)
        mv_2 = ModuleVariableFactory(module=self.module)
        expected_variable_ids = [mv.gql_id for mv in (mv_1, mv_2)]
        query = """
query ModuleQuery($gqlId: ID!){module(id: $gqlId){ id variables { edges { node { id value } } } } }"""
        result = self.gql_client.execute(query, variable_values=self.td, context_value=self.context)
        variable_ids = [edge['node']['id'] for edge in result['data']['module']['variables']['edges']]
        for variable_id in expected_variable_ids:
            self.assertIn(variable_id, variable_ids)
        self.assertEqual(expected_variable_ids, variable_ids)


class TestReadModuleDefinitionProcedure(GQLTestCase):
    """Ensure reading ModuleDefinitionProcedure works"""

    node_name = "ModuleDefinitionProcedureNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.all_query = """{allModuleDefinitionProcedures{ edges{ node{ id procedure{ id } moduleDefinition{ id }}}}}"""
        cls.node_query = """query ModuleDefinitionProcedureQuery($moduledefinitionprocedureid: ID!){
            moduleDefinitionProcedure(id: $moduledefinitionprocedureid){ id moduleDefinition{ id } procedure{ id }}}"""

    def setUp(self):
        self.module_definition = ModuleDefinitionFactory()
        self.procedure = ProcedureFactory()
        self.module_definition_procedure = ModuleDefinitionProcedureFactory(
            module_definition=self.module_definition, procedure=self.procedure
        )
        self.td = {
            "moduledefinitionprocedureid": self.module_definition_procedure.gql_id,
            'module_definition': self.module_definition.gql_id,
            'procedure': self.procedure.gql_id,
        }

    def test_read_all_requires_login(self):
        """allModuleDefinitionProcedures query without a user is unauthorized"""
        result = self.gql_client.execute(self.all_query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        result = self.gql_client.execute(self.node_query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        module_definition_procedures = [ModuleDefinitionProcedureFactory() for _ in range(3)]

        for obj in module_definition_procedures:
            grant_role(self.viewer["role"], obj.get_privilege_ancestor(), self.viewer["user"])

        for obj in module_definition_procedures[1:]:
            grant_role(self.editor["role"], obj.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], module_definition_procedures[2].get_privilege_ancestor(), self.owner["user"])

        # No roles
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allModuleDefinitionProcedures"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allModuleDefinitionProcedures"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allModuleDefinitionProcedures"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allModuleDefinitionProcedures"]["edges"]), 1)

    def test_read_node_works(self):
        grant_role(self.viewer["role"], self.module_definition_procedure.get_privilege_ancestor(), self.viewer["user"])
        result = self.gql_client.execute(
            self.node_query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.fail_on_errors(result)
        self.assertEqual(
            int(from_global_id(result["data"]["moduleDefinitionProcedure"]["id"])[1]), self.module_definition_procedure.id
        )
        self.assertEqual(
            int(from_global_id(result["data"]["moduleDefinitionProcedure"]["moduleDefinition"]["id"])[1]),
            self.module_definition_procedure.module_definition.id,
        )
        self.assertEqual(
            int(from_global_id(result["data"]["moduleDefinitionProcedure"]["procedure"]["id"])[1]),
            self.module_definition_procedure.procedure.id,
        )


class TestCreateModuleDefinitionProcedure(GQLTestCase):
    node_name = "ModuleDefinitionProcedureNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.module_definition = ModuleDefinitionFactory()
        self.procedure = ProcedureFactory()
        self.td = {'moduleDefinition': self.module_definition.gql_id, 'procedure': self.procedure.gql_id, 'name': 'proc_alias'}

        self.query = """
mutation ($moduleDefinition: ID!, $procedure: ID!, $name: String!) {
    createModuleDefinitionProcedure(input: {
        moduleDefinition: $moduleDefinition
        procedure: $procedure
        name: $name
    }) {
        moduleDefinitionProcedureEdge {
            node {
                id
                moduleDefinition {
                    id
                }
                procedure {
                    id
                }
                name
            }
        }
    }
}
"""

    def test_create_requires_user(self):
        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        self.assertRaises(
            ModuleDefinitionProcedure.DoesNotExist, ModuleDefinitionProcedure.objects.get, **{"name": self.td["name"]}
        )

    def test_create_requires_privileges(self):
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.assert_query_was_unauthorized(result)

        self.assertRaises(
            ModuleDefinitionProcedure.DoesNotExist, ModuleDefinitionProcedure.objects.get, **{"name": self.td["name"]}
        )

        grant_role(self.owner["role"], self.module_definition, self.owner["user"])
        self.assert_query_was_unauthorized(result)

        self.assertRaises(
            ModuleDefinitionProcedure.DoesNotExist, ModuleDefinitionProcedure.objects.get, **{"name": self.td["name"]}
        )

        revoke_role(self.owner["role"], self.module_definition, self.owner["user"])
        grant_role(self.owner["role"], self.procedure, self.owner["user"])
        self.assert_query_was_unauthorized(result)

        self.assertRaises(
            ModuleDefinitionProcedure.DoesNotExist, ModuleDefinitionProcedure.objects.get, **{"name": self.td["name"]}
        )

    def test_create_produces_result(self):
        grant_role(self.owner["role"], self.module_definition, self.owner["user"])
        grant_role(self.owner["role"], self.procedure, self.owner["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        lookup = ModuleDefinitionProcedure.objects.get(name=self.td["name"])

        self.assertEqual(lookup.name, self.td["name"])
        self.assertEqual(lookup.module_definition, self.module_definition)
        self.assertEqual(lookup.procedure, self.procedure)


class TestUpdateModuleDefinitionProcedure(GQLTestCase):
    node_name = "ModuleDefinitionProcedureNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.module_definition_procedure = ModuleDefinitionProcedureFactory()
        self.td = {"moduleDefinitionProcedure": self.module_definition_procedure.gql_id, "name": "updated_procedure"}
        self.query = """mutation ($moduleDefinitionProcedure: ID!, $name: String!){
             updateModuleDefinitionProcedure(input: {
                id: $moduleDefinitionProcedure,
                name: $name
                    })
                   {moduleDefinitionProcedure
                   {id name procedure{ id } moduleDefinition{ id }}}}
                """

    def test_update_requires_privilege(self):
        grant_role(self.viewer["role"], self.module_definition_procedure.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        grant_role(self.owner["role"], self.module_definition_procedure.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        lookup = ModuleDefinitionProcedure.objects.get(pk=self.module_definition_procedure.id)

        self.assertEqual(lookup.name, self.td["name"])


class TestDeleteModuleDefinitionProcedure(GQLTestCase):
    node_name = "ModuleDefinitionProcedureNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.module_definition_procedure = ModuleDefinitionProcedureFactory()
        self.td = {"moduleDefinitionProcedure": self.module_definition_procedure.gql_id}
        self.query = """mutation ($moduleDefinitionProcedure: ID!){
             deleteModuleDefinitionProcedure(input: {
                id: $moduleDefinitionProcedure,
                    })
                   { id }
                   }
                """

    def test_delete_requires_privilege(self):
        grant_role(self.viewer["role"], self.module_definition_procedure.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        ModuleDefinitionProcedure.objects.get(pk=self.module_definition_procedure.id)

    def test_delete_produces_result(self):
        grant_role(self.owner["role"], self.module_definition_procedure.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertTrue(result["data"]["deleteModuleDefinitionProcedure"]["id"])

        self.assertRaises(
            ModuleDefinitionProcedure.DoesNotExist,
            ModuleDefinitionProcedure.objects.get,
            **{"pk": self.module_definition_procedure.id},
        )


class TestCreateModuleDefinitionMutation(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        import json
        from ery_backend.base.utils import get_gql_id
        from ery_backend.frontends.models import Frontend
        from languages_plus.models import Language
        from ery_backend.actions.models import ActionStep

        web = Frontend.objects.get(name='Web')
        language = Language.objects.get(pk='en')
        default_template = TemplateFactory(frontend=web)
        default_theme = ThemeFactory()
        button = Widget.objects.get(name='Button', namespace='mui')
        self.actionstep_info_1 = {
            'order': 0,
            'forEach': ActionStep.FOR_EACH_CHOICES.current_hand_only,
            'actionType': ActionStep.ACTION_TYPE_CHOICES.log,
            'logMessage': 'This is a log',
            'condition': 'MyCondition',
        }
        self.actionstep_info_2 = {
            'order': 0,
            'forEach': ActionStep.FOR_EACH_CHOICES.current_hand_only,
            'actionType': ActionStep.ACTION_TYPE_CHOICES.log,
            'logMessage': 'This is a log',
            'condition': 'MyCondition2',
        }
        self.vci_info = [
            {'value': 'fdt', 'translations': [{'caption': "Four Donuts Tonight!", 'language': get_gql_id('Language', 'en')}]}
        ]
        variabledef_info = [
            {
                'name': 'my_vd',
                'scope': VariableDefinition.SCOPE_CHOICES.hand,
                'dataType': VariableDefinition.DATA_TYPE_CHOICES.int,
                'defaultValue': '47',
                'specifiable': True,
                'isPayoff': False,
                'isOutputData': False,
                'monitored': True,
            },
            {
                'name': 'my_cond_vd_1',
                'scope': VariableDefinition.SCOPE_CHOICES.hand,
                'dataType': VariableDefinition.DATA_TYPE_CHOICES.stage,
                'defaultValue': json.dumps('MyVDStageDef'),
                'specifiable': True,
                'isPayoff': False,
                'isOutputData': False,
                'monitored': True,
            },
            {
                'name': 'my_cond_vd_2',
                'scope': VariableDefinition.SCOPE_CHOICES.team,
                'dataType': VariableDefinition.DATA_TYPE_CHOICES.choice,
                'defaultValue': json.dumps('fdt'),
                'specifiable': True,
                'isPayoff': False,
                'isOutputData': False,
                'monitored': True,
                'variablechoiceitemSet': self.vci_info,
            },
        ]
        action_info = [
            {'name': 'MyAction', 'steps': [self.actionstep_info_1]},
            {'name': 'MyAction2', 'steps': [self.actionstep_info_2]},
        ]
        form_info = [
            {
                'name': 'MyForm',
                'items': [
                    {
                        'order': 0,
                        'tabOrder': 0,
                        'field': {
                            'name': 'MyField',
                            'widget': button.gql_id,
                            'randomMode': FormField.RANDOM_CHOICES.asc,
                            'variableDefinition': 'my_vd',
                            'disable': 'MyCondition',
                            'initialValue': json.dumps('abx'),
                            'helperText': "NO HELP FOR YOU",
                            'required': True,
                            'choices': [
                                {
                                    'value': 'abx',
                                    'order': 0,
                                    'translations': [
                                        {'language': get_gql_id('Language', 'en'), 'caption': '1st translation'},
                                        {'language': get_gql_id('Language', 'aa'), 'caption': '2nd translation'},
                                    ],
                                }
                            ]
                            # XXX: Add validator
                        },
                    },
                    {
                        'order': 1,
                        'tabOrder': 1,
                        'buttonList': {
                            'name': 'MyButtonList',
                            'buttons': [
                                {
                                    'name': 'MyButton',
                                    'buttonText': 'My Button',
                                    'widget': button.gql_id,
                                    'submit': False,
                                    'disable': 'MyCondition',
                                    'hide': 'MyCondition2',
                                }
                            ],
                        },
                    },
                ],
            }
        ]
        condition_info = [
            {
                'name': 'MyCondition',
                'leftType': Condition.TYPE_CHOICES.variable,
                'rightType': Condition.TYPE_CHOICES.variable,
                'leftVariableDefinition': 'my_cond_vd_1',
                'rightVariableDefinition': 'my_cond_vd_2',
                'relation': Condition.RELATION_CHOICES.equal,
            },
            {
                'name': 'MyCondition2',
                'leftType': Condition.TYPE_CHOICES.expression,
                'rightType': Condition.TYPE_CHOICES.expression,
                'leftExpression': '1 == 1',
                'rightExpression': '1 == 2',
                'relation': Condition.RELATION_CHOICES.equal,
            },
            {
                'name': 'MySubConditionHavingCondition',
                'leftType': Condition.TYPE_CHOICES.sub_condition,
                'rightType': Condition.TYPE_CHOICES.sub_condition,
                'leftSubCondition': 'MyCondition',
                'rightSubCondition': 'MyCondition2',
                'operator': Condition.BINARY_OPERATOR_CHOICES.op_and,
            },
        ]
        self.stagedef_info = [
            {
                'name': 'MyStageDef',
                'breadcrumbType': StageDefinition.BREADCRUMB_TYPE_CHOICES.all,
                'endStage': True,
                'redirectOnSubmit': True,
                'preAction': 'MyAction2',
            },
            {'name': 'MyVDStageDef',},
        ]
        self.module_definition = ModuleDefinition.objects.create(
            name='MyModuleDefinition',
            primary_frontend=web,
            primary_language=language,
            default_template=default_template,
            default_theme=default_theme,
        )
        self.input = {
            "input": {
                "name": "MyModuleDefinition",
                # "startStage": "MyStageDef",
                "primaryFrontend": web.gql_id,
                "primaryLanguage": get_gql_id('Language', 'en'),
                "defaultTemplate": default_template.gql_id,
                "defaultTheme": default_theme.gql_id,
                "conditionSet": condition_info,
                "actionSet": action_info,
                "forms": form_info,
                "stageDefinitions": self.stagedef_info,
                "variabledefinitionSet": variabledef_info,
                "state": ModuleDefinition.STATE_CHOICES.alpha,
            }
        }
        # startStage

        self.mutation = """
mutation SerializedModuleDefinitionMutation($input: SerializedModuleDefinitionInput!){
    serializedModuleDefinition(input: $input){
        id
        name
        primaryFrontend
        primaryLanguage
        defaultTemplate
        defaultTheme
        forms {
            id
            name
            items{ edges{ node{
                id
                order
                field{ id name choices{ edges{ node{ value translations{ edges{ node{ language{ iso6391 }}}}}}}}
                buttonList{ id buttons{ edges{ node{ name id }}}}
            }}}
        }
        actionSet { id name steps{ edges{ node{ order actionType condition{ id }}} }}
        conditionSet { id leftVariableDefinition { id name } leftSubCondition { id name }}
        stageDefinitions { id preAction{ id name steps{ edges{ node{ condition{ id name }}}}}}
        variabledefinitionSet {
            id
            name
            defaultValue
            variablechoiceitemSet{ edges{ node{ id translations{ edges{ node{ caption }}}}}}}
        errors {
            field
            messages
        }
    }
}"""

    def test_invalid_create_condition(self):
        # Condition referenced by action actually does not exist
        self.actionstep_info_1['condition'] = 'YourCondition'
        result = self.gql_client.execute(
            self.mutation, variable_values=self.input, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.assertIn('errors', result)

    def test_invalid_create_action(self):
        # Action referenced by StageDefinition does not exist
        self.stagedef_info[0]['preAction'] = 'YourAction'
        result = self.gql_client.execute(
            self.mutation, variable_values=self.input, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.assertIn('errors', result)

    # XXX: Fix in issue #813
    # def test_invalid_choice(self):
    #     # Variable of data_type choice has default_value that is not subset of choices
    #     self.input['input']['variabledefinitionSet'][2]['variablechoiceitemSet'][0]['value'] = 'aaa'
    #     result = self.gql_client.execute(self.mutation, variable_values=self.input,
    #                                      context_value=self.gql_client.get_context(user=self.owner["user"]))
    #     self.assertIn('errors', result)

    def test_create_with_cyclic_fields(self):
        """Fields require each other, requiring retry if not created yet"""
        # Actionstep.condition is created during deserialization
        from ery_backend.actions.models import Action

        result = self.gql_client.execute(
            self.mutation, variable_values=self.input, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.assertIsNotNone(result['data']['serializedModuleDefinition'].pop('primaryFrontend'))
        self.assertIsNotNone(result['data']['serializedModuleDefinition'].pop('primaryLanguage'))
        self.assertIsNotNone(result['data']['serializedModuleDefinition'].pop('defaultTemplate'))
        self.assertIsNotNone(result['data']['serializedModuleDefinition'].pop('defaultTheme'))

        conditionSet_data = result['data']['serializedModuleDefinition'].pop('conditionSet')
        condition_ids = [condition_data['id'] for condition_data in conditionSet_data]
        my_condition = Condition.objects.filter(
            pk__in=[from_global_id(condition_id)[1] for condition_id in condition_ids]
        ).get(name='MyCondition')
        self.assertIsNotNone(my_condition)

        actionSet_data = result['data']['serializedModuleDefinition'].pop('actionSet')
        action_ids = [action_data['id'] for action_data in actionSet_data]

        actions = Action.objects.filter(pk__in=[from_global_id(action_id)[1] for action_id in action_ids])
        my_action = actions.get(name='MyAction')
        self.assertIsNotNone(my_action)
        self.assertTrue(my_action.steps.filter(condition=my_condition).exists())

        forms_data = result['data']['serializedModuleDefinition'].pop('forms')
        form_ids = [form_data['id'] for form_data in forms_data]
        form = Form.objects.filter(pk__in=[from_global_id(form_id)[1] for form_id in form_ids]).get(name='MyForm')

        choice_field = form.items.get(field__name='MyField').field

        self.assertTrue(choice_field.choices.filter(value='abx').exists())
        vdSet_data = result['data']['serializedModuleDefinition'].pop('variabledefinitionSet')
        vd_ids = [vd_data['id'] for vd_data in vdSet_data]
        # VD of stage type. This is a string value, so no need to worry about pre_action
        stage_vd = VariableDefinition.objects.filter(pk__in=[from_global_id(vd_id)[1] for vd_id in vd_ids]).get(
            name='my_cond_vd_1'
        )

        self.assertEqual(stage_vd.data_type, VariableDefinition.DATA_TYPE_CHOICES.stage)
        self.assertTrue(stage_vd.module_definition.has_stage(stage_vd.default_value))
