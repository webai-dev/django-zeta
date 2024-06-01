import os
from unittest import mock

from ery_backend.base.testcases import EryTestCase

from ..models import ImageAsset
from ..factories import ImageAssetFactory


DEMO_FILE_NAME = f"{os.getcwd()}/ery_backend/assets/tests/data/iamnotacatidontsaymeow.jpg"


class TestProfileImage(EryTestCase):
    @mock.patch('ery_backend.assets.models.ImageAsset.bucket')
    def setUp(self, mock_bucket):
        self.profile_image = ImageAssetFactory(content_type=ImageAsset.HTTP_CONTENT_TYPES.png)

    def test_exists(self):
        self.assertIsNotNone(self.profile_image)

    def test_expected_attributes(self):
        self.profile_image.refresh_from_db()
        self.assertEqual(self.profile_image.content_type, ImageAsset.HTTP_CONTENT_TYPES.png)

    def test_filename(self):
        self.assertEqual(self.profile_image.filename, f'imageasset/{self.profile_image.pk}.png')

    @mock.patch('ery_backend.assets.models.ImageAsset.bucket')
    def test_create(self, mock_bucket):
        """
        Confirm correct content type is set on instance.
        """
        profile_image = ImageAsset.objects.create_file(file_data=open(DEMO_FILE_NAME, 'rb').read())
        self.assertEqual(profile_image.content_type, ImageAsset.HTTP_CONTENT_TYPES.jpeg)


class TestCoverImage(EryTestCase):
    @mock.patch('ery_backend.assets.models.ImageAsset.bucket')
    def setUp(self, mock_bucket):
        self.cover_image = ImageAssetFactory(content_type=ImageAsset.HTTP_CONTENT_TYPES.png)

    def test_exists(self):
        self.assertIsNotNone(self.cover_image)

    def test_expected_attributes(self):
        self.cover_image.refresh_from_db()
        self.assertEqual(self.cover_image.content_type, ImageAsset.HTTP_CONTENT_TYPES.png)

    def test_filename(self):
        self.assertEqual(self.cover_image.filename, f'imageasset/{self.cover_image.pk}.png')

    @mock.patch('ery_backend.assets.models.ImageAsset.bucket')
    def test_create(self, mock_bucket):
        """
        Confirm correct content type is set on instance.
        """
        cover_image = ImageAsset.objects.create_file(file_data=open(DEMO_FILE_NAME, 'rb').read())
        self.assertEqual(cover_image.content_type, ImageAsset.HTTP_CONTENT_TYPES.jpeg)
