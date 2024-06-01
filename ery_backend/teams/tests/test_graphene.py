import graphene
from ery_backend.base.testcases import GQLTestCase

from ery_backend.modules.factories import ModuleFactory
from ery_backend.roles.utils import grant_role
from ery_backend.stints.factories import StintFactory
from ery_backend.syncs.schema import EraQuery
from ery_backend.users.schema import ViewerQuery
from ery_backend.variables.factories import TeamVariableFactory
from ..factories import TeamFactory


class TestQuery(EraQuery, ViewerQuery, graphene.ObjectType):
    pass


class TestReadTeam(GQLTestCase):
    """Ensure reading Team works"""

    node_name = "TeamNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def test_read_all_requires_login(self):
        """allTeams query without a user is unauthorized"""
        query = """{viewer{ allTeams{ edges{ node{ id }}}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        team = TeamFactory()
        td = {"teamid": team.gql_id}

        query = """query TeamQuery($teamid: ID!){viewer{ team(id: $teamid){ id }}}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        query = """{viewer{ allTeams{ edges{ node{ id era{ name }}}}}}"""
        teams = [TeamFactory() for _ in range(3)]

        for obj in teams:
            grant_role(self.viewer["role"], obj.stint.get_privilege_ancestor(), self.viewer["user"])

        for obj in teams[1:]:
            grant_role(self.editor["role"], obj.stint.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], teams[2].stint.get_privilege_ancestor(), self.owner["user"])
        # No roles
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["viewer"]["allTeams"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["viewer"]["allTeams"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["viewer"]["allTeams"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["viewer"]["allTeams"]["edges"]), 1)


class TestReadRelationships(GQLTestCase):
    """
    Confirm user can access related models as intended.
    """

    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def setUp(self):
        stint = StintFactory()
        self.module = ModuleFactory(stint=stint)
        self.team = TeamFactory(stint=stint)
        grant_role(self.viewer["role"], stint, self.viewer["user"])

        self.td = {"gqlId": self.team.gql_id}
        self.context = self.gql_client.get_context(user=self.viewer["user"])
        self.user = self.viewer["user"]
        self.user.current_team = self.team
        self.user.save()

    def test_variables(self):
        tv_1 = TeamVariableFactory(module=self.module, team=self.team)
        tv_2 = TeamVariableFactory(module=self.module, team=self.team)
        expected_team_variable_ids = [tv.gql_id for tv in (tv_1, tv_2)]

        query = """
query TeamQuery($gqlId: ID!){viewer{ team(id: $gqlId){ variables { edges { node { id value } } } } } }"""
        result = self.gql_client.execute(query, variable_values=self.td, context_value=self.context)
        team_variable_ids = [edge['node']['id'] for edge in result['data']["viewer"]['team']['variables']['edges']]
        for team_variable_id in expected_team_variable_ids:
            self.assertIn(team_variable_id, team_variable_ids)
