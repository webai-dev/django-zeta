import unittest

import graphene
from languages_plus.models import Language
from reversion.models import Version, Revision

from ery_backend.actions.schema import ActionQuery
from ery_backend.base.testcases import EryTestCase, GQLTestCase, create_revisions
from ery_backend.modules.factories import ModuleDefinitionWidgetFactory
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.mutations import TemplateMutation, ThemeMutation
from ery_backend.roles.utils import grant_role, revoke_role
from ery_backend.stages.factories import StageTemplateFactory, StageDefinitionFactory
from ery_backend.themes.factories import ThemeFactory
from ery_backend.users.schema import ViewerQuery
from ery_backend.widgets.factories import WidgetFactory
from ery_backend.widgets.models import Widget

# Must come after stage imports do avoid undefined Node type in gql
from ery_backend.mutations import ImageAssetMutation, ModuleDefinitionMutation, StintSpecificationMutation

from ..locale_schema import LanguageQuery
from ..schema import VersionQuery, VersionMutation, RevisionQuery, RevisionMutation, EryMutationMixin
from ..utils import get_gql_id


class TestPrivilegedNodeMixin(EryTestCase):
    def test_get_node(self):
        """
        Verified in test_graphene.py of every app (containing model with Read query) using
        "test_read_requires_login" test.
        """


class TestQuery(ActionQuery, VersionQuery, RevisionQuery, ViewerQuery, LanguageQuery, graphene.ObjectType):
    pass


class TestMutation(
    VersionMutation,
    RevisionMutation,
    ModuleDefinitionMutation,
    TemplateMutation,
    StintSpecificationMutation,
    ThemeMutation,
    ImageAssetMutation,
    graphene.ObjectType,
):
    pass


class TestEryMutationMixin(EryTestCase):
    def test_gql_id_to_pk(self):
        module_definition = ModuleDefinitionFactory()
        module_definition_gql_id_1 = module_definition.gql_id
        module_definition_gql_id_2 = module_definition.gql_id
        module_definition_gql_id_3 = module_definition.gql_id
        self.assertEqual(EryMutationMixin.gql_id_to_pk(module_definition_gql_id_1), module_definition.id)
        self.assertEqual(EryMutationMixin.gql_id_to_pk(module_definition_gql_id_2), module_definition.id)
        self.assertEqual(EryMutationMixin.gql_id_to_pk(module_definition_gql_id_3), module_definition.id)

    def test_add_all_atributes(self):
        """
        Verified in test_graphene.py of every app (containing model with Update mutation)
        in TestUpdate<Class>
        """


class TestRevertVersion(GQLTestCase):
    node_name = 'VersionNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.module_definition_widget = ModuleDefinitionWidgetFactory(name='ModuleWidgetZero')
        grant_role(self.editor['role'], self.module_definition_widget.module_definition, self.editor['user'])
        grant_role(self.viewer['role'], self.module_definition_widget.module_definition, self.viewer['user'])

    def test_revert_requires_privilege(self):
        """
        Confirm reverting requires "update" privilege.
        """
        create_revisions([{'obj': self.module_definition_widget, 'attr': 'comment'}], revision_n=1, user=self.editor['user'])
        django_pk = Version.objects.get_for_object(self.module_definition_widget).first().pk
        td = {"gqlId": get_gql_id('Version', django_pk)}

        query = '''mutation RevertVersion($gqlId: ID!){revertVersion(input: {id: $gqlId}){success}}'''
        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_revert_errors(self):
        """
        Confirm expected error handling when referenced foreign key doesn't exist.
        """
        original_widget = self.module_definition_widget.widget
        original_widget_id = original_widget.id
        # save a reference to original widget
        create_revisions([{'obj': self.module_definition_widget, 'attr': 'comment'}], revision_n=1, user=self.editor['user'])
        self.module_definition_widget.widget = WidgetFactory()
        original_widget.delete()
        original_widget = None
        django_pk = Version.objects.get_for_object(self.module_definition_widget).order_by('revision__date_created').first().pk

        td = {"gqlId": get_gql_id('Version', django_pk)}
        query = '''mutation RevertVersion($gqlId: ID!){revertVersion(input: {id: $gqlId}){success}}'''

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.editor["user"])
        )
        expected_error = (
            f"Version for object, {self.module_definition_widget}, references a nonexistent related model:"
            f" {Widget} with pk {original_widget_id}, and cannot be re-created."
        )
        self.assertEqual(result['errors'][0]['message'], expected_error)


