import json
import unittest

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist

from ery_backend.base.cache import cache, get_func_cache_key, invalidate_tag
from ery_backend.base.exceptions import EryTypeError
from ery_backend.base.testcases import EryTestCase
from ery_backend.users.factories import UserFactory, GroupFactory
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.stages.factories import StageDefinitionFactory
from ery_backend.users.models import User
from ..factories import PrivilegeFactory, RoleFactory
from ..models import RoleAssignment, Role, Privilege, RoleParent
from ..utils import has_privilege, grant_role, revoke_role, get_cached_role_ids_by_privilege


class TestPrivileges(EryTestCase):
    """
    Confirm :class:`~ery_backend.roles.models.Privilege` related utility functions work as expected.
    """

    def setUp(self):
        self.user = UserFactory()
        self.group = GroupFactory()
        self.privilege = PrivilegeFactory()
        self.role = RoleFactory()
        self.role.privileges.add(self.privilege)
        self.module_definition = ModuleDefinitionFactory()

    def test_grant_role(self):
        """
        Confirm roles are granted as expected.
        """

        # for object query without reverse relationship
        # based on user
        obj_content_type = ContentType.objects.get_for_model(self.module_definition)
        self.assertFalse(
            RoleAssignment.objects.filter(
                object_id=self.module_definition.id, content_type__pk=obj_content_type.pk, role=self.role, user=self.user
            ).exists()
        )
        # granter confirms reversion.set_user works
        actual_role_assignment = grant_role(self.role, self.module_definition, self.user, granter=self.user)
        expected_role_assignment = RoleAssignment.objects.filter(
            object_id=self.module_definition.id, content_type__pk=obj_content_type.pk, role=self.role, user=self.user
        ).first()
        self.assertIsNotNone(expected_role_assignment)
        self.assertEqual(actual_role_assignment, expected_role_assignment)
        grant_role(self.role, self.module_definition, self.user)  # Confirm no duplicate role exists
        self.assertEqual(
            RoleAssignment.objects.filter(
                object_id=self.module_definition.id, content_type__pk=obj_content_type.pk, role=self.role, user=self.user
            ).count(),
            1,
        )

        # based on group
        obj_content_type = ContentType.objects.get_for_model(self.privilege)
        self.assertFalse(
            RoleAssignment.objects.filter(
                object_id=self.privilege.id, content_type__pk=obj_content_type.pk, role=self.role, group=self.group
            ).exists()
        )
        grant_role(self.role, self.privilege, group=self.group)
        self.assertTrue(
            RoleAssignment.objects.filter(
                object_id=self.privilege.id, content_type__pk=obj_content_type.pk, role=self.role, group=self.group
            ).exists()
        )
        grant_role(self.role, self.privilege, group=self.group)  # Confirm no duplicate
        self.assertEqual(
            RoleAssignment.objects.filter(
                object_id=self.privilege.id, content_type__pk=obj_content_type.pk, role=self.role, group=self.group
            ).count(),
            1,
        )

    def test_expected_grant_errors(self):
        """
        Confirm expected errors during misuse of grant_role.
        """
        # should occur if incorrect object type for role, obj, or user due to coded exception.

        # missing role
        with self.assertRaises(EryTypeError):
            grant_role(None, self.module_definition, user=self.user)
        # missing object
        with self.assertRaises(EryTypeError):
            grant_role(self.role, None, user=self.user)
        # missing user
        with self.assertRaises(EryTypeError):
            grant_role(self.role, self.module_definition, user=None)
        # incorrect user type
        with self.assertRaises(EryTypeError):
            grant_role(self.role, self.module_definition, user=self.group)
        # missing group
        with self.assertRaises(EryTypeError):
            grant_role(self.role, self.module_definition, group=None)
        # incorrect group type
        with self.assertRaises(EryTypeError):
            grant_role(self.role, self.module_definition, group=self.user)
        # user and group passed in
        with self.assertRaises(EryTypeError):
            grant_role(self.role, self.module_definition, user=self.user, granter=self.group)

    def test_revoke_role(self):
        """
        Confirm roles are revoked as expected.
        """
        grant_role(self.role, self.privilege, user=self.user)
        # For object query without reverse relationship
        obj_content_type = ContentType.objects.get_for_model(self.privilege)
        self.assertTrue(
            RoleAssignment.objects.filter(
                object_id=self.privilege.id, content_type__pk=obj_content_type.pk, role=self.role, user=self.user
            ).exists()
        )
        # Granter confirms reversion.set_user works
        revoke_role(self.role, self.privilege, user=self.user, revoker=self.user)
        grant_role(self.role, self.privilege, group=self.group)
        revoke_role(self.role, self.privilege, group=self.group)
        self.assertFalse(
            RoleAssignment.objects.filter(
                object_id=self.privilege.id, content_type__pk=obj_content_type.pk, role=self.role, user=self.user
            ).exists()
        )
        revoke_role(self.role, self.privilege, user=self.user)  # Confirm no errors arise from nonexistent user role
        revoke_role(self.role, self.privilege, group=self.group)  # Confirm no errors arise from nonexistent group role

    def test_expected_revoke_errors(self):
        """
        Confirm expected errors during misuse of revoke_role.
        """

        # missing role
        with self.assertRaises(EryTypeError):
            revoke_role(None, self.privilege, self.user)
        # incorrect role
        with self.assertRaises(EryTypeError):
            revoke_role(self.user, self.privilege, self.role)
        # missing object
        with self.assertRaises(EryTypeError):
            revoke_role(self.role, None, self.user)
        # missing user
        with self.assertRaises(EryTypeError):
            revoke_role(self.role, self.privilege, None)
        # incorrect user
        with self.assertRaises(EryTypeError):
            revoke_role(self.role, self.privilege, self.role)

    def test_has_privilege(self):
        """
        Check that role_assignment exists for user and object such that role_assignment definition includes privilege.
        """
        self.assertFalse(has_privilege(self.privilege, self.user, self.privilege.name))
        grant_role(self.role, self.privilege, user=self.user)
        self.assertTrue(has_privilege(self.privilege, self.user, self.privilege.name))
        revoke_role(self.role, self.privilege, user=self.user)
        self.assertFalse(has_privilege(self.privilege, self.user, self.privilege.name))
        self.user.groups.add(self.group)
        grant_role(self.role, self.privilege, group=self.group)
        # Confirms has_privilege based on group
        self.assertTrue(has_privilege(self.privilege, self.user, self.privilege.name))
        with self.assertRaises(ObjectDoesNotExist):
            has_privilege(self.privilege, self.user, 'fake_privilege')

    def test_complex_has_privilege(self):
        """
        Check role_assignment exists for user and object using object's privilege_ancestor.
        """
        stage_definition = StageDefinitionFactory()
        self.assertFalse(has_privilege(stage_definition, self.user, self.privilege.name))
        grant_role(self.role, stage_definition.module_definition, self.user)
        self.assertTrue(has_privilege(stage_definition, self.user, self.privilege.name))
        revoke_role(self.role, stage_definition.module_definition, self.user)
        self.assertFalse(has_privilege(stage_definition, self.user, self.privilege.name))
        self.user.groups.add(self.group)
        grant_role(self.role, stage_definition.module_definition, group=self.group)
        # Confirms has_privilege based on group
        self.assertTrue(has_privilege(stage_definition, self.user, self.privilege.name))

    def test_expected_has_privilege_errors(self):
        """
        Confirm expected errors during misuse of has_privilege.
        """
        with self.assertRaises(EryTypeError):
            has_privilege(None, self.user, self.privilege.name)
        with self.assertRaises(EryTypeError):
            has_privilege(self.privilege, None, self.privilege.name)
        with self.assertRaises(EryTypeError):
            has_privilege(self.privilege, self.privilege, self.privilege.name)
        with self.assertRaises(EryTypeError):
            has_privilege(self.privilege, self.user, None)
        with self.assertRaises(EryTypeError):
            has_privilege(self.privilege, self.user, self.privilege)

    def test_superuser_always_has_privilege(self):
        superuser = User.objects.create_superuser(username='supa_the_usa', profile=json.dumps({}), password='thatiam')
        superuser.refresh_from_db()
        stage_definition = StageDefinitionFactory()
        self.assertFalse(has_privilege(stage_definition, self.user, self.privilege.name))
        self.assertTrue(has_privilege(stage_definition, superuser, self.privilege.name))


