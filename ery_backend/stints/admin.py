from django.contrib import admin

from reversion.admin import VersionAdmin

from ery_backend.hands.models import Hand
from ery_backend.teams.models import Team
from .models import StintDefinition, Stint, StintDefinitionModuleDefinition, StintDefinitionVariableDefinition


class StintTeamInline(admin.TabularInline):
    model = Team


class StintHandInline(admin.TabularInline):
    model = Hand


class StintDefinitionModuleDefinitionInline(admin.TabularInline):
    model = StintDefinitionModuleDefinition


class StintDefinitionVariableDefinitionInline(admin.TabularInline):
    model = StintDefinitionVariableDefinition


@admin.register(Stint)
class StintAdmin(VersionAdmin):
    inlines = [StintTeamInline, StintHandInline]


@admin.register(StintDefinition)
class StintDefinitionAdmin(VersionAdmin):
    model = StintDefinition
    exclude = ('slug',)
    inlines = [
        StintDefinitionModuleDefinitionInline,
        StintDefinitionVariableDefinitionInline,
    ]
