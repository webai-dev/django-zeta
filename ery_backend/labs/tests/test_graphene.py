from unittest import mock
import graphene

from ery_backend.base.testcases import GQLTestCase, create_test_hands
from ery_backend.mutations import LabMutation
from ery_backend.roles.utils import grant_role
from ery_backend.stints.factories import StintFactory
from ery_backend.stints.models import Stint
from ery_backend.stints.schema import StintQuery
from ery_backend.users.factories import UserFactory

from ..factories import LabFactory
from ..models import Lab
from ..schema import LabQuery


class TestQuery(StintQuery, LabQuery, graphene.ObjectType):
    pass


class TestMutation(LabMutation, graphene.ObjectType):
    pass


class TestReadLab(GQLTestCase):
    """Ensure reading Lab works"""

    node_name = "LabNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def test_read_all_requires_login(self):
        """allLabs query without a user is unauthorized"""
        query = """{allLabs{ edges{ node{ id }}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        lab = LabFactory()
        td = {"labid": lab.gql_id}

        query = """query LabQuery($labid: ID!){lab(id: $labid){ id }}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        query = """{allLabs{ edges{ node{ currentStint {id } }}}}"""
        stint = StintFactory()
        labs = [LabFactory(current_stint=stint) for _ in range(3)]

        for obj in labs:
            grant_role(self.viewer["role"], obj, self.viewer["user"])

        for obj in labs[1:]:
            grant_role(self.editor["role"], obj, self.editor["user"])

        grant_role(self.owner["role"], labs[2], self.owner["user"])
        # No roles
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allLabs"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allLabs"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allLabs"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allLabs"]["edges"]), 1)


class TestCreateLab(GQLTestCase):
    node_name = "LabNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_create_requires_privilege(self):
        td = {
            "name": "test_create_requires_privilege",
            "comment": "don't create this lab",
            "secret": "41dayswithoutatestcras...DOH",
        }

        query = """mutation{ createLab(input: {
                    name: "%s"
                    comment: "%s"
                    secret: "%s"})
                   {labEdge { node
                   {id name comment secret }}}}
                """ % (
            td["name"],
            td["comment"],
            td["secret"],
        )

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

        self.assertRaises(Lab.DoesNotExist, Lab.objects.get, **{"name": td["name"]})

    def test_create_produces_result(self):
        td = {"name": "test_create_produces_result", "comment": "you can do it", "secret": "blu42achooo"}

        query = """mutation{ createLab(input: {
                    name: "%s"
                    comment: "%s"
                    secret: "%s"})
                   {labEdge { node
                   {id name comment secret }}}}
                """ % (
            td["name"],
            td["comment"],
            td["secret"],
        )

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)

        lookup = Lab.objects.get(name=td["name"])

        self.assertEqual(lookup.name, td["name"])
        self.assertEqual(lookup.comment, td["comment"])
        self.assertEqual(lookup.secret, td["secret"])


class TestUpdateLab(GQLTestCase):
    node_name = "LabNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_update_requires_privilege(self):
        lab = LabFactory()
        lab_gql_id = lab.gql_id
        grant_role(self.viewer["role"], lab, self.viewer["user"])

        td = {"name": "test_update_requires_privilege", "comment": "leave it alone", "secret": "youToldDidntYOU"}

        query = """mutation{ updateLab(input: {
                    id: "%s"
                    name: "%s"
                    comment: "%s"
                    secret: "%s" }){lab
                   {id name comment secret}}}
                """ % (
            lab_gql_id,
            td["name"],
            td["comment"],
            td["secret"],
        )

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        lab = LabFactory()
        lab_id = lab.pk
        lab_gql_id = lab.gql_id
        grant_role(self.owner["role"], lab, self.owner["user"])

        td = {"name": "test_update_requires_privilege", "comment": "leave it alone", "secret": "youToldDidntYOU"}

        query = """mutation{ updateLab(input: {
                    id: "%s"
                    name: "%s"
                    comment: "%s"
                    secret: "%s" }){lab
                   {id name comment secret}}}
                """ % (
            lab_gql_id,
            td["name"],
            td["comment"],
            td["secret"],
        )

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)

        lookup = Lab.objects.get(pk=lab_id)

        self.assertEqual(lookup.name, td["name"])
        self.assertEqual(lookup.comment, td["comment"])
        self.assertEqual(lookup.secret, td["secret"])


class TestDeleteLab(GQLTestCase):
    node_name = "LabNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_delete_requires_privilege(self):
        lab = LabFactory()
        lab_id = lab.pk
        lab_gql_id = lab.gql_id

        grant_role(self.viewer["role"], lab, self.viewer["user"])

        query = """mutation{ deleteLab(input: {
                    id: "%s" }){ id }}""" % (
            lab_gql_id,
        )

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

        Lab.objects.get(pk=lab_id)

    def test_delete_produces_result(self):
        lab = LabFactory()
        lab_id = lab.pk
        lab_gql_id = lab.gql_id

        grant_role(self.owner["role"], lab, self.owner["user"])

        query = """mutation{ deleteLab(input: {
                    id: "%s" }){ id }}""" % (
            lab_gql_id,
        )

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)

        self.assertIsNotNone(result["data"]["deleteLab"]["id"])

        self.assertRaises(Lab.DoesNotExist, Lab.objects.get, **{"pk": lab_id})


