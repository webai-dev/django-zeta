from django.contrib import admin

from reversion.admin import VersionAdmin

from ery_backend.variables.models import TeamVariable
from .models import Team, TeamNetworkDefinition, TeamNetwork


class TeamVariableInline(admin.TabularInline):
    model = TeamVariable


class TeamHandInline(admin.TabularInline):
    model = Team.hands.through


@admin.register(Team)
class TeamAdmin(VersionAdmin):
    inlines = [TeamHandInline, TeamVariableInline]


@admin.register(TeamNetworkDefinition)
class TeamNetworkDefinitionAdmin(VersionAdmin):
    pass


@admin.register(TeamNetwork)
class TeamNetworkAdmin(VersionAdmin):
    pass
