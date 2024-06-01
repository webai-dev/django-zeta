from django.contrib import admin

from reversion.admin import VersionAdmin

from .models import Condition


@admin.register(Condition)
class ConditionAdmin(VersionAdmin):
    list_display = ('name', 'module_definition', 'left_type', 'right_type')
