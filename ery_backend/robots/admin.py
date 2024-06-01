from django.contrib import admin

from reversion.admin import VersionAdmin

from .models import Robot, RobotRule


@admin.register(Robot)
class RobotAdmin(VersionAdmin):
    pass


@admin.register(RobotRule)
class RobotRuleAdmin(VersionAdmin):
    pass
