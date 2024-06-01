from ery_backend.actions.factories import ActionFactory
from ery_backend.base.testcases import EryTestCase
from ery_backend.modules.factories import ModuleDefinitionFactory

from ..factories import EraFactory


class TestEra(EryTestCase):
    def setUp(self):
        self.module_definition = ModuleDefinitionFactory()
        self.action = ActionFactory(module_definition=self.module_definition)
        self.message = 'A new era is dawning'
        self.era = EraFactory(
            action=self.action, module_definition=self.module_definition, name='test-era', comment=self.message, is_team=True
        )

    def test_exists(self):
        self.assertIsNotNone(self.era)

    def test_expected_attributes(self):
        self.assertEqual(self.era.name, 'test-era')
        self.assertEqual(self.era.comment, self.message)
        self.assertEqual(self.era.module_definition, self.module_definition)
        self.assertEqual(self.era.action, self.action)
        self.assertTrue(self.era.is_team)
        self.assertIsNotNone(self.era.slug)

    def test_get_privilege_ancestor(self):
        self.assertEqual(self.era.get_privilege_ancestor(), self.era.module_definition)

    def test_get_privilege_ancestor_cls(self):
        self.assertEqual(self.era.get_privilege_ancestor_cls(), self.era.module_definition.__class__)

    def test_get_privilege_ancestor_filter_path(self):
        self.assertEqual(self.era.get_privilege_ancestor_filter_path(), 'module_definition')

    def test_duplicate(self):
        era_2 = self.era.duplicate()
        self.assertIsNotNone(era_2)
        self.assertEqual('{}_copy'.format(self.era.name), era_2.name)
        self.assertNotEqual(self.era, era_2)
        # Siblings should be equivalent
        self.assertEqual(self.era.action, era_2.action)
        # Parents should be equivalent
        self.assertEqual(self.era.module_definition, era_2.module_definition)
