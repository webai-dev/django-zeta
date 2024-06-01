from django.contrib import admin

from reversion.admin import VersionAdmin

from .models import StageDefinition, StageTemplate, StageTemplateBlock, StageTemplateBlockTranslation, Redirect


class TemplateInline(admin.TabularInline):
    model = StageDefinition.templates.through


class StageTemplateBlockTranslationInline(admin.TabularInline):
    model = StageTemplateBlockTranslation


class StageTemplateBlockInline(admin.TabularInline):
    model = StageTemplateBlock


@admin.register(StageTemplateBlock)
class StageTemplateBlockAdmin(VersionAdmin):
    list_display = (
        'name',
        'admin_name',
    )
    inlines = [StageTemplateBlockTranslationInline]


class RedirectInline(admin.TabularInline):
    model = Redirect
    fk_name = 'stage_definition'


@admin.register(StageDefinition)
class StageDefinitionAdmin(VersionAdmin):
    inlines = [TemplateInline, RedirectInline]


@admin.register(StageTemplate)
class StageTemplateAdmin(VersionAdmin):
    list_display = ('stage_definition', 'template', 'module_definition')
    inlines = [StageTemplateBlockInline]
