from unittest import mock

import graphene

from ery_backend.base.testcases import GQLTestCase, create_test_stintdefinition
from ery_backend.frontends.models import Frontend
from ery_backend.hands.factories import HandFactory
from ery_backend.hands.models import Hand
from ery_backend.mutations import StintMutation
from ery_backend.roles.utils import grant_role
from ery_backend.stints.models import Stint
from ery_backend.stint_specifications.models import StintSpecification
from ery_backend.stint_specifications.factories import StintSpecificationFactory
from ery_backend.stint_specifications.schema import StintSpecificationQuery
from ery_backend.syncs.schema import EraQuery
from ery_backend.teams.factories import TeamFactory
from ery_backend.teams.schema import TeamQuery
from ery_backend.users.factories import UserFactory

from ..factories import StintDefinitionFactory, StintFactory
from ..schema import StintDefinitionQuery, StintQuery


class TestQuery(EraQuery, StintQuery, StintDefinitionQuery, StintSpecificationQuery, TeamQuery, graphene.ObjectType):
    pass


class TestMutation(StintMutation, graphene.ObjectType):
    pass


class TestReadStintDefinition(GQLTestCase):
    """Ensure reading StintDefinition works"""

    node_name = "StintDefinitionNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def test_read_all_requires_login(self):
        """allStintDefinitions query without a user is unauthorized"""
        query = """{allStintDefinitions{ edges{ node{ id name}}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        stint_definition = StintDefinitionFactory()
        td = {"stintdefinitionid": stint_definition.gql_id}

        query = """query StintDefinitionQuery($stintdefinitionid: ID!){stintDefinition(id: $stintdefinitionid){ id name }}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        query = """{allStintDefinitions{ edges{ node{ id name }}}}"""

        stint_definitions = [StintDefinitionFactory() for _ in range(3)]

        for obj in stint_definitions:
            grant_role(self.viewer["role"], obj, self.viewer["user"])

        for obj in stint_definitions[1:]:
            grant_role(self.editor["role"], obj, self.editor["user"])

        grant_role(self.owner["role"], stint_definitions[2], self.owner["user"])

        # No roles
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStintDefinitions"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStintDefinitions"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStintDefinitions"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStintDefinitions"]["edges"]), 1)

    def test_no_soft_deletes_in_all_query(self):
        """
        Confirm soft_deleted objects are not returned in query.
        """
        query = """{allStintDefinitions { edges{ node{ id }}}}"""
        stint_definition = StintDefinitionFactory()
        grant_role(self.viewer["role"], stint_definition, self.viewer["user"])

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(len(result["data"]["allStintDefinitions"]["edges"]), 1)

        stint_definition.soft_delete()
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(len(result["data"]["allStintDefinitions"]["edges"]), 0)

    def test_no_soft_deletes_in_single_query(self):
        """
        Confirms soft_deleted object not returned in query.
        """
        query = """query StintDefinitionQuery($stintDefinitionid: ID!){
            stintDefinition(id: $stintDefinitionid){ id }}
            """
        stint_definition = StintDefinitionFactory()
        grant_role(self.viewer["role"], stint_definition, self.viewer["user"])

        result = self.gql_client.execute(
            query,
            variable_values={"stintDefinitionid": stint_definition.gql_id},
            context_value=self.gql_client.get_context(user=self.viewer["user"]),
        )
        self.fail_on_errors(result)

        stint_definition.soft_delete()
        result = self.gql_client.execute(
            query,
            variable_values={"stintDefinitionid": stint_definition.gql_id},
            context_value=self.gql_client.get_context(user=self.viewer["user"]),
        )
        self.assertEqual('StintDefinition matching query does not exist.', result['errors'][0]['message'])


class TestReadStint(GQLTestCase):
    """Ensure reading Stint works"""

    node_name = "StintNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def test_read_all_requires_login(self):
        """allStints query without a user is unauthorized"""
        query = """
{
    allStints {
        edges {
            node {
                id
                status
            }
        }
    }
}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        stint = StintFactory()
        td = {"stintid": stint.gql_id}

        query = """query StintQuery($stintid: ID!){stint(id: $stintid){ id status }}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        query = """
{
    allStints {
        edges {
            node {
                id
                status
                started
                ended
            }
        }
    }
}
"""
        stints = [StintFactory() for _ in range(3)]

        for obj in stints:
            grant_role(self.viewer["role"], obj.get_privilege_ancestor(), self.viewer["user"])

        for obj in stints[1:]:
            grant_role(self.editor["role"], obj.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], stints[2].get_privilege_ancestor(), self.owner["user"])
        # No roles
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStints"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStints"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStints"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStints"]["edges"]), 1)

    def test_read_all_filter_where_to_run(self):
        """allStints query without a user is unauthorized"""
        stints = [
            StintFactory(
                stint_specification=StintSpecificationFactory(where_to_run=StintSpecification.WHERE_TO_RUN_CHOICES.lab)
            )
            for _ in range(1)
        ]
        stints += [
            StintFactory(
                stint_specification=StintSpecificationFactory(where_to_run=StintSpecification.WHERE_TO_RUN_CHOICES.market)
            )
            for _ in range(2)
        ]
        stints += [
            StintFactory(
                stint_specification=StintSpecificationFactory(where_to_run=StintSpecification.WHERE_TO_RUN_CHOICES.simulation)
            )
            for _ in range(3)
        ]

        for obj in stints:
            grant_role(self.viewer["role"], obj.get_privilege_ancestor(), self.viewer["user"])
            grant_role(self.viewer["role"], obj.stint_specification.get_privilege_ancestor(), self.viewer["user"])

        query = """
{
    allStintSpecifications {
        edges {
            node {
                stints {
                    edges {
                        node {
                            id
                            status
                        }
                    }
                }
            }
        }
    }
}"""
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(len(result["data"]["allStintSpecifications"]["edges"]), 6)

        query = """
{
    allStintSpecifications(whereToRun: "lab") {
        edges {
            node {
                stints {
                    edges {
                        node {
                            id
                            status
                        }
                    }
                }
            }
        }
    }
}"""
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(len(result["data"]["allStintSpecifications"]["edges"]), 1)

        query = """
{
    allStintSpecifications(whereToRun: "market") {
        edges {
            node {
                stints {
                    edges {
                        node {
                            id
                            status
                        }
                    }
                }
            }
        }
    }
}"""
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(len(result["data"]["allStintSpecifications"]["edges"]), 2)

        query = """
{
    allStintSpecifications(whereToRun: "simulation") {
        edges {
            node {
                stints {
                    edges {
                        node {
                            id
                            status
                        }
                    }
                }
            }
        }
    }
}"""
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(len(result["data"]["allStintSpecifications"]["edges"]), 3)


