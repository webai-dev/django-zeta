#! /usr/bin/env python
# -*- coding: utf-8 -*-
import graphene
from languages_plus.models import Language

from ery_backend.base.testcases import GQLTestCase, create_test_hands
from ery_backend.mutations import TemplateMutation
from ery_backend.roles.utils import grant_role, has_privilege
from ery_backend.stint_specifications.models import StintSpecificationAllowedLanguageFrontend
from ery_backend.templates.models import Template
from ery_backend.templates.factories import TemplateFactory, TemplateBlockFactory, TemplateBlockTranslationFactory
from ery_backend.themes.schema import ThemeQuery

from ..schema import TemplateQuery


class TestQuery(TemplateQuery, ThemeQuery, graphene.ObjectType):
    pass


class TestMutation(TemplateMutation, graphene.ObjectType):
    pass


class TestReadTemplate(GQLTestCase):
    node_name = "TemplateNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_read_all_requires_login(self):
        query = """{allTemplates {edges { node { id name comment }}}}"""

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        template = TemplateFactory()
        grant_role(self.viewer["role"], template, self.viewer["user"])
        td = {"gqlId": template.gql_id}

        query = """query Template($gqlId: ID!){template(id: $gqlId){id name comment }}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_privileges(self):
        query = """{allTemplates {edges { node { id name comment }}}}"""
        templates = [TemplateFactory(), TemplateFactory(), TemplateFactory()]

        for t in templates:
            grant_role(self.viewer["role"], t, self.viewer["user"])

        for t in templates[1:]:
            grant_role(self.editor["role"], t, self.editor["user"])

        grant_role(self.owner["role"], templates[2], self.owner["user"])

        # No Roles
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertNotIn(templates[0].gql_id, [data["node"]["id"] for data in result["data"]["allTemplates"]["edges"]])

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        for template in templates:
            self.assertIn(template.gql_id, [data["node"]["id"] for data in result["data"]["allTemplates"]["edges"]])

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertNotIn(templates[0].gql_id, [data["node"]["id"] for data in result["data"]["allTemplates"]["edges"]])
        for template in templates[1:]:
            self.assertIn(template.gql_id, [data["node"]["id"] for data in result["data"]["allTemplates"]["edges"]])

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertNotIn(templates[1].gql_id, [data["node"]["id"] for data in result["data"]["allTemplates"]["edges"]])
        self.assertIn(templates[2].gql_id, [data["node"]["id"] for data in result["data"]["allTemplates"]["edges"]])

    def test_no_soft_deletes_in_all_query(self):
        """
        Confirm soft_deleted objects are not returned in query
        """
        query = """{allTemplates { edges{ node{ id name comment }}}}"""
        template = TemplateFactory()
        grant_role(self.viewer["role"], template, self.viewer["user"])

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertIn(template.gql_id, [data["node"]["id"] for data in result["data"]["allTemplates"]["edges"]])

        template.soft_delete()
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertNotIn(template.gql_id, [data["node"]["id"] for data in result["data"]["allTemplates"]["edges"]])

    def test_no_soft_deletes_in_single_query(self):
        """
        Confirms soft_deleted object not returned in query.
        """
        query = """query TemplateQuery($templateid: ID!){
            template(id: $templateid){ id }}
            """
        template = TemplateFactory()
        grant_role(self.viewer["role"], template, self.viewer["user"])

        result = self.gql_client.execute(
            query,
            variable_values={"templateid": template.gql_id},
            context_value=self.gql_client.get_context(user=self.viewer["user"]),
        )
        self.fail_on_errors(result)

        template.soft_delete()
        result = self.gql_client.execute(
            query,
            variable_values={"templateid": template.gql_id},
            context_value=self.gql_client.get_context(user=self.viewer["user"]),
        )
        self.assertEqual('Template matching query does not exist.', result['errors'][0]['message'])


class TestCreateTemplate(GQLTestCase):
    node_name = "TemplateNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_create_requires_login(self):
        query = """
mutation {
    createTemplate(input: {
        name: "Test Create Requires Login",
        comment: "Don't create this"
    }) {
        templateEdge {
            node {
                id
                name
                comment
            }
        }
    }
}"""

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)
        self.assertRaises(Template.DoesNotExist, Template.objects.get, **{"name": "Test Create Requires Login"})

    def test_create_adds_template(self):
        td = {"name": "Create adds template", "comment": "This is a test"}

        query = """
mutation CreateTemplate($name: String, $comment: String) {
    createTemplate(input: {
        name: $name,
        comment: $comment
    }) {
        templateEdge {
            node {
                id
                name
                comment
            }
        }
    }
}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        for field in td:
            self.assertEqual(result["data"]["createTemplate"]["templateEdge"]["node"][field], td[field])

        lookup = Template.objects.get(name=td["name"])

        self.assertTrue(has_privilege(lookup, self.owner["user"], "read"))
        self.assertTrue(has_privilege(lookup, self.owner["user"], "update"))
        self.assertTrue(has_privilege(lookup, self.owner["user"], "delete"))

        for field in td:
            self.assertEqual(getattr(lookup, field), td[field], msg=f"{field} values mismatch")


