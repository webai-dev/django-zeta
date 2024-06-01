import unittest

from django.db.models.signals import m2m_changed, post_save

from factory.django import mute_signals

from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.roles.factories import RoleFactory, PrivilegeFactory
from ery_backend.roles.utils import get_cached_role_ids_by_privilege, grant_role
from ery_backend.stints.factories import StintDefinitionFactory
from ery_backend.stints.models import StintDefinition
from ery_backend.users.factories import UserFactory

from ..cache import cache
from ..testcases import EryTestCase


@unittest.skip('Address in issue #710')
class TestRoleRelatedSignals(EryTestCase):
    def setUp(self):
        self.privilege = PrivilegeFactory()
        self.roles_cache_key = get_cached_role_ids_by_privilege.cache_key(self.privilege.name)
        self.stint = StintDefinitionFactory()
        self.user = UserFactory()
        self.role = RoleFactory()
        self.role_2 = RoleFactory()
        self.privilege.role_set.add(self.role)
        grant_role(self.role, self.stint, self.user)

    def test_minimal_invalidation_on_privilege_add_nosignal(self):
        get_cached_role_ids_by_privilege(self.privilege.name)  # minimally generate cache
        with mute_signals(m2m_changed):
            self.role.privileges.add(self.privilege)
            self.assertIn(self.roles_cache_key, cache.keys('*'))

    def test_minimal_invalidation_on_privilege_add_signal(self):
        get_cached_role_ids_by_privilege(self.privilege.name)  # minimally generate cache
        self.role.privileges.add(self.privilege)
        self.assertNotIn(self.roles_cache_key, cache.keys('*'))

    def test_minimal_invalidation_on_privilege_remove_nosignal(self):
        get_cached_role_ids_by_privilege(self.privilege.name)  # minimally generate cache
        self.assertIn(self.roles_cache_key, cache.keys('*'))
        with mute_signals(m2m_changed):
            self.role.privileges.remove(self.privilege)
            self.assertIn(self.roles_cache_key, cache.keys('*'))

    def test_minimal_invalidation_on_privilege_remove_signal(self):
        get_cached_role_ids_by_privilege(self.privilege.name)  # minimally generate cache
        self.role.privileges.remove(self.privilege)
        self.assertNotIn(self.roles_cache_key, cache.keys('*'))

    def test_filter_privilege_invalidation_on_privilege_remove_nosignal(self):
        with mute_signals(m2m_changed):
            initial = StintDefinition.objects.filter_privilege(self.privilege.name, user=self.user)
            self.role.privileges.remove(self.privilege)
            new = StintDefinition.objects.filter_privilege(self.privilege.name, user=self.user)  # refresh cache
            self.assertEqual(list(initial), list(new))

    def test_filter_privilege_invalidation_on_privilege_remove_signal(self):
        initial = StintDefinition.objects.filter_privilege(self.privilege.name, user=self.user)
        self.role.privileges.remove(self.privilege)
        new = StintDefinition.objects.filter_privilege(self.privilege.name, user=self.user)  # refresh cache
        self.assertNotEqual(list(initial), list(new))


@unittest.skip("Address in issue #538")
class TestCommandGenerationSignals(EryTestCase):
    """
    Confirm default commands auto-assigned on creation of new module definition.
    """

    def test_command_generation_on_signal(self):
        module_definition = ModuleDefinitionFactory()
        self.assertTrue(module_definition.command_set.filter(name='help').exists())
        self.assertTrue(module_definition.command_set.filter(name='back').exists())
        self.assertTrue(module_definition.command_set.filter(name='next').exists())

    def test_command_generation_nosignal(self):
        with mute_signals(post_save):
            module_definition = ModuleDefinitionFactory()
            self.assertEqual(module_definition.command_set.count(), 0)
