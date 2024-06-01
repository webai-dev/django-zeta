import graphene

from ery_backend.actions.factories import ActionFactory
from ery_backend.actions.schema import ActionQuery
from ery_backend.base.testcases import GQLTestCase
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.modules.schema import ModuleDefinitionQuery
from ery_backend.mutations import EraMutation
from ery_backend.roles.utils import grant_role
from ery_backend.syncs.factories import EraFactory

from ..models import Era
from ..schema import EraQuery


class TestQuery(EraQuery, ActionQuery, ModuleDefinitionQuery, graphene.ObjectType):
    pass


class TestMutation(EraMutation, graphene.ObjectType):
    pass


class TestReadEra(GQLTestCase):
    node_name = "EraNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_read_requires_login(self):
        md = ModuleDefinitionFactory()
        if md.start_era:
            self.fail("Autogeneration fixed. Update code.")
        md.start_era = EraFactory(module_definition=md)
        md.save()
        era = Era.objects.get(module_definition=md)
        era_id = era.gql_id

        td = {"gqlId": era_id}

        query = """query Era($gqlId: ID!){era(id: $gqlId){name comment}}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

        query = """{allEras {edges {node{name comment moduleDefinition{id name}}}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_filters_by_privilege(self):
        mds = [ModuleDefinitionFactory() for _ in range(3)]
        for md in mds:
            if md.start_era:
                self.fail("Autogeneration fixed. Update code.")
            md.start_era = EraFactory(module_definition=md)
            md.save()

        for md in mds:
            grant_role(self.viewer["role"], md, self.viewer["user"])

        for md in mds[1:]:
            grant_role(self.editor["role"], md, self.editor["user"])

        grant_role(self.owner["role"], mds[2], self.owner["user"])

        query = """{allEras {edges {node {id name comment moduleDefinition{id name}}}}}"""

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allEras"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allEras"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allEras"]["edges"]), 1)


class TestCreateEra(GQLTestCase):
    node_name = "EraNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_create_requires_privileges(self):
        md = ModuleDefinitionFactory()
        grant_role(self.viewer["role"], md, self.viewer["user"])

        action = ActionFactory()

        td = {
            "mdId": md.gql_id,
            "actionId": action.gql_id,
            "name": "test create requires privileges",
            "comment": "not this one",
        }

        query = """
mutation CreateEra($mdId: ID!, $actionId: ID, $name: String, $comment: String) {
    createEra(input: {
        moduleDefinition: $mdId,
        action: $actionId,
        name: $name,
        comment: $comment
    }) {
        eraEdge {
            node {
                id
                name
                comment
            }
        }
    }
}
                """

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_create_produces_era(self):
        md = ModuleDefinitionFactory()
        grant_role(self.owner["role"], md, self.owner["user"])

        action = ActionFactory()

        td = {"name": "test create produces era", "comment": "create this era", "mdId": md.gql_id, "actionId": action.gql_id}

        query = """
mutation CreateEra($mdId: ID!, $actionId: ID, $name: String, $comment: String) {
    createEra(input: {
        moduleDefinition: $mdId,
        action: $actionId,
        name: $name,
        comment: $comment
    }) {
        eraEdge {
            node {
                id
                name
                comment
                moduleDefinition {
                    name
                }
                action {
                    name
                }
            }
        }
    }
}
"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertEqual(result["data"]["createEra"]["eraEdge"]["node"]["moduleDefinition"]["name"], md.name)

        self.assertEqual(result["data"]["createEra"]["eraEdge"]["node"]["action"]["name"], action.name)

        td.pop("mdId")
        td.pop("actionId")

        for field in td:
            self.assertEqual(result["data"]["createEra"]["eraEdge"]["node"][field], td[field], msg=f"mismatch on {field}")

        lookup = Era.objects.get(name=td["name"])

        self.assertEqual(lookup.module_definition, md)
        self.assertEqual(lookup.action, action)

        for field in td:
            self.assertEqual(getattr(lookup, field, None), td[field], msg=f"mismatch on {field}")


class TestUpdateEra(GQLTestCase):
    node_name = "EraNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_update_requires_privilege(self):
        md = ModuleDefinitionFactory()
        if md.start_era:
            self.fail("Autogeneration fixed. Update code.")
        md.start_era = EraFactory(module_definition=md)
        md.save()
        grant_role(self.viewer["role"], md, self.viewer["user"])

        era_id = md.start_era.gql_id
        action = ActionFactory(module_definition=md)

        td = {
            "name": "test update requires privilege",
            "comment": "don't allow this change",
            "eraId": era_id,
            "actionId": action.gql_id,
        }

        query = """mutation UpdateEra($eraId: ID!, $actionId: ID, $name: String, $comment: String)
                    { updateEra( input: {
                    id: $eraId,
                    action: $actionId,
                    name: $name,
                    comment: $comment})
                   {era{  id name comment action { id }}}}
                """

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        md = ModuleDefinitionFactory()
        if md.start_era:
            self.fail("Autogeneration fixed. Update code.")
        md.start_era = EraFactory(module_definition=md)
        md.save()
        grant_role(self.owner["role"], md, self.owner["user"])

        era_id = md.start_era.gql_id
        action = ActionFactory(module_definition=md)

        td = {
            "name": "test update requires privilege",
            "comment": "don't allow this change",
            "eraId": era_id,
            "actionId": action.gql_id,
        }

        query = """mutation UpdateEra($eraId: ID!, $actionId: ID, $name: String, $comment: String)
                    { updateEra( input: {
                    id: $eraId,
                    action: $actionId,
                    name: $name,
                    comment: $comment})
                   {era{  id name comment action { id }}}}
                """
        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertEqual(result["data"]["updateEra"]["era"]["action"]["id"], td["actionId"])

        td.pop("eraId")
        td.pop("actionId")

        for field in td:
            self.assertEqual(result["data"]["updateEra"]["era"][field], td[field], msg=f"mismatch on {field}")

        era = Era.objects.get(pk=md.start_era.id)

        self.assertEqual(era.action.pk, action.pk)

        for field in td:
            self.assertEqual(getattr(era, field, None), td[field], msg=f"mismatch on {field}")


class TestDeleteEra(GQLTestCase):
    node_name = "EraNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_delete_requires_privilege(self):
        md = ModuleDefinitionFactory()
        grant_role(self.viewer["role"], md, self.viewer["user"])
        if md.start_era:
            self.fail("Autogeneration fixed. Update code.")
        md.start_era = EraFactory(module_definition=md)
        md.save()
        era = md.start_era
        era_id = era.pk
        td = {"gqlId": era.gql_id}

        query = """mutation DeleteEra($gqlId: ID!){ deleteEra(input: {id: $gqlId}){id}} """

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        Era.objects.get(pk=era_id)

    def test_delete_produces_result(self):
        md = ModuleDefinitionFactory()
        if md.start_era:
            self.fail("Autogeneration fixed. Update code.")
        md.start_era = EraFactory(module_definition=md)
        md.save()
        grant_role(self.owner["role"], md, self.owner["user"])

        era = md.start_era
        era_id = era.pk
        td = {"gqlId": era.gql_id}

        query = """mutation DeleteEra($gqlId: ID!){ deleteEra(input: {id: $gqlId}){id}}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertTrue(result["data"]["deleteEra"]["id"])
        self.assertRaises(Era.DoesNotExist, Era.objects.get, **{"pk": era_id})
