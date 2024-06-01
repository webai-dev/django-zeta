import os
from unittest import mock

import graphene

from ery_backend.base.testcases import GQLTestCase
from ery_backend.mutations import ImageAssetMutation
from ery_backend.roles.utils import grant_role

from ..factories import ImageAssetFactory
from ..models import ImageAsset
from ..schema import ImageAssetQuery, DatasetAssetQuery


DEMO_FILE_NAME = f"{os.getcwd()}/ery_backend/assets/tests/data/iamnotacatidontsaymeow.jpg"


class TestQuery(ImageAssetQuery, DatasetAssetQuery, graphene.ObjectType):
    pass


class TestMutation(ImageAssetMutation, graphene.ObjectType):
    pass


class TestReadImageAsset(GQLTestCase):
    """Ensure reading ImageAsset works"""

    node_name = "ImageAssetNode"

    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def test_read_all_requires_login(self):
        """allImageAssets query without a user is unauthorized"""
        query = """{allImageAssets{ edges{ node{ id }}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    @mock.patch('ery_backend.assets.models.ImageAsset.bucket')
    def test_read_node_requires_login(self, mock_bucket):
        image_asset = ImageAssetFactory()
        td = {"image_asset_id": image_asset.gql_id}

        query = """query ImageAssetQuery($image_asset_id: ID!){imageAsset(id: $image_asset_id){ id }}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    @mock.patch('ery_backend.assets.models.ImageAsset.bucket')
    def test_read_all_filters_by_privilege(self, mock_bucket):
        query = """{allImageAssets{ edges{ node{ id }}}}"""
        image_assets = [ImageAssetFactory() for _ in range(3)]

        for obj in image_assets:
            grant_role(self.viewer["role"], obj, self.viewer["user"])

        for obj in image_assets[1:]:
            grant_role(self.editor["role"], obj, self.editor["user"])

        grant_role(self.owner["role"], image_assets[2], self.owner["user"])
        # No roles
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allImageAssets"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allImageAssets"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allImageAssets"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allImageAssets"]["edges"]), 1)

    @mock.patch('ery_backend.assets.models.ImageAsset.bucket')
    def test_expected_fields(self, mock_bucket):
        """
        Verify fields unique to query.
        """
        query = """{allImageAssets{ edges{ node{ id url }}}}"""
        image_asset = ImageAssetFactory()
        gql_id = image_asset.gql_id

        grant_role(self.viewer["role"], image_asset, self.viewer["user"])

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        # GQL ids are not generated equivalently
        self.assertEqual(f'assets/{gql_id}'[:20], result["data"]["allImageAssets"]["edges"][0]['node']['url'][:20])

    @mock.patch('ery_backend.assets.models.ImageAsset.bucket')
    def test_no_soft_deletes_in_all_query(self, mock_bucket):
        """
        Confirm soft_deleted objects are not returned in query.
        """
        query = """{allImageAssets { edges{ node{ id }}}}"""
        image_asset = ImageAssetFactory()
        grant_role(self.viewer["role"], image_asset, self.viewer["user"])

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(len(result["data"]["allImageAssets"]["edges"]), 1)

        image_asset.soft_delete()
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(len(result["data"]["allImageAssets"]["edges"]), 0)

    @mock.patch('ery_backend.assets.models.ImageAsset.bucket')
    def test_no_soft_deletes_in_single_query(self, mock_bucket):
        """
        Confirms soft_deleted object not returned in query.
        """
        query = """query ImageAssetQuery($imageAssetid: ID!){
            imageAsset(id: $imageAssetid){ id }}
            """
        image_asset = ImageAssetFactory()
        grant_role(self.viewer["role"], image_asset, self.viewer["user"])

        result = self.gql_client.execute(
            query,
            variable_values={"imageAssetid": image_asset.gql_id},
            context_value=self.gql_client.get_context(user=self.viewer["user"]),
        )
        self.fail_on_errors(result)

        image_asset.soft_delete()
        result = self.gql_client.execute(
            query,
            variable_values={"imageAssetid": image_asset.gql_id},
            context_value=self.gql_client.get_context(user=self.viewer["user"]),
        )
        self.assertEqual('ImageAsset matching query does not exist.', result['errors'][0]['message'])


class TestDeleteImageAsset(GQLTestCase):
    node_name = "ImageAssetNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @mock.patch('ery_backend.assets.models.ImageAsset.bucket')
    def setUp(self, mock_bucket):
        self.image_asset = ImageAssetFactory()
        self.td = {"imageAsset": self.image_asset.gql_id}
        self.query = """mutation ($imageAsset: ID!){
             deleteImageAsset(input: {
                id: $imageAsset,
                    })
                   { id }
                   }
                """

    def test_delete_requires_privilege(self):
        grant_role(self.viewer["role"], self.image_asset.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        ImageAsset.objects.get(pk=self.image_asset.id)

    def test_delete_produces_result(self):
        grant_role(self.owner["role"], self.image_asset.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertIsNotNone(result["data"]["deleteImageAsset"]["id"])

        self.image_asset.refresh_from_db()
        self.assertEqual(self.image_asset.state, self.image_asset.STATE_CHOICES.deleted)
