from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = 'ery_backend.users'
    verbose_name = "Users"

    def ready(self):
        pass
