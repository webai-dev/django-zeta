from test_plus.test import TestCase

from ery_backend.keywords.factories import KeywordFactory
from ..factories import ThemeFactory, ThemePaletteFactory
from ..models import ThemePalette, Theme


class TestTheme(TestCase):
    def setUp(self):
        self.theme = ThemeFactory(name='test-theme', comment='EryTheme', published=True,)
        self.theme_palette = ThemePaletteFactory(theme=self.theme)

    def test_exists(self):
        self.assertIsNotNone(self.theme)

    def test_expected_attributes(self):
        self.assertEqual(self.theme.name, 'test-theme')
        self.assertEqual(self.theme.comment, 'EryTheme')
        self.assertTrue(self.theme.published)

    def test_duplicate(self):
        preload_keywords = [KeywordFactory() for _ in range(3)]
        for keyword in preload_keywords:
            self.theme.keywords.add(keyword)

        theme_2 = self.theme.duplicate()
        self.assertIsNotNone(theme_2)
        self.assertEqual(theme_2.name, '{}_copy'.format(self.theme.name))
        theme_palette_2 = ThemePalette.objects.filter(theme=theme_2).first()
        self.assertIsNotNone(theme_palette_2)
        self.assertEqual(theme_palette_2.name, self.theme_palette.name)
        # Children should not be equivalent
        self.assertNotEqual(theme_palette_2, self.theme_palette)

        # Expected keywords
        for keyword in preload_keywords:
            self.assertIn(keyword, theme_2.keywords.all())

    def test_import(self):
        xml = open('ery_backend/themes/tests/data/module_definition-theme-1.bxml', 'rb')
        theme = Theme.import_instance_from_xml(xml, name='instance_new')

        self.assertIsNotNone(theme)
        self.assertEqual(theme.name, 'instance_new')


class TestThemePalette(TestCase):
    def setUp(self):
        self.theme = ThemeFactory()
        self.theme_palette = ThemePaletteFactory(theme=self.theme, name='secondary', main='#ff0000', light='#ffeeee')

    def test_exists(self):
        self.assertIsNotNone(self.theme_palette)

    def test_expected_attributes(self):
        self.assertEqual(self.theme_palette.theme, self.theme)
        self.assertEqual(self.theme_palette.name, 'secondary')
        self.assertEqual(self.theme_palette.main, '#ff0000')
        self.assertEqual(self.theme_palette.light, '#ffeeee')

    def test_get_privilege_ancestor(self):
        self.assertEqual(self.theme_palette.get_privilege_ancestor(), self.theme_palette.theme)

    def test_get_privilege_ancestor_cls(self):
        self.assertEqual(self.theme_palette.get_privilege_ancestor_cls(), self.theme_palette.theme.__class__)

    def test_get_privilege_ancestor_filter_path(self):
        self.assertEqual(self.theme_palette.get_privilege_ancestor_filter_path(), 'theme')
