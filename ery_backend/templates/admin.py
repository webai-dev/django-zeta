from django.contrib import admin

from reversion.admin import VersionAdmin

from .models import Template, TemplateBlock, TemplateBlockTranslation, TemplateWidget


@admin.register(TemplateWidget)
class TemplateWidgetAdmin(VersionAdmin):
    list_display = ('template', 'widget')


class TemplateBlockTranslationInline(admin.TabularInline):
    model = TemplateBlockTranslation


class TemplateBlockInline(admin.TabularInline):
    model = TemplateBlock


@admin.register(Template)
class TemplateAdmin(VersionAdmin):
    exclude = ('slug',)
    inlines = [TemplateBlockInline]


@admin.register(TemplateBlock)
class TemplateBlockAdmin(VersionAdmin):
    list_display = (
        'name',
        'admin_name',
    )

    inlines = [TemplateBlockTranslationInline]
