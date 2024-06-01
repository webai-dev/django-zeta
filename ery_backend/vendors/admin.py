from django.contrib import admin

from reversion.admin import VersionAdmin

from .models import Vendor


@admin.register(Vendor)
class VendorAdmin(VersionAdmin):
    pass