class TestSetLabStint(GQLTestCase):
    node_name = "LabNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        hand = create_test_hands(n=1, signal_pubsub=False).first()
        cls.lab = LabFactory()
        cls.lab_gql_id = cls.lab.gql_id
        cls.stint_specification = hand.stint.stint_specification
        cls.stint_specification_gql_id = cls.stint_specification.gql_id
        cls.td = {"stintSpecificationId": cls.stint_specification_gql_id, "labid": cls.lab_gql_id}

        cls.query = """mutation SetLabStint($stintSpecificationId: ID!, $labid: ID!){
                    setLabStint(input: {
                        id: $labid,
                        stintSpecificationId: $stintSpecificationId
                    }){ success }}
                """

    def test_set_requires_privilege(self):
        grant_role(self.viewer["role"], self.lab, self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        # Still fails to pass, due to lack of stint_specification privileges
        grant_role(self.owner["role"], self.lab, self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_set_works(self):
        grant_role(self.owner['role'], self.lab, self.owner["user"])
        grant_role(self.owner["role"], self.stint_specification.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.assertTrue(result["data"]["setLabStint"]["success"])


class TestStartLabStint(GQLTestCase):
    node_name = "LabNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        hand = create_test_hands(n=1, signal_pubsub=False).first()
        cls.lab = LabFactory()
        cls.lab_gql_id = cls.lab.gql_id
        stint_specification = hand.stint.stint_specification
        cls.lab.set_stint(stint_specification.id, UserFactory())
        cls.td = {"labid": cls.lab_gql_id, "handN": 1}

        cls.query = """mutation StartLabStint($labid: ID!, $handN: Int!){
                    startLabStint(input: {
                        id: $labid,
                        handN: $handN,
                        signalPubsub: false
                    }){ success }}
                """

    def test_start_requires_privilege(self):
        grant_role(self.viewer["role"], self.lab, self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_start_works(self):
        self.assertEqual(self.lab.current_stint.status, None)
        grant_role(self.owner["role"], self.lab, self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.assertTrue(result["data"]["startLabStint"]["success"])
        self.lab.current_stint.refresh_from_db()
        self.assertEqual(self.lab.current_stint.status, Stint.STATUS_CHOICES.running)


class TestStopLabStint(GQLTestCase):
    node_name = "LabNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        hand = create_test_hands(n=1, signal_pubsub=False).first()
        cls.lab = LabFactory()
        cls.lab_gql_id = cls.lab.gql_id
        stint_specification = hand.stint.stint_specification
        cls.lab.set_stint(stint_specification.id, UserFactory())
        cls.lab.start(1, UserFactory(), signal_pubsub=False)
        cls.td = {"labid": cls.lab_gql_id, "handN": 1}

        cls.query = """mutation StopLabStint($labid: ID!){
                    stopLabStint(input: {
                        id: $labid
                    }){ success }}
                """

    def test_stop_requires_privilege(self):
        grant_role(self.viewer["role"], self.lab, self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    @mock.patch('ery_backend.hands.models.Hand.pay')
    def test_stop_works(self, mock_pay):
        grant_role(self.owner["role"], self.lab, self.owner["user"])

        self.assertEqual(self.lab.current_stint.status, Stint.STATUS_CHOICES.running)
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.assertTrue(result["data"]["stopLabStint"]["success"])
        self.lab.current_stint.refresh_from_db()
        self.assertEqual(self.lab.current_stint.status, Stint.STATUS_CHOICES.cancelled)


class TestChangeLabStint(GQLTestCase):
    node_name = "LabNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        hand = create_test_hands(n=1, signal_pubsub=False).first()
        cls.lab = LabFactory()
        cls.lab_gql_id = cls.lab.gql_id
        stint_specification = hand.stint.stint_specification
        stint_specification_2 = create_test_hands(n=1, signal_pubsub=False).first().stint.stint_specification
        cls.lab.set_stint(stint_specification_2.id, UserFactory())
        cls.change_stint = cls.lab.current_stint
        cls.lab.set_stint(stint_specification.id, UserFactory())
        cls.start_stint = cls.lab.current_stint
        cls.lab.start(1, UserFactory(), signal_pubsub=False)

        cls.td = {"labid": cls.lab_gql_id, "stintid": cls.change_stint.gql_id}

        cls.query = """mutation ChangeLabStint($labid: ID!, $stintid: ID!){
                    changeLabStint(input: {
                        id: $labid
                        stintId: $stintid
                    }){ success }}
                """

    def test_change_requires_privilege(self):
        grant_role(self.viewer["role"], self.lab, self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    @mock.patch('ery_backend.hands.models.Hand.pay')
    def test_change_works(self, mock_pay):
        grant_role(self.owner["role"], self.lab, self.owner["user"])

        self.assertEqual(self.lab.current_stint, self.start_stint)
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.assertTrue(result["data"]["changeLabStint"]["success"])
        self.lab.refresh_from_db()
        # Confirm changed stint
        self.assertEqual(self.lab.current_stint, self.change_stint)
        self.start_stint.refresh_from_db()
        # Previous stint should be cancelled
        self.assertEqual(self.start_stint.status, Stint.STATUS_CHOICES.cancelled)
