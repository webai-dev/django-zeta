from ery_backend.assets.factories import ImageAssetFactory
from ery_backend.base.testcases import EryTestCase
from ..models import User
from ..factories import UserFactory, GroupFactory


class TestUser(EryTestCase):
    def setUp(self):
        self.profile_image = ImageAssetFactory()
        self.user = UserFactory(username='test-user', profile={}, profile_image=self.profile_image)

    def test_exists(self):
        self.assertIsNotNone(self.user)

    def test_expected_attributes(self):
        self.assertEqual(self.user.username, 'test-user')
        self.assertEqual(self.user.profile, {})
        self.assertEqual(self.user.profile_image, self.profile_image)
        # should be autocreated
        self.assertEqual(self.user.my_folder.name, f"MyFolder_{self.user.username}")

    def test_special_creation(self):
        user = User.objects.create_user(username='TestSpecialUser', profile={}, password='llamaswhatelsewouldyoueverlove')
        self.assertEqual(user.my_folder.name, f"MyFolder_{user.username}")


class TestGroup(EryTestCase):
    def setUp(self):
        self.group = GroupFactory(name='test-group')

    def test_exists(self):
        self.assertIsNotNone(self.group)

    def test_expected_attributes(self):
        self.assertEqual(self.group.name, 'test-group')


class TestFileTouch(EryTestCase):
    pass
