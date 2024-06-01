from ery_backend.base.schema import EryObjectType, PrivilegedNodeMixin, VersionMixin
from ery_backend.folders.schema import FileNodeMixin

from .models import Theme, ThemePalette, ThemeTypography


class ThemeNode(FileNodeMixin, VersionMixin, EryObjectType):
    class Meta:
        model = Theme


ThemeQuery = ThemeNode.get_query_class()


class ThemePaletteNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = ThemePalette


ThemePaletteQuery = ThemePaletteNode.get_query_class()


class ThemeTypographyNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = ThemeTypography


ThemeTypographyQuery = ThemeTypographyNode.get_query_class()
