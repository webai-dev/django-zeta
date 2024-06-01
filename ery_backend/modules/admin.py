from django.contrib import admin

from reversion.admin import VersionAdmin

from ery_backend.variables.models import ModuleVariable

from .models import (
    WidgetChoice,
    WidgetChoiceTranslation,
    ModuleEvent,
    ModuleDefinitionWidget,
    ModuleDefinitionProcedure,
    ModuleDefinition,
    Module,
    ModuleEventStep,
)


class ModuleEventStepInline(admin.TabularInline):
    model = ModuleEventStep


@admin.register(ModuleEventStep)
class ModuleEventStepAdmin(VersionAdmin):
    list_display = ('event_name', 'event_type', 'widget_name', 'event_id')

    @staticmethod
    def event_name(obj):
        return obj.module_event.name

    @staticmethod
    def event_type(obj):
        return obj.module_event.event_type

    @staticmethod
    def widget_name(obj):
        return obj.module_event.widget.name

    @staticmethod
    def event_id(obj):
        return obj.module_event.id


class WidgetChoiceTranslationInline(admin.TabularInline):
    model = WidgetChoiceTranslation


class WidgetChoiceInline(admin.TabularInline):
    model = WidgetChoice


class EventInline(admin.TabularInline):
    model = ModuleEvent


@admin.register(WidgetChoice)
class WidgetChoiceAdmin(VersionAdmin):
    list_display = ('widget', 'value', 'order')
    inlines = [WidgetChoiceTranslationInline]


@admin.register(ModuleEvent)
class EventAdmin(VersionAdmin):
    list_display = ('widget', 'event_type', 'name', 'id')

    inlines = [ModuleEventStepInline]


@admin.register(ModuleDefinitionWidget)
class ModuleDefinitionWidgetAdmin(VersionAdmin):
    list_display = ('name', 'module_definition', 'widget')
    inlines = [EventInline, WidgetChoiceInline]


class ModuleDefinitionProcedureInline(admin.TabularInline):
    model = ModuleDefinitionProcedure


@admin.register(ModuleDefinition)
class ModuleDefinitionAdmin(VersionAdmin):
    exclude = ('slug',)
    inlines = (ModuleDefinitionProcedureInline,)


class ModuleVariableInline(admin.TabularInline):
    model = ModuleVariable


@admin.register(Module)
class ModuleAdmin(VersionAdmin):
    inlines = [ModuleVariableInline]
