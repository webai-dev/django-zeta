import string
import random
from unittest import mock, skip

import graphene


from ery_backend.assets.factories import ImageAssetFactory
from ery_backend.base.testcases import GQLTestCase
from ery_backend.procedures.factories import ProcedureFactory
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.modules.schema import ModuleDefinitionQuery
from ery_backend.mutations import FileCommentMutation, FileStarMutation
from ery_backend.roles.utils import grant_role
from ery_backend.stints.factories import StintDefinitionFactory
from ery_backend.templates.factories import TemplateFactory
from ery_backend.users.schema import UserQuery, ViewerQuery
from ery_backend.widgets.factories import WidgetFactory


from ..factories import FileCommentFactory, FileStarFactory
from ..models import FileComment, FileStar
from ..schema import FileCommentQuery, FileStarQuery


def make_text():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=32))


class TestQuery(FileStarQuery, UserQuery, FileCommentQuery, ViewerQuery, ModuleDefinitionQuery, graphene.ObjectType):
    pass


class TestMutation(FileStarMutation, FileCommentMutation, graphene.ObjectType):
    pass


class TestReadFileComment(GQLTestCase):
    node_name = "FileCommentNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_read_requires_login(self):
        """
        User must be logged in to use the FileCommentQuery
        """
        file_comment = FileCommentFactory()
        td = {"gqlId": file_comment.gql_id}

        query = """query Read($gqlId: ID!){ fileComment(id: $gqlId){
            user {id} comment
            }}"""

        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)


class TestCreateFileComment(GQLTestCase):
    node_name = "FileCommentNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def create_with(self, obj, object_node_name, user=None):
        """
        Run a standard creation test of a comment on the provided object

        Arguments:
            obj: the object of the comment, as made in a factory
            object_node_name: graphene schema's node name
        """
        obj_gid = obj.gql_id
        td = {"comment": "some comment", "on": obj_gid}

        mutation = """
mutation CreateFileComment($on: ID!, $comment: String!) {
    createFileComment(input: {
        on: $on,
        comment: $comment 
    }) {
        userCommentEdge {
            node {
                id
                comment
            }
        }
    }
}"""
        kwargs = {'variable_values': td}
        if user:
            kwargs['context_value'] = self.gql_client.get_context(user=user)

        result = self.gql_client.execute(mutation, **kwargs)
        return result

    @mock.patch('ery_backend.assets.models.ImageAsset.bucket')
    def test_create_with_image_asset(self, mock_bucket):
        """
        Comment can be created for a google image
        """
        obj = ImageAssetFactory()
        unauthorized_result = self.create_with(obj, "ImageAssetNode")
        self.assert_query_was_unauthorized(unauthorized_result)
        grant_role(self.owner["role"], obj, self.owner["user"])
        authorized_result = self.create_with(obj, "ImageAssetNode", self.owner["user"])
        self.fail_on_errors(authorized_result)
        self.assertEqual(
            authorized_result["data"]["createFileComment"]["userCommentEdge"]["node"]["comment"],
            "some comment",
            msg="Comment didn't match in GQL response",
        )

        obj.refresh_from_db()
        self.assertEqual(obj.filecomment_set.all()[0].comment, "some comment", msg="Comment didn't match in database")

    def test_create_with_prodedure(self):
        """
        Comment can be created for a procedure
        """
        obj = ProcedureFactory()
        unauthorized_result = self.create_with(obj, "ProcedureNode")
        self.assert_query_was_unauthorized(unauthorized_result)
        grant_role(self.owner["role"], obj, self.owner["user"])
        authorized_result = self.create_with(obj, "ProcedureNode", self.owner["user"])
        self.fail_on_errors(authorized_result)
        self.assertEqual(
            authorized_result["data"]["createFileComment"]["userCommentEdge"]["node"]["comment"],
            "some comment",
            msg="Comment didn't match in GQL response",
        )

        obj.refresh_from_db()
        self.assertEqual(obj.filecomment_set.all()[0].comment, "some comment", msg="Comment didn't match in database")

    def test_create_with_module_definition(self):
        """
        Comment can be created for a module definition
        """
        obj = ModuleDefinitionFactory()
        unauthorized_result = self.create_with(obj, "ModuleDefinitionNode")
        self.assert_query_was_unauthorized(unauthorized_result)
        grant_role(self.owner["role"], obj, self.owner["user"])
        authorized_result = self.create_with(obj, "ModuleDefinitionNode", self.owner["user"])
        self.fail_on_errors(authorized_result)
        self.assertEqual(
            authorized_result["data"]["createFileComment"]["userCommentEdge"]["node"]["comment"],
            "some comment",
            msg="Comment didn't match in GQL response",
        )

        obj.refresh_from_db()
        self.assertEqual(obj.filecomment_set.all()[0].comment, "some comment", msg="Comment didn't match in database")

    def test_create_with_stint_definition(self):
        """
        Comment can be created for a stint definition
        """
        obj = StintDefinitionFactory()
        unauthorized_result = self.create_with(obj, "StintDefinitionNode")
        self.assert_query_was_unauthorized(unauthorized_result)
        grant_role(self.owner["role"], obj, self.owner["user"])
        authorized_result = self.create_with(obj, "StintDefinitionNode", self.owner["user"])
        self.fail_on_errors(authorized_result)
        self.assertEqual(
            authorized_result["data"]["createFileComment"]["userCommentEdge"]["node"]["comment"],
            "some comment",
            msg="Comment didn't match in GQL response",
        )

        obj.refresh_from_db()
        self.assertEqual(obj.filecomment_set.all()[0].comment, "some comment", msg="Comment didn't match in database")

    def test_create_with_template(self):
        """
        Comment can be created for a template
        """
        obj = TemplateFactory()
        unauthorized_result = self.create_with(obj, "TemplateNode")
        self.assert_query_was_unauthorized(unauthorized_result)
        grant_role(self.owner["role"], obj, self.owner["user"])
        authorized_result = self.create_with(obj, "TemplateNode", self.owner["user"])
        self.fail_on_errors(authorized_result)
        self.assertEqual(
            authorized_result["data"]["createFileComment"]["userCommentEdge"]["node"]["comment"],
            "some comment",
            msg="Comment didn't match in GQL response",
        )

        obj.refresh_from_db()
        self.assertEqual(obj.filecomment_set.all()[0].comment, "some comment", msg="Comment didn't match in database")

    def test_create_with_widget(self):
        """
        Comment can be created for a widget
        """
        obj = WidgetFactory()
        unauthorized_result = self.create_with(obj, "WidgetNode")
        self.assert_query_was_unauthorized(unauthorized_result)
        grant_role(self.owner["role"], obj, self.owner["user"])
        authorized_result = self.create_with(obj, "WidgetNode", self.owner["user"])
        self.fail_on_errors(authorized_result)
        self.assertEqual(
            authorized_result["data"]["createFileComment"]["userCommentEdge"]["node"]["comment"],
            "some comment",
            msg="Comment didn't match in GQL response",
        )

        obj.refresh_from_db()
        self.assertEqual(obj.filecomment_set.all()[0].comment, "some comment", msg="Comment didn't match in database")


