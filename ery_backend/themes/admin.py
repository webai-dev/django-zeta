from django.contrib import admin

from reversion.admin import VersionAdmin

from .models import Theme, ThemePalette, ThemeTypography


class ThemePaletteInline(admin.TabularInline):
    model = ThemePalette


class ThemeTypographyInline(admin.TabularInline):
    model = ThemeTypography


@admin.register(Theme)
class ThemeAdmin(VersionAdmin):
    exclude = ('slug',)
    inlines = [ThemePaletteInline]


@admin.register(ThemePalette)
class ThemePaletteAdmin(VersionAdmin):
    pass


@admin.register(ThemeTypography)
class ThemeTypographyAdmin(VersionAdmin):
    pass
