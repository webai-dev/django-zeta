from django.apps import AppConfig


class RolesConfig(AppConfig):
    name = 'ery_backend.roles'
    verbose_name = "Roles"

    def ready(self):
        """Override this to put in:
            Users system checks
            Users signal registration
        """
