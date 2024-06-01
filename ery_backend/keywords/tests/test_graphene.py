from unittest import mock
import unittest

import graphene
from graphql_relay.node.node import from_global_id

from ery_backend.assets.factories import ImageAssetFactory
from ery_backend.base.testcases import GQLTestCase
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.mutations import KeywordMutation
from ery_backend.procedures.factories import ProcedureFactory
from ery_backend.roles.utils import grant_role
from ery_backend.stints.factories import StintDefinitionFactory
from ery_backend.templates.factories import TemplateFactory
from ery_backend.themes.factories import ThemeFactory
from ery_backend.validators.factories import ValidatorFactory
from ery_backend.users.schema import ViewerQuery
from ery_backend.widgets.factories import WidgetFactory

from ..factories import KeywordFactory
from ..models import Keyword
from ..schema import KeywordQuery


class TestQuery(KeywordQuery, ViewerQuery, graphene.ObjectType):
    pass


class TestMutation(KeywordMutation, graphene.ObjectType):
    pass


class TestReadKeyword(GQLTestCase):
    """Ensure reading Keyword works"""

    node_name = "KeywordNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.all_query = """{allKeywords{ edges{ node{ name }}}}"""
        cls.node_query = """query KeywordQuery($keywordid: ID!){
            keyword(id: $keywordid){ id  }}"""

    def setUp(self):
        self.keyword = KeywordFactory()
        self.td = {"keywordid": self.keyword.gql_id}

    def test_read_all_works(self):
        keywords = [KeywordFactory() for _ in range(3)]

        # No roles
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        data = [node_data['node']['name'] for node_data in result['data']['allKeywords']['edges']]
        self.fail_on_errors(result)
        for keyword in keywords:
            self.assertIn(keyword.name, data)

    def test_read_node_works(self):
        result = self.gql_client.execute(
            self.node_query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.fail_on_errors(result)
        self.assertEqual(int(from_global_id(result["data"]["keyword"]["id"])[1]), self.keyword.id)


class TestCreateKeyword(GQLTestCase):
    node_name = "KeywordNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):

        self.td = {'name': 'test', 'comment': 'That Isssssss, what it Isssssss'}

        self.query = """
