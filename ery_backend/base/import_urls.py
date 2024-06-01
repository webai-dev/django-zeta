from django.urls import path

from . import views

urlpatterns = [
    path('dataset_file', views.ImportDatasetFileView.as_view()),
    path('dataset', views.ImportDatasetView.as_view()),
    path('widget_file', views.ImportWidgetFileView.as_view()),
    path('widget', views.ImportWidgetView.as_view()),
    path('procedure_file', views.ImportProcedureFileView.as_view()),
    path('procedure', views.ImportProcedureView.as_view()),
    path('module_definition_file', views.ImportModuleDefinitionFileView.as_view()),
    path('module_definition', views.ImportModuleDefinitionView.as_view()),
    path('stint_definition_file', views.ImportStintDefinitionFileView.as_view()),
    path('stint_definition', views.ImportStintDefinitionView.as_view()),
    path('simple_stint_definition', views.ImportSimpleStintDefinitionView.as_view()),
    path('template_file', views.ImportTemplateFileView.as_view()),
    path('template', views.ImportTemplateView.as_view()),
    path('theme_file', views.ImportThemeFileView.as_view()),
    path('theme', views.ImportThemeView.as_view()),
    path('validator_file', views.ImportValidatorFileView.as_view()),
    path('validator', views.ImportValidatorView.as_view()),
]
