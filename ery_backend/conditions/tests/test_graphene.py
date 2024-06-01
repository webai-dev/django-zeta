from string import Template

import graphene

from ery_backend.base.testcases import GQLTestCase
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.mutations import ConditionMutation
from ery_backend.roles.utils import grant_role
from ery_backend.users.schema import ViewerQuery
from ery_backend.variables.factories import VariableDefinitionFactory

from ..schema import ConditionQuery
from ..models import Condition
from ..factories import ConditionFactory


class TestQuery(ConditionQuery, ViewerQuery, graphene.ObjectType):
    pass


class TestMutation(ConditionMutation, graphene.ObjectType):
    pass


class TestReadCondition(GQLTestCase):
    node_name = "ConditionNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_read_requires_login(self):
        condition = ConditionFactory()
        c_gql_id = condition.gql_id

        grant_role(self.viewer["role"], condition.module_definition, self.viewer["user"])

        # allConditions
        query = """{viewer{ allConditions {edges {node {id name}}}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

        # single Condition
        query = Template("""{viewer{ condition(id: "$gql_id"){id name}}}""").substitute(gql_id=c_gql_id)
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_filters_by_privilege(self):
        conditions = [
            ConditionFactory(left_type=Condition.TYPE_CHOICES.expression, right_type=Condition.TYPE_CHOICES.expression)
            for _ in range(3)
        ]

        for c in conditions:
            grant_role(self.viewer["role"], c.module_definition, self.viewer["user"])

        for c in conditions[1:]:
            grant_role(self.editor["role"], c.module_definition, self.editor["user"])

        grant_role(self.owner["role"], conditions[2].module_definition, self.owner["user"])

        query = """{viewer{ allConditions {edges {node {id name}}}}}"""

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)

        self.assertEqual(len(result["data"]["viewer"]["allConditions"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)

        self.assertEqual(len(result["data"]["viewer"]["allConditions"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)

        self.assertEqual(len(result["data"]["viewer"]["allConditions"]["edges"]), 1)


class TestCreateCondition(GQLTestCase):
    node_name = "ConditionNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_create_requires_privileges(self):
        md = ModuleDefinitionFactory()
        md_gql_id = md.gql_id

        right_vd = VariableDefinitionFactory(module_definition=md)
        rvd_gql_id = right_vd.gql_id
        left_vd = VariableDefinitionFactory(module_definition=md)
        lvd_gql_id = left_vd.gql_id
        grant_role(self.viewer["role"], md, self.viewer["user"])

        td = {
            "name": "test_create_requires_privileges",
            "comment": "don't create this one",
            "leftType": "variable",
            "rightType": "variable",
        }

        query = Template(
            """
mutation {
    createCondition(input: {
        moduleDefinition: "$md_gql_id",
        name: "$name",
        comment: "$comment",
        leftType: "$leftType",
        rightType: "$rightType",
        leftVariableDefinition: "$lvd_gql_id",
        rightVariableDefinition: "$rvd_gql_id"
    }) {
        conditionEdge {
            node {
                id
                name
                comment
                leftType
                rightType
            }
        }
    }
}
"""
        ).substitute(md_gql_id=md_gql_id, lvd_gql_id=lvd_gql_id, rvd_gql_id=rvd_gql_id, **td)

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)
        self.assertRaises(Condition.DoesNotExist, Condition.objects.get, name=td["name"])

    def test_create_produces_result(self):
        md = ModuleDefinitionFactory()
        md_gql_id = md.gql_id

        right_vd = VariableDefinitionFactory(module_definition=md)
        rvd_gql_id = right_vd.gql_id
        left_vd = VariableDefinitionFactory(module_definition=md)
        lvd_gql_id = left_vd.gql_id

        grant_role(self.owner["role"], md, self.owner["user"])

        td = {
            "name": "test_create_produces_result",
            "comment": "do it! do it now!",
            "leftType": "variable",
            "rightType": "variable",
        }

        query = Template(
            """
