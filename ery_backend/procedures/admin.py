from django.contrib import admin

from reversion.admin import VersionAdmin

from .models import Procedure, ProcedureArgument


class ProcedureArgumentInline(admin.TabularInline):
    model = ProcedureArgument


@admin.register(Procedure)
class ProcedureAdmin(VersionAdmin):
    inlines = (ProcedureArgumentInline,)
    exclude = ('slug',)