class TestUpdateFileComment(GQLTestCase):
    node_name = "FileCommentNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_update_requires_privileges(self):
        """Unprivileged users cannot update FileComments"""
        user_comment = FileCommentFactory()

        grant_role(self.viewer["role"], user_comment.get_privilege_ancestor(), self.viewer["user"])

        td = {"gqlId": user_comment.gql_id, "comment": make_text()}

        mutation = """mutation UpdateFileComment(
            $gqlId: ID!, $comment: String){
            updateFileComment(input: {
                id: $gqlId,
                comment: $comment })
            { userComment
            { user {id} comment }}}"""

        result = self.gql_client.execute(
            mutation, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        user_comment.refresh_from_db()

        self.assertNotEqual(getattr(user_comment, "comment"), td["comment"])

    def test_update_produces_result(self):
        """UpdateFileComment alters the database"""
        user_comment = FileCommentFactory()

        grant_role(self.editor["role"], user_comment.get_privilege_ancestor(), self.editor["user"])

        td = {"gqlId": user_comment.gql_id, "comment": make_text()}

        mutation = """mutation UpdateFileComment(
            $gqlId: ID!, $comment: String){
            updateFileComment(input: {
                id: $gqlId,
                comment: $comment })
            { userComment
            { user {id} comment }}}"""

        result = self.gql_client.execute(
            mutation, variable_values=td, context_value=self.gql_client.get_context(user=self.editor["user"])
        )
        self.fail_on_errors(result)

        user_comment.refresh_from_db()

        self.assertEqual(getattr(user_comment, "comment"), td["comment"])


class TestDeleteFileComment(GQLTestCase):
    node_name = "FileCommentNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_delete_requires_privileges(self):
        """Unprivileged user cannot delete FileComment"""
        user_comment = FileCommentFactory()
        user_comment_id = user_comment.pk
        td = {"gqlId": user_comment.gql_id}

        grant_role(self.viewer["role"], user_comment.get_privilege_ancestor(), self.viewer["user"])

        mutation = """mutation DeleteFileComment($gqlId: ID!){
            deleteFileComment(input: {id: $gqlId}){success}}"""

        result = self.gql_client.execute(mutation, variable_values=td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            mutation, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        # Prove it's still in the database
        FileComment.objects.get(pk=user_comment_id)

    def test_delete_produces_result(self):
        """DeleteFileComment deletes the record"""

        user_comment = FileCommentFactory()
        user_comment_id = user_comment.pk
        td = {"gqlId": user_comment.gql_id}

        grant_role(self.owner["role"], user_comment.get_privilege_ancestor(), self.owner["user"])

        mutation = """mutation DeleteFileComment($gqlId: ID!){
            deleteFileComment(input: {id: $gqlId}){success}}"""

        result = self.gql_client.execute(
            mutation, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertTrue(result["data"]["deleteFileComment"]["success"])
        self.assertRaises(FileComment.DoesNotExist, FileComment.objects.get, **{"pk": user_comment_id})


class TestReadFileStar(GQLTestCase):
    node_name = "FileStarNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @skip("XXX: Address in issue #740")
    def test_read_does_not_requires_login(self):
        """
        User must be logged in to use the FileStarQuery
        """
        star = FileStarFactory()
        td = {"gqlId": star.gql_id}

        query = """query Read($gqlId: ID!){ fileStar(id: $gqlId){
            moduleDefinition {id}
            }}"""

        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

        query = """{allFileStars {edges {node { user {id}}}}}"""

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_filters_by_privilege(self):
        """
        allFileStars filters by privilege
        """
        # Permission Setup
        stars = [FileStarFactory(), FileStarFactory(), FileStarFactory()]

        for star in stars:
            grant_role(self.viewer["role"], star, self.viewer["user"])

        for star in stars[1:]:
            grant_role(self.editor["role"], star, self.editor["user"])

        grant_role(self.owner["role"], stars[2], self.owner["user"])

        # Query
        query = """{allFileStars {edges {node { user {id} }}}}"""

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFileStars"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFileStars"]["edges"]), 3)

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFileStars"]["edges"]), 3)


