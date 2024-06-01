import graphene
from graphql_relay.node.node import from_global_id

from ery_backend.base.testcases import GQLTestCase

from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.mutations import ProcedureMutation, ProcedureArgumentMutation
from ery_backend.roles.utils import grant_role
from ery_backend.users.schema import ViewerQuery
from ..factories import ProcedureFactory, ProcedureArgumentFactory
from ..models import Procedure, ProcedureArgument
from ..schema import ProcedureQuery, ProcedureArgumentQuery


class TestQuery(ViewerQuery, ProcedureQuery, ProcedureArgumentQuery, graphene.ObjectType):
    pass


class TestMutation(ProcedureMutation, ProcedureArgumentMutation, graphene.ObjectType):
    pass


class TestReadProcedure(GQLTestCase):
    """Ensure reading Procedure works."""

    node_name = "ProcedureNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.all_query = """{allProcedures{ edges{ node{ id name comment}}}}"""
        cls.node_query = """query ProcedureQuery($procedureid: ID!){
            procedure(id: $procedureid){ id name comment}}"""

    def setUp(self):
        self.procedure = ProcedureFactory()
        self.td = {
            "procedureid": self.procedure.gql_id,
        }

    def test_read_all_requires_login(self):
        """allProcedures query without a user is unauthorized"""
        result = self.gql_client.execute(self.all_query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        result = self.gql_client.execute(self.node_query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        procedures = [ProcedureFactory() for _ in range(3)]

        for obj in procedures:
            grant_role(self.viewer["role"], obj.get_privilege_ancestor(), self.viewer["user"])

        for obj in procedures[1:]:
            grant_role(self.editor["role"], obj.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], procedures[2].get_privilege_ancestor(), self.owner["user"])
        # No roles
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allProcedures"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allProcedures"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allProcedures"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allProcedures"]["edges"]), 1)

    def test_read_node_works(self):
        grant_role(self.viewer["role"], self.procedure.get_privilege_ancestor(), self.viewer["user"])
        result = self.gql_client.execute(
            self.node_query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.fail_on_errors(result)
        self.assertEqual(int(from_global_id(result["data"]["procedure"]["id"])[1]), self.procedure.id)

    def test_no_soft_deletes_in_all_query(self):
        """
        Confirm soft_deleted objects are not returned in query.
        """
        query = """{allProcedures { edges{ node{ id }}}}"""
        procedure = ProcedureFactory()
        grant_role(self.viewer["role"], procedure, self.viewer["user"])

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(len(result["data"]["allProcedures"]["edges"]), 1)

        procedure.soft_delete()
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(len(result["data"]["allProcedures"]["edges"]), 0)

    def test_no_soft_deletes_in_single_query(self):
        """
        Confirms soft_deleted object not returned in query.
        """
        query = """query ProcedureQuery($procedureid: ID!){
            procedure(id: $procedureid){ id }}
            """
        procedure = ProcedureFactory()
        grant_role(self.viewer["role"], procedure, self.viewer["user"])

        result = self.gql_client.execute(
            query,
            variable_values={"procedureid": procedure.gql_id},
            context_value=self.gql_client.get_context(user=self.viewer["user"]),
        )
        self.fail_on_errors(result)

        procedure.soft_delete()
        result = self.gql_client.execute(
            query,
            variable_values={"procedureid": procedure.gql_id},
            context_value=self.gql_client.get_context(user=self.viewer["user"]),
        )
        self.assertEqual('Procedure matching query does not exist.', result['errors'][0]['message'])


class TestCreateProcedure(GQLTestCase):
    node_name = "ProcedureNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.module_definition = ModuleDefinitionFactory()

    def setUp(self):
        self.td = {
            'name': 'test_procedure',
            'comment': 'That is what it is',
        }

        self.query = """
