from django.contrib import admin

from reversion.admin import VersionAdmin

from .models import (
    VariableDefinition,
    VariableChoiceItem,
    ModuleVariable,
    HandVariable,
    TeamVariable,
    VariableChoiceItemTranslation,
)


class VariableChoiceItemTranslationInline(admin.TabularInline):
    model = VariableChoiceItemTranslation


class VariableChoiceItemInline(admin.TabularInline):
    model = VariableChoiceItem


class VariableChoiceItemAdmin(VersionAdmin):
    inlines = [VariableChoiceItemTranslationInline]


@admin.register(VariableDefinition)
class VariableDefinitionAdmin(VersionAdmin):
    exclude = ('slug',)
    list_display = ('name', 'module_definition', 'scope', 'default_value')
    inlines = [VariableChoiceItemInline]


@admin.register(ModuleVariable)
class ModuleVariableAdmin(VersionAdmin):
    model = ModuleVariable


@admin.register(TeamVariable)
class TeamVariableAdmin(VersionAdmin):
    model = TeamVariable


@admin.register(HandVariable)
class HandVariableAdmin(VersionAdmin):
    model = HandVariable
