from django.contrib import admin

from reversion.admin import VersionAdmin

from .models import Log


@admin.register(Log)
class LogAdmin(VersionAdmin):
    pass
