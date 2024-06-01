from django.contrib import admin

from reversion.admin import VersionAdmin

from .models import (
    StintSpecification,
    StintSpecificationVariable,
    StintSpecificationCountry,
    StintSpecificationAllowedLanguageFrontend,
)


class StintSpecificationVariableInline(admin.TabularInline):
    model = StintSpecificationVariable


class StintSpecificationCountryInline(admin.TabularInline):
    model = StintSpecificationCountry


@admin.register(StintSpecificationAllowedLanguageFrontend)
class AllowedLanguageFrontendAdmin(VersionAdmin):
    model = StintSpecificationAllowedLanguageFrontend
    list_display = ('language', 'frontend')


@admin.register(StintSpecification)
class StintSpecificationAdmin(VersionAdmin):
    exclude = ('slug',)
    list_display = ('name', 'stint_definition')
    inlines = [
        StintSpecificationVariableInline,
        StintSpecificationCountryInline,
    ]
