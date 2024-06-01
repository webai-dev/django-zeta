from django.contrib import admin

from .models import Dataset


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    pass
