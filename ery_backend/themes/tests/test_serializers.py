from test_plus.test import TestCase

from ery_backend.themes.factories import ThemeFactory, ThemePaletteFactory
from ery_backend.themes.models import Theme, ThemePalette


class TestThemeBXMLSerializer(TestCase):
    def setUp(self):
        self.theme = ThemeFactory()
        self.theme_serializer = Theme.get_bxml_serializer()(self.theme)

    def test_exists(self):
        self.assertIsNotNone(self.theme_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.theme_serializer.data['name'], self.theme.name)
        self.assertEqual(self.theme_serializer.data['comment'], self.theme.comment)
        self.assertEqual(self.theme_serializer.data['published'], self.theme.published)


class TestThemePaletteSerializer(TestCase):
    def setUp(self):
        self.theme_palette = ThemePaletteFactory()
        self.theme_palette_serializer = ThemePalette.get_bxml_serializer()(self.theme_palette)

    def test_exists(self):
        self.assertIsNotNone(self.theme_palette_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.theme_palette_serializer.data['name'], self.theme_palette.name)
        self.assertEqual(self.theme_palette_serializer.data['main'], self.theme_palette.main)
        self.assertEqual(self.theme_palette_serializer.data['light'], self.theme_palette.light)
        self.assertEqual(self.theme_palette_serializer.data['dark'], self.theme_palette.dark)
