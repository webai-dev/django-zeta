from django.urls import path
from django.shortcuts import render

from ery_backend.stints.views import render_stint

from .views import render_vendor_marketplace, render_vendor_manifest


urlpatterns = [
    path('<vendor_gql_id>/', render_vendor_marketplace),
    path('<vendor_gql_id>/manifest.json', render_vendor_manifest),
    path('<vendor_gql_id>/sw.js', lambda request, vendor_gql_id: render(request, 'sw.js', context={"vendor": vendor_gql_id})),
    path('<vendor_gql_id>/stint/<stint_gql_id>', render_stint),
]
