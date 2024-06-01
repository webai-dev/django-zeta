from django.contrib import admin

from reversion.admin import VersionAdmin

from .models import Command, CommandTemplate, CommandTemplateBlock, CommandTemplateBlockTranslation


class CommandTemplateBlockTranslationInline(admin.TabularInline):
    model = CommandTemplateBlockTranslation


class CommandTemplateBlockInline(admin.TabularInline):
    model = CommandTemplateBlock


@admin.register(CommandTemplateBlock)
class CommandTemplateBlockAdmin(VersionAdmin):
    inlines = [
        CommandTemplateBlockTranslationInline,
    ]


@admin.register(CommandTemplate)
class CommandTemplateAdmin(VersionAdmin):
    inlines = [
        CommandTemplateBlockInline,
    ]


@admin.register(Command)
class CommandAdmin(VersionAdmin):
    pass
