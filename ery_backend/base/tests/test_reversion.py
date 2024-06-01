import reversion
from reversion.models import Version, Revision

from ery_backend.actions.factories import ActionFactory
from ery_backend.base.testcases import EryTestCase
from ery_backend.roles.factories import PrivilegeFactory, RoleFactory, RoleAssignmentFactory
from ery_backend.users.factories import UserFactory, GroupFactory


class TestSingleReversion(EryTestCase):
    def setUp(self):
        with reversion.create_revision():
            self.user = UserFactory(username='user-54')
            reversion.set_user(self.user)
            reversion.set_comment("Initialize user")

    def test_revert_user_name(self):
        self.assertEqual(self.user.username, 'user-54')
        with reversion.create_revision():
            self.user.username = 'user-55'
            self.user.save()

            reversion.set_user(self.user)
            reversion.set_comment("Changed username")

        self.assertNotEqual(self.user.username, 'user-54')
        # first is most recent revision. Choose one before first to revert back once.
        versions = Version.objects.get_for_object(self.user).all()
        versions[len(versions) - (len(versions) - 1)].revert()
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'user-54')


class TestMultiReversion(EryTestCase):
    """
    TLDR: Versions within a reversion can be accessed and reverted independently of each other or at once.
    """

    def setUp(self):
        self.role = RoleFactory(name='creator')
        self.privilege = PrivilegeFactory(name='create')
        self.privilege_2 = PrivilegeFactory(name='delete')
        self.user = UserFactory()

        with reversion.create_revision():
            self.group = GroupFactory(name='group-54')
            self.role_instance = RoleAssignmentFactory(role=self.role, user=self.user, obj=self.privilege)

            reversion.set_user(self.user)
            reversion.set_comment("Initialize role_instance and user")

        self.assertEqual(self.role_instance.obj, self.privilege)
        self.assertEqual(self.group.name, 'group-54')

        with reversion.create_revision():
            self.role_instance.obj = self.privilege_2
            self.role_instance.save()
            self.group.name = 'group-55'
            self.group.save()

            reversion.set_user(self.user)
            reversion.set_comment("Change privilege object and username")

        self.role_instance.refresh_from_db()
        self.group.refresh_from_db()

    def test_revert_per_object(self):

        self.assertEqual(self.role_instance.obj, self.privilege_2)
        self.assertEqual(self.group.name, 'group-55')

        versions = Version.objects.get_for_object(self.group).all()
        versions[len(versions) - (len(versions) - 1)].revert()

        self.group.refresh_from_db()
        # confirms revision blocks with multiple changes don't all revert
        # by getting version for one of those objects if getting by version
        self.assertNotEqual(self.group.name, 'group-54')
        self.assertNotEqual(self.role_instance.obj, self.privilege)

        versions = Version.objects.get_for_object(self.role_instance)
        versions[len(versions) - (len(versions) - 1)].revert()

        self.role_instance.refresh_from_db()
        self.assertEqual(self.role_instance.obj, self.privilege)

    def test_revert_per_block(self):
        self.assertEqual(self.role_instance.obj, self.privilege_2)
        self.assertEqual(self.group.name, 'group-55')
        revision = Revision.objects.get(comment="Initialize role_instance and user")
        revision.revert()

        self.group.refresh_from_db()
        self.role_instance.refresh_from_db()
        # confirms revision blocks with multiple changes revert at once if getting by revision
        self.assertEqual(self.group.name, 'group-54')
        self.assertEqual(self.role_instance.obj, self.privilege)

    def tearDown(self):
        """
        At the DB flush stage during the execution of functional tests in tests/functional, django fails to recreate
        permissions with a FK constraint error, references a content type that does not exist in the DB. This happens
        because the content type created in this test case is still in the cache, even after truncating the corresponding
        table. This is addressed by manually clearing the cache.

        Diagnosis and solution obtained from https://code.djangoproject.com/ticket/10827
        """
        from django.contrib.contenttypes.models import ContentType

        ContentType.objects.clear_cache()


class TestVersionMixin(EryTestCase):
    """
    VersionMixin should create a 'versions' attribute that correctly retrieves any versions of an object that have been
    produced.
    """

    def test_actions_have_versions(self):
        """Actions have a 'versions' attribute."""
        user = UserFactory()
        action = ActionFactory()
        object_id = action.id
        content_type_id = action.get_content_type().id

        with reversion.create_revision():
            action.comment = "Change 1"
            action.save()
            reversion.set_user(user)

        self.assertEqual(Version.objects.filter(object_id=object_id, content_type_id=content_type_id).count(), 1)

        with reversion.create_revision():
            action.name = "I haz the name"
            action.save()
            reversion.set_user(user)

        self.assertEqual(Version.objects.filter(object_id=object_id, content_type_id=content_type_id).count(), 2)
