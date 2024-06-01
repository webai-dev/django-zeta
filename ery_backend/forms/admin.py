from django.contrib import admin

from reversion.admin import VersionAdmin

from .models import Form, FormButton, FormButtonList, FormField, FormItem, FormFieldChoice, FormFieldChoiceTranslation


class FormItemInline(admin.TabularInline):
    model = FormItem


class FormFieldChoiceInline(admin.TabularInline):
    model = FormFieldChoice


class FormFieldChoiceTranslationInline(admin.TabularInline):
    model = FormFieldChoiceTranslation


@admin.register(FormFieldChoice)
class FormFieldChoiceAdmin(VersionAdmin):
    list_display = ('field', 'value', 'order')
    inlines = [FormFieldChoiceTranslationInline]


@admin.register(Form)
class FormAdmin(VersionAdmin):
    exclude = ('slug',)
    inlines = [FormItemInline]


@admin.register(FormField)
class FormFieldAdmin(VersionAdmin):
    inlines = [FormFieldChoiceInline]


class FormButtonInline(admin.TabularInline):
    model = FormButton


@admin.register(FormButtonList)
class FormButtonListAdmin(VersionAdmin):
    inlines = [FormButtonInline]
