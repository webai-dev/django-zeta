from django.contrib import admin

from reversion.admin import VersionAdmin

from .models import Validator


@admin.register(Validator)
class ValidatorAdmin(VersionAdmin):
    exclude = ('slug',)
