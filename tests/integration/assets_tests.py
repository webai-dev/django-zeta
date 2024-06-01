import json
import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client as DjangoClient

from graphql_relay.node.node import from_global_id

from ery_backend.assets.factories import ImageAssetFactory
from ery_backend.assets.models import ImageAsset
from ery_backend.base.testcases import EryTestCase, EryLiveServerTestCase
from ery_backend.users.factories import UserFactory


DEMO_IMAGE_NAME = f"{os.getcwd()}/ery_backend/assets/tests/data/iamnotacatidontsaymeow.jpg"


class TestImageAsset(EryTestCase):
    def test_create(self):  # pylint: disable=no-self-use
        """We can create a ImageAsset"""
        with open(DEMO_IMAGE_NAME, "rb") as f:
            ImageAsset.objects.create_file(f.read())

    def test_retrieve(self):
        """ImageAsset data is retrievable"""

        with open(DEMO_IMAGE_NAME, "rb") as f:
            data = f.read()
            asset = ImageAsset.objects.create_file(data)
            self.assertEqual(asset.http_response.content, data)

    def test_delete(self):
        """ImageAsset data can be deleted"""

        with open(DEMO_IMAGE_NAME, "rb") as f:
            asset = ImageAsset.objects.create_file(f.read())

        name = asset.filename
        bucket = asset.bucket
        blob = bucket.get_blob(name)
        self.assertIsNot(blob, None)

        asset_id = asset.id
        asset.delete()
        blob = bucket.get_blob(name)
        self.assertIsNone(blob)
        self.assertFalse(ImageAsset.objects.filter(id=asset_id).exists())


class TestImageActions(EryLiveServerTestCase):
    def setUp(self):
        self.zablano = UserFactory(username='petezablano')
        # zablano must be logged in
        self.client = self.get_loggedin_client(self.zablano)

    def test_download_image_asset(self):
        """
        Confirm image can be succesfully downloaded
        """
        image_content = open(DEMO_IMAGE_NAME, 'rb').read()
        image = ImageAsset.objects.create_file(image_content)
        response = self.client.get(f'/assets/{image.gql_id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(image_content, response.content)


class TestImageAccessFailure(EryLiveServerTestCase):
    def setUp(self):
        self.zablano = UserFactory(username='petezablano')
        self.client = self.get_loggedin_client(self.zablano)

    def test_access_failure(self):
        image_content = open(DEMO_IMAGE_NAME, 'rb').read()
        image = ImageAsset.objects.create_file(image_content)
        image.blob.delete()
        response = self.client.get(f'/asset/{image.gql_id}')
        self.assertEqual(response.status_code, 404)


class TestUploadImageAsset(EryLiveServerTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.file_obj = SimpleUploadedFile(
            name='moooo.jpg', content=open(DEMO_IMAGE_NAME, 'rb').read(), content_type='image/jpeg'
        )
        cls.mutation = """mutation { uploadImageAsset(input: {}){success }}"""

    def test_upload_requires_privilege(self):
        client = DjangoClient()
        mutation_response = client.post(f'{self.live_server_url}/graphql/', {'file': self.file_obj, 'query': self.mutation})
        mutation_content = json.loads(mutation_response.content.decode('utf-8'))
        self.assertEqual(mutation_content['errors'][0]['message'], 'not authorized')

    def test_upload_produces_result(self):
        silvia = UserFactory(username='Silvia4prez')
        silvia.profile_image = ImageAssetFactory()
        silvia.save()
        loggedin_client = self.get_loggedin_client(silvia)

        query = """query ImageQuery{viewer{allImageAssets{ edges{ node{ url }}}}}"""

        mutation_response = loggedin_client.post(
            f'{self.live_server_url}/graphql/', {'file': self.file_obj, 'query': self.mutation}
        )
        mutation_content = json.loads(mutation_response.content.decode('utf-8'))
        self.assertTrue(mutation_content['data']['uploadImageAsset']['success'])
        query_response = loggedin_client.post(f'{self.live_server_url}/graphql/', {'query': query})
        query_content = json.loads(query_response.content.decode('utf-8'))
        self.assertIsNotNone(query_content['data']['viewer']['allImageAssets']['edges'][0]['node']['url'])


class TestDeleteImageAsset(EryLiveServerTestCase):
    def setUp(self):
        self.silvia = UserFactory(username='Silvia4prez')
        self.loggedin_client = self.get_loggedin_client(self.silvia)

        file_obj = SimpleUploadedFile(name='moooo.jpg', content=open(DEMO_IMAGE_NAME, 'rb').read(), content_type='image/jpeg')
        mutation = """mutation { uploadImageAsset(input: {}){
                    success imageAssetEdge{ node { id }}}}"""
        mutation_response = self.loggedin_client.post(
            f'{self.live_server_url}/graphql/', {'file': file_obj, 'query': mutation}
        )
        mutation_content = json.loads(mutation_response.content.decode('utf-8'))
        self.profile_image_gql_id = mutation_content['data']['uploadImageAsset']['imageAssetEdge']['node']['id']

    def test_delete_produces_result(self):
        mutation = f"""mutation DeleteImage{{ deleteImageAsset(input: {{id: "{self.profile_image_gql_id}" }})
                    {{ id }}}}"""

        mutation_response = self.loggedin_client.post(f'{self.live_server_url}/graphql/', {'query': mutation})
        mutation_content = json.loads(mutation_response.content.decode('utf-8'))

        self.assertIsNotNone(mutation_content["data"]["deleteImageAsset"]["id"])

        image_asset = ImageAsset.objects.get(pk=from_global_id(self.profile_image_gql_id)[1])
        self.assertEqual(image_asset.state, image_asset.STATE_CHOICES.deleted)
