import random
import string
import unittest
from math import pi

from django.core.cache import cache

from ery_backend.base.testcases import EryTestCase, create_test_hands
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.modules.models import ModuleDefinition
from ery_backend.roles.models import Privilege, Role, RoleParent
from ery_backend.roles.utils import grant_role, revoke_role, has_privilege
from ery_backend.users.factories import UserFactory
from ery_backend.variables.factories import VariableDefinitionFactory, HandVariableFactory
from ..cache import get_func_cache_key, get_func_cache_key_for_hand, invalidate_tag, set_tagged, ery_cache


class TestCaching(EryTestCase):
    def setUp(self):
        # self.module_content_type = self.module.get_content_type()
        pass

    def test_get_func_cache_key(self):
        privilege = Privilege.objects.create(name='elevate')
        module = ModuleDefinitionFactory()
        user = UserFactory()
        func_args = [module, user, privilege.name]
        result = get_func_cache_key(has_privilege, *func_args)
        self.assertEqual(result, f"FCK:has_privilege:{module.get_cache_key()}," f"{user.get_cache_key()},'elevate':")

    @unittest.skip
    def test_get_func_cache_key_for_hand(self):
        """
        Confirm cache key is created which includes a hand's stint's context and module_definition version.
        """
        hand = create_test_hands(n=1, signal_pubsub=False).first()
        md = hand.current_module.stint_definition_module_definition.module_definition
        vd = VariableDefinitionFactory(module_definition=md, name='myvariable')
        HandVariableFactory(hand=hand, variable_definition=vd)
        value = 'myvariable * 32'
        expected_result = f'func:{value}:{hand.stint.get_context(hand)}:{md.version}'
        result = get_func_cache_key_for_hand(value, hand)
        self.assertEqual(result, expected_result)

    def test_cache_returns(self):
        cache.set('ery', 'body')
        self.assertEqual(cache.get('ery'), 'body')
        cache.delete('ery')  # cache persists across tests otherwise

    def test_monkey_patch_cache_set(self):
        tags_map = {'tags_1': set(), 'tags_2': set(['key5'])}
        # does set_tagged correctly update cache? What about set for 1 tag?
        set_tagged('key1', 'value1', tags_map.keys())
        self.assertEqual(cache.get('tags_1'), set(['key1']))
        self.assertEqual(cache.get('key1'), 'value1')
        # does latter question above work consistently?
        set_tagged('key2', 'value2', tags_map.keys())
        self.assertEqual(cache.get('tags_1'), set(['key1', 'key2']))
        # does latter question hold for multiple tags?
        cache.set('tags_2', tags_map['tags_2'])
        set_tagged('key3', 'value3', tags_map.keys())
        self.assertEqual(cache.get('tags_1'), set(['key1', 'key2', 'key3']))
        self.assertEqual(cache.get('tags_2'), set(['key3', 'key5']))
        cache.delete('key1')
        cache.delete('value1')
        cache.delete('key2')
        cache.delete('value2')
        cache.delete('tags_2')
        cache.delete('keys3')
        cache.delete('value3')

    def test_invalidate_tag(self):
        tags_map = {'inval_tag_1': set(['inval_key1']), 'inval_tag_2': set(['inval_key1', 'inval_key2'])}
        cache.set('inval_key1', 'value1')
        cache.set('inval_key2', 'value2')
        cache.set('inval_tag_1', tags_map['inval_tag_1'])
        cache.set('inval_tag_2', tags_map['inval_tag_2'])

        # confirm elements in cache with correct values
        self.assertEqual(cache.get('inval_key1'), 'value1')
        self.assertEqual(cache.get('inval_key2'), 'value2')
        self.assertEqual(cache.get('inval_tag_1'), tags_map['inval_tag_1'])
        self.assertEqual(cache.get('inval_tag_2'), tags_map['inval_tag_2'])
        invalidate_tag('inval_tag_1')

        # confirm proper elements are removed
        self.assertIsNone(cache.get('inval_key1'))
        self.assertIsNone(cache.get('inval_tag_1'))
        self.assertEqual(cache.get('inval_key2'), 'value2')
        self.assertEqual(cache.get('inval_tag_2'), tags_map['inval_tag_2'])
        invalidate_tag('inval_tag_2')

    @unittest.skip('Address in issue #710')
    def test_invalidate_cache_on_grantrole(self):
        privilege = Privilege.objects.create(name='elevatehigher')
        user = UserFactory()
        module = ModuleDefinitionFactory()
        editor = Role.objects.create(name='changeitdude')
        editor.privileges.add(privilege)
        owner = Role.objects.create(name='ownitdude')
        RoleParent.objects.create(role=owner, parent=editor)
        grant_role(owner, module, user)
        ModuleDefinition.objects.filter_privilege(privilege_name='elevatehigher', user=user)
        tag_key = get_func_cache_key(
            ModuleDefinition.get_ids_by_role_assignment, ModuleDefinition, [editor.id, owner.id], user, None
        )
        self.assertIn(tag_key, cache.keys('*'))
        self.assertEqual(list(cache.get(tag_key)), [module.id])
        module_2 = ModuleDefinitionFactory()
        # tag created from filter_privilege should be removed after role is granted
        grant_role(owner, module_2, user=user)
        self.assertNotIn(tag_key, cache.keys('*'))

    @unittest.skip('Address in issue #710')
    def test_invalidate_cache_on_revokerole(self):
        privilege = Privilege.objects.create(name='elevatehigherer')
        module = ModuleDefinitionFactory()
        editor = Role.objects.create(name='changeitdudet')
        editor.privileges.add(privilege)
        owner = Role.objects.create(name='ownitdudet')
        RoleParent.objects.create(role=owner, parent=editor)
        user = UserFactory()
        grant_role(owner, module, user=user)
        ModuleDefinition.objects.filter_privilege(privilege_name='elevatehigherer', user=user)
        tag_key = get_func_cache_key(
            ModuleDefinition.get_ids_by_role_assignment, ModuleDefinition, [editor.id, owner.id], user, None
        )
        self.assertIn(tag_key, cache.keys('*'))
        # tag created from filter_privilege should be removed after role is revoked
        revoke_role(owner, module, user)
        self.assertNotIn(tag_key, cache.keys('*'))

    def test_cache_decorator_stores_function(self):
        """Make sure @ery_cache handles functions correctly."""

        @ery_cache
        def hello(text):
            return "Hello {}!".format(text)

        world = "".join([random.choice(string.ascii_letters) for x in range(5)])

        key = hello.cache_key(world)
        self.assertIs(cache.get(key, None), None)

        hello(world)
        self.assertEqual(cache.get(key, None), f"Hello {world}!")

        hello.invalidate(world)
        self.assertIs(cache.get(key, None), None)

    def test_cache_decorator_stores_methods(self):
        """Make sure @ery_cache handles class methods correctly."""

        class Hello:
            def __init__(self, name):
                self.name = name

            @ery_cache
            def say(self):
                return f"Hello {self.name}!"

        hello_world = Hello("".join([random.choice(string.ascii_letters) for x in range(5)]))

        key = Hello.say.cache_key(hello_world)
        self.assertIs(cache.get(key, None), None)

        hello_world.say()
        self.assertEqual(cache.get(key, None), f"Hello {hello_world.name}!")

        Hello.say.invalidate(hello_world)
        self.assertIs(cache.get(key, None), None)

    def test_cache_decorator_handles_static(self):
        """Make sure @ery_cache handles static class methods correctly."""

        class Calculator:
            def __init__(self):
                pass

            @staticmethod  # Note that @staticmethod is supposed to be outermost in Python
            @ery_cache
            def area(radius):
                return pi * (radius ** 2)

        c = Calculator()
        r = random.randint(2, 20)

        key = Calculator.area.cache_key(r)
        self.assertIs(cache.get(key), None, msg="area cached too soon")

        area = c.area(r)
        self.assertEqual(cache.get(key), area, msg="area not cached correctly")

        Calculator.area.invalidate(r)
        self.assertIs(cache.get(key), None, msg="area was not invalidated")

    def test_cache_decorator_handes_classmethod(self):
        """Make sure @ery_cache handles class methods correctly."""

        class Square:
            corners = 4

            def __init__(self, width):
                self.width = width

            @classmethod  # Note that @classmethod is supposed to be outermost in Python
            @ery_cache
            def reshape(cls, moar):
                return cls.corners + moar

        s = Square(random.randint(2, 20))

        extra_corners = random.randint(2, 6)
        key = Square.reshape.cache_key(Square, extra_corners)
        self.assertIs(cache.get(key), None, msg="reshape cached too soon")

        total_corners = s.reshape(extra_corners)
        self.assertEqual(cache.get(key), total_corners, msg="reshape not cached correctly")

        Square.reshape.invalidate(Square, extra_corners)
        self.assertIs(cache.get(key), None, msg="reshape was not invalidated")

    def test_cache_decorator_works_with_ery_keys(self):
        owner = Role.objects.create(name='ownit')
        user = UserFactory()

        class Hello:
            def __init__(self):
                pass

            @staticmethod
            @ery_cache
            def say(user, nope=None):
                return f"Hello {user.username}"

        tag = owner.get_cache_tag()
        invalidate_tag(tag)  # clear previous
        hello = Hello()
        hello_say_key = Hello.say.cache_key(user, nope=owner)

        result = hello.say(user, nope=owner)

        self.assertEqual(cache.get(tag), set([hello_say_key]), msg="arguments with .get_cache_key() didn't link key to tag")

        self.assertEqual(cache.get(hello_say_key), result, msg="failed to cache hello.say(..)")
        invalidate_tag(tag)
        self.assertEqual(cache.get(tag), None, msg="failed to invalidate by tag")