class TestRevertRevision(GQLTestCase):
    node_name = 'RevisionNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.module_definition_widget = ModuleDefinitionWidgetFactory(name='ModuleWidgetZero')
        grant_role(self.editor['role'], self.module_definition_widget.module_definition, self.editor['user'])
        grant_role(self.viewer['role'], self.module_definition_widget.module_definition, self.viewer['user'])

    def test_single_revert_requires_privilege(self):
        """
        Confirm reverting requires "update" privilege.
        """
        create_revisions([{'obj': self.module_definition_widget, 'attr': 'comment'}], revision_n=1, user=self.editor['user'])
        django_pk = Revision.objects.filter(user=self.editor['user']).first().pk

        td = {"gqlId": get_gql_id('Revision', django_pk)}
        query = '''mutation RevertRevision($gqlId: ID!){revertRevision(input: {id: $gqlId}){success}}'''

        # user loses privilege on an object and therefore should not be able to revert said object
        revoke_role(self.editor['role'], self.module_definition_widget.module_definition, self.editor['user'])

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.editor['user'])
        )
        self.assert_query_was_unauthorized(result)

        # works when user regains privilege
        grant_role(self.editor['role'], self.module_definition_widget.module_definition, self.editor['user'])
        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.editor['user'])
        )
        self.assertTrue(result['data']['revertRevision']['success'])

    def test_multi_revert_requires_privilege(self):
        """
        User loses privilege on one of many objects in the revision, and can therefore not run revision.revert, even though
        user maintains privilege on other objects in revision.
        """
        module_definition_widget_2 = ModuleDefinitionWidgetFactory(
            name='ModuleDefinitionWidgetOne', module_definition=self.module_definition_widget.module_definition
        )
        grant_role(self.editor['role'], module_definition_widget_2.module_definition, self.editor['user'])
        create_revisions(
            [
                {'obj': self.module_definition_widget, 'attr': 'comment'},
                {'obj': module_definition_widget_2, 'attr': 'comment'},
            ],
            revision_n=1,
            squash=True,
            user=self.editor['user'],
        )
        django_pk = Revision.objects.filter(user=self.editor['user']).first().pk

        td = {"gqlId": get_gql_id('Revision', django_pk)}
        query = '''mutation RevertRevision($gqlId: ID!){revertRevision(input: {id: $gqlId}){success}}'''
        revoke_role(self.editor['role'], self.module_definition_widget.module_definition, self.editor['user'])

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.editor["user"])
        )
        self.assert_query_was_unauthorized(result)

        # works when user regains privilege
        grant_role(self.editor['role'], self.module_definition_widget.module_definition, self.editor['user'])
        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.editor["user"])
        )
        self.assertTrue(result['data']['revertRevision']['success'])

    def test_revert_errors(self):
        """
        Confirm expected error handling when referenced foreign key doesn't exist.
        """
        module_definition_widget_2 = ModuleDefinitionWidgetFactory(
            name='ModuleDefinitionWidgetOne', module_definition=self.module_definition_widget.module_definition
        )
        original_widget = self.module_definition_widget.widget
        original_widget_id = original_widget.id
        # save a reference to original widget
        create_revisions(
            [
                {'obj': self.module_definition_widget, 'attr': 'comment'},
                {'obj': module_definition_widget_2, 'attr': 'comment'},
            ],
            revision_n=1,
            squash=True,
            user=self.editor['user'],
        )
        original_comment = module_definition_widget_2.comment
        module_definition_widget_2.comment = None
        module_definition_widget_2.save()
        self.module_definition_widget.widget = WidgetFactory()
        original_widget.delete()
        original_widget = None
        django_pk = Revision.objects.filter(user=self.editor['user']).first().pk

        td = {"gqlId": get_gql_id('Revision', django_pk)}
        query = '''mutation RevertRevision($gqlId: ID!){revertRevision(input: {id: $gqlId}){success}}'''

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.editor["user"])
        )

        # since one version fails revert, should return error
        expected_error = (
            f"Version for object, {self.module_definition_widget}, references a nonexistent related"
            f" model: {Widget} with pk {original_widget_id}, and cannot be re-created."
        )
        self.assertEqual(result['errors'][0]['message'], expected_error)
        # experiencing one error should mean none of the versions successfully revert
        module_definition_widget_2.refresh_from_db()
        self.assertNotEqual(module_definition_widget_2.comment, original_comment)


