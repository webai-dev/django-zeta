import graphene
from graphql_relay.node.node import from_global_id

from ery_backend.base.testcases import GQLTestCase
from ery_backend.mutations import ValidatorMutation
from ery_backend.roles.utils import grant_role

from ..factories import ValidatorFactory
from ..models import Validator
from ..schema import ValidatorQuery


class TestQuery(ValidatorQuery, graphene.ObjectType):
    pass


class TestMutation(ValidatorMutation, graphene.ObjectType):
    pass


class TestReadValidator(GQLTestCase):
    """Ensure reading Validator works"""

    node_name = "ValidatorNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.all_query = """{allValidators{ edges{ node{ id }}}}"""
        cls.node_query = """query ValidatorQuery($validatorid: ID!){
            validator(id: $validatorid){ id  }}"""

    def setUp(self):
        self.validator = ValidatorFactory(regex=None)
        self.td = {
            "validatorid": self.validator.gql_id,
        }

    def test_read_all_requires_login(self):
        """allValidators query without a user is unauthorized"""
        result = self.gql_client.execute(self.all_query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        result = self.gql_client.execute(self.node_query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        validators = [ValidatorFactory(regex=None) for _ in range(3)]

        for obj in validators:
            grant_role(self.viewer["role"], obj.get_privilege_ancestor(), self.viewer["user"])

        for obj in validators[1:]:
            grant_role(self.editor["role"], obj.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], validators[2].get_privilege_ancestor(), self.owner["user"])
        # No roles
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allValidators"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allValidators"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allValidators"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allValidators"]["edges"]), 1)

    def test_read_node_works(self):
        grant_role(self.viewer["role"], self.validator.get_privilege_ancestor(), self.viewer["user"])
        result = self.gql_client.execute(
            self.node_query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.fail_on_errors(result)
        self.assertEqual(int(from_global_id(result["data"]["validator"]["id"])[1]), self.validator.id)

    def test_no_soft_deletes_in_all_query(self):
        """
        Confirm soft_deleted objects are not returned in query.
        """
        query = """{allValidators { edges{ node{ id }}}}"""
        validator = ValidatorFactory(regex=None)
        grant_role(self.viewer["role"], validator, self.viewer["user"])

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(len(result["data"]["allValidators"]["edges"]), 1)

        validator.soft_delete()
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(len(result["data"]["allValidators"]["edges"]), 0)

    def test_no_soft_deletes_in_single_query(self):
        """
        Confirms soft_deleted object not returned in query.
        """
        query = """query ValidatorQuery($validatorid: ID!){
            validator(id: $validatorid){ id }}
            """
        validator = ValidatorFactory(regex=None)
        grant_role(self.viewer["role"], validator, self.viewer["user"])

        result = self.gql_client.execute(
            query,
            variable_values={"validatorid": validator.gql_id},
            context_value=self.gql_client.get_context(user=self.viewer["user"]),
        )
        self.fail_on_errors(result)

        validator.soft_delete()
        result = self.gql_client.execute(
            query,
            variable_values={"validatorid": validator.gql_id},
            context_value=self.gql_client.get_context(user=self.viewer["user"]),
        )
        self.assertEqual('Validator matching query does not exist.', result['errors'][0]['message'])


class TestCreateValidator(GQLTestCase):
    node_name = "ValidatorNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.td = {
            "name": "Test Validator",
            "comment": "Test Validator",
            "code": "beepboopbeep",
            "nullable": True,
            "regex": None,
        }

        self.query = """mutation ($name: String!, $comment: String, $code: String, $regex: String, $nullable: Boolean){
             createValidator(input: {
                name: $name
                comment: $comment
                code: $code
                nullable: $nullable
                regex: $regex
                    })
                   {validator
                   {id name comment code nullable regex}}}
                """

    def test_create_requires_privilege(self):
        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        self.assertRaises(Validator.DoesNotExist, Validator.objects.get, **{"name": self.td["name"]})

    def test_create_produces_result(self):
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        lookup = Validator.objects.get(name=self.td["name"])

        self.assertEqual(lookup.name, self.td["name"])
        self.assertEqual(lookup.comment, self.td["comment"])
        self.assertEqual(lookup.regex, self.td["regex"])
        self.assertEqual(lookup.code, self.td["code"])
        self.assertEqual(lookup.nullable, self.td["nullable"])


class TestUpdateValidator(GQLTestCase):
    node_name = "ValidatorNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.validator = ValidatorFactory(regex=None, nullable=False)
        self.td = {
            "validator": self.validator.gql_id,
            "name": "UpdateTestValidator",
            "comment": "Update test validator",
            "code": '0100011000',
            "nullable": True,
        }
        self.query = """mutation ($validator: ID!, $name: String!, $comment: String,
                                  $code: String, $nullable: Boolean){
             updateValidator(input: {
                id: $validator,
                name: $name
                comment: $comment
                code: $code
                nullable: $nullable
                    })
                   {validator
                   {id name comment regex code nullable}}}
                """

    def test_update_requires_privilege(self):
        grant_role(self.viewer["role"], self.validator.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        grant_role(self.owner["role"], self.validator.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        lookup = Validator.objects.get(pk=self.validator.id)

        self.assertEqual(lookup.name, self.td["name"])
        self.assertEqual(lookup.comment, self.td["comment"])
        self.assertEqual(lookup.code, self.td["code"])
        self.assertEqual(lookup.nullable, self.td["nullable"])


class TestDeleteValidator(GQLTestCase):
    node_name = "ValidatorNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.validator = ValidatorFactory(code=None)
        self.td = {"validator": self.validator.gql_id}
        self.query = """mutation ($validator: ID!){
             deleteValidator(input: {
                id: $validator,
                    })
                   { success }
                   }
                """

    def test_delete_requires_privilege(self):
        grant_role(self.viewer["role"], self.validator.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        Validator.objects.get(pk=self.validator.id)

    def test_delete_produces_result(self):
        grant_role(self.owner["role"], self.validator.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertTrue(result["data"]["deleteValidator"]["success"])

        self.validator.refresh_from_db()
        self.assertEqual(self.validator.state, self.validator.STATE_CHOICES.deleted)
