from django.apps import AppConfig


class StintsConfig(AppConfig):
    name = 'ery_backend.stints'
    verbose_name = "Stints"

    def ready(self):
        pass