mutation ($name: String!, $comment: String) {
    createKeyword(input: {
        name: $name
        comment: $comment
    }) {
        keywordEdge {
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

        lookup = Keyword.objects.get(name=self.td["name"])
        self.assertEqual(lookup.comment, self.td["comment"])


class TestUpdateKeyword(GQLTestCase):
    node_name = "KeywordNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.keyword = KeywordFactory()
        self.td = {"keyword": self.keyword.gql_id, "name": "TestKeyword", "comment": "A new one"}
        self.query = """
mutation ($keyword: ID!, $name: String!, $comment: String) {
    updateKeyword(input: {
        id: $keyword
        name: $name
        comment: $comment
    }) {
        keyword { id }
    }
}"""

    def test_update_produces_result(self):
        grant_role(self.owner["role"], self.keyword.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        lookup = Keyword.objects.get(pk=self.keyword.id)

        self.assertEqual(lookup.name, self.td["name"])
        self.assertEqual(lookup.comment, self.td["comment"])


class TestDeleteKeyword(GQLTestCase):
    node_name = "KeywordNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.keyword = KeywordFactory()
        self.td = {"keyword": self.keyword.gql_id}
        self.query = """mutation ($keyword: ID!){
             deleteKeyword(input: {
                id: $keyword,
                    })
                   { id }
                   }
                """

    def test_delete_requires_privilege(self):
        grant_role(self.viewer["role"], self.keyword.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        Keyword.objects.get(pk=self.keyword.id)

    def test_delete_produces_result(self):
        grant_role(self.owner["role"], self.keyword.get_privilege_ancestor(), self.owner["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertTrue(result["data"]["deleteKeyword"]["id"])

        self.assertRaises(Keyword.DoesNotExist, Keyword.objects.get, **{"pk": self.keyword.id})


class TestKeywordSearch(GQLTestCase):
    """
    Confirm multiple EryFiles can be searched via keyword
    """

    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @classmethod
    @mock.patch('ery_backend.assets.models.ImageAsset.bucket')
    def setUpClass(cls, mock_bucket, *args, **kwargs):
        super().setUpClass(*args, **kwargs)

        cls.sd = StintDefinitionFactory(name='testsd')
        cls.md = ModuleDefinitionFactory()
        cls.template = TemplateFactory()
        cls.procedure = ProcedureFactory()
        cls.theme = ThemeFactory()
        cls.image_asset = ImageAssetFactory()
        cls.widget = WidgetFactory()
        cls.validator = ValidatorFactory(code=None)
        for obj in (cls.sd, cls.md, cls.template, cls.procedure, cls.theme, cls.image_asset, cls.widget, cls.validator):
            grant_role(cls.viewer['role'], obj, cls.viewer['user'])
        # cls.query = """query{ viewer{ library { stintDefinition{ keywords{ edges{ node{ id }}} } }}}"""
        cls.keyword_one = KeywordFactory(name='test')
        cls.keyword_two = KeywordFactory(name='testtwo')
        cls.keyword_three = KeywordFactory(name='testthree')

    def setUp(self):
        self.td = {
            'keywordone': self.keyword_one.gql_id,
            'keywordtwo': self.keyword_two.gql_id,
            'keywordthree': self.keyword_three.gql_id,
        }

    @unittest.skip("XXX: Address in issue #755")
    def test_keyword_search(self):
        query_1 = """query { viewer{ allStintDefinitions(keywords_Name: "test"){ edges{ node{ name }}}}}"""
        query_2 = """query { viewer{ allStintDefinitions(keywords_Name: "testtwo"){ edges{ node{ name }}}}}"""

        # query_1 should return the correct stint_definition, which was assigned said keyword
        self.sd.keywords.add(self.keyword_one)
        result = self.gql_client.execute(query_1, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(result['data']['viewer']['allStintDefinitions']['edges'][0]['node']['name'], self.sd.name)

        # query_2 should not return a stint_definition, as said keyword was not assigned.
        result = self.gql_client.execute(query_2, context_value=self.gql_client.get_context(user=self.viewer["user"]))

        self.assertEqual(len(result['data']['viewer']['allStintDefinitions']['edges']), 0)

        # Confirm search works for other classes
        test_query = """query { viewer{ allModuleDefinitions(keywords_Name: "testthree"){ edges{ node{ name }}}}}"""
        result = self.gql_client.execute(test_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(len(result['data']['viewer']['allModuleDefinitions']['edges']), 0)
        self.md.keywords.add(self.keyword_three)
        result = self.gql_client.execute(test_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(result['data']['viewer']['allModuleDefinitions']['edges'][0]['node']['name'], self.md.name)

        test_query = """query { viewer{ allTemplates(keywords_Name: "testtwo"){ edges{ node{ name }}}}}"""
        result = self.gql_client.execute(test_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(len(result['data']['viewer']['allTemplates']['edges']), 0)
        self.template.keywords.add(self.keyword_two)
        result = self.gql_client.execute(test_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(result['data']['viewer']['allTemplates']['edges'][0]['node']['name'], self.template.name)

        test_query = """query { viewer{ allWidgets(keywords_Name: "testtwo"){ edges{ node{ name }}}}}"""
        result = self.gql_client.execute(test_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(len(result['data']['viewer']['allWidgets']['edges']), 0)
        self.widget.keywords.add(self.keyword_two)
        result = self.gql_client.execute(test_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(result['data']['viewer']['allWidgets']['edges'][0]['node']['name'], self.widget.name)

        test_query = """query { viewer{ allProcedures(keywords_Name: "testtwo"){ edges{ node{ name }}}}}"""
        result = self.gql_client.execute(test_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(len(result['data']['viewer']['allProcedures']['edges']), 0)
        self.procedure.keywords.add(self.keyword_two)
        result = self.gql_client.execute(test_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(result['data']['viewer']['allProcedures']['edges'][0]['node']['name'], self.procedure.name)

        test_query = """query { viewer{ allThemes(keywords_Name: "testtwo"){ edges{ node{ name }}}}}"""
        result = self.gql_client.execute(test_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(len(result['data']['viewer']['allThemes']['edges']), 0)
        self.theme.keywords.add(self.keyword_two)
        result = self.gql_client.execute(test_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(result['data']['viewer']['allThemes']['edges'][0]['node']['name'], self.theme.name)

        test_query = """query { viewer{ allImageAssets(keywords_Name: "testtwo"){ edges{ node{ name }}}}}"""
        result = self.gql_client.execute(test_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(len(result['data']['viewer']['allImageAssets']['edges']), 0)
        self.image_asset.keywords.add(self.keyword_two)
        result = self.gql_client.execute(test_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(result['data']['viewer']['allImageAssets']['edges'][0]['node']['name'], self.image_asset.name)

        test_query = """query { viewer{ allValidators(keywords_Name: "testtwo"){ edges{ node{ name }}}}}"""
        result = self.gql_client.execute(test_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(len(result['data']['viewer']['allValidators']['edges']), 0)
        self.validator.keywords.add(self.keyword_two)
        result = self.gql_client.execute(test_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(result['data']['viewer']['allValidators']['edges'][0]['node']['name'], self.validator.name)
