from django.contrib import admin

from reversion.admin import VersionAdmin

from .models import Warden


@admin.register(Warden)
class WardenAdmin(VersionAdmin):
    pass