class TestSoftDelete(GQLTestCase):
    """
    Confirm soft delete (state change to deleted) is done in place of default django delete
    during delete mutations of EryFile subclasses.
    """

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def assert_soft_delete_works(self, instance):
        model_cls = instance.__class__
        model_name = model_cls.__name__
        instance_gql_id = instance.gql_id
        self.assertNotEqual(instance.state, model_cls.STATE_CHOICES.deleted)
        grant_role(self.owner['role'], instance, self.owner['user'])
        query = f"""mutation Delete{model_name}($gqlId: ID!){{ delete{model_name}(input: {{
                    id: $gqlId }}){{ id }}}}"""
        result = self.gql_client.execute(
            query,
            variable_values={'gqlId': instance_gql_id},
            context_value=self.gql_client.get_context(user=self.owner["user"]),
        )
        self.assertIsNotNone(result['data'][f'delete{model_name}']['id'])
        self.assertTrue(model_cls.objects.filter(id=instance.id).exists())
        instance.refresh_from_db()
        self.assertEqual(instance.state, model_cls.STATE_CHOICES.deleted)

    @unittest.skip('Requires widget delete mutation')
    def test_widget(self):
        pass

    @unittest.skip('Requires stintdefinition delete mutation')
    def test_stintdefinition(self):
        pass

    @unittest.skip('Requires validator delete mutation')
    def test_validator(self):
        pass

    @unittest.skip('Requires stint_specification delete mutation')
    def test_stintspecification(self):
        pass

    @unittest.skip('Requires procedure delete mutation')
    def test_procedure(self):
        pass

    def test_theme(self):
        theme = ThemeFactory()
        self.assert_soft_delete_works(theme)


class TestReadLanguage(GQLTestCase):
    """Ensure reading Language works"""

    node_name = "LanguageNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.all_query = """{allLanguages{ edges{ node{ id }}}}"""
        cls.node_query = """query LanguageQuery($languageid: ID!){
            language(id: $languageid){ nameEn }}"""

    def setUp(self):
        self.language = Language.objects.get(pk='en')
        self.td = {"languageid": get_gql_id('Language', self.language.pk)}

    def test_read_node_works(self):
        result = self.gql_client.execute(
            self.node_query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.fail_on_errors(result)
        self.assertEqual(result["data"]["language"]["nameEn"], self.language.name_en)


class TestFilterSiblingPrivilege(GQLTestCase):
    """
    Confirm privilege is filtered on all{Model} queries.
    """

    node_name = "ModuleDefinitionNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)

    def setUp(self):
        self.stage_definition = StageDefinitionFactory()
        self.st = StageTemplateFactory(stage_definition=self.stage_definition)
        self.other_st = StageTemplateFactory()
        grant_role(self.owner['role'], self.st.get_privilege_ancestor(), self.owner['user'])
        self.td = {'stageDefinition': self.stage_definition.gql_id, 'stageTemplates': self.st.gql_id}

    def test_privilege_filtering(self):
        initial_query = """query FilterQuery{ viewer{ allStageTemplates{ edges{ node{ id }} }}}"""
        result = self.gql_client.execute(
            initial_query, context_value=self.gql_client.get_context(user=self.owner["user"]), variable_values=self.td
        )
        data = result['data']['viewer']['allStageTemplates']['edges']
        self.assertEqual(data[0]['node']['id'], self.st.gql_id)
        self.assertEqual(len(data[0]['node']), 1)

    def test_limit(self):
        for _ in range(3):
            st = StageTemplateFactory(stage_definition=self.stage_definition)
            grant_role(self.owner['role'], st.get_privilege_ancestor(), self.owner['user'])
        initial_query = """query FilterQuery{ viewer{ allStageTemplates{ edges{ node{ id }} }}}"""
        initial_result = self.gql_client.execute(
            initial_query, context_value=self.gql_client.get_context(user=self.owner["user"]), variable_values=self.td
        )
        initial_data = initial_result['data']['viewer']['allStageTemplates']['edges']
        self.assertEqual(len(initial_data), 4)
        limit_query = """query FilterQuery{ viewer{ allStageTemplates(last: 2){ edges{ node{ id }} }}}"""
        limit_result = self.gql_client.execute(
            limit_query, context_value=self.gql_client.get_context(user=self.owner["user"]), variable_values=self.td
        )
        limit_data = limit_result['data']['viewer']['allStageTemplates']['edges']
        self.assertEqual(len(limit_data), 2)

        initial_node_query = """
