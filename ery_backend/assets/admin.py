from django.contrib import admin
from .models import ImageAsset, DatasetAsset

admin.site.register(ImageAsset)
admin.site.register(DatasetAsset)
