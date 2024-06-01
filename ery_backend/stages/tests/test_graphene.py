# pylint:disable=too-many-lines
import graphene
from graphql_relay.node.node import from_global_id

from ery_backend.base.testcases import GQLTestCase
from ery_backend.base.utils import get_gql_id
from ery_backend.frontends.models import Frontend
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.mutations import (
    StageDefinitionMutation,
    StageTemplateMutation,
    StageMutation,
    StageTemplateBlockTranslationMutation,
    StageTemplateBlockMutation,
)
from ery_backend.roles.utils import grant_role
from ery_backend.templates.factories import TemplateFactory
from ery_backend.themes.factories import ThemeFactory
from ery_backend.themes.schema import ThemeQuery
from ery_backend.templates.schema import TemplateQuery

from ..factories import (
    StageDefinitionFactory,
    StageTemplateFactory,
    StageFactory,
    StageTemplateBlockFactory,
    StageTemplateBlockTranslationFactory,
)
from ..models import StageDefinition, StageTemplate, Stage, StageTemplateBlockTranslation, StageTemplateBlock
from ..schema import (
    StageDefinitionQuery,
    StageTemplateQuery,
    StageQuery,
    StageTemplateBlockTranslationQuery,
    StageTemplateBlockQuery,
)


class TestQuery(
    StageDefinitionQuery,
    StageTemplateBlockTranslationQuery,
    StageTemplateBlockQuery,
    StageTemplateQuery,
    StageQuery,
    TemplateQuery,
    ThemeQuery,
    graphene.ObjectType,
):
    pass


class TestMutation(
    StageMutation,
    StageDefinitionMutation,
    StageTemplateMutation,
    StageTemplateBlockTranslationMutation,
    StageTemplateBlockMutation,
    graphene.ObjectType,
):
    pass


class TestReadStageDefinition(GQLTestCase):
    """Ensure reading stages works"""

    node_name = "StageDefinitionNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_read_all_requires_login(self):
        """allStageDefinitions query without a user is unauthorized"""
        query = """{allStageDefinitions{ edges { node { id name }}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        stage_definition = StageDefinitionFactory()
        td = {"sid": stage_definition.gql_id}

        query = """query StageDefinitionQuery($sid: ID!){stageDefinition(id: $sid){ id name }}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        query = """{allStageDefinitions{ edges { node { id name }}}}"""

        stage_definitions = [
            StageDefinitionFactory(module_definition=ModuleDefinitionFactory()),
            StageDefinitionFactory(module_definition=ModuleDefinitionFactory()),
            StageDefinitionFactory(module_definition=ModuleDefinitionFactory()),
        ]

        for s in stage_definitions:
            grant_role(self.viewer["role"], s.module_definition, self.viewer["user"])

        for s in stage_definitions[1:]:
            grant_role(self.editor["role"], s.module_definition, self.editor["user"])

        grant_role(self.owner["role"], stage_definitions[2].module_definition, self.owner["user"])

        # No roles
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStageDefinitions"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStageDefinitions"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStageDefinitions"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStageDefinitions"]["edges"]), 1)