class TestUpdateTemplate(GQLTestCase):
    node_name = "TemplateNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_update_requires_privilege(self):
        template = TemplateFactory()
        tid = template.pk

        grant_role(self.viewer["role"], template, self.viewer["user"])

        td = {"name": "Test Update Requires Privilege", "comment": "Don't use this comment", "gqlId": template.gql_id}

        query = """mutation UpdateTemplate($gqlId: ID!, $name: String, $comment: String)
                    { updateTemplate(input: {
                    id: $gqlId,
                    name: $name,
                    comment: $comment,
                }){ template { id name comment }}}
                """

        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        lookup = Template.objects.get(pk=tid)

        self.assertNotEqual(lookup.name, td["name"])
        self.assertNotEqual(lookup.comment, td["comment"])

    def test_update_produces_correct_change(self):
        template = TemplateFactory()
        tid = template.pk

        grant_role(self.owner["role"], template, self.owner["user"])

        td = {"name": "Test Update Produces Correct Change", "comment": "You haz the update", "gqlId": template.gql_id}

        query = """mutation UpdateTemplate($gqlId: ID!, $name: String, $comment: String)
                    { updateTemplate(input: {
                    id: $gqlId,
                    name: $name,
                    comment: $comment,
                }){ template { id name comment }}}
                """

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        td.pop("gqlId")

        for field in td:
            self.assertEqual(result["data"]["updateTemplate"]["template"][field], td[field], msg=f"mismatch on {field}")

        lookup = Template.objects.get(pk=tid)

        self.assertEqual(lookup.name, td["name"])
        self.assertEqual(lookup.comment, td["comment"])


class TestDeleteTemplate(GQLTestCase):
    node_name = "TemplateNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_delete_requires_privilege(self):
        template = TemplateFactory()
        tid = template.pk
        td = {"gqlId": template.gql_id}

        grant_role(self.viewer["role"], template, self.viewer["user"])

        query = """mutation DeleteTemplate($gqlId: ID!){ deleteTemplate(input: {
                    id: $gqlId}){id}}"""

        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        Template.objects.get(pk=tid)

    def test_delete_removes_template(self):
        template = TemplateFactory()
        td = {"gqlId": template.gql_id}

        grant_role(self.owner["role"], template, self.owner["user"])

        query = """mutation DeleteTemplate($gqlId: ID!){ deleteTemplate(input: {
                    id: $gqlId}){id}}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )

        self.fail_on_errors(result)

        template.refresh_from_db()
        self.assertEqual(template.state, template.STATE_CHOICES.deleted)


class TestBlockInfo(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_block_info(self):
        hand = create_test_hands(frontend_type='Web').first()
        preferred_language = Language.objects.get(pk='en')
        hand.stint.stint_specification.allowed_language_frontend_combinations.add(
            StintSpecificationAllowedLanguageFrontend.objects.get_or_create(
                frontend=hand.frontend, language=preferred_language, stint_specification=hand.stint.stint_specification
            )[0]
        )

        ancestral_template = TemplateFactory()
        parental_template = TemplateFactory(parental_template=ancestral_template)
        # template_block content should be of preferred language
        template = TemplateFactory(
            parental_template=parental_template, frontend=hand.frontend, primary_language=preferred_language
        )
        grant_role(self.owner['role'], template, self.owner['user'])
        template_block_1 = TemplateBlockFactory(template=template)
        TemplateBlockTranslationFactory(template_block=template_block_1, language=preferred_language)
        template_block_2 = TemplateBlockFactory(template=template)
        TemplateBlockTranslationFactory(template_block=template_block_2, language=preferred_language)
        template_block_3 = TemplateBlockFactory(template=template)
        TemplateBlockTranslationFactory(template_block=template_block_3, language=preferred_language)
        expected_results = {}
        for template_block in [template_block_1, template_block_2, template_block_3]:
            expected_results[template_block.name] = template_block.get_translation(language=preferred_language).content

        blocks = template.get_blocks(preferred_language)
        formatted_block_info = [
            {
                'content': data['content'],
                'blockType': data['block_type'],
                'ancestorTemplateId': str(data['ancestor_id']),
                'name': name,
            }
            for name, data in blocks.items()
        ]
        td = {'templateid': template.gql_id}
        query = """
query AllBlockInfo($templateid: ID!){
    template(id: $templateid){
        allBlockInfo{
            name
            content
            blockType
            ancestorTemplateId
        }
    }
}"""
        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )

        result_block_info = result['data']['template']['allBlockInfo']
        for block_info in formatted_block_info:
            self.assertIn(block_info, result_block_info)
