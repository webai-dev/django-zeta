from django.contrib import admin

from reversion.admin import VersionAdmin

from .models import NewsItem


@admin.register(NewsItem)
class NewsItemAdmin(VersionAdmin):
    pass
