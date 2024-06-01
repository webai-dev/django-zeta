import unittest

from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache

from ery_backend.comments.factories import FileStarFactory
from ery_backend.frontends.factories import FrontendFactory
from ery_backend.templates.factories import TemplateFactory
from ery_backend.templates.models import Template
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.modules.models import ModuleDefinition
from ery_backend.roles.factories import RoleFactory, RoleAssignmentFactory, PrivilegeFactory, RoleParentFactory
from ery_backend.roles.models import RoleAssignment, Role
from ery_backend.roles.utils import grant_role, revoke_role, has_privilege, get_cached_role_ids_by_privilege
from ery_backend.stages.factories import StageDefinitionFactory, StageTemplateFactory, StageTemplateBlockFactory
from ery_backend.stages.models import StageDefinition, StageTemplateBlock
from ery_backend.themes.factories import ThemeFactory
from ery_backend.themes.models import Theme
from ery_backend.users.factories import UserFactory, GroupFactory

from ..cache import get_func_cache_key
from ..exceptions import EryTypeError
from ..testcases import EryTestCase


class TestEryManager(EryTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.group = GroupFactory()
        self.role = RoleFactory()
        self.moduledefinition = ModuleDefinitionFactory(name='ModuleOne')
        self.moduledefinition_2 = ModuleDefinitionFactory(name='ModuleTwo')
        self.privilege = PrivilegeFactory()
        self.role.privileges.add(self.privilege)
        grant_role(self.role, self.moduledefinition, self.user)
        grant_role(self.role, self.moduledefinition, None, self.group)
        self.role_instance = RoleAssignment.objects.filter(
            user=self.user, role=self.role, object_id=self.moduledefinition.id
        ).first()
        self.roles = [self.role]
        self.role_ids = [r.id for r in self.roles]
        self.roles_cache_key = get_func_cache_key(get_cached_role_ids_by_privilege, self.privilege.name)

    def test_filter_privilege(self):
        # one object, assigned directly to privilege held by role assigned to user
        return_query = ModuleDefinition.objects.filter_privilege(privilege_name=self.privilege.name, user=self.user)
        self.assertEqual(return_query.first(), self.moduledefinition)

        # additional objects of different type, assigned directly to privilege held by role assigned to user
        template = TemplateFactory()
        grant_role(self.role, template, self.user)
        self.assertEqual(
            Template.objects.filter_privilege(privilege_name=self.privilege.name, user=self.user).first(), template
        )
        theme = ThemeFactory()
        grant_role(self.role, theme, self.user)
        self.assertEqual(Theme.objects.filter_privilege(privilege_name=self.privilege.name, user=self.user).first(), theme)

        # additional objects of same type, assigned directly to privilege held by role assigned to user
        cache.delete(self.roles_cache_key)
        grant_role(self.role, self.moduledefinition_2, self.user)
        # pylint:disable=consider-using-set-comprehension
        self.assertEqual(
            set(ModuleDefinition.objects.filter_privilege(privilege_name=self.privilege.name, user=self.user).all()),
            set([self.moduledefinition, self.moduledefinition_2]),
        )

        # check another privilege, inherited by a role that is assigned to user
        privilege_2 = PrivilegeFactory()
        role_2 = RoleFactory()
        role_2.privileges.add(privilege_2)
        RoleParentFactory(role=self.role, parent=role_2)

        self.assertEqual(ModuleDefinition.objects.filter_privilege(privilege_2.name, user=self.user).count(), 2)

        # check another privilege, belonging to one of user's groups
        privilege_3 = PrivilegeFactory()
        role_3 = RoleFactory()
        role_3.privileges.add(privilege_3)
        self.user.groups.add(self.group)
        self.assertEqual(ModuleDefinition.objects.filter_privilege(privilege_3.name, user=self.user).count(), 0)
        grant_role(role_3, self.moduledefinition, group=self.group)
        self.assertEqual(ModuleDefinition.objects.filter_privilege(privilege_3.name, group=self.group).count(), 1)
        self.assertEqual(ModuleDefinition.objects.filter_privilege(privilege_3.name, user=self.user).count(), 1)

        # check another privilege, inherited by a role two generations up, assigned to user
        # grant is on role_3. Inherited by role_2. Inherited by role_1.
        user = UserFactory()
        RoleParentFactory(role=role_2, parent=role_3)
        grant_role(self.role, self.moduledefinition, user=user)
        self.assertEqual(ModuleDefinition.objects.filter_privilege(privilege_3.name, user=user).count(), 1)

        # confirm filter_privilege works on a model inheriting up one generation of privilege
        privilege = PrivilegeFactory(name='360throughflaminghoop')
        role = RoleFactory()
        role.privileges.add(privilege)
        module_definition = ModuleDefinitionFactory()
        stage_definition = StageDefinitionFactory(module_definition=module_definition)
        self.assertEqual(StageDefinition.objects.filter_privilege('360throughflaminghoop', user).count(), 0)
        grant_role(role, module_definition, user)
        self.assertEqual(ModuleDefinition.objects.filter_privilege('360throughflaminghoop', user).count(), 1)
        self.assertEqual(StageDefinition.objects.filter_privilege('360throughflaminghoop', user).first(), stage_definition)

        # confirm filter_privilege works on a model inheriting up three generations of privilege
        privilege = PrivilegeFactory(name='paynotaxes')
        role = RoleFactory()
        role.privileges.add(privilege)
        stage_template = StageTemplateFactory(stage_definition=stage_definition)
        stage_template_block = StageTemplateBlockFactory(stage_template=stage_template)
        self.assertEqual(StageTemplateBlock.objects.filter_privilege('paynotaxes', user).count(), 0)
        grant_role(role, module_definition, user)
        self.assertEqual(ModuleDefinition.objects.filter_privilege('paynotaxes', user).count(), 1)
        self.assertEqual(StageTemplateBlock.objects.filter_privilege('paynotaxes', user).first(), stage_template_block)

    @unittest.skip('Address in issue #710')
    def test_get_cached_obj_ids_by_role_ids(self):
        # confirm cached_getObjIds_from_roles gets expected obj_id
        role_instance_ids = self.moduledefinition.get_ids_by_role_assignment(self.role_ids, user=self.user)
        self.assertEqual(list(role_instance_ids), [self.moduledefinition.id])

        # confirm cached_getObjIds_from_roles caches
        RoleAssignmentFactory(role=self.role, obj=self.moduledefinition_2, user=self.user)
        new_role_instance_objs = RoleAssignment.objects.filter(
            role__in=self.role_ids, content_type=self.moduledefinition.get_content_type(), user=self.user
        ).values_list('object_id', flat=True)

        new_role_instance_ids = list(new_role_instance_objs.values_list('object_id', flat=True))
        self.assertNotEqual(
            self.moduledefinition.get_ids_by_role_assignment(self.role_ids, user=self.user), new_role_instance_ids
        )

        revoke_role(self.role, self.moduledefinition_2, self.user)

        # confirm works for group
        obj_content_type = ContentType.objects.get_for_model(self.moduledefinition)
        role_instance_ids = self.moduledefinition.get_ids_by_role_assignment(self.role_ids, group=self.group)
        self.assertEqual(list(role_instance_ids), [self.moduledefinition.id])

        # confirm cached_getObjIds_from_roles caches
        RoleAssignmentFactory(role=self.role, obj=self.moduledefinition_2, group=self.group)
        new_role_instance_objs_2 = RoleAssignment.objects.filter(
            role__in=self.role_ids, content_type=obj_content_type, group=self.group
        ).values_list('object_id', flat=True)

        new_role_instance_ids_2 = list(new_role_instance_objs_2.values_list('object_id', flat=True))
        self.assertNotEqual(
            self.moduledefinition.get_ids_by_role_assignment(self.role_ids, group=self.group), new_role_instance_ids_2
        )

    @unittest.skip('Address in issue #710')
    def test_get_ids_by_role_assignment_invalidation(self):
        # confirm granting/revoking a role removes all results of get_cached_ids_by_roles for user
        ModuleDefinition.get_ids_by_role_assignment([self.role.id], self.user, None)
        cache_key_1 = get_func_cache_key(
            ModuleDefinition.get_ids_by_role_assignment, ModuleDefinition, [self.role.id], self.user, None
        )
        role_2 = RoleFactory()
        ModuleDefinition.get_ids_by_role_assignment([self.role.id, role_2.id], self.user, None)
        # key changes as func arguments change (addition of role_2 in this case)
        cache_key_2 = get_func_cache_key(
            ModuleDefinition.get_ids_by_role_assignment, ModuleDefinition, [self.role.id, role_2.id], self.user, None
        )
        # modifying role on user should not change group keys
        ModuleDefinition.get_ids_by_role_assignment([self.role.id], None, self.group)
        cache_key_3 = get_func_cache_key(
            ModuleDefinition.get_ids_by_role_assignment, ModuleDefinition, [self.role.id], None, self.group
        )
        self.assertIn(cache_key_1, cache.keys('*'))
        self.assertIn(cache_key_2, cache.keys('*'))
        self.assertIn(cache_key_3, cache.keys('*'))

        # granting a new role to user should remove all related keys for user, but not group
        grant_role(RoleFactory(), self.moduledefinition, self.user)
        self.assertNotIn(cache_key_1, cache.keys('*'))
        self.assertNotIn(cache_key_2, cache.keys('*'))
        self.assertIn(cache_key_3, cache.keys('*'))

        # reset keys
        ModuleDefinition.get_ids_by_role_assignment([self.role.id], self.user, None)
        ModuleDefinition.get_ids_by_role_assignment([self.role.id, role_2.id], self.user, None)
        self.assertIn(cache_key_1, cache.keys('*'))
        self.assertIn(cache_key_2, cache.keys('*'))
        self.assertIn(cache_key_3, cache.keys('*'))

        # revoking role should remove keys related to user, but not group
        revoke_role(self.role, self.moduledefinition, self.user)
        self.assertNotIn(cache_key_1, cache.keys('*'))
        self.assertNotIn(cache_key_2, cache.keys('*'))
        self.assertIn(cache_key_3, cache.keys('*'))

        cache.delete(cache_key_1)
        cache.delete(cache_key_2)
        cache.delete(cache_key_3)
        # similar confirmations for group
        self.user.groups.add(self.group)

        # reset keys and prepare for new check
        revoke_role(self.role, self.moduledefinition, None, self.group)
        ModuleDefinition.get_ids_by_role_assignment([self.role.id], self.user, None)
        ModuleDefinition.get_ids_by_role_assignment([self.role.id, role_2.id], self.user, None)
        ModuleDefinition.get_ids_by_role_assignment([self.role.id], None, self.group)

        # dummy check
        self.assertIn(cache_key_1, cache.keys('*'))
        self.assertIn(cache_key_2, cache.keys('*'))
        self.assertIn(cache_key_3, cache.keys('*'))

        # should affect user, since user is part of group
        grant_role(self.role, self.moduledefinition, None, self.group)
        self.assertNotIn(cache_key_1, cache.keys('*'))
        self.assertNotIn(cache_key_2, cache.keys('*'))
        self.assertNotIn(cache_key_3, cache.keys('*'))

        # reset keys
        ModuleDefinition.get_ids_by_role_assignment([self.role.id], self.user, None)
        ModuleDefinition.get_ids_by_role_assignment([self.role.id, role_2.id], self.user, None)
        self.assertIn(cache_key_1, cache.keys('*'))
        self.assertIn(cache_key_2, cache.keys('*'))

        revoke_role(self.role, self.moduledefinition, group=self.group)
        self.assertNotIn(cache_key_1, cache.keys("*"))
        self.assertNotIn(cache_key_2, cache.keys("*"))
        self.assertNotIn(cache_key_3, cache.keys("*"))

    def test_create_with_owner(self):
        """
        Confirm owner role is assigned on create.
        """
        user = UserFactory()
        module_definition = ModuleDefinitionFactory()

        # only assigns to top level hierarchical models
        with self.assertRaises(EryTypeError):
            StageDefinition.objects.create_with_owner(user, module_definition=module_definition, name='TestStage')

        module_definition2 = ModuleDefinition.objects.create_with_owner(
            user,
            name='TestMd',
            primary_frontend=module_definition.primary_frontend,
            default_template=TemplateFactory(),
            default_theme=ThemeFactory(),
        )
        self.assertIsInstance(module_definition, ModuleDefinition)
        self.assertTrue(has_privilege(module_definition2, user, 'create'))
        self.assertTrue(has_privilege(module_definition2, user, 'read'))
        self.assertTrue(has_privilege(module_definition2, user, 'update'))
        self.assertTrue(has_privilege(module_definition2, user, 'delete'))
        self.assertTrue(has_privilege(module_definition2, user, 'grant'))
        self.assertTrue(has_privilege(module_definition2, user, 'revoke'))
        self.assertTrue(has_privilege(module_definition2, user, 'export'))
        self.assertTrue(has_privilege(module_definition2, user, 'start'))
        self.assertTrue(has_privilege(module_definition2, user, 'stop'))
        self.assertTrue(has_privilege(module_definition2, user, 'change'))

    def test_delete_with_owner(self):
        """
        Confirm owner role is removed on create.
        """
        user = UserFactory()
        owner = Role.objects.get(name='owner')

        # preload objects
        module_definition2 = ModuleDefinition.objects.create_with_owner(
            user,
            name='TestMd',
            primary_frontend=FrontendFactory(),
            default_template=TemplateFactory(),
            default_theme=ThemeFactory(),
        )
        module_definition2_id = module_definition2.id
        self.assertTrue(
            RoleAssignment.objects.filter(
                content_type=module_definition2.get_content_type(), user=user, role=owner, object_id=module_definition2_id
            ).exists()
        )

        # delete should leave obj and remove role assignment
        ModuleDefinition.objects.delete_with_owner([module_definition2_id], user)
        self.assertTrue(ModuleDefinition.objects.filter(id=module_definition2_id).exists())
        self.assertFalse(
            RoleAssignment.objects.filter(
                content_type=module_definition2.get_content_type(), user=user, role=owner, object_id=module_definition2_id
            ).exists()
        )


class TestEryFileManager(EryTestCase):
    def setUp(self):
        self.template_1 = TemplateFactory()
        self.user = UserFactory()

    def test_add_popularity(self):
        template_2 = TemplateFactory()
        template_3 = TemplateFactory()

        for _ in range(3):
            FileStarFactory(module_definition=None, template=self.template_1)
        for _ in range(2):
            FileStarFactory(module_definition=None, template=template_3)
        for _ in range(1):
            FileStarFactory(module_definition=None, template=template_2)

        output = Template.objects.add_popularity()
        self.assertEqual(output.get(id=self.template_1.id).popularity, 3)
        self.assertEqual(output.get(id=template_3.id).popularity, 2)
        self.assertEqual(output.get(id=template_2.id).popularity, 1)

    def test_filter_privilege(self):
        """
        Confirm published instances appear for read privilege filter.
        """
        # dummy check
        self.assertFalse(Template.objects.filter_privilege('read', self.user).filter(id=self.template_1.id).exists())
        self.template_1.published = True
        self.template_1.save()
        # should appear when published for read privilege
        self.assertTrue(Template.objects.filter_privilege('read', self.user).filter(id=self.template_1.id).exists())
        # but not for other privileges
        self.assertFalse(Template.objects.filter_privilege('create', self.user).filter(id=self.template_1.id).exists())