query NodeQuery($stageDefinition: ID!) {
    viewer {
        stageDefinition(id: $stageDefinition) {
            stageTemplates {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    }
}"""
        context_value = self.gql_client.get_context(user=self.owner["user"])
        initial_node_result = self.gql_client.execute(initial_node_query, context_value=context_value, variable_values=self.td)
        initial_node_data = initial_node_result['data']['viewer']['stageDefinition']['stageTemplates']['edges']
        self.assertEqual(len(initial_node_data), 4)

        limit_node_query = """
query NodeQuery($stageDefinition: ID!) {
    viewer {
        stageDefinition(id: $stageDefinition) {
            stageTemplates(last: 2) {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    }
}"""
        context_value = self.gql_client.get_context(user=self.owner["user"])
        limit_node_result = self.gql_client.execute(limit_node_query, context_value=context_value, variable_values=self.td)
        limit_node_data = limit_node_result['data']['viewer']['stageDefinition']['stageTemplates']['edges']
        self.assertEqual(len(limit_node_data), 2)

    def test_offset(self):
        st = StageTemplateFactory(stage_definition=self.stage_definition)
        grant_role(self.owner['role'], st.get_privilege_ancestor(), self.owner['user'])
        initial_query = """query FilterQuery{ viewer{ allStageTemplates{ edges{ node{ id }} }}}"""
        initial_result = self.gql_client.execute(
            initial_query, context_value=self.gql_client.get_context(user=self.owner["user"]), variable_values=self.td
        )
        initial_data = initial_result['data']['viewer']['allStageTemplates']['edges']
        self.assertEqual(len(initial_data), 2)
        offset_query = """query FilterQuery{ viewer{ allStageTemplates(first: 1){ edges{ node{ id }} }}}"""
        offset_result = self.gql_client.execute(
            offset_query, context_value=self.gql_client.get_context(user=self.owner["user"]), variable_values=self.td
        )
        offset_data = offset_result['data']['viewer']['allStageTemplates']['edges']
        self.assertEqual(len(offset_data), 1)

        initial_node_query = """
query NodeQuery($stageDefinition: ID!) {
    viewer {
        stageDefinition(id: $stageDefinition) {
            stageTemplates {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    }
}"""
        context_value = self.gql_client.get_context(user=self.owner["user"])
        initial_node_result = self.gql_client.execute(initial_node_query, context_value=context_value, variable_values=self.td)
        initial_node_data = initial_node_result['data']['viewer']['stageDefinition']['stageTemplates']['edges']
        self.assertEqual(len(initial_node_data), 2)

        offset_node_query = """
query NodeQuery($stageDefinition: ID!) {
    viewer {
        stageDefinition(id: $stageDefinition) {
            stageTemplates(first: 1) {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    }
}"""
        context_value = self.gql_client.get_context(user=self.owner["user"])
        offset_node_result = self.gql_client.execute(offset_node_query, context_value=context_value, variable_values=self.td)
        offset_node_data = offset_node_result['data']['viewer']['stageDefinition']['stageTemplates']['edges']
        self.assertEqual(len(offset_node_data), 1)

    def test_ids(self):
        sts = [StageTemplateFactory(stage_definition=self.stage_definition) for _ in range(3)]
        for st in sts:
            grant_role(self.owner['role'], st.get_privilege_ancestor(), self.owner['user'])
        self.td['ids'] = [st.gql_id for st in sts]
        filtered_query = """query FilterQuery($ids: [ID!]){ viewer{ allStageTemplates(ids: $ids){ edges{ node{ id }} }}}"""
        filtered_result = self.gql_client.execute(
            filtered_query, context_value=self.gql_client.get_context(user=self.owner["user"]), variable_values=self.td
        )
        filtered_data = filtered_result['data']['viewer']['allStageTemplates']['edges']
        self.assertEqual(len(filtered_data), 3)

        node_query = """
query NodeQuery($stageDefinition: ID!, $ids: [ID!]) {
    viewer {
        stageDefinition(id: $stageDefinition) {
            stageTemplates(ids: $ids) {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    }
}"""
        context_value = self.gql_client.get_context(user=self.owner["user"])
        node_result = self.gql_client.execute(node_query, context_value=context_value, variable_values=self.td)
        node_data = node_result['data']['viewer']['stageDefinition']['stageTemplates']['edges']
        self.assertEqual(len(node_data), 3)