mutation {
    createCondition(input: {
        moduleDefinition: "$md_gql_id",
        name: "$name",
        comment: "$comment",
        leftType: "$leftType",
        rightType: "$rightType",
        leftVariableDefinition: "$lvd_gql_id",
        rightVariableDefinition: "$rvd_gql_id"
    }){
        conditionEdge {
            node {
                id
                name
                comment
                leftType
                rightType
            }
        }
    }
}"""
        ).substitute(md_gql_id=md_gql_id, lvd_gql_id=lvd_gql_id, rvd_gql_id=rvd_gql_id, **td)

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)

        self.assertEqual(result["data"]["createCondition"]["conditionEdge"]["node"]["name"].lower(), td["name"])
        self.assertEqual(result["data"]["createCondition"]["conditionEdge"]["node"]["comment"].lower(), td["comment"])
        self.assertEqual(result["data"]["createCondition"]["conditionEdge"]["node"]["leftType"].lower(), td["leftType"])
        self.assertEqual(result["data"]["createCondition"]["conditionEdge"]["node"]["rightType"].lower(), td["rightType"])

        lookup = Condition.objects.get(name=td["name"], comment=td["comment"])
        self.assertEqual(lookup.name, td["name"])
        self.assertEqual(lookup.comment, td["comment"])
        self.assertEqual(lookup.left_type.lower(), td["leftType"])
        self.assertEqual(lookup.right_type.lower(), td["rightType"])

        self.assertEqual(lookup.left_variable_definition.pk, left_vd.pk)

        self.assertEqual(lookup.right_variable_definition.pk, right_vd.pk)


class TestUpdateCondition(GQLTestCase):
    node_name = "ConditionNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_update_requires_privilege(self):
        condition = ConditionFactory()
        c_gql_id = condition.gql_id
        grant_role(self.viewer["role"], condition.module_definition, self.viewer["user"])

        lvd = VariableDefinitionFactory(module_definition=condition.module_definition)
        lvd_gql_id = lvd.gql_id

        td = {
            "name": "test_update_requires_privilege",
            "comment": "This is the wrong comment.",
            "leftType": "variable",
        }

        query = Template(
            """mutation{updateCondition(input: {
            id: "$c_gql_id",
            name: "$name",
            comment: "$comment",
            leftType: "$leftType",
            leftVariableDefinition: "$lvd_gql_id"}){condition
            { id name comment leftType }}}
            """
        ).substitute(c_gql_id=c_gql_id, lvd_gql_id=lvd_gql_id, **td)

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        condition = ConditionFactory()
        c_gql_id = condition.gql_id
        grant_role(self.owner["role"], condition.module_definition, self.owner["user"])

        lvd = VariableDefinitionFactory(module_definition=condition.module_definition)
        lvd_gql_id = lvd.gql_id

        td = {
            "name": "test_update_produces_result",
            "comment": "Updates gonna getcha",
            "leftType": "variable",
        }

        query = Template(
            """mutation{updateCondition(input: {
            id: "$c_gql_id",
            name: "$name",
            comment: "$comment",
            leftType: "$leftType",
            leftVariableDefinition: "$lvd_gql_id"}){condition
            { id name comment leftType }}}
            """
        ).substitute(c_gql_id=c_gql_id, lvd_gql_id=lvd_gql_id, **td)

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)

        for field in td:
            self.assertEqual(
                result["data"]["updateCondition"]["condition"][field].lower(),
                td[field].lower(),
                msg=f"response mismatch on {field}",
            )

        lookup = Condition.objects.get(name=td["name"], comment=td["comment"])

        self.assertEqual(lookup.name, td["name"])
        self.assertEqual(lookup.comment, td["comment"])
        self.assertEqual(lookup.left_type.lower(), td["leftType"])


class TestDeleteCondition(GQLTestCase):
    node_name = "ConditionNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_delete_requires_privileges(self):
        condition = ConditionFactory()
        cid = condition.pk
        c_gql_id = condition.gql_id
        grant_role(self.viewer["role"], condition.module_definition, self.viewer["user"])

        query = Template(
            """mutation{ deleteCondition(input:
            { id: "$c_gql_id" }){ id }}"""
        ).substitute(c_gql_id=c_gql_id)

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

        Condition.objects.get(pk=cid)

    def test_delete_produces_result(self):
        condition = ConditionFactory()
        cid = condition.pk
        c_gql_id = condition.gql_id
        grant_role(self.owner["role"], condition.module_definition, self.owner["user"])

        query = Template(
            """mutation{ deleteCondition(input:
            { id: "$c_gql_id" }){ id }}"""
        ).substitute(c_gql_id=c_gql_id)

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)

        self.assertIsNotNone(result["data"]["deleteCondition"]["id"])
        self.assertRaises(Condition.DoesNotExist, Condition.objects.get, **{"pk": cid})