class TestCreateStageDefinition(GQLTestCase):
    node_name = "StageDefinitionNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_create_requires_login(self):
        md = ModuleDefinitionFactory()
        grant_role(self.owner["role"], md, self.owner["user"])
        td = {"gqlId": md.gql_id}

        query = """mutation CreateStageDefinition($gqlId: ID!){ createStageDefinition(input: {
                    name: "Test Create Requires Login",
                    comment: "Don't create this.",
                    moduleDefinition: $gqlId})
                    { stageDefinitionEdge { node { id name comment }}}}
                """

        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_create_produces_stage_definition(self):
        md = ModuleDefinitionFactory()
        grant_role(self.owner["role"], md, self.owner["user"])

        test_data = {"gqlId": md.gql_id, "name": "TestCreateProducesStageDefinition", "comment": "This is a test."}

        query = """mutation CreateStageDefinition($gqlId: ID!, $name: String, $comment: String)
                    { createStageDefinition(input: {
                    name: $name,
                    comment: $comment,
                    moduleDefinition: $gqlId})
                    { stageDefinitionEdge { node { id name comment moduleDefinition { name id } }}}}
                """

        create_result = self.gql_client.execute(
            query, variable_values=test_data, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(create_result)

        self.assertEqual(
            create_result["data"]["createStageDefinition"]["stageDefinitionEdge"]["node"]["name"], test_data["name"]
        )

        self.assertEqual(
            create_result["data"]["createStageDefinition"]["stageDefinitionEdge"]["node"]["comment"], test_data["comment"]
        )

        self.assertEqual(
            create_result["data"]["createStageDefinition"]["stageDefinitionEdge"]["node"]["moduleDefinition"]["id"],
            test_data["gqlId"],
        )


class TestUpdateStageDefinition(GQLTestCase):
    node_name = "StageDefinitionNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_update_requires_privileges(self):
        md = ModuleDefinitionFactory()
        stage_definition = StageDefinitionFactory(module_definition=md)
        grant_role(self.viewer["role"], md, self.viewer["user"])
        test_data = {"gqlId": stage_definition.gql_id, "name": "Test Update Requires Privileges", "comment": "This is a test."}

        query = """mutation UpdateStageDefinition($gqlId: ID!, $name: String, $comment: String)
                    { updateStageDefinition(input: {
                    id: $gqlId,
                    name: $name,
                    comment: $comment,
                    })
                    { stageDefinition { id name comment }}}
                """
        result = self.gql_client.execute(query, variable_values=test_data)
        self.assert_query_was_unauthorized(result)

    def test_update_produces_correct_change(self):
        md = ModuleDefinitionFactory()
        stage_definition = StageDefinitionFactory(module_definition=md)
        grant_role(self.owner["role"], md, self.owner["user"])

        test_data = {
            "gqlId": stage_definition.gql_id,
            "name": "TestUpdateProducesCorrectChange",
            "comment": "Update produced correct change",
        }

        query = """mutation UpdateStageDefinition($gqlId: ID!, $name: String, $comment: String){ updateStageDefinition(input: {
                    id: $gqlId,
                    name: $name,
                    comment: $comment
                    })
                    { stageDefinition { id name comment }}}
                """

        result = self.gql_client.execute(
            query, variable_values=test_data, context_value=self.gql_client.get_context(user=self.owner["user"])
        )

        self.assertEqual(result["data"]["updateStageDefinition"]["stageDefinition"]["name"], test_data["name"])

        self.assertEqual(result["data"]["updateStageDefinition"]["stageDefinition"]["comment"], test_data["comment"])


class TestDelete(GQLTestCase):
    node_name = "StageDefinitionNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_delete_requires_privileges(self):
        md = ModuleDefinitionFactory()
        grant_role(self.viewer["role"], md, self.viewer["user"])
        stage_definition = StageDefinitionFactory(module_definition=md)

        td = {"gqlId": stage_definition.gql_id}

        query = """mutation DeleteStageDefinition($gqlId: ID!){ deleteStageDefinition(input: {
                    id: $gqlId }){ id }}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        lookup = StageDefinition.objects.get(pk=stage_definition.pk)
        self.assertIsNot(lookup, None)

    def test_delete_removes_stage_definition(self):
        md = ModuleDefinitionFactory()
        grant_role(self.owner["role"], md, self.owner["user"])
        stage_definition = StageDefinitionFactory(module_definition=md)

        stage_definition_id = stage_definition.pk
        td = {"gqlId": stage_definition.gql_id}

        query = """mutation DeleteStageDefinition($gqlId: ID!){ deleteStageDefinition(input: {
                    id: $gqlId }){ id }}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertRaises(StageDefinition.DoesNotExist, StageDefinition.objects.get, **{"pk": stage_definition_id})


class TestReadStageTemplate(GQLTestCase):
    node_name = "StageTemplateNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_read_requires_login(self):
        stage_template = StageTemplateFactory()
        md = stage_template.stage_definition.module_definition

        # all stage templates
        query = """{allStageTemplates{ edges{ node{
                    id
                    stageDefinition {id name}
                    template {id name}
                    theme {id name}}}}}"""

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

        grant_role(self.viewer["role"], md, self.viewer["user"])

        # single stage template
        td = {"gqlId": stage_template.gql_id}

        query = """query StageTemplate($gqlId: ID!){stageTemplate(id: $gqlId)
                    {stageDefinition {id name}
                     template {id name}
                     theme {id name}}}"""

        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_filters_by_privilege(self):
        stage_templates = [StageTemplateFactory(), StageTemplateFactory(), StageTemplateFactory()]

        for st in stage_templates:
            md = st.stage_definition.module_definition
            grant_role(self.viewer["role"], md, self.viewer["user"])
        for st in stage_templates[1:]:
            md = st.stage_definition.module_definition
            grant_role(self.editor["role"], md, self.editor["user"])
        grant_role(self.owner["role"], stage_templates[2].stage_definition.module_definition, self.owner["user"])

        query = """{allStageTemplates {edges {node {id}}}}"""

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStageTemplates"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStageTemplates"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStageTemplates"]["edges"]), 1)


class TestCreateStageTemplate(GQLTestCase):
    node_name = "StageTemplateNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_create_requires_login(self):
        stage_definition = StageDefinitionFactory()
        template = TemplateFactory()
        theme = ThemeFactory()

        td = {"stageDefinitionId": stage_definition.gql_id, "templateId": template.gql_id, "themeId": theme.gql_id}

        query = """mutation CreateStageTemplate($stageDefinitionId: ID!, $templateId: ID!, $themeId: ID!)
                    { createStageTemplate(input: {
                    stageDefinition: $stageDefinitionId,
                    template: $templateId,
                    theme: $themeId}){
                    stageTemplateEdge{ node {id }}}}
                """

        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_create_produces_result(self):
        stage_definition = StageDefinitionFactory()
        template = TemplateFactory()
        theme = ThemeFactory()

        td = {
            "stageDefinitionId": stage_definition.gql_id,
            "templateId": template.gql_id,
            "themeId": theme.gql_id,
        }

        grant_role(self.owner["role"], stage_definition.module_definition, self.owner["user"])

        query = """mutation CreateStageTemplate($stageDefinitionId: ID!, $templateId: ID!, $themeId: ID!)
                    { createStageTemplate(input: {
                    stageDefinition: $stageDefinitionId,
                    template: $templateId,
                    theme: $themeId}){
                    stageTemplateEdge { node { id }}}}
                """

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        td2 = {"gqlId": result["data"]["createStageTemplate"]["stageTemplateEdge"]["node"]["id"]}

        query = """query StageTemplate($gqlId: ID!){stageTemplate(id: $gqlId){
                    stageDefinition{ name }
                    template{ name }
                    theme{ name }}}
                """

        result = self.gql_client.execute(
            query, variable_values=td2, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertEqual(result["data"]["stageTemplate"]["stageDefinition"]["name"], stage_definition.name)

        self.assertEqual(result["data"]["stageTemplate"]["template"]["name"], template.name)

        self.assertEqual(result["data"]["stageTemplate"]["theme"]["name"], theme.name)


class TestDeleteStageTemplate(GQLTestCase):
    node_name = "StageTemplateNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_delete_requires_privileges(self):
        stage_template = StageTemplateFactory()
        st_id = stage_template.pk
        td = {"gqlId": stage_template.gql_id}

        grant_role(self.viewer["role"], stage_template.stage_definition.module_definition, self.viewer["user"])

        query = """mutation DeleteStageTemplate($gqlId: ID!){deleteStageTemplate(input: {id: $gqlId}){id}}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)
        StageTemplate.objects.get(pk=st_id)

    def test_delete_produces_result(self):
        stage_template = StageTemplateFactory()
        st_id = stage_template.pk
        td = {"gqlId": stage_template.gql_id}

        grant_role(self.owner["role"], stage_template.stage_definition.module_definition, self.owner["user"])

        query = """mutation DeleteStageTemplate($gqlId: ID!){deleteStageTemplate(input: {id: $gqlId}){id}}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertRaises(StageTemplate.DoesNotExist, StageTemplate.objects.get, **{"pk": st_id})


class TestReadStage(GQLTestCase):
    """Ensure reading Stage works"""

    node_name = "StageNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def test_read_all_requires_login(self):
        """allStages query without a user is unauthorized"""
        query = """{allStages{ edges{ node{ id }}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        stage = StageFactory()
        td = {"stageid": stage.gql_id}

        query = """query StageQuery($stageid: ID!){stage(id: $stageid){ id }}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        query = """{allStages{ edges{ node{ id }}}}"""
        stages = [StageFactory() for _ in range(3)]

        for obj in stages:
            grant_role(self.viewer["role"], obj.stage_definition.module_definition, self.viewer["user"])

        for obj in stages[1:]:
            grant_role(self.editor["role"], obj.stage_definition.module_definition, self.editor["user"])

        grant_role(self.owner["role"], stages[2].stage_definition.module_definition, self.owner["user"])
        # No roles
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStages"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStages"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStages"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStages"]["edges"]), 1)


