import graphene

from ery_backend.base.testcases import GQLTestCase
from ery_backend.modules.factories import ModuleFactory
from ery_backend.modules.schema import ModuleQuery
from ery_backend.roles.utils import grant_role
from ery_backend.stages.schema import StageQuery
from ery_backend.stints.factories import StintFactory
from ery_backend.stints.schema import StintQuery
from ery_backend.syncs.schema import EraQuery
from ery_backend.variables.factories import HandVariableFactory
from ery_backend.variables.schema import HandVariableQuery

from ..factories import HandFactory
from ..schema import HandQuery


class TestQuery(EraQuery, HandQuery, HandVariableQuery, ModuleQuery, StageQuery, StintQuery, graphene.ObjectType):
    pass


class TestReadHand(GQLTestCase):
    """Ensure reading Hand works"""

    node_name = "HandNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def test_read_all_requires_login(self):
        """allHands query without a user is unauthorized"""
        query = """{allHands{ edges{ node{ id }}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        hand = HandFactory()
        td = {"handid": hand.gql_id}

        query = """query HandQuery($handid: ID!){hand(id: $handid){ id }}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        query = """{allHands{ edges{ node{
         id status era{ name }
         currentModule{ stint{ status } }
         stage{ stageDefinition{ name } } lastSeen }}}}"""
        hands = [HandFactory() for _ in range(3)]

        for obj in hands:
            grant_role(self.viewer["role"], obj.stint.get_privilege_ancestor(), self.viewer["user"])

        for obj in hands[1:]:
            grant_role(self.editor["role"], obj.stint.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], hands[2].stint.get_privilege_ancestor(), self.owner["user"])
        # No roles
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allHands"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allHands"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allHands"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allHands"]["edges"]), 1)


class TestReadRelationships(GQLTestCase):
    """
    Confirm user can access related models as intended.
    """

    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def setUp(self):
        stint = StintFactory()
        self.module = ModuleFactory(stint=stint)
        self.hand = HandFactory(stint=stint, current_module=self.module)
        grant_role(self.viewer["role"], stint, self.viewer["user"])
        self.td = {"gqlId": self.hand.gql_id}
        self.context = self.gql_client.get_context(user=self.viewer["user"])

    def test_variables(self):
        hv_1 = HandVariableFactory(module=self.module, hand=self.hand)
        hv_2 = HandVariableFactory(module=self.module, hand=self.hand)
        expected_variable_ids = [hv.gql_id for hv in (hv_1, hv_2)]
        query = """\
query HandQuery($gqlId: ID!) {
    hand(id: $gqlId) {
        id
        variables {
            edges {
                node {
                    id
                    value
                }
            }
        }
    }
}"""
        grant_role(self.viewer["role"], self.hand.stint.get_privilege_ancestor(), self.viewer["user"])
        result = self.gql_client.execute(query, variable_values=self.td, context_value=self.context)
        variable_ids = [edge['node']['id'] for edge in result['data']['hand']['variables']['edges']]
        for variable_id in expected_variable_ids:
            self.assertIn(variable_id, variable_ids)
