import graphene

from ery_backend.base.schema import EryMutationMixin
from ery_backend.base.testcases import GQLTestCase, create_test_hands
from ery_backend.hands.schema import HandQuery
from ery_backend.modules.schema import ModuleQuery
from ery_backend.stints.schema import StintQuery
from ery_backend.teams.schema import TeamQuery
from ery_backend.roles.utils import grant_role
from ..factories import LogFactory
from ..schema import LogQuery


class TestQuery(HandQuery, LogQuery, ModuleQuery, StintQuery, TeamQuery, graphene.ObjectType):
    pass


class TestReadLog(GQLTestCase):
    """Ensure reading Log works"""

    node_name = "LogNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def test_read_all_requires_login(self):
        """allLogs query without a user is unauthorized"""
        query = """{allLogs{ edges{ node{ id }}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        log = LogFactory()
        td = {"logid": log.gql_id}

        query = """query LogQuery($logid: ID!){log(id: $logid){ id }}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        query = """{allLogs{ edges{ node{ id }}}}"""
        logs = [LogFactory() for _ in range(3)]

        for obj in logs:
            grant_role(self.viewer["role"], obj.stint.get_privilege_ancestor(), self.viewer["user"])

        for obj in logs[1:]:
            grant_role(self.editor["role"], obj.stint.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], logs[2].stint.get_privilege_ancestor(), self.owner["user"])
        # No roles
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allLogs"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allLogs"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allLogs"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allLogs"]["edges"]), 1)

    def test_related_models(self):
        """
        Confirm all related models can be accessed.
        """
        hand = create_test_hands(n=1).first()
        team = hand.current_team
        module = hand.current_module
        stint = hand.stint
        hand_log = LogFactory(hand=hand, team=team, module=module, stint=stint)
        team_log = LogFactory(team=team, stint=stint)
        stint_log = LogFactory(stint=stint)

        grant_role(self.owner["role"], hand_log.stint.get_privilege_ancestor(), self.owner["user"])

        td = {'logid': hand_log.gql_id}
        query = """query LogQuery($logid: ID!){log(id: $logid){ hand { id } module { id }}}"""
        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.assertEqual(EryMutationMixin.gql_id_to_pk(result['data']['log']['hand']['id']), hand.pk)
        self.assertEqual(EryMutationMixin.gql_id_to_pk(result['data']['log']['module']['id']), module.pk)

        td = {'logid': team_log.gql_id}
        query = """query LogQuery($logid: ID!){log(id: $logid){ team { id } }}"""
        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.assertEqual(EryMutationMixin.gql_id_to_pk(result['data']['log']['team']['id']), team.pk)

        td = {'logid': stint_log.gql_id}
        query = """query LogQuery($logid: ID!){log(id: $logid){ stint { id } }}"""
        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.assertEqual(EryMutationMixin.gql_id_to_pk(result['data']['log']['stint']['id']), stint.pk)
