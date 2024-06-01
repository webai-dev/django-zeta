from django.urls import path
from .views import download_image_asset

urlpatterns = [
    path('<gql_id>', download_image_asset),
]
