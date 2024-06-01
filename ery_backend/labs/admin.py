from django.contrib import admin

from reversion.admin import VersionAdmin

from .models import Lab


@admin.register(Lab)
class LabAdmin(VersionAdmin):
    exclude = ('slug',)
