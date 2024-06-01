import unittest

from django.core.exceptions import ObjectDoesNotExist, ValidationError

from ery_backend.base.cache import cache
from ery_backend.base.testcases import EryTestCase
from ery_backend.stints.factories import StintDefinitionFactory
from ery_backend.stints.models import StintDefinition
from ery_backend.users.factories import UserFactory, GroupFactory

from ..factories import RoleAssignmentFactory, PrivilegeFactory, RoleFactory, RoleParentFactory
from ..models import RoleAssignment
from ..utils import get_cached_role_ids_by_privilege, grant_role, _get_privilege


class TestRoleAssignment(EryTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.privilege = PrivilegeFactory()
        self.role = RoleFactory(name='creator')

    def test_role_exists(self):
        self.assertIsNotNone(self.role)

    def test_give_role_assignment_to_user(self):
        """
        Ensures user can be assigned to role instance without convenience function.
        Convenience function with custom exception required to prevent duplicate role instance assignment.
        """
        # For object query without reverse relationship
        self.assertFalse(
            RoleAssignment.objects.filter(
                object_id=self.privilege.id,
                content_type__pk=self.privilege.get_content_type().pk,
                role=self.role,
                user=self.user,
            ).exists()
        )
        RoleAssignment.objects.create(obj=self.privilege, role=self.role, user=self.user)
        self.assertTrue(
            RoleAssignment.objects.filter(
                object_id=self.privilege.id,
                content_type__pk=self.privilege.get_content_type().pk,
                role=self.role,
                user=self.user,
            ).exists()
        )


class TestPrivilege(EryTestCase):
    def setUp(self):
        self.comment = 'Our most realistic factory yet'
        self.privilege = PrivilegeFactory(name='create', comment=self.comment)
        self.role = RoleFactory()

    def test_privilege_exists(self):
        self.assertIsNotNone(self.privilege)

    def test_expected_attributes(self):
        self.assertEqual(self.privilege.name, 'create')
        self.assertEqual(self.privilege.comment, self.comment)


@unittest.skip('Address in issue #710')
class TestPrivilegeInvalidation(EryTestCase):
    def setUp(self):
        self.stint = StintDefinitionFactory()
        self.user = UserFactory()
        self.role = RoleFactory()
        self.role_2 = RoleFactory()
        self.privilege = PrivilegeFactory()
        self.privilege.role_set.add(self.role)
        self.get_privilege_key = _get_privilege.cache_key(self.privilege.name)
        self.roles_cache_key = get_cached_role_ids_by_privilege.cache_key(self.privilege.name)
        grant_role(self.role, self.stint, self.user)

    def test_minimal_invalidation_on_privilege_delete(self):
        get_cached_role_ids_by_privilege(self.privilege.name)  # minimally generate cache
        self.assertIn(self.roles_cache_key, cache.keys('*'))
        self.privilege.delete()
        self.assertNotIn(self.roles_cache_key, cache.keys('*'))

    def test_filter_privilege_invalidation_on_privilege_delete(self):
        StintDefinition.objects.filter_privilege(self.privilege.name, user=self.user)
        self.privilege.delete()
        with self.assertRaises(ObjectDoesNotExist):
            StintDefinition.objects.filter_privilege(self.privilege.name, user=self.user)  # confirms no cached result exists

    def test_minimal_invalidation_on_privilege_save_signal(self):
        cache.delete(self.get_privilege_key)  # clear pre-existing
        cache.delete(self.roles_cache_key)
        get_cached_role_ids_by_privilege(self.privilege.name)  # minimally generate cache
        self.privilege.comment = 'Another change is a\'comin'
        self.privilege.save()
        self.assertNotIn(self.roles_cache_key, cache.keys('*'))

    def test_filter_privilege_invalidation_on_role_delete(self):
        initial = StintDefinition.objects.filter_privilege(self.privilege.name, user=self.user)
        self.role.delete()
        new = StintDefinition.objects.filter_privilege(self.privilege.name, user=self.user)  # refresh cache
        self.assertNotEqual(list(initial), list(new))


class TestRole(EryTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.group = GroupFactory()
        self.comment = 'Test role'
        self.role = RoleFactory(name='creator', comment=self.comment)
        self.role_2 = RoleFactory(name='base_creator')
        self.role_3 = RoleFactory(name='basement_creator')
        self.role_4 = RoleFactory(name='sub_basement_creator')
        self.role_5 = RoleFactory(name='black_hole_creator')
        self.privilege = PrivilegeFactory()
        RoleParentFactory(role=self.role, parent=self.role_2)
        self.role_assignment = RoleAssignmentFactory(role=self.role, obj=self.privilege, user=self.user)

    def test_role_exists(self):
        self.assertIsNotNone(self.role)

    def test_role_assignment_exists(self):
        self.assertIsNotNone(self.role_assignment)

    def test_expected_attributes(self):
        self.assertEqual(self.role.name, 'creator')
        self.assertEqual(self.role.comment, self.comment)

    def test_has_privilege(self):
        self.assertNotIn(self.privilege, self.role.privileges.all())
        self.assertFalse(self.role.has_privilege(self.privilege.name))
        self.role.privileges.add(self.privilege)
        self.assertTrue(self.role.has_privilege(self.privilege.name))
        self.assertIn(self.privilege, self.role.privileges.all())

    def test_parent_has_privilege(self):
        self.assertFalse(self.role.has_privilege(self.privilege.name))
        self.assertFalse(self.role_2.has_privilege(self.privilege.name))
        self.role_2.privileges.add(self.privilege)
        self.assertTrue(self.role_2.has_privilege(self.privilege.name))
        self.assertTrue(self.role.has_privilege(self.privilege.name))

    def test_parent_exists(self):
        self.assertIn(self.role_2, self.role.parents.all())

    def test_save_functionality(self):
        # No parent or user
        with self.assertRaises(ValidationError):
            role_assignment = RoleAssignment()
            role_assignment.save()

        # Parent and user
        with self.assertRaises(ValidationError):
            role_assignment = RoleAssignment(user=self.user, group=self.group)
            role_assignment.save()

    def test_get_descendant_ids(self):
        # set up 2nd gen inheritance
        RoleParentFactory(role=self.role, parent=self.role_2)
        RoleParentFactory(role=self.role, parent=self.role_3)
        RoleParentFactory(role=self.role_2, parent=self.role_4)
        RoleParentFactory(role=self.role_3, parent=self.role_5)
        self.assertEqual(self.role_5.get_descendant_ids(), {role.id for role in [self.role, self.role_3]})

    def test_get_inherited_privilege_ids(self):
        # Source one
        RoleParentFactory(role=self.role, parent=self.role_2)
        self.role_2.privileges.add(PrivilegeFactory())
        # Source two
        RoleParentFactory(role=self.role, parent=self.role_3)
        self.role_3.privileges.add(PrivilegeFactory())
        # Recursive check
        RoleParentFactory(role=self.role_2, parent=self.role_4)
        self.role_4.privileges.add(PrivilegeFactory())

        inherited_privilege_ids = self.role._get_inherited_privilege_ids()  # pylint: disable=protected-access
        self.assertIn(self.role_2.privileges.first().id, inherited_privilege_ids)
        self.assertIn(self.role_3.privileges.first().id, inherited_privilege_ids)
        self.assertIn(self.role_4.privileges.first().id, inherited_privilege_ids)

    def test_get_all_privilege_ids(self):
        # Source one
        RoleParentFactory(role=self.role, parent=self.role_2)
        self.role_2.privileges.add(PrivilegeFactory())
        self.role.privileges.add(PrivilegeFactory())

        privilege_ids = self.role.get_all_privilege_ids()
        self.assertIn(self.role.privileges.first().id, privilege_ids)
        self.assertIn(self.role_2.privileges.first().id, privilege_ids)


class TestRoleParent(EryTestCase):
    def setUp(self):
        self.role = RoleFactory()
        self.parent = RoleFactory()
        self.role_parent = RoleParentFactory(role=self.role, parent=self.parent)

    def test_exists(self):
        self.assertIsNotNone(self.role_parent)

    def test_circularity(self):
        # Role == parent
        with self.assertRaises(ValidationError):
            RoleParentFactory(role=self.role, parent=self.role)

        # Parent has parent that leads back to 1st role
        grandparent = RoleFactory()
        RoleParentFactory(role=self.parent, parent=grandparent)
        with self.assertRaises(ValidationError):
            RoleParentFactory(role=grandparent, parent=self.role)

        greatgrand = RoleFactory()
        supagrand = RoleFactory()
        RoleParentFactory(role=grandparent, parent=greatgrand)
        RoleParentFactory(role=greatgrand, parent=supagrand)
        # Supagrand (top ancestor) references parent (1st ancestor)
        with self.assertRaises(ValidationError):
            RoleParentFactory(role=supagrand, parent=self.parent)

        # A separate branch that references original branch after divergence should not trigger error
        othergreatgrand = RoleFactory()
        RoleParentFactory(role=grandparent, parent=othergreatgrand)
        RoleParentFactory(role=othergreatgrand, parent=greatgrand)
        # Reference before divergance should trigger an error
        with self.assertRaises(ValidationError):
            RoleParentFactory(role=othergreatgrand, parent=self.parent)
