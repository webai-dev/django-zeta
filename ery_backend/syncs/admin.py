from django.contrib import admin

from reversion.admin import VersionAdmin

from .models import Era


@admin.register(Era)
class EraAdmin(VersionAdmin):
    pass
