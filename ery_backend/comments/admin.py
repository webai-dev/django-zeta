from django.contrib import admin
from reversion.admin import VersionAdmin

from .models import FileComment, FileStar


@admin.register(FileComment)
class FileCommentAdmin(VersionAdmin):
    pass


@admin.register(FileStar)
class FileStarAdmin(VersionAdmin):
    pass