class TestCreateFileStar(GQLTestCase):
    node_name = "FileStarNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def create_with(self, obj, object_node_name, user=None):
        """
        Run a standard creation test of a comment on the provided object

        Arguments:
            obj: the object of the comment, as made in a factory
            object_node_name: graphene schema's node name
        """
        obj_gid = obj.gql_id
        td = {"on": obj_gid}

        mutation = """mutation CreateFileStar($on: ID!){
            createFileStar(input: {
                on: $on })
            { fileStar { id user {username}}}}"""

        kwargs = {'variable_values': td}
        if user:
            kwargs['context_value'] = self.gql_client.get_context(user=user)

        result = self.gql_client.execute(mutation, **kwargs)
        return result

    @mock.patch('ery_backend.assets.models.ImageAsset.bucket')
    def test_create_with_image_asset(self, mock_bucket):
        """
        Comment can be created for a google image
        """
        obj = ImageAssetFactory()
        unauthorized_result = self.create_with(obj, "ImageAssetNode")
        self.assert_query_was_unauthorized(unauthorized_result)
        grant_role(self.owner["role"], obj, self.owner["user"])
        authorized_result = self.create_with(obj, "ImageAssetNode", self.owner["user"])
        self.fail_on_errors(authorized_result)
        self.assertEqual(
            authorized_result["data"]["createFileStar"]["fileStar"]["user"]["username"],
            self.owner["user"].username,
            msg="GQL returns suggests star created with wrong user",
        )
        obj.refresh_from_db()
        self.assertEqual(
            obj.filestar_set.all()[0].user.username,
            self.owner["user"].username,
            msg="Database shows star created with wrong user",
        )

    def test_create_with_prodedure(self):
        """
        Comment can be created for a procedure
        """
        obj = ProcedureFactory()
        unauthorized_result = self.create_with(obj, "ProcedureNode")
        self.assert_query_was_unauthorized(unauthorized_result)
        grant_role(self.owner["role"], obj, self.owner["user"])
        authorized_result = self.create_with(obj, "ProcedureNode", self.owner["user"])
        self.fail_on_errors(authorized_result)
        self.assertEqual(
            authorized_result["data"]["createFileStar"]["fileStar"]["user"]["username"],
            self.owner["user"].username,
            msg="GQL returns suggests star created with wrong user",
        )
        obj.refresh_from_db()
        self.assertEqual(
            obj.filestar_set.all()[0].user.username,
            self.owner["user"].username,
            msg="Database shows star created with wrong user",
        )

    def test_create_with_module_definition(self):
        """
        Comment can be created for a module definition
        """
        obj = ModuleDefinitionFactory()
        unauthorized_result = self.create_with(obj, "ModuleDefinitionNode")
        self.assert_query_was_unauthorized(unauthorized_result)
        grant_role(self.owner["role"], obj, self.owner["user"])
        authorized_result = self.create_with(obj, "ModuleDefinitionNode", self.owner["user"])
        self.fail_on_errors(authorized_result)
        self.assertEqual(
            authorized_result["data"]["createFileStar"]["fileStar"]["user"]["username"],
            self.owner["user"].username,
            msg="GQL returns suggests star created with wrong user",
        )
        obj.refresh_from_db()
        self.assertEqual(
            obj.filestar_set.all()[0].user.username,
            self.owner["user"].username,
            msg="Database shows star created with wrong user",
        )

    def test_create_with_stint_definition(self):
        """
        Comment can be created for a stint definition
        """
        obj = StintDefinitionFactory()
        unauthorized_result = self.create_with(obj, "StintDefinitionNode")
        self.assert_query_was_unauthorized(unauthorized_result)
        grant_role(self.owner["role"], obj, self.owner["user"])
        authorized_result = self.create_with(obj, "StintDefinitionNode", self.owner["user"])
        self.fail_on_errors(authorized_result)
        self.assertEqual(
            authorized_result["data"]["createFileStar"]["fileStar"]["user"]["username"],
            self.owner["user"].username,
            msg="GQL returns suggests star created with wrong user",
        )
        obj.refresh_from_db()
        self.assertEqual(
            obj.filestar_set.all()[0].user.username,
            self.owner["user"].username,
            msg="Database shows star created with wrong user",
        )

    def test_create_with_template(self):
        """
        Comment can be created for a template
        """
        obj = TemplateFactory()
        unauthorized_result = self.create_with(obj, "TemplateNode")
        self.assert_query_was_unauthorized(unauthorized_result)
        grant_role(self.owner["role"], obj, self.owner["user"])
        authorized_result = self.create_with(obj, "TemplateNode", self.owner["user"])
        self.fail_on_errors(authorized_result)
        self.assertEqual(
            authorized_result["data"]["createFileStar"]["fileStar"]["user"]["username"],
            self.owner["user"].username,
            msg="GQL returns suggests star created with wrong user",
        )
        obj.refresh_from_db()
        self.assertEqual(
            obj.filestar_set.all()[0].user.username,
            self.owner["user"].username,
            msg="Database shows star created with wrong user",
        )

    def test_create_with_widget(self):
        """
        Comment can be created for a widget
        """
        obj = WidgetFactory()
        unauthorized_result = self.create_with(obj, "WidgetNode")
        self.assert_query_was_unauthorized(unauthorized_result)
        grant_role(self.owner["role"], obj, self.owner["user"])
        authorized_result = self.create_with(obj, "WidgetNode", self.owner["user"])
        self.fail_on_errors(authorized_result)
        self.assertEqual(
            authorized_result["data"]["createFileStar"]["fileStar"]["user"]["username"],
            self.owner["user"].username,
            msg="GQL returns suggests star created with wrong user",
        )
        obj.refresh_from_db()
        self.assertEqual(
            obj.filestar_set.all()[0].user.username,
            self.owner["user"].username,
            msg="Database shows star created with wrong user",
        )


class TestDeleteFileStar(GQLTestCase):
    node_name = "FileStarNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_delete_requires_privileges(self):
        """Unprivileged user cannot delete FileStar"""
        star = FileStarFactory()
        star_id = star.pk
        td = {"gqlId": star.gql_id}
        grant_role(self.viewer["role"], star, self.viewer["user"])

        mutation = """mutation DeleteFileStar($gqlId: ID!){
            deleteFileStar(input: {id: $gqlId}){success}}"""

        result = self.gql_client.execute(mutation, variable_values=td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            mutation, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        # Prove it's still in the database
        FileStar.objects.get(pk=star_id)

    def test_delete_produces_result(self):
        """DeleteFileStar deletes the record"""

        star = FileStarFactory()
        star_id = star.pk
        td = {"gqlId": star.gql_id}

        grant_role(self.owner["role"], star, self.owner["user"])

        mutation = """mutation DeleteFileStar($gqlId: ID!){
            deleteFileStar(input: {id: $gqlId}){success}}"""

        result = self.gql_client.execute(
            mutation, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertTrue(result["data"]["deleteFileStar"]["success"])
        self.assertRaises(FileStar.DoesNotExist, FileStar.objects.get, **{"pk": star_id})