@unittest.skip('Address in issue #710')
class TestCaching(EryTestCase):
    """
    Confirm methods are cached and invalidated (in cache) as expected.
    """

    def test_get_cached_role_ids_by_privilege(self):
        """
        Confirms get_cached_role_ids_by_privilege caches correctly.
        """
        privilege = Privilege.objects.create(name='create_clone_2')
        editor = Role.objects.create(name='editor_clone_2')
        editor.privileges.add(privilege)
        owner = Role.objects.create(name='owner_clone_2')
        RoleParent.objects.create(parent=editor, role=owner)
        # confirm get_cached_role_ids_by_privilege gets expected role_ids
        role_ids = [r.id for r in [editor, owner]]
        function_role_ids = get_cached_role_ids_by_privilege('create_clone_2')
        self.assertIn(editor.get_cache_tag(), cache.keys('*'))  # Confirms tag created for role
        # Tags should not be created for indirect ownership
        self.assertNotIn(owner.get_cache_tag(), cache.keys('*'))
        self.assertEqual(role_ids, function_role_ids)

    def test_get_cached_role_ids_by_privilege_invalidation(self):
        """
        Confirms cache_key for get_cached_role_ids_by_privilege is invalidated if any of its associated
        tags are invalidated.
        """
        privilege = Privilege.objects.create(name='create_clone_3')
        expected_cache_key = get_func_cache_key(get_cached_role_ids_by_privilege, privilege.name)
        editor = Role.objects.create(name='editor_clone_3')
        editor.privileges.add(privilege)

        # creates key in cache
        get_cached_role_ids_by_privilege('create_clone_3')
        self.assertIn(expected_cache_key, cache.keys('*'))

        cache_tag = editor.get_cache_tag()
        # cached key should be deleted if a connected role's tag is invalidated
        invalidate_tag(cache_tag)
        self.assertNotIn(expected_cache_key, cache.keys('*'))

        # If privilege is invalidated, role tag remains in cache, since role is not tagged to privilege
        # recreate cache key
        get_cached_role_ids_by_privilege('create_clone_3')
        self.assertIn(expected_cache_key, cache.keys('*'))
        self.assertIn(cache_tag, cache.keys('*'))
        # should only remove cache key
        invalidate_tag(privilege.get_cache_tag())
        self.assertNotIn(expected_cache_key, cache.keys('*'))
        self.assertIn(cache_tag, cache.keys('*'))

    def test_has_privilege_invalidation(self):
        """
        Confirms cache_key for has_privilege is invalidated if any of its connected tags are
        invalidated.
        """
        user = UserFactory()
        stage_definition = StageDefinitionFactory()
        privilege = Privilege.objects.create(name='create_clone_4')
        owner = Role.objects.create(name='owner_clone_4')
        owner.privileges.add(privilege)
        grant_role(owner, stage_definition.module_definition, user)
        # created cache_key
        self.assertTrue(has_privilege(stage_definition, user, 'create_clone_4'))
        expected_cache_key = get_func_cache_key(has_privilege, stage_definition, user, 'create_clone_4')
        self.assertIn(expected_cache_key, cache.keys('*'))

        # invalidating privilege tag should remove associated cache key
        invalidate_tag(privilege.get_cache_tag())  # tag generated via setup
        self.assertNotIn(expected_cache_key, cache.keys('*'))

        # recreate cache_key
        has_privilege(stage_definition, user, 'create_clone_4')
        self.assertIn(expected_cache_key, cache.keys('*'))
        # invalidating role tag should remove associated cache key
        invalidate_tag(owner.get_cache_tag())
        self.assertNotIn(expected_cache_key, cache.keys('*'))
