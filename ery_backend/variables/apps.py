from django.apps import AppConfig


class VariablesConfig(AppConfig):
    name = 'ery_backend.variables'
    verbose_name = "Variables"

    def ready(self):
        pass
