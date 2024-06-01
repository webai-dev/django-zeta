from django.contrib import admin

from reversion.admin import VersionAdmin

from ery_backend.variables.models import HandVariable
from .models import Hand


class HandVariableInline(admin.TabularInline):
    model = HandVariable


@admin.register(Hand)
class HandAdmin(VersionAdmin):
    inlines = [HandVariableInline]
