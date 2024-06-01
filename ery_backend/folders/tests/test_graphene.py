from unittest import mock

import datetime as dt
import pytz
import graphene
from graphene.utils.str_converters import to_camel_case

from ery_backend.assets.factories import ImageAssetFactory
from ery_backend.base.mixins import StateMixin
from ery_backend.base.testcases import GQLTestCase
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.mutations import FolderMutation, LinkMutation
from ery_backend.procedures.factories import ProcedureFactory
from ery_backend.roles.utils import grant_role, revoke_role
from ery_backend.stints.factories import StintDefinitionFactory
from ery_backend.templates.factories import TemplateFactory
from ery_backend.themes.factories import ThemeFactory
from ery_backend.validators.factories import ValidatorFactory
from ery_backend.users.schema import ViewerQuery
from ery_backend.widgets.factories import WidgetFactory
from ery_backend.widgets.schema import WidgetQuery

from ..factories import FolderFactory, LinkFactory
from ..models import Folder, Link
from ..schema import FolderQuery, LinkQuery


class TestQuery(FolderQuery, LinkQuery, WidgetQuery, ViewerQuery, graphene.ObjectType):
    pass


class TestMutation(FolderMutation, LinkMutation, graphene.ObjectType):
    pass


class TestReadFolder(GQLTestCase):
    """Ensure reading Folder works"""

    node_name = "FolderNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        # Read tests are not concerned with permissions assigned by default
        # Read tests are not concerned with permissions assigned by default
        revoke_role(cls.owner['role'], cls.no_roles['user'].my_folder, cls.no_roles['user'])
        revoke_role(cls.owner['role'], cls.viewer['user'].my_folder, cls.viewer['user'])
        revoke_role(cls.owner['role'], cls.editor['user'].my_folder, cls.editor['user'])
        revoke_role(cls.owner['role'], cls.owner['user'].my_folder, cls.owner['user'])

    def test_read_all_requires_login(self):
        """allFolders query without a user is unauthorized"""
        query = """{allFolders{ edges{ node{ id }}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        folder = FolderFactory()
        td = {"folderid": folder.gql_id}

        query = """query FolderQuery($folderid: ID!){folder(id: $folderid){ id }}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_node_works(self):
        folder = FolderFactory()
        td = {"folderid": folder.gql_id}

        query = """query FolderQuery($folderid: ID!){folder(id: $folderid){ id }}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        query = """
{
    allFolders {
        edges {
            node {
                id
            }
        }
    }
}
"""
        folders = [FolderFactory() for _ in range(3)]

        for folder in folders:
            grant_role(self.viewer["role"], folder, self.viewer["user"])
        for folder in folders[1:]:
            grant_role(self.editor["role"], folder, self.editor["user"])
        grant_role(self.owner["role"], folders[2], self.owner["user"])

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFolders"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFolders"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFolders"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFolders"]["edges"]), 1)


class TestQueryFiles(GQLTestCase):
    node_name = "FolderNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @mock.patch('ery_backend.assets.models.ImageAsset.bucket')
    def setUp(self, mock_bucket):
        self.folder = FolderFactory()
        self.sd = StintDefinitionFactory()
        self.md = ModuleDefinitionFactory()
        self.procedure = ProcedureFactory()
        self.template = TemplateFactory()
        self.theme = ThemeFactory()
        self.widget = WidgetFactory()
        self.image_asset = ImageAssetFactory()
        self.validator = ValidatorFactory(code=None)
        grant_role(self.owner['role'], self.folder, self.owner['user'])
        grant_role(self.owner['role'], self.sd, self.owner['user'])
        grant_role(self.owner['role'], self.md, self.owner['user'])
        grant_role(self.owner['role'], self.template, self.owner['user'])
        grant_role(self.owner['role'], self.theme, self.owner['user'])
        grant_role(self.owner['role'], self.procedure, self.owner['user'])
        grant_role(self.owner['role'], self.widget, self.owner['user'])
        grant_role(self.owner['role'], self.image_asset, self.owner['user'])
        grant_role(self.owner['role'], self.validator, self.owner['user'])
        self.td = {
            "stint_definition": self.sd.gql_id,
            "module_definition": self.md.gql_id,
            "template": self.template.gql_id,
            "theme": self.theme.gql_id,
            "procedure": self.procedure.gql_id,
            "widget": self.widget.gql_id,
            "image_asset": self.image_asset.gql_id,
            "validator": self.validator.gql_id,
            "folderid": self.folder.gql_id,
        }

        self.query = """query FolderQuery($folderid: ID!){folder(id: $folderid){
             id files{ stintDefinition {id} moduleDefinition {id } template { id }
                       theme { id } procedure { id } widget { id } imageAsset { id }
                       validator { id }
              }}}"""

    def test_query_files(self):
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        data = result['data']['folder']['files']
        for generated_instance in [
            self.sd,
            self.md,
            self.procedure,
            self.template,
            self.theme,
            self.widget,
            self.image_asset,
            self.validator,
        ]:
            camel_name = to_camel_case(generated_instance.__class__.__name__)
            formatted_name = camel_name[0].lower() + camel_name[1:]
            for datum in data:
                if datum[formatted_name]:
                    match = datum[formatted_name]['id'] == generated_instance.gql_id
                    if match:
                        break
            self.assertTrue(match, f"No match found for {generated_instance}")


class TestCreateFolder(GQLTestCase):
    node_name = "FolderNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.td = {"name": 'test folder', "parentFolder": FolderFactory().gql_id}

        self.query = """
