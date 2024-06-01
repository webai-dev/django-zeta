from django.urls import path

from .views import render_as_csv, render_as_gsheet, gsheet_callback

urlpatterns = [
    path('<dataset_id>/csv', render_as_csv),
    path('<dataset_id>/gsheet', render_as_gsheet),
    path('gsheet_callback', gsheet_callback),
]
