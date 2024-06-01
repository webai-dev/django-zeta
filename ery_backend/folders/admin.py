from django.contrib import admin
from reversion.admin import VersionAdmin
from .models import Folder, Link


class LinkInline(admin.TabularInline):
    model = Link
    fk_name = 'folder'


@admin.register(Link)
class LinkAdmin(VersionAdmin):
    pass


@admin.register(Folder)
class FolderAdmin(VersionAdmin):
    inlines = [LinkInline]
