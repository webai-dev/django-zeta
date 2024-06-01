from django.contrib import admin
from reversion.admin import VersionAdmin

from .models import Keyword


@admin.register(Keyword)
class KeywordAdmin(VersionAdmin):
    pass