class TestCreateStage(GQLTestCase):
    node_name = "StageNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.stage_definition = StageDefinitionFactory()
        cls.stagedef_gql_id = cls.stage_definition.gql_id
        cls.td = {"stageDefinitionId": cls.stagedef_gql_id}
        cls.query = """
mutation CreateStage($stageDefinitionId: ID!) {
    createStage(input: {
        stageDefinition: $stageDefinitionId,
        preactionStarted: true
    }) {
        stageEdge {
            node {
                stageDefinition {
                    name
                }
                preactionStarted
            }
        }
    }
}"""

    def test_create_requires_login(self):
        grant_role(self.viewer["role"], self.stage_definition.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        self.assertRaises(Stage.DoesNotExist, Stage.objects.get, **{"stage_definition": self.stage_definition})

    def test_create_produces_result(self):
        grant_role(self.owner["role"], self.stage_definition.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        lookup = Stage.objects.get(stage_definition=self.stage_definition)

        self.assertEqual(lookup.stage_definition, self.stage_definition)
        self.assertTrue(lookup.preaction_started)


class TestUpdateStage(GQLTestCase):
    node_name = "StageNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.query = """mutation UpdateStage($stageId: ID!){
                        updateStage(input: {
                            id: $stageId,
                            preactionStarted: true
                        })
                        {
                            stage{
                                stageDefinition{
                                    name
                                }
                                preactionStarted
                        }
                    }}"""

    def setUp(self):
        self.stage = StageFactory()
        self.stage_gql_id = self.stage.gql_id
        self.td = {"stageId": self.stage_gql_id}

    def test_update_requires_privilege(self):
        grant_role(self.viewer["role"], self.stage.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        lookup = Stage.objects.get(pk=self.stage.id)

        self.assertFalse(lookup.preaction_started)

        grant_role(self.owner["role"], self.stage.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        lookup.refresh_from_db()
        self.assertTrue(lookup.preaction_started)


class TestDeleteStage(GQLTestCase):
    node_name = "StageNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.query = """mutation DeleteStage($stageId: ID!){ deleteStage(input: {
                    id: $stageId }){ id }}"""

    def setUp(self):
        self.stage = StageFactory()
        self.stage_id = self.stage.pk
        stage_gql_id = self.stage.gql_id
        self.td = {'stageId': stage_gql_id}

    def test_delete_requires_privilege(self):

        grant_role(self.viewer["role"], self.stage.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        Stage.objects.get(pk=self.stage_id)

    def test_delete_produces_result(self):
        grant_role(self.owner["role"], self.stage.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertIsNotNone(result["data"]["deleteStage"]["id"])

        self.assertRaises(Stage.DoesNotExist, Stage.objects.get, **{"pk": self.stage_id})


class TestReadStageTemplateBlock(GQLTestCase):
    """Ensure reading StageTemplateBlock works"""

    node_name = "StageTemplateBlockNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.all_query = """{allStageTemplateBlocks{ edges{ node{ id stageTemplate{ id } name comment }}}}"""
        cls.node_query = """query StageTemplateBlockQuery($stagetemplateblockid: ID!){
            stageTemplateBlock(id: $stagetemplateblockid){ id stageTemplate{ id } name comment }}"""

    def setUp(self):
        self.stage_template_block = StageTemplateBlockFactory()
        self.td = {
            "stagetemplateblockid": self.stage_template_block.gql_id,
        }

    def test_read_all_requires_login(self):
        """allStageTemplateBlocks query without a user is unauthorized"""
        result = self.gql_client.execute(self.all_query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        result = self.gql_client.execute(self.node_query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        stage_template_blocks = [StageTemplateBlockFactory() for _ in range(3)]

        # No roles
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStageTemplateBlocks"]["edges"]), 0)

        # Viewer
        for obj in stage_template_blocks:
            grant_role(self.viewer["role"], obj.get_privilege_ancestor(), self.viewer["user"])
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStageTemplateBlocks"]["edges"]), 3)

        # Editor
        for obj in stage_template_blocks[1:]:
            grant_role(self.editor["role"], obj.get_privilege_ancestor(), self.editor["user"])
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStageTemplateBlocks"]["edges"]), 2)

        # Owner
        grant_role(self.owner["role"], stage_template_blocks[2].get_privilege_ancestor(), self.owner["user"])
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStageTemplateBlocks"]["edges"]), 1)

    def test_read_node_works(self):
        grant_role(self.viewer["role"], self.stage_template_block.get_privilege_ancestor(), self.viewer["user"])
        result = self.gql_client.execute(
            self.node_query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.fail_on_errors(result)
        self.assertEqual(int(from_global_id(result["data"]["stageTemplateBlock"]["id"])[1]), self.stage_template_block.id)


class TestCreateStageTemplateBlock(GQLTestCase):
    node_name = "StageTemplateBlockNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.stage_template = StageTemplateFactory()
        self.td = {"name": "TestStageTemplateBlock", "comment": "testing it", "stageTemplateId": self.stage_template.gql_id}

        self.query = """
mutation ($name: String!, $comment: String, $stageTemplateId: ID!) {
    createStageTemplateBlock(input: {
        name: $name,
        comment: $comment,
        stageTemplate: $stageTemplateId
    }) {
        stageTemplateBlockEdge {
            node {
                id
            }
        }
    }
}"""

    def test_create_requires_privilege(self):
        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        self.assertRaises(StageTemplateBlock.DoesNotExist, StageTemplateBlock.objects.get, **{"name": self.td["name"]})

    def test_create_produces_result(self):
        grant_role(self.owner["role"], self.stage_template.get_privilege_ancestor(), self.owner["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        lookup = StageTemplateBlock.objects.get(name=self.td["name"])

        self.assertEqual(lookup.name, self.td["name"])
        self.assertEqual(lookup.stage_template, self.stage_template)


class TestUpdateStageTemplateBlock(GQLTestCase):
    node_name = "StageTemplateBlockNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.stage_template_block = StageTemplateBlockFactory()
        self.td = {
            "stageTemplateBlock": self.stage_template_block.gql_id,
            "name": "TestStageTemplateBlock",
            "comment": "Testing update",
        }
        self.query = """mutation ($stageTemplateBlock: ID!, $name: String!, $comment: String!){
             updateStageTemplateBlock(input: {
                id: $stageTemplateBlock,
                name: $name
                comment: $comment
                    })
                   {stageTemplateBlock
                   { id }}}
                """

    def test_update_requires_privilege(self):
        grant_role(self.viewer["role"], self.stage_template_block.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        grant_role(self.owner["role"], self.stage_template_block.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        lookup = StageTemplateBlock.objects.get(pk=self.stage_template_block.id)

        self.assertEqual(lookup.name, self.td["name"])


class TestDeleteStageTemplateBlock(GQLTestCase):
    node_name = "StageTemplateBlockNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.stage_template_block = StageTemplateBlockFactory()
        self.td = {"stageTemplateBlock": self.stage_template_block.gql_id}
        self.query = """mutation ($stageTemplateBlock: ID!){
             deleteStageTemplateBlock(input: {
                id: $stageTemplateBlock,
                    })
                   { id }
                   }
                """

    def test_delete_requires_privilege(self):
        grant_role(self.viewer["role"], self.stage_template_block.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        StageTemplateBlock.objects.get(pk=self.stage_template_block.id)

    def test_delete_produces_result(self):
        grant_role(self.owner["role"], self.stage_template_block.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertIsNotNone(result["data"]["deleteStageTemplateBlock"]["id"])

        self.assertRaises(
            StageTemplateBlock.DoesNotExist, StageTemplateBlock.objects.get, **{"pk": self.stage_template_block.id}
        )


class TestReadStageTemplateBlockTranslation(GQLTestCase):
    """Ensure reading StageTemplateBlockTranslation works"""

    node_name = "StageTemplateBlockTranslationNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        # XXX: Add fields
        cls.all_query = """{allStageTemplateBlockTranslations{ edges{ node{
             id frontend{ name }  language{ nameEn } stageTemplateBlock{ name }}}}}"""
        cls.node_query = """query StageTemplateBlockTranslationQuery($stagetemplateblocktranslationid: ID!){
            stageTemplateBlockTranslation(id: $stagetemplateblocktranslationid){
                 id frontend{ name } language{ nameEn } stageTemplateBlock{ name }}}"""

    def setUp(self):
        self.stage_template_block_translation = StageTemplateBlockTranslationFactory()
        self.td = {
            "stagetemplateblocktranslationid": self.stage_template_block_translation.gql_id,
        }

    def test_read_all_requires_login(self):
        """allStageTemplateBlockTranslations query without a user is unauthorized"""
        result = self.gql_client.execute(self.all_query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        result = self.gql_client.execute(self.node_query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        stage_template_block_translations = [StageTemplateBlockTranslationFactory() for _ in range(3)]

        for obj in stage_template_block_translations:
            grant_role(self.viewer["role"], obj.get_privilege_ancestor(), self.viewer["user"])

        for obj in stage_template_block_translations[1:]:
            grant_role(self.editor["role"], obj.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], stage_template_block_translations[2].get_privilege_ancestor(), self.owner["user"])
        # No roles
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStageTemplateBlockTranslations"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStageTemplateBlockTranslations"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStageTemplateBlockTranslations"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStageTemplateBlockTranslations"]["edges"]), 1)

    def test_read_node_works(self):
        grant_role(self.viewer["role"], self.stage_template_block_translation.get_privilege_ancestor(), self.viewer["user"])
        result = self.gql_client.execute(
            self.node_query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.fail_on_errors(result)
        self.assertEqual(
            int(from_global_id(result["data"]["stageTemplateBlockTranslation"]["id"])[1]),
            self.stage_template_block_translation.id,
        )


class TestCreateStageTemplateBlockTranslation(GQLTestCase):
    node_name = "StageTemplateBlockTranslationNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.stage_template_block = StageTemplateBlockFactory()
        self.td = {
            'languageId': get_gql_id('Language', 'en'),
            'content': "Some content",
            'frontendId': Frontend.objects.get(name='Web').gql_id,
            'stageTemplateBlockId': self.stage_template_block.gql_id,
        }

        self.query = """
mutation ($languageId: ID!, $content: String!, $frontendId: ID!, $stageTemplateBlockId: ID!) {
    createStageTemplateBlockTranslation(input: {
        language: $languageId
        content: $content
        frontend: $frontendId
        stageTemplateBlock: $stageTemplateBlockId
    }) {
        stageTemplateBlockTranslationEdge {
            node {
                id 
            }
        }
    }
}"""

    def test_create_requires_privilege(self):
        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        self.assertRaises(
            StageTemplateBlockTranslation.DoesNotExist,
            StageTemplateBlockTranslation.objects.get,
            **{"content": self.td["content"]},
        )

    def test_create_produces_result(self):
        grant_role(self.owner["role"], self.stage_template_block.get_privilege_ancestor(), self.owner["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        lookup = StageTemplateBlockTranslation.objects.get(content=self.td["content"])

        self.assertEqual(lookup.content, self.td["content"])
        self.assertEqual(lookup.language.pk, 'en')
        self.assertEqual(lookup.frontend.name, 'Web')


class TestUpdateStageTemplateBlockTranslation(GQLTestCase):
    node_name = "StageTemplateBlockTranslationNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.stage_template_block_translation = StageTemplateBlockTranslationFactory()
        self.td = {
            'languageId': get_gql_id('Language', 'aa'),
            "stageTemplateBlockTranslation": self.stage_template_block_translation.gql_id,
            'content': "Some content",
            'frontendId': Frontend.objects.get(name='Web').gql_id,
        }
        self.query = """mutation ($stageTemplateBlockTranslation: ID!, $content: String!, $frontendId: ID!, $languageId: ID!){
             updateStageTemplateBlockTranslation(input: {
                id: $stageTemplateBlockTranslation
                content: $content
                frontend: $frontendId
                language: $languageId
                    })
                   {stageTemplateBlockTranslation
                   { id }}}
                """

    def test_update_requires_privilege(self):
        grant_role(self.viewer["role"], self.stage_template_block_translation.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        grant_role(self.owner["role"], self.stage_template_block_translation.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        lookup = StageTemplateBlockTranslation.objects.get(pk=self.stage_template_block_translation.id)

        self.assertEqual(lookup.content, self.td["content"])
        self.assertEqual(lookup.language.pk, 'aa')
        self.assertEqual(lookup.frontend.name, 'Web')


class TestDeleteStageTemplateBlockTranslation(GQLTestCase):
    node_name = "StageTemplateBlockTranslationNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.stage_template_block_translation = StageTemplateBlockTranslationFactory()
        self.td = {"stageTemplateBlockTranslation": self.stage_template_block_translation.gql_id}
        self.query = """mutation ($stageTemplateBlockTranslation: ID!){
             deleteStageTemplateBlockTranslation(input: {
                id: $stageTemplateBlockTranslation,
                    })
                   { id }
                   }
                """

    def test_delete_requires_privilege(self):
        grant_role(self.viewer["role"], self.stage_template_block_translation.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        StageTemplateBlockTranslation.objects.get(pk=self.stage_template_block_translation.id)

    def test_delete_produces_result(self):
        grant_role(self.owner["role"], self.stage_template_block_translation.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertIsNotNone(result["data"]["deleteStageTemplateBlockTranslation"]["id"])

        self.assertRaises(
            StageTemplateBlockTranslation.DoesNotExist,
            StageTemplateBlockTranslation.objects.get,
            **{"pk": self.stage_template_block_translation.id},
        )


class TestBlockInfo(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_block_info(self):
        from languages_plus.models import Language
        from ery_backend.base.testcases import create_test_hands
        from ery_backend.stint_specifications.models import StintSpecificationAllowedLanguageFrontend
        from ery_backend.templates.factories import TemplateBlockFactory, TemplateBlockTranslationFactory

        preferred_language = Language.objects.get(pk='ab')
        default_language = Language.objects.get(pk='en')
        hand = create_test_hands(n=1, signal_pubsub=False, frontend_type='Web').first()
        hand.stint.stint_specification.allowed_language_frontend_combinations.add(
            StintSpecificationAllowedLanguageFrontend.objects.get_or_create(
                language=preferred_language, frontend=hand.frontend, stint_specification=hand.stint.stint_specification
            )[0]
        )
        hand.language = preferred_language
        hand.stint.stint_specification.save()
        frontend = Frontend.objects.get(name='Web')
        template = TemplateFactory(frontend=frontend, primary_language=default_language)
        child_template = TemplateFactory(frontend=frontend, parental_template=template)
        stage_template = StageTemplateFactory(template=child_template)
        grant_role(self.owner['role'], stage_template.get_privilege_ancestor(), self.owner['user'])

        template_block = TemplateBlockFactory(template=template)
        TemplateBlockTranslationFactory(template_block=template_block, language=preferred_language)
        child_template_block_1 = TemplateBlockFactory(template=child_template, name='ChildIchi')
        TemplateBlockTranslationFactory(template_block=child_template_block_1, language=preferred_language)
        TemplateBlockTranslationFactory(template_block=child_template_block_1, language=default_language)
        child_template_block_2 = TemplateBlockFactory(template=child_template, name='ChildNi')
        TemplateBlockTranslationFactory(template_block=child_template_block_2, language=preferred_language)
        template_block_2 = TemplateBlockFactory(template=child_template, name='ChildSan')
        TemplateBlockTranslationFactory(template_block=template_block_2, language=preferred_language)
        child_stage_block_3 = StageTemplateBlockFactory(stage_template=stage_template, name='ChildSan')
        StageTemplateBlockTranslationFactory(
            stage_template_block=child_stage_block_3, frontend=frontend, language=preferred_language
        )
        child_template_block_4 = TemplateBlockFactory(template=child_template, name='ChildShi')
        TemplateBlockTranslationFactory(template_block=child_template_block_4, language=preferred_language)
        # template translation with preferred or default language and unique name should be included
        child_stage_block_4 = StageTemplateBlockFactory(stage_template=stage_template, name='ChildShi')
        StageTemplateBlockTranslationFactory(
            stage_template_block=child_stage_block_4, frontend=frontend, language=preferred_language
        )

        blocks = stage_template.get_blocks(hand.frontend, hand.language)
        formatted_block_info = [
            {
                'content': data['content'],
                'blockType': data['block_type'],
                'ancestorTemplateId': str(data['ancestor_id']) if data['block_type'] == 'TemplateBlock' else None,
                'name': name,
            }
            for name, data in blocks.items()
        ]
        td = {'stagetemplateid': stage_template.gql_id, 'languageid': get_gql_id('LanguageNode', 'ab')}
        query = """
query AllBlockInfo($stagetemplateid: ID!, $languageid: ID!){
    stageTemplate(id: $stagetemplateid){
        allBlockInfo(language: $languageid){
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
        result_block_info = result['data']['stageTemplate']['allBlockInfo']
        for block_info in formatted_block_info:
            self.assertIn(block_info, result_block_info)
