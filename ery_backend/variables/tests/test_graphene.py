import graphene
from ery_backend.base.testcases import GQLTestCase, random_dt_value
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.mutations import VariableDefinitionMutation
from ery_backend.roles.utils import grant_role
from ery_backend.users.schema import ViewerQuery
from ..factories import ModuleVariableFactory, TeamVariableFactory, HandVariableFactory, VariableDefinitionFactory
from ..models import VariableDefinition


class TestQuery(ViewerQuery, graphene.ObjectType):
    pass


class TestMutation(VariableDefinitionMutation, graphene.ObjectType):
    pass


class TestReadModuleVariable(GQLTestCase):
    """Ensure reading ModuleVariable works"""

    node_name = "ModuleVariableNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def test_read_all_requires_login(self):
        """allModuleVariables query without a user is unauthorized"""
        query = """{viewer{ allModuleVariables{ edges{ node{ id }}}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        module_variable = ModuleVariableFactory()
        td = {"modulevariableid": module_variable.gql_id}

        query = """query ModuleVariableQuery($modulevariableid: ID!){viewer{ moduleVariable(id: $modulevariableid){ id }}}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        query = """{viewer{ allModuleVariables{ edges{ node{ id value }}}}}"""
        module_variables = [ModuleVariableFactory() for _ in range(3)]

        for obj in module_variables:
            grant_role(self.viewer["role"], obj.module.stint.get_privilege_ancestor(), self.viewer["user"])

        for obj in module_variables[1:]:
            grant_role(self.editor["role"], obj.module.stint.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], module_variables[2].module.stint.get_privilege_ancestor(), self.owner["user"])
        # No roles
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["viewer"]["allModuleVariables"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["viewer"]["allModuleVariables"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["viewer"]["allModuleVariables"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["viewer"]["allModuleVariables"]["edges"]), 1)


class TestReadTeamVariable(GQLTestCase):
    """Ensure reading TeamVariable works"""

    node_name = "TeamVariableNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def test_read_all_requires_login(self):
        """allTeamVariables query without a user is unauthorized"""
        query = """{viewer{ allTeamVariables{ edges{ node{ id }}}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        team_variable = TeamVariableFactory()
        td = {"teamvariableid": team_variable.gql_id}

        query = """query TeamVariableQuery($teamvariableid: ID!){viewer{ teamVariable(id: $teamvariableid){ id }}}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        query = """{viewer{ allTeamVariables{ edges{ node{ id value }}}}}"""
        team_variables = [TeamVariableFactory() for _ in range(3)]

        for obj in team_variables:
            grant_role(self.viewer["role"], obj.get_privilege_ancestor(), self.viewer["user"])

        for obj in team_variables[1:]:
            grant_role(self.editor["role"], obj.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], team_variables[2].get_privilege_ancestor(), self.owner["user"])
        # No roles
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["viewer"]["allTeamVariables"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["viewer"]["allTeamVariables"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["viewer"]["allTeamVariables"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["viewer"]["allTeamVariables"]["edges"]), 1)


class TestReadHandVariable(GQLTestCase):
    """Ensure reading HandVariable works"""

    node_name = "HandVariableNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def test_read_all_requires_login(self):
        """allHandVariables query without a user is unauthorized"""
        query = """{viewer{ allHandVariables{ edges{ node{ id }}}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        hand_variable = HandVariableFactory()
        td = {"handvariableid": hand_variable.gql_id}

        query = """query HandVariableQuery($handvariableid: ID!){viewer{ handVariable(id: $handvariableid){ id }}}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        query = """{viewer{ allHandVariables{ edges{ node{ id value }}}}}"""
        hand_variables = [HandVariableFactory() for _ in range(3)]

        for obj in hand_variables:
            grant_role(self.viewer["role"], obj.get_privilege_ancestor(), self.viewer["user"])

        for obj in hand_variables[1:]:
            grant_role(self.editor["role"], obj.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], hand_variables[2].get_privilege_ancestor(), self.owner["user"])
        # No roles
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["viewer"]["allHandVariables"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["viewer"]["allHandVariables"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["viewer"]["allHandVariables"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["viewer"]["allHandVariables"]["edges"]), 1)


class TestReadVariableDefinition(GQLTestCase):
    node_name = "VariableDefinitionNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_read_requires_login(self):
        vd = VariableDefinitionFactory()
        grant_role(self.viewer["role"], vd.module_definition, self.viewer["user"])

        query = """{viewer{ allVariableDefinitions {edges {node {
                    id name comment scope dataType specifiable
                    isOutputData}}}}}"""

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

        vd_gql_id = vd.gql_id

        query = """{viewer{ variableDefinition(id: "%s"){
                    id name comment scope dataType specifiable
                    isOutputData}}}
                """ % (
            vd_gql_id
        )

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_filters_by_privilege(self):
        vds = [VariableDefinitionFactory(), VariableDefinitionFactory(), VariableDefinitionFactory()]

        for vd in vds:
            grant_role(self.viewer["role"], vd.module_definition, self.viewer["user"])

        for vd in vds[1:]:
            grant_role(self.editor["role"], vd.module_definition, self.editor["user"])

        grant_role(self.owner["role"], vds[2].module_definition, self.owner["user"])

        query = """{viewer{ allVariableDefinitions{ edges{ node{
                    id name comment }}}}}"""
        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)

        self.assertEqual(len(result["data"]["viewer"]["allVariableDefinitions"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)

        self.assertEqual(len(result["data"]["viewer"]["allVariableDefinitions"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)

        self.assertEqual(len(result["data"]["viewer"]["allVariableDefinitions"]["edges"]), 1)


class TestCreateVariableDefinition(GQLTestCase):
    node_name = "VariableDefinitionNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_create_requires_privilege(self):
        md = ModuleDefinitionFactory()
        md_gql_id = md.gql_id
        grant_role(self.viewer["role"], md, self.viewer["user"])

        td = {
            "name": "test_create_requires_privilege",
            "comment": "don't create this VariableDefinition",
            "scope": "team",
            "dataType": "float",
            "specifiable": True,
            "isOutputData": False,
        }

        query = """
mutation{ createVariableDefinition(input: {
    moduleDefinition: "%s"
    name: "%s"
    comment: "%s"
    scope: "%s"
    dataType: "%s"
    specifiable: %s
    isOutputData: %s}) {
        variableDefinitionEdge {
            node {
                id
                name
                comment
                scope
                dataType
                specifiable
                isOutputData
            }
        }
    }
}""" % (
            md_gql_id,
            td["name"],
            td["comment"],
            td["scope"],
            td["dataType"],
            str(td["specifiable"]).lower(),
            str(td["isOutputData"]).lower(),
        )

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

        self.assertRaises(VariableDefinition.DoesNotExist, VariableDefinition.objects.get, **{"name": td["name"]})

    def test_create_produces_result(self):
        md = ModuleDefinitionFactory()
        md_gql_id = md.gql_id
        grant_role(self.owner["role"], md, self.owner["user"])

        td = {
            "name": "test_create_produces_result",
            "comment": "you can do it",
            "scope": "team",
            "dataType": "float",
            "specifiable": True,
            "isOutputData": False,
        }

        query = """
mutation{ createVariableDefinition(input: {
    moduleDefinition: "%s"
    name: "%s"
    comment: "%s"
    scope: "%s"
    dataType: "%s"
    specifiable: %s
    isOutputData: %s}) {
        variableDefinitionEdge {
            node {
                id
                name
                comment
                scope
                dataType
                specifiable
                isOutputData
            }
        }
    }
}""" % (
            md_gql_id,
            td["name"],
            td["comment"],
            td["scope"],
            td["dataType"],
            str(td["specifiable"]).lower(),
            str(td["isOutputData"]).lower(),
        )

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)

        lookup = VariableDefinition.objects.get(name=td["name"])

        self.assertEqual(lookup.name, td["name"])
        self.assertEqual(lookup.comment, td["comment"])
        self.assertEqual(lookup.scope, td["scope"])
        self.assertEqual(lookup.data_type, td["dataType"])
        self.assertEqual(lookup.specifiable, td["specifiable"])
        self.assertEqual(lookup.is_output_data, td["isOutputData"])


class TestUpdateVariableDefinition(GQLTestCase):
    node_name = "VariableDefinitionNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_update_requires_privilege(self):
        vd = VariableDefinitionFactory()
        vd_gql_id = vd.gql_id
        grant_role(self.viewer["role"], vd.module_definition, self.viewer["user"])

        td = {"name": "test_update_requires_privilege", "comment": "leave it alone", "scope": "team", "dataType": "float"}

        query = """mutation{ updateVariableDefinition(input: {
                    id: "%s"
                    name: "%s"
                    comment: "%s"
                    scope: "%s"
                    dataType: "%s" }){variableDefinition
                   {id name comment scope dataType}}}
                """ % (
            vd_gql_id,
            td["name"],
            td["comment"],
            td["scope"],
            td["dataType"],
        )

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        vd = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.float)
        vd_id = vd.pk
        vd_gql_id = vd.gql_id
        grant_role(self.owner["role"], vd.module_definition, self.owner["user"])

        td = {
            "name": "test_update_produces_result",
            "comment": "leave it alone",
            "scope": "team",
            "dataType": VariableDefinition.DATA_TYPE_CHOICES.float,
            "defaultValue": random_dt_value(VariableDefinition.DATA_TYPE_CHOICES.float),
        }

        query = """mutation{ updateVariableDefinition(input: {
                    id: "%s"
                    name: "%s"
                    comment: "%s"
                    scope: "%s"
                    dataType: "%s"
                    defaultValue: "%s" }){variableDefinition
                   {id name comment scope dataType}}}
                """ % (
            vd_gql_id,
            td["name"],
            td["comment"],
            td["scope"],
            td["dataType"],
            td["defaultValue"],
        )

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)

        lookup = VariableDefinition.objects.get(pk=vd_id)

        self.assertEqual(lookup.name, td["name"])
        self.assertEqual(lookup.comment, td["comment"])
        self.assertEqual(lookup.scope, td["scope"])
        self.assertEqual(lookup.data_type, td["dataType"])


class TestDeleteVariableDefinition(GQLTestCase):
    node_name = "VariableDefinitionNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_delete_requires_privilege(self):
        vd = VariableDefinitionFactory()
        vd_id = vd.pk
        vd_gql_id = vd.gql_id

        grant_role(self.viewer["role"], vd.module_definition, self.viewer["user"])

        query = """mutation{ deleteVariableDefinition(input: {
                    id: "%s" }){ id }}""" % (
            vd_gql_id,
        )

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

        VariableDefinition.objects.get(pk=vd_id)

    def test_delete_produces_result(self):
        vd = VariableDefinitionFactory()
        vd_id = vd.pk
        vd_gql_id = vd.gql_id

        grant_role(self.owner["role"], vd.module_definition, self.owner["user"])

        query = """mutation{  deleteVariableDefinition(input: {
                    id: "%s" }){ id }}""" % (
            vd_gql_id,
        )

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)

        self.assertIsNotNone(result["data"]["deleteVariableDefinition"]["id"])

        self.assertRaises(VariableDefinition.DoesNotExist, VariableDefinition.objects.get, **{"pk": vd_id})
