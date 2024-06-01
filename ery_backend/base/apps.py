from django.apps import AppConfig


class BaseConfig(AppConfig):
    name = 'ery_backend.base'
    verbose_name = "Base"

    def ready(self):
        # Side-effect connects signals
        from .signals import post_save, m2m_changed  # pylint: disable=unused-variable, unused-import