mutation ($name: String, $comment: String) {
    createProcedure(input: {
        name: $name
        comment: $comment
    }) {
        procedureEdge {
            node {
                id
            }
        }
    }
}
"""

    def test_create_produces_result(self):
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        lookup = Procedure.objects.get(name=self.td["name"])

        self.assertEqual(lookup.name, self.td["name"])
        self.assertEqual(lookup.comment, self.td["comment"])


class TestUpdateProcedure(GQLTestCase):
    node_name = "ProcedureNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.procedure = ProcedureFactory()
        self.td = {"procedure": self.procedure.gql_id, "name": "test_procedure", "comment": "that is what it is"}
        self.query = """mutation ($procedure: ID!, $name: String!, $comment: String!){
             updateProcedure(input: {
                id: $procedure,
                name: $name
                comment: $comment
                    }){
                        procedure {
                            id name comment }
                        }
                    }
                """

    def test_update_requires_privilege(self):
        grant_role(self.viewer["role"], self.procedure.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        grant_role(self.owner["role"], self.procedure.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        lookup = Procedure.objects.get(pk=self.procedure.id)

        self.assertEqual(lookup.name, self.td["name"])
        self.assertEqual(lookup.comment, self.td["comment"])


class TestDeleteProcedure(GQLTestCase):
    node_name = "ProcedureNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.procedure = ProcedureFactory()
        self.td = {"procedure": self.procedure.gql_id}
        self.query = """mutation ($procedure: ID!){
             deleteProcedure(input: {
                id: $procedure,
                    })
                   { id }
                   }
                """

    def test_delete_requires_privilege(self):
        grant_role(self.viewer["role"], self.procedure.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        Procedure.objects.get(pk=self.procedure.id)

    def test_delete_produces_result(self):
        grant_role(self.owner["role"], self.procedure.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertTrue(result["data"]["deleteProcedure"]["id"])

        self.procedure.refresh_from_db()
        self.assertEqual(self.procedure.state, self.procedure.STATE_CHOICES.deleted)


class TestReadProcedureArgument(GQLTestCase):
    """Ensure reading ProcedureArgument works"""

    node_name = "ProcedureArgumentNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.all_query = """{allProcedureArguments{ edges{ node{ id procedure{ name }}}}}"""
        cls.node_query = """query ProcedureArgumentQuery($procedureargumentid: ID!){
            procedureArgument(id: $procedureargumentid){ id  procedure{ name }}}"""

    def setUp(self):
        self.procedure_argument = ProcedureArgumentFactory()
        self.td = {
            "procedureargumentid": self.procedure_argument.gql_id,
        }

    def test_read_all_requires_login(self):
        """allProcedureArguments query without a user is unauthorized"""
        result = self.gql_client.execute(self.all_query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        result = self.gql_client.execute(self.node_query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        procedure_arguments = [ProcedureArgumentFactory() for _ in range(3)]

        for obj in procedure_arguments:
            grant_role(self.viewer["role"], obj.get_privilege_ancestor(), self.viewer["user"])

        for obj in procedure_arguments[1:]:
            grant_role(self.editor["role"], obj.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], procedure_arguments[2].get_privilege_ancestor(), self.owner["user"])
        # No roles
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allProcedureArguments"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allProcedureArguments"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allProcedureArguments"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allProcedureArguments"]["edges"]), 1)

    def test_read_node_works(self):
        grant_role(self.viewer["role"], self.procedure_argument.get_privilege_ancestor(), self.viewer["user"])
        result = self.gql_client.execute(
            self.node_query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.fail_on_errors(result)
        self.assertEqual(int(from_global_id(result["data"]["procedureArgument"]["id"])[1]), self.procedure_argument.id)


class TestCreateProcedureArgument(GQLTestCase):
    node_name = "ProcedureArgumentNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.procedure = ProcedureFactory()
        self.td = {'procedure': self.procedure.gql_id, 'name': 'test_procedure_arg', 'comment': "Test procedure arg"}

        self.query = """
mutation ($procedure: ID!, $name: String!, $comment: String) {
    createProcedureArgument(input: {
        name: $name
        comment: $comment
        procedure: $procedure
    }) {
        procedureArgumentEdge {
            node {
                id
                procedure {
                    id
                }
                name
                comment
            }
        }
    }
}
"""

    def test_create_requires_user(self):
        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        self.assertRaises(ProcedureArgument.DoesNotExist, ProcedureArgument.objects.get, **{"name": self.td["name"]})

    def test_create_requires_privilege(self):
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.assert_query_was_unauthorized(result)
        self.assertRaises(ProcedureArgument.DoesNotExist, ProcedureArgument.objects.get, **{"name": self.td["name"]})

    def test_create_produces_result(self):
        grant_role(self.owner["role"], self.procedure, self.owner["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        lookup = ProcedureArgument.objects.get(name=self.td["name"])

        self.assertEqual(lookup.name, self.td["name"])
        self.assertEqual(lookup.comment, self.td["comment"])
        self.assertEqual(lookup.procedure, self.procedure)


class TestUpdateProcedureArgument(GQLTestCase):
    node_name = "ProcedureArgumentNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.procedure_argument = ProcedureArgumentFactory()
        self.td = {
            "procedureArgument": self.procedure_argument.gql_id,
            "name": "test_procedure_argument",
            "comment": "Test procedure argument new comment",
        }
        self.query = """mutation ($procedureArgument: ID!, $name: String!, $comment: String){
             updateProcedureArgument(input: {
                id: $procedureArgument,
                name: $name
                comment: $comment
                    }){
                        procedureArgument {
                            id comment name procedure { id }
                        }
                    }
                }
                """

    def test_update_requires_privilege(self):
        grant_role(self.viewer["role"], self.procedure_argument.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        grant_role(self.owner["role"], self.procedure_argument.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        lookup = ProcedureArgument.objects.get(pk=self.procedure_argument.id)

        self.assertEqual(lookup.comment, self.td["comment"])


class TestDeleteProcedureArgument(GQLTestCase):
    node_name = "ProcedureArgumentNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.procedure_argument = ProcedureArgumentFactory()
        self.td = {"procedureArgument": self.procedure_argument.gql_id}
        self.query = """mutation ($procedureArgument: ID!){
             deleteProcedureArgument(input: {
                id: $procedureArgument,
                    })
                   { id }
                   }
                """

    def test_delete_requires_privilege(self):
        grant_role(self.viewer["role"], self.procedure_argument.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        ProcedureArgument.objects.get(pk=self.procedure_argument.id)

    def test_delete_produces_result(self):
        grant_role(self.owner["role"], self.procedure_argument.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertTrue(result["data"]["deleteProcedureArgument"]["id"])

        self.assertRaises(ProcedureArgument.DoesNotExist, ProcedureArgument.objects.get, **{"pk": self.procedure_argument.id})
