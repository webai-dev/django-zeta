from django.urls import path
from .views import (
    ExportModuleDefinitionView,
    ExportLabView,
    ExportStintDefinitionView,
    ExportSimpleStintDefinitionView,
    ExportTemplateView,
    ExportThemeView,
    ExportValidatorView,
    ExportWidgetView,
    ExportProcedureView,
    ExportFrontendView,
)

urlpatterns = [
    path('frontend/<gql_id>', ExportFrontendView.as_view()),
    path('frontend/<gql_id>/slugged', ExportFrontendView.as_view(), kwargs={'slugged': True}),
    path('lab/<gql_id>/slugged', ExportLabView.as_view(), kwargs={'slugged': True}),
    path('widget/<gql_id>', ExportWidgetView.as_view()),
    path('widget/<gql_id>/slugged', ExportWidgetView.as_view(), kwargs={'slugged': True}),
    path('module_definition/<gql_id>', ExportModuleDefinitionView.as_view()),
    path('module_definition/<gql_id>/slugged', ExportModuleDefinitionView.as_view(), kwargs={'slugged': True}),
    path('procedure/<gql_id>', ExportProcedureView.as_view()),
    path('procedure/<gql_id>', ExportProcedureView.as_view(), kwargs={'slugged': True}),
    path('stint_definition/<gql_id>', ExportStintDefinitionView.as_view()),
    path('stint_definition/<gql_id>/slugged', ExportStintDefinitionView.as_view(), kwargs={'slugged': True}),
    path('simple_stint_definition/<gql_id>', ExportSimpleStintDefinitionView.as_view()),
    path('template/<gql_id>', ExportTemplateView.as_view()),
    path('template/<gql_id>/slugged', ExportTemplateView.as_view(), kwargs={'slugged': True}),
    path('theme/<gql_id>', ExportThemeView.as_view()),
    path('theme/<gql_id>/slugged', ExportThemeView.as_view(), kwargs={'slugged': True}),
    path('validator/<gql_id>', ExportValidatorView.as_view()),
    path('validator/<gql_id>/slugged', ExportValidatorView.as_view(), kwargs={'slugged': True}),
]
