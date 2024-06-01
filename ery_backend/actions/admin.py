from django.contrib import admin

from reversion.admin import VersionAdmin

from .models import Action, ActionStep


class ActionStepInline(admin.TabularInline):
    model = ActionStep
    fk_name = 'action'


@admin.register(Action)
class ActionAdmin(VersionAdmin):
    inlines = [ActionStepInline]


@admin.register(ActionStep)
class ActionStepAdmin(VersionAdmin):
    pass
