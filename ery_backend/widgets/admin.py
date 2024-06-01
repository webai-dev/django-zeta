from django.contrib import admin

from reversion.admin import VersionAdmin

from .models import Widget, WidgetConnection, WidgetEvent, WidgetEventStep, WidgetProp, WidgetState


@admin.register(WidgetConnection)
class WidgetConnectionAdmin(VersionAdmin):
    pass


def event_action_type(obj):
    return obj.event_action_type


def event_type(obj):
    return obj.widget_event.event_type


def event_name(obj):
    return obj.widget_event.name


def widget_name(obj):
    return obj.widget_event.widget.name


@admin.register(WidgetEventStep)
class WidgetEventStepAdmin(VersionAdmin):
    list_display = (event_action_type, event_type, event_name, widget_name)


class WidgetEventStepInline(admin.TabularInline):
    model = WidgetEventStep


@admin.register(WidgetEvent)
class WidgetEventAdmin(VersionAdmin):
    list_display = ('widget', 'event_type', 'name')

    inlines = [WidgetEventStepInline]


class WidgetStateInline(admin.TabularInline):
    model = WidgetState


class WidgetEventInline(admin.TabularInline):
    model = WidgetEvent


class WidgetConnectionInline(admin.TabularInline):
    model = WidgetConnection
    fk_name = 'originator'


class WidgetPropInline(admin.TabularInline):
    model = WidgetProp


@admin.register(Widget)
class WidgetAdmin(VersionAdmin):
    exclude = ('slug',)
    inlines = [WidgetPropInline, WidgetEventInline, WidgetConnectionInline, WidgetStateInline]