mutation CreateFolder($name: String, $parentFolder: ID!) {
    createFolder(input: {
        name: $name,
        parentFolder: $parentFolder
    }) {
        folderEdge {
            node {
                id
            }
        }
    }
}
"""

    def test_create_requires_login(self):
        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        self.assertRaises(Folder.DoesNotExist, Folder.objects.get, **{"name": self.td["name"]})

    def test_create_produces_result(self):
        """Confirm folder with parent created correctly."""
        parent_folder = FolderFactory()
        self.td['parentFolder'] = parent_folder.gql_id
        query = """
mutation CreateFolder($name: String, $parentFolder: ID!) {
    createFolder(input: {
        name: $name,
        parentFolder: $parentFolder
    }) {
        folderEdge {
            node {
                id
            }
        }
    }
}
"""
        result = self.gql_client.execute(
            query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        lookup = Folder.objects.get(name=self.td["name"])
        self.assertEqual(lookup.name, self.td["name"])

        self.assertTrue(Link.objects.filter(parent_folder=parent_folder, folder=lookup).exists())


class TestUpdateFolder(GQLTestCase):
    node_name = "FolderNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.folder = FolderFactory()
        self.folder_gql_id = self.folder.gql_id
        self.td = {"gqlId": self.folder_gql_id, "name": 'test folder', "comment": 'a test for updating'}
        self.query = """mutation UpdateFolder($gqlId: ID!, $name: String, $comment: String){updateFolder(input: {
                            id: $gqlId,
                            name: $name,
                            comment: $comment
                            })
                        {folder{  id name comment}}}
                """

    def test_update_requires_privilege(self):
        grant_role(self.viewer["role"], self.folder, self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        grant_role(self.owner["role"], self.folder, self.owner["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        lookup = Folder.objects.get(pk=self.folder.id)

        self.assertEqual(lookup.name, self.td["name"])
        self.assertEqual(lookup.comment, self.td["comment"])


class TestDeleteFolder(GQLTestCase):
    node_name = "FolderNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.folder = FolderFactory()
        self.folder_gql_id = self.folder.gql_id
        self.td = {'gqlId': self.folder_gql_id}
        self.query = """mutation DeleteFolder($gqlId: ID!){ deleteFolder(input: {
                            id: $gqlId}){ id }}"""

    def test_delete_requires_privilege(self):
        grant_role(self.viewer["role"], self.folder, self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        Folder.objects.get(pk=self.folder.id)

    def test_delete_produces_result(self):
        grant_role(self.owner["role"], self.folder, self.owner["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertTrue(result["data"]["deleteFolder"]["id"])

        self.assertRaises(Folder.DoesNotExist, Folder.objects.get, **{"pk": self.folder.id})


class TestReadLink(GQLTestCase):
    """Ensure reading Link works"""

    node_name = "LinkNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.parent_folder = FolderFactory()
        cls.stint_definition = StintDefinitionFactory()

    def test_read_all_requires_login(self):
        """allLinks query without a user is unauthorized"""
        query = """{allLinks{ edges{ node{ id }}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        link = LinkFactory(
            parent_folder=self.parent_folder, stint_definition=self.stint_definition, reference_type='stint_definition'
        )
        td = {"linkid": link.gql_id}

        query = """query LinkQuery($linkid: ID!){link(id: $linkid){ id }}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        query = """{allLinks{ edges{ node{ id }}}}"""
        links = [LinkFactory(stint_definition=self.stint_definition) for _ in range(3)]

        for obj in links:
            grant_role(self.viewer["role"], obj.get_privilege_ancestor(), self.viewer["user"])

        for obj in links[1:]:
            grant_role(self.editor["role"], obj.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], links[2].get_privilege_ancestor(), self.owner["user"])
        # No roles
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allLinks"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allLinks"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allLinks"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allLinks"]["edges"]), 1)

    @mock.patch('ery_backend.assets.models.ImageAsset.bucket')
    def test_read_node_works_on_related_models(self, mock_bucket):
        base_query = """query LinkQuery($linkid: ID!){link(id: $linkid)"""
        stint_link = LinkFactory(
            parent_folder=self.parent_folder, stint_definition=self.stint_definition, reference_type='stint_definition'
        )
        grant_role(self.owner["role"], stint_link.get_privilege_ancestor(), self.owner["user"])
        stint_link_gql_id = stint_link.gql_id
        result = self.gql_client.execute(
            base_query + '{stintDefinition { id }}} ',
            variable_values={"linkid": stint_link_gql_id},
            context_value=self.gql_client.get_context(user=self.owner["user"]),
        )
        self.assertIsNotNone(result['data']['link']['stintDefinition']['id'])
        module_link = LinkFactory(
            parent_folder=self.parent_folder, module_definition=ModuleDefinitionFactory(), reference_type='module_definition'
        )
        grant_role(self.owner["role"], module_link.get_privilege_ancestor(), self.owner["user"])
        module_link_gql_id = module_link.gql_id
        result = self.gql_client.execute(
            base_query + '{moduleDefinition { id }}} ',
            variable_values={"linkid": module_link_gql_id},
            context_value=self.gql_client.get_context(user=self.owner["user"]),
        )
        self.assertIsNotNone(result['data']['link']['moduleDefinition']['id'])
        # XXX: Address in #282
        # procedure_link = LinkFactory(folder=self.folder, procedure=ProcedureFactory())
        # grant_role(self.owner["role"], procedure_link, self.owner["user"])
        # procedure_link_gql_id = self.gql_id(procedure_link.pk)
        # result = self.gql_client.execute(
        # base_query + '{procedure { id }}} ',
        #                                  variable_values={"linkid": procedure_link_gql_id},
        #                                  context_value=self.gql_client.get_context(user=self.owner["user"]))
        # self.assertIsNotNone(result['data']['link']['procedure']['id'])
        profile_image_link = LinkFactory(
            parent_folder=self.parent_folder, image_asset=ImageAssetFactory(), reference_type='image_asset'
        )
        grant_role(self.owner["role"], profile_image_link.get_privilege_ancestor(), self.owner["user"])
        profile_image_link_gql_id = profile_image_link.gql_id
        result = self.gql_client.execute(
            base_query + '{imageAsset { id }}} ',
            variable_values={"linkid": profile_image_link_gql_id},
            context_value=self.gql_client.get_context(user=self.owner["user"]),
        )
        self.assertIsNotNone(result['data']['link']['imageAsset']['id'])
        # XXX: Address in #282
        # cover_image_link = LinkFactory(parent_folder=self.parent_folder, cover_image=CoverImageFactory())
        # grant_role(self.owner["role"], cover_image_link, self.owner["user"])
        # cover_image_link_gql_id = self.gql_id(cover_image_link.pk)
        # result = self.gql_client.execute(
        # base_query + '{coverImage { id }}} ',
        #                                  variable_values={"linkid": cover_image_link_gql_id},
        #                                  context_value=self.gql_client.get_context(user=self.owner["user"]))
        # self.assertIsNotNone(result['data']['link']['coverImage']['id'])
        widget_link = LinkFactory(parent_folder=self.parent_folder, widget=WidgetFactory(), reference_type='widget')
        grant_role(self.owner["role"], widget_link.get_privilege_ancestor(), self.owner["user"])
        widget_link_gql_id = widget_link.gql_id
        result = self.gql_client.execute(
            base_query + '{widget { id }}} ',
            variable_values={"linkid": widget_link_gql_id},
            context_value=self.gql_client.get_context(user=self.owner["user"]),
        )
        self.assertIsNotNone(result['data']['link']['widget']['id'])
        template_link = LinkFactory(parent_folder=self.parent_folder, template=TemplateFactory(), reference_type='template')
        grant_role(self.owner["role"], template_link.get_privilege_ancestor(), self.owner["user"])
        template_link_gql_id = template_link.gql_id
        result = self.gql_client.execute(
            base_query + '{template { id }}} ',
            variable_values={"linkid": template_link_gql_id},
            context_value=self.gql_client.get_context(user=self.owner["user"]),
        )
        self.assertIsNotNone(result['data']['link']['template']['id'])


class TestReadFilteredLinks(GQLTestCase):
    node_name = "LinkNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.now = dt.datetime.now().astimezone(pytz.UTC)
        cls.later = cls.now + dt.timedelta(days=1)
        cls.before = cls.now - dt.timedelta(days=1)

    @mock.patch('ery_backend.assets.models.ImageAsset.bucket')
    def setUp(self, mock_bucket):
        state_choices = StateMixin.STATE_CHOICES
        self.parent_folder = FolderFactory()
        self.other_parent_folder = FolderFactory()

        sd = StintDefinitionFactory(name='TestOne', state=state_choices.prealpha)
        self.sd_link = LinkFactory(
            stint_definition=sd, module_definition=None, parent_folder=self.parent_folder, reference_type='stint_definition'
        )

        md = ModuleDefinitionFactory(state=state_choices.beta)
        self.md_link = LinkFactory(module_definition=md, parent_folder=self.other_parent_folder)

        theme = ThemeFactory(state=state_choices.prealpha)
        self.theme_link = LinkFactory(theme=theme, module_definition=None, parent_folder=self.parent_folder)

        procedure = ProcedureFactory(state=state_choices.beta)
        self.procedure_link = LinkFactory(procedure=procedure, module_definition=None, parent_folder=self.other_parent_folder)

        template = TemplateFactory(state=state_choices.beta)
        self.template_link = LinkFactory(template=template, module_definition=None, parent_folder=self.parent_folder)

        validator = ValidatorFactory(code=None, state=state_choices.beta)
        self.validator_link = LinkFactory(validator=validator, module_definition=None, parent_folder=self.parent_folder)

        widget = WidgetFactory(state=state_choices.beta)
        self.widget_link = LinkFactory(widget=widget, module_definition=None, parent_folder=self.parent_folder)

        image = ImageAssetFactory(state=state_choices.beta)
        self.image_link = LinkFactory(image_asset=image, module_definition=None, parent_folder=self.parent_folder)

        grant_role(self.viewer["role"], self.parent_folder, self.viewer["user"])
        grant_role(self.viewer["role"], self.other_parent_folder, self.viewer["user"])

        grant_role(self.viewer["role"], sd, self.viewer["user"])
        grant_role(self.viewer["role"], md, self.viewer["user"])
        grant_role(self.viewer["role"], template, self.viewer["user"])
        grant_role(self.viewer["role"], validator, self.viewer["user"])
        grant_role(self.viewer["role"], widget, self.viewer["user"])
        grant_role(self.viewer["role"], image, self.viewer["user"])

    def test_read_filtered_links_by_model_attrs(self):
        """
        Confirm standard model filter fields still work.
        """
        unfiltered_query = """query {allLinks{ edges{ node{ id }}}}"""
        filtered_query = """query FilteredQuery($parentFolder: ID!){
            allLinks(parentFolder: $parentFolder){ edges{ node{ id }}}}"""
        td = {'parentFolder': self.parent_folder.gql_id}
        unfiltered_result = self.gql_client.execute(
            unfiltered_query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        filtered_result = self.gql_client.execute(
            filtered_query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        unfiltered_data = unfiltered_result['data']['allLinks']['edges']
        filtered_data = filtered_result['data']['allLinks']['edges']
        self.assertEqual(len(unfiltered_data), 8)
        self.assertEqual(len(filtered_data), 6)

    def test_read_filtered_links_by_name(self):
        """
        Confirm model filterable by name.
        """
        query = """query{ allLinks(name: "TestOne"){ edges{ node{ id }}}}"""
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        data = result['data']['allLinks']['edges']
        self.assertEqual(len(data), 1)

    def test_modified_before(self):
        """
        Confirm model filterable by modified_before
        """
        query = """query ModifiedBefore($modifiedBefore: DateTime!){ allLinks(modifiedBefore: $modifiedBefore){
                    edges{ node{ id }}}}"""
        td = {'modifiedBefore': self.later.isoformat()}
        result1 = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        data1 = result1['data']['allLinks']['edges']
        self.assertEqual(len(data1), 8)

        td2 = {'modifiedBefore': self.now.isoformat()}
        result2 = self.gql_client.execute(
            query, variable_values=td2, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        data2 = result2['data']['allLinks']['edges']
        self.assertEqual(len(data2), 0)

    def test_modified_after(self):
        """
        Confirm model filterable by modified_after
        """
        query = """query ModifiedAfter($modifiedAfter: DateTime!){ allLinks(modifiedAfter: $modifiedAfter){
                    edges{ node{ id }}}}"""
        td = {'modifiedAfter': self.before.isoformat()}
        result1 = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        data1 = result1['data']['allLinks']['edges']
        self.assertEqual(len(data1), 8)

        td2 = {'modifiedAfter': self.later.isoformat()}
        result2 = self.gql_client.execute(
            query, variable_values=td2, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        data2 = result2['data']['allLinks']['edges']
        self.assertEqual(len(data2), 0)

    def test_is_ready(self):
        """
        Confirm model filterable by state
        """
        query = """query{ allLinks(isReady: true){
                    edges{ node{ id }}}}"""
        result1 = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        data1 = result1['data']['allLinks']['edges']

        self.assertEqual(len(data1), 6)

    def test_exclude_stintdefinition(self):
        """
        Confirm stint_definition filter works
        """
        td = {'value': True}
        query = """query Test($value: Boolean!){ allLinks(excludeStintDefinitions: $value){
                    edges{ node{ id }}}}"""
        result1 = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assertNotIn(self.sd_link.gql_id, [edge['node']['id'] for edge in result1['data']['allLinks']['edges']])

        td['value'] = False
        result2 = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assertIn(self.sd_link.gql_id, [edge['node']['id'] for edge in result2['data']['allLinks']['edges']])

    def test_exclude_moduledefinition(self):
        """
        Confirm module_definition filter works
        """
        td = {'value': True}
        query = """query Test($value: Boolean!){ allLinks(excludeModuleDefinitions: $value){
                    edges{ node{ id }}}}"""
        result1 = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assertNotIn(self.md_link.gql_id, [edge['node']['id'] for edge in result1['data']['allLinks']['edges']])

        td['value'] = False
        result2 = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assertIn(self.md_link.gql_id, [edge['node']['id'] for edge in result2['data']['allLinks']['edges']])

    def test_exclude_theme(self):
        """
        Confirm theme filter works
        """
        td = {'value': True}
        query = """query Test($value: Boolean!){ allLinks(excludeThemes: $value){
                    edges{ node{ id }}}}"""
        result1 = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assertNotIn(self.theme_link.gql_id, [edge['node']['id'] for edge in result1['data']['allLinks']['edges']])

        td['value'] = False
        result2 = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assertIn(self.theme_link.gql_id, [edge['node']['id'] for edge in result2['data']['allLinks']['edges']])

    def test_exclude_procedure(self):
        """
        Confirm procedure filter works
        """
        td = {'value': True}
        query = """query Test($value: Boolean!){ allLinks(excludeProcedures: $value){
                    edges{ node{ id }}}}"""
        result1 = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assertNotIn(self.procedure_link.gql_id, [edge['node']['id'] for edge in result1['data']['allLinks']['edges']])

        td['value'] = False
        result2 = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assertIn(self.procedure_link.gql_id, [edge['node']['id'] for edge in result2['data']['allLinks']['edges']])

    def test_exclude_template(self):
        """
        Confirm template filter works
        """
        td = {'value': True}
        query = """query Test($value: Boolean!){ allLinks(excludeTemplates: $value){
                    edges{ node{ id }}}}"""
        result1 = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assertNotIn(self.template_link.gql_id, [edge['node']['id'] for edge in result1['data']['allLinks']['edges']])

        td['value'] = False
        result2 = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assertIn(self.template_link.gql_id, [edge['node']['id'] for edge in result2['data']['allLinks']['edges']])

    def test_exclude_validator(self):
        """
        Confirm validtor filter works
        """
        td = {'value': True}
        query = """query Test($value: Boolean!){ allLinks(excludeValidators: $value){
                    edges{ node{ id }}}}"""
        result1 = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assertNotIn(self.validator_link.gql_id, [edge['node']['id'] for edge in result1['data']['allLinks']['edges']])

        td['value'] = False
        result2 = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assertIn(self.validator_link.gql_id, [edge['node']['id'] for edge in result2['data']['allLinks']['edges']])

    def test_exclude_widget(self):
        """
        Confirm widget filter works
        """
        td = {'value': True}
        query = """query Test($value: Boolean!){ allLinks(excludeWidgets: $value){
                    edges{ node{ id }}}}"""
        result1 = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assertNotIn(self.widget_link.gql_id, [edge['node']['id'] for edge in result1['data']['allLinks']['edges']])

        td['value'] = False
        result2 = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assertIn(self.widget_link.gql_id, [edge['node']['id'] for edge in result2['data']['allLinks']['edges']])

    def test_exclude_image(self):
        """
        Confirm image filter works
        """
        td = {'value': True}
        query = """query Test($value: Boolean!){ allLinks(excludeImages: $value){
                    edges{ node{ id }}}}"""
        result1 = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assertNotIn(self.image_link.gql_id, [edge['node']['id'] for edge in result1['data']['allLinks']['edges']])

        td['value'] = False
        result2 = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assertIn(self.image_link.gql_id, [edge['node']['id'] for edge in result2['data']['allLinks']['edges']])

    def test_limit(self):
        query1 = """{ allLinks{ edges{ node{ id }}}}"""
        result = self.gql_client.execute(query1, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        data1 = result['data']['allLinks']['edges']
        self.assertEqual(len(data1), 8)
        query2 = """{ allLinks(last: 3){ edges{ node{ id }}}}"""
        result2 = self.gql_client.execute(query2, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        data2 = result2['data']['allLinks']['edges']
        self.assertEqual(len(data2), 3)

    def test_offset(self):
        query1 = """{ allLinks{ edges{ node{ id }}}}"""
        result = self.gql_client.execute(query1, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        data1 = result['data']['allLinks']['edges']
        self.assertEqual(len(data1), 8)
        query2 = """{ allLinks(offset: 3){ edges{ node{ id }}}}"""
        result2 = self.gql_client.execute(query2, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        data2 = result2['data']['allLinks']['edges']
        self.assertEqual(len(data2), 5)

    def test_state(self):
        td = {'value': StateMixin.STATE_CHOICES.prealpha}
        query = """query Test($value: String!){ allLinks(state: $value){ edges{ node{ id }}}}"""
        result1 = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        data1 = result1['data']['allLinks']['edges']
        self.assertEqual(len(data1), 2)
        td['value'] = StateMixin.STATE_CHOICES.beta
        result2 = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        data2 = result2['data']['allLinks']['edges']
        self.assertEqual(len(data2), 6)


class TestCreateLink(GQLTestCase):
    node_name = "LinkNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @classmethod
    @mock.patch('ery_backend.assets.models.ImageAsset.bucket')
    def setUpClass(cls, mock_bucket, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.query = """mutation CreateLink($parentFolderId: ID!, $imageAssetId: ID){
            createLink(input: {
                parentFolder: $parentFolderId,
                imageAsset: $imageAssetId
                })
                {linkEdge{ node{ id imageAsset{ id } }}}}"""

    def setUp(self):
        self.parent_folder = FolderFactory()
        self.parent_folder_gql_id = self.parent_folder.gql_id
        self.profile_image = ImageAssetFactory()
        self.profile_image_gql_id = self.profile_image.gql_id
        self.td = {'parentFolderId': self.parent_folder_gql_id, 'imageAssetId': self.profile_image_gql_id}

    def test_create_requires_login(self):
        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        self.assertRaises(Link.DoesNotExist, Link.objects.get, **{"parent_folder__id": self.parent_folder.id})

    def test_create_requires_folder_ownership(self):
        """
        Must have ownership over an added parent_folder
        """
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_create_produces_result(self):
        grant_role(self.owner['role'], self.parent_folder, self.owner['user'])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        lookup = Link.objects.get(parent_folder__id=self.parent_folder.id)

        self.assertEqual(lookup.image_asset.id, self.profile_image.id)


class TestUpdateLink(GQLTestCase):
    node_name = "LinkNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.query = """mutation UpdateLink($parentFolderId: ID!, $templateId: ID, $linkId: ID!){
            updateLink(input: {
                id: $linkId,
                parentFolder: $parentFolderId,
                template: $templateId
                })
                {link{ id template{ id } folder{ id } }}}"""

    def setUp(self):
        self.link = LinkFactory(template=TemplateFactory())
        self.link_gql_id = self.link.gql_id
        self.parent_folder = FolderFactory()
        self.parent_folder_gql_id = self.parent_folder.gql_id
        self.template = TemplateFactory()
        self.template_gql_id = self.template.gql_id
        self.td = {'parentFolderId': self.parent_folder_gql_id, 'templateId': self.template_gql_id, 'linkId': self.link_gql_id}

    def test_update_requires_privilege(self):
        grant_role(self.viewer["role"], self.link.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        grant_role(self.owner["role"], self.link.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        lookup = Link.objects.get(pk=self.link.id)

        self.assertEqual(lookup.parent_folder.id, self.parent_folder.id)
        self.assertEqual(lookup.template.id, self.template.id)


class TestDeleteLink(GQLTestCase):
    node_name = "LinkNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.link = LinkFactory(template=TemplateFactory())
        self.link_gql_id = self.link.gql_id

        self.td = {'linkId': self.link_gql_id}

        self.query = """mutation DeleteLink($linkId: ID!){
             deleteLink(input: { id: $linkId })
             { id }}"""

    def test_delete_requires_privilege(self):
        grant_role(self.viewer["role"], self.link.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        Link.objects.get(pk=self.link.id)

    def test_delete_produces_result(self):
        grant_role(self.owner["role"], self.link.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertTrue(result["data"]["deleteLink"]["id"])

        self.assertRaises(Link.DoesNotExist, Link.objects.get, **{"pk": self.link.id})
