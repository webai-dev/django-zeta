from django.contrib import admin

from reversion.admin import VersionAdmin

from .models import Role, RoleAssignment, Privilege


class RoleParentInline(admin.TabularInline):
    model = Role.parents.through
    fk_name = 'role'


@admin.register(Role)
class RoleAdmin(VersionAdmin):
    inlines = [RoleParentInline]


@admin.register(RoleAssignment)
class RoleAssignmentAdmin(VersionAdmin):
    pass


@admin.register(Privilege)
class PrivilegeAdmin(VersionAdmin):
    pass
