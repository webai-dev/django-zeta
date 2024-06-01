from unittest import mock
import random
import string
import time

import graphene


from ery_backend.assets.factories import ImageAssetFactory
from ery_backend.base.testcases import GQLTestCase
from ery_backend.comments.factories import FileStarFactory
from ery_backend.procedures.factories import ProcedureFactory
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.mutations import FileTouchMutation
from ery_backend.roles.utils import grant_role
from ery_backend.stints.factories import StintDefinitionFactory
from ery_backend.templates.factories import TemplateFactory
from ery_backend.themes.factories import ThemeFactory
from ery_backend.users.factories import UserFactory, FileTouchFactory
from ery_backend.validators.factories import ValidatorFactory
from ery_backend.widgets.factories import WidgetFactory

from ..schema import FileTouchQuery, ViewerQuery, UserQuery


def make_text():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=32))


class TestQuery(FileTouchQuery, UserQuery, ViewerQuery, graphene.ObjectType):
    pass


class TestMutation(FileTouchMutation, graphene.ObjectType):
    pass


class TestUsers(GQLTestCase):
    node_name = "UserNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.all_query = """query AllUsers($username: String!){ allUsers(username: $username){ edges{ node{ id username }}}}"""
        cls.query = """query User($id: ID!){
                        user(id: $id){
                            id username }}"""
        cls.user = UserFactory(username='jonesbbqandfootmessage')
        cls.td = {'id': cls.user.gql_id, 'username': cls.user.username}

    def test_user_query_requires_login(self):
        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_user_query_works_with_login(self):
        grant_role(self.viewer['role'], self.user, self.viewer['user'])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.fail_on_errors(result)

        self.assertEqual(result["data"]["user"]["username"], self.user.username)

    def test_allUsers_query_works_with_login(self):
        result = self.gql_client.execute(
            self.all_query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.fail_on_errors(result)

        self.assertEqual(result["data"]["allUsers"]["edges"][0]["node"]["username"], self.user.username)


class TestViewer(GQLTestCase):
    node_name = "ViewerNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def test_viewer_query_requires_login(self):
        query = """query ViewerQuery { viewer { id username }}"""

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_viewer_works_with_login(self):
        query = """query ViewerQuery { viewer { id username }}"""
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)

        self.assertEqual(result["data"]["viewer"]["username"], self.viewer["user"].username)

    def test_all_queries_available(self):
        available_queries = [
            "allActions",
            "allActionSteps",
            "allModuleDefinitions",
            "allStageDefinitions",
            "allEras",
            "allTemplates",
            "allThemes",
        ]
        base_query = """query ViewerQuery { viewer { %s { edges { node { id }}}}}"""

        for q in available_queries:
            query = base_query % (q,)
            result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
            self.fail_on_errors(result)


class TestReadFileTouch(GQLTestCase):
    node_name = "FileTouchNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_read_requires_login(self):
        """
        User must be logged in to use the FileTouchQuery
        """
        file_touch = FileTouchFactory()
        td = {"gqlId": file_touch.gql_id}

        query = """query Read($gqlId: ID!){ fileTouch(id: $gqlId){
            timestamp
            }}"""

        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

        query = """{allFileTouches {edges {node { timestamp }}}}"""

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_filters_by_privilege(self):
        """
        allFileTouches filters by privilege
        """
        # Permission Setup
        file_touches_viewer = [FileTouchFactory(user=self.viewer['user']) for _ in range(3)]
        file_touches_editor = [FileTouchFactory(user=self.editor['user']) for _ in range(3)]
        file_touches_owner = [FileTouchFactory(user=self.owner['user']) for _ in range(3)]

        for file_touch in file_touches_viewer:
            grant_role(self.viewer["role"], file_touch, self.viewer["user"])

        for file_touch in file_touches_editor[1:]:
            grant_role(self.editor["role"], file_touch, self.editor["user"])

        grant_role(self.owner["role"], file_touches_owner[2], self.owner["user"])

        # Query
        query = """{allFileTouches {edges {node { timestamp }}}}"""

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFileTouches"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFileTouches"]["edges"]), 3)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFileTouches"]["edges"]), 3)


class TestCreateFileTouch(GQLTestCase):
    node_name = "FileTouchNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def create_with(self, obj, object_node_name, user=None):
        """
        Run a standard creation test of a comment on the provided object

        Arguments:
            obj: the object of the comment, as made in a factory
            object_node_name: graphene schema's node name
        """
        obj_gid = obj.gql_id
        td = {"comment": make_text(), "on": obj_gid}

        mutation = """mutation CreateFileTouch($on: ID!){
            createFileTouch(input: {
                on: $on })
            { fileTouch { id timestamp }}}"""

        kwargs = {'variable_values': td}
        if user:
            kwargs['context_value'] = self.gql_client.get_context(user=user)

        result = self.gql_client.execute(mutation, **kwargs)
        return result

    @mock.patch('ery_backend.assets.models.ImageAsset.bucket')
    def test_create_with_image_asset(self, mock_bucket):
        """
        Filetouch can be created for a google image
        """
        obj = ImageAssetFactory()
        unauthorized_result = self.create_with(obj, "ImageAssetNode")
        self.assert_query_was_unauthorized(unauthorized_result)
        grant_role(self.owner["role"], obj, self.owner["user"])
        authorized_result = self.create_with(obj, "ImageAssetNode", self.owner["user"])
        self.fail_on_errors(authorized_result)
        obj.refresh_from_db()
        self.assertEqual(
            obj.filetouch_set.all()[0].timestamp.isoformat(),
            authorized_result["data"]["createFileTouch"]["fileTouch"]["timestamp"],
            msg=f"Timestamp in database did not match GQL response {authorized_result}",
        )

    def test_create_with_prodedure(self):
        """
        Filetouch can be created for a procedure
        """
        obj = ProcedureFactory()
        unauthorized_result = self.create_with(obj, "ProcedureNode")
        self.assert_query_was_unauthorized(unauthorized_result)
        grant_role(self.owner["role"], obj, self.owner["user"])
        authorized_result = self.create_with(obj, "ProcedureNode", self.owner["user"])
        self.fail_on_errors(authorized_result)
        obj.refresh_from_db()
        self.assertEqual(
            obj.filetouch_set.all()[0].timestamp.isoformat(),
            authorized_result["data"]["createFileTouch"]["fileTouch"]["timestamp"],
            msg=f"Timestamp in database did not match GQL response {authorized_result}",
        )

    def test_create_with_module_definition(self):
        """
        Filetouch can be created for a module definition
        """
        obj = ModuleDefinitionFactory()
        unauthorized_result = self.create_with(obj, "ModuleDefinitionNode")
        self.assert_query_was_unauthorized(unauthorized_result)
        grant_role(self.owner["role"], obj, self.owner["user"])
        authorized_result = self.create_with(obj, "ModuleDefinitionNode", self.owner["user"])
        self.fail_on_errors(authorized_result)
        obj.refresh_from_db()
        self.assertEqual(
            obj.filetouch_set.all()[0].timestamp.isoformat(),
            authorized_result["data"]["createFileTouch"]["fileTouch"]["timestamp"],
            msg=f"Timestamp in database did not match GQL response {authorized_result}",
        )

    def test_create_with_stint_definition(self):
        """
        Filetouch can be created for a stint definition
        """
        obj = StintDefinitionFactory()
        unauthorized_result = self.create_with(obj, "StintDefinitionNode")
        self.assert_query_was_unauthorized(unauthorized_result)
        grant_role(self.owner["role"], obj, self.owner["user"])
        authorized_result = self.create_with(obj, "StintDefinitionNode", self.owner["user"])
        self.fail_on_errors(authorized_result)
        obj.refresh_from_db()
        self.assertEqual(
            obj.filetouch_set.all()[0].timestamp.isoformat(),
            authorized_result["data"]["createFileTouch"]["fileTouch"]["timestamp"],
            msg=f"Timestamp in database did not match GQL response {authorized_result}",
        )

    def test_create_with_template(self):
        """
        Filetouch can be created for a template
        """
        obj = TemplateFactory()
        unauthorized_result = self.create_with(obj, "TemplateNode")
        self.assert_query_was_unauthorized(unauthorized_result)
        grant_role(self.owner["role"], obj, self.owner["user"])
        authorized_result = self.create_with(obj, "TemplateNode", self.owner["user"])
        self.fail_on_errors(authorized_result)
        obj.refresh_from_db()
        self.assertEqual(
            obj.filetouch_set.all()[0].timestamp.isoformat(),
            authorized_result["data"]["createFileTouch"]["fileTouch"]["timestamp"],
            msg=f"Timestamp in database did not match GQL response {authorized_result}",
        )

    def test_create_with_widget(self):
        """
        Filetouch can be created for a widget
        """
        obj = WidgetFactory()
        unauthorized_result = self.create_with(obj, "WidgetNode")
        self.assert_query_was_unauthorized(unauthorized_result)
        grant_role(self.owner["role"], obj, self.owner["user"])
        authorized_result = self.create_with(obj, "WidgetNode", self.owner["user"])
        self.fail_on_errors(authorized_result)
        obj.refresh_from_db()
        self.assertEqual(
            obj.filetouch_set.all()[0].timestamp.isoformat(),
            authorized_result["data"]["createFileTouch"]["fileTouch"]["timestamp"],
            msg=f"Timestamp in database did not match GQL response {authorized_result}",
        )


class TestUpdateFileTouch(GQLTestCase):
    node_name = "FileTouchNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_update_requires_privileges(self):
        """Unprivileged users cannot update FileTouches"""
        file_touch = FileTouchFactory()
        begin = file_touch.timestamp
        time.sleep(1)
        grant_role(self.viewer["role"], file_touch, self.viewer["user"])

        td = {
            "gqlId": file_touch.gql_id,
        }

        mutation = """mutation UpdateFileTouch($gqlId: ID!){
            updateFileTouch(input: { id: $gqlId })
            { fileTouch{  timestamp }}}"""

        result = self.gql_client.execute(
            mutation, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        file_touch.refresh_from_db()

        self.assertEqual(file_touch.timestamp, begin)

    def test_update_produces_result(self):
        """UpdateFileTouch alters the database"""
        file_touch = FileTouchFactory()
        begin = file_touch.timestamp
        time.sleep(1)

        grant_role(self.editor["role"], file_touch, self.editor["user"])

        td = {"gqlId": file_touch.gql_id}

        mutation = """mutation UpdateFileTouch($gqlId: ID!){
            updateFileTouch(input: { id: $gqlId })
            { fileTouch{ timestamp }}}"""

        result = self.gql_client.execute(
            mutation, variable_values=td, context_value=self.gql_client.get_context(user=self.editor["user"])
        )
        self.fail_on_errors(result)

        file_touch.refresh_from_db()
        self.assertTrue(file_touch.timestamp > begin)
        self.assertEqual(file_touch.timestamp.isoformat(), result["data"]["updateFileTouch"]["fileTouch"]["timestamp"])


class TestLibrary(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    # pylint:disable=too-many-branches
    def setUp(self):
        name_nums = ["One", "Two", "Three"]
        templates = {name: TemplateFactory(name=f"Template{name}") for name in name_nums}
        modules = {name: ModuleDefinitionFactory(name=f"ModuleDefinition{name}") for name in name_nums}
        stints = {name: StintDefinitionFactory(name=f"StintDefinition{name}") for name in name_nums}
        themes = {name: ThemeFactory(name=f"Theme{name}") for name in name_nums}
        procedures = {name: ProcedureFactory(name=f"procedure_{name}".lower()) for name in name_nums}
        widgets = {name: WidgetFactory(name=f"Widget{name}") for name in name_nums}
        images = {name: ImageAssetFactory(name=f'ImageAsset{name}.png') for name in name_nums}
        validators = {name: ValidatorFactory(name=f'Validator{name}', code=None) for name in name_nums}
        stars = 1
        for template in (templates["One"], templates["Three"], templates["Two"]):
            grant_role(self.owner["role"], template, self.owner["user"])
            for _ in range(stars):
                FileStarFactory(template=template, module_definition=None)
            stars += 1
        stars = 3
        for module in (modules["Three"], modules["Two"], modules["One"]):
            grant_role(self.owner["role"], module, self.owner["user"])
            for _ in range(stars):
                FileStarFactory(module_definition=module)
            stars -= 1
        stars = 1
        for stint in (stints["One"], stints["Two"], stints["Three"]):
            grant_role(self.owner["role"], stint, self.owner["user"])
            for _ in range(stars):
                FileStarFactory(module_definition=None, stint_definition=stint)
            stars += 1
        stars = 1
        for theme in (themes["One"], themes["Two"], themes["Three"]):
            grant_role(self.owner["role"], theme, self.owner["user"])
            for _ in range(stars):
                FileStarFactory(module_definition=None, theme=theme)
            stars += 1
        stars = 1
        for procedure in (procedures["One"], procedures["Two"], procedures["Three"]):
            grant_role(self.owner["role"], procedure, self.owner["user"])
            for _ in range(stars):
                FileStarFactory(module_definition=None, procedure=procedure)
            stars += 1
        stars = 1
        for widget in (widgets["One"], widgets["Two"], widgets["Three"]):
            grant_role(self.owner["role"], widget, self.owner["user"])
            for _ in range(stars):
                FileStarFactory(module_definition=None, widget=widget)
            stars += 1
        stars = 1
        for image in (images["One"], images["Two"], images["Three"]):
            grant_role(self.owner["role"], image, self.owner["user"])
            for _ in range(stars):
                FileStarFactory(module_definition=None, image_asset=image)
            stars += 1
        stars = 1
        for validator in (validators["One"], validators["Two"], validators["Three"]):
            grant_role(self.owner["role"], validator, self.owner["user"])
            for _ in range(stars):
                FileStarFactory(module_definition=None, validator=validator)
            stars += 1

    def test_library(self):
        """
        Confirm query correctly orders by popularity, and creates objects with expected attributes.
        """

        def _get_obj(data):
            for key in [
                'stintDefinition',
                'moduleDefinition',
                'procedure',
                'template',
                'widget',
                'theme',
                'imageAsset',
                'validator',
            ]:
                if data[key]:
                    return data[key]
            raise Exception(f"No object found in {data}")

        query = """{viewer{ library{ stintDefinition{ name comment modified }
                                     template { name comment modified}
                                     moduleDefinition { name comment modified }
                                     procedure{ name comment modified }
                                     theme{ name comment modified }
                                     widget{ name comment modified }
                                     imageAsset{ name comment modified }
                                     validator { name comment modified }
                                     owner{ username} popularity }}}"""

        self.owner["user"].query_library.invalidate()  # pylint:disable=protected-access
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        data = result["data"]["viewer"]["library"]
        searchable_data = []

        for obj_data in data:
            searchable_data.append(_get_obj(obj_data)['name'])
        first_tier_loc = searchable_data.index("procedure_three")
        second_tier_loc = searchable_data.index("procedure_two")
        third_tier_loc = searchable_data.index("procedure_one")

        self.assertTrue(first_tier_loc < second_tier_loc)
        self.assertTrue(second_tier_loc < third_tier_loc)

        other_first_tier_names = [
            f"{model}Three" for model in ["StintDefinition", "Theme", "ModuleDefinition", "Widget", "Validator"]
        ] + ["TemplateTwo", "ImageAssetThree.png"]
        other_second_tier_names = [
            f"{model}Two" for model in ["StintDefinition", "Theme", "ModuleDefinition", "Widget", "Validator"]
        ] + ["TemplateThree", "ImageAssetTwo.png"]
        other_third_tier_names = [
            f"{model}One" for model in ["StintDefinition", "Theme", "ModuleDefinition", "Widget", "Template", "Validator"]
        ] + ["ImageAssetOne.png"]

        for name in other_first_tier_names:

            self.assertTrue(searchable_data.index(name) < second_tier_loc)
        for name in other_second_tier_names:
            self.assertTrue(searchable_data.index(name) < third_tier_loc)
        for name in other_third_tier_names:
            self.assertTrue(searchable_data.index(name) > second_tier_loc)

        test_obj_data = {'obj': _get_obj(data[0]), 'popularity': data[0]['popularity'], 'owner': data[0]['owner']}
        self.assertIsNotNone(test_obj_data['obj']['name'])
        self.assertIsNotNone(test_obj_data['obj']['comment'])
        self.assertIsNotNone(test_obj_data['owner']['username'])
        self.assertIsNotNone(test_obj_data['obj']['modified'])
        self.assertIsNotNone(test_obj_data['popularity'])


class TestViewerFileTouches(GQLTestCase):
    """
    Confirm file touches accessible through Viewer.
    """

    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.query = """query viewer{ allFileTouches { edges{ node{ id }} }}"""

    def setUp(self):
        self.ft_1 = FileTouchFactory(user=self.viewer['user'])
        grant_role(self.viewer['role'], self.ft_1, self.viewer['user'])

        self.ft_2 = FileTouchFactory(user=self.owner['user'])
        grant_role(self.viewer['role'], self.ft_2, self.viewer['user'])

    def test_read_file_touches(self):

        result = self.gql_client.execute(self.query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        data = [node_data['node']['id'] for node_data in result['data']['allFileTouches']['edges']]
        # If user has read privilege, but not associated with touch, do not show
        self.assertNotIn(self.ft_2.gql_id, data)
        # Show if user has read privilege, and associated with touch
        self.assertIn(self.ft_1.gql_id, data)
