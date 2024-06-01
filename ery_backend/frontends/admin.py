from django.contrib import admin

from reversion.admin import VersionAdmin

from .models import Frontend


@admin.register(Frontend)
class FrontendAdmin(VersionAdmin):
    exclude = ('slug',)