class TestReadRelationships(GQLTestCase):
    """
    Confirm user can access related models as intended.
    """

    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def setUp(self):
        self.stint = StintFactory()
        grant_role(self.viewer["role"], self.stint.get_privilege_ancestor(), self.viewer["user"])
        self.td = {"gqlId": self.stint.gql_id}
        self.context = self.gql_client.get_context(user=self.viewer["user"])

    def test_teams(self):
        team_1 = TeamFactory(stint=self.stint)
        team_2 = TeamFactory(stint=self.stint)
        expected_team_ids = [team.gql_id for team in (team_1, team_2)]
        query = """
query StintQuery($gqlId: ID!){stint(id: $gqlId){ id teams{ edges{ node{ id name }}}}}
"""
        result = self.gql_client.execute(query, variable_values=self.td, context_value=self.context)
        team_ids = [edge['node']['id'] for edge in result['data']['stint']['teams']['edges']]
        for team_id in expected_team_ids:
            self.assertIn(team_id, team_ids)

    def test_hands(self):
        hand_1 = HandFactory(stint=self.stint)
        hand_2 = HandFactory(stint=self.stint)
        expected_hand_ids = [hand.gql_id for hand in (hand_1, hand_2)]
        query = """
query StintQuery($gqlId: ID!){stint(id: $gqlId){ id hands{ edges{ node{ id era{ name }}}}}}
"""
        result = self.gql_client.execute(query, variable_values=self.td, context_value=self.context)
        hand_ids = [edge['node']['id'] for edge in result['data']['stint']['hands']['edges']]
        for hand_id in expected_hand_ids:
            self.assertIn(hand_id, hand_ids)


class TestStartStint(GQLTestCase):
    node_name = "StintNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        stint_definition = create_test_stintdefinition(Frontend.objects.get(name='Web'))
        self.stint_specification = StintSpecificationFactory(stint_definition=stint_definition)
        self.stint = self.stint_specification.realize(UserFactory())
        self.hand = HandFactory(stint=self.stint, user=UserFactory())
        self.test_data = {"gqlId": self.stint.gql_id}
        self.query = """
mutation StartStint($gqlId: ID!){
    startStint(input: {id: $gqlId, signalPubsub: false}){
        success
    }
}"""

    def test_stop_requires_authorization(self):
        result = self.gql_client.execute(
            self.query, variable_values=self.test_data, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_start_stint(self):
        """
        Confirm hand/stint status changes on start.
        """
        self.hand.refresh_from_db()
        self.assertIsNone(self.hand.status)
        grant_role(self.owner["role"], self.stint.get_privilege_ancestor(), self.owner["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.test_data, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.assertEqual(True, result['data']['startStint']['success'])
        self.hand.refresh_from_db()
        self.stint.refresh_from_db()
        self.assertEqual(self.hand.status, Hand.STATUS_CHOICES.active)
        self.assertEqual(self.stint.status, Stint.STATUS_CHOICES.running)


class TestStopStint(GQLTestCase):
    node_name = "StintNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        stint_definition = create_test_stintdefinition(Frontend.objects.get(name='Web'))
        self.stint_specification = StintSpecificationFactory(stint_definition=stint_definition)
        self.stint = self.stint_specification.realize(UserFactory())
        self.hand = HandFactory(stint=self.stint, user=UserFactory())
        self.test_data = {"gqlId": self.stint.gql_id}
        self.query = """
mutation StopStint($gqlId: ID!){
    stopStint(input: {id: $gqlId}){
        success
    }
}"""

    def test_stop_requires_authorization(self):
        result = self.gql_client.execute(
            self.query, variable_values=self.test_data, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.assert_query_was_unauthorized(result)

    @mock.patch('ery_backend.hands.models.Hand.pay')
    def test_stop_stint(self, mock_pay):
        """
        Confirm hand/stint status changes on stop
        """
        grant_role(self.owner["role"], self.stint.get_privilege_ancestor(), self.owner["user"])
        self.stint.start(started_by=UserFactory(), signal_pubsub=False)

        result = self.gql_client.execute(
            self.query, variable_values=self.test_data, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.assertEqual(True, result['data']['stopStint']['success'])
        self.stint.refresh_from_db()
        self.hand.refresh_from_db()
        self.assertEqual(self.stint.status, Stint.STATUS_CHOICES.cancelled)
        self.assertEqual(self.hand.status, Hand.STATUS_CHOICES.cancelled)
        self.assertEqual(self.stint.stopped_by, self.owner["user"])
