import unittest

import graphene
from graphql_relay.node.node import from_global_id

from ery_backend.base.testcases import GQLTestCase

from ..factories import FrontendFactory
from ..schema import FrontendQuery


class TestQuery(FrontendQuery, graphene.ObjectType):
    pass


class TestReadFrontend(GQLTestCase):
    """Ensure reading Frontend works"""

    node_name = "FrontendNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.all_query = """\
{
    allFrontends {
        edges {
            node {
                id
            }
        }
    }
}
"""
        cls.node_query = """\
query FrontendQuery($frontendid: ID!) {
    frontend(id: $frontendid) {
        id
    }
}
"""

    def setUp(self):
        self.frontend = FrontendFactory()
        self.td = {"frontendid": self.frontend.gql_id}

    @unittest.skip("XXX: Address in issue #740")
    def test_read_all_requires_login(self):
        """allFrontends query without a user is unauthorized"""
        result = self.gql_client.execute(self.all_query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_works(self):
        result = self.gql_client.execute(
            self.node_query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.fail_on_errors(result)
        self.assertEqual(int(from_global_id(result["data"]["frontend"]["id"])[1]), self.frontend.id)
