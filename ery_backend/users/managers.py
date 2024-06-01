from django.contrib.auth.base_user import BaseUserManager
from django.db import models


class UserQuerySet(models.QuerySet):
    def from_dataloader(self, context):
        """
        Load current queryset into model's :class:`promise.DataLoader`.

        Args:
            - context (:class:`channels.http.AsgiRequest`): Used to acquire DataLoader.

        Returns:
            :class:`promise.Promise`[List[:class:`~ery_backend.base.models.EryModel`]]
        """
        dataloader = context.get_data_loader(self.model)
        return dataloader.load_many(self.values_list('id', flat=True))


class UserManager(BaseUserManager):
    def get_queryset(self):
        return UserQuerySet(self.model, using=self._db)

    def from_dataloader(self, context, ids):
        dataloader = context.get_data_loader(self.model)
        return dataloader.load_many(ids)

    def _create_user(self, username, profile=None, password=None, **extra_fields):
        """
        Create and save a user with the given username, profile, and password.
        """
        from ery_backend.folders.models import Folder
        from ery_backend.roles.utils import grant_ownership

        if not username:
            raise ValueError('The given username must be set')

        folder = Folder.objects.create(name=f'MyFolder_{username}')
        username = self.model.normalize_username(username)
        user = self.model(username=username, profile=profile, my_folder=folder, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        grant_ownership(folder, user)

        return user

    def create_user(self, username, profile=None, password=None, **extra_fields):
        kwargs = {'username': username, 'profile': profile or {}}
        if password is not None:
            kwargs['password'] = password
        return self._create_user(**kwargs)

    # Needed to create admin superuser account from ./manage.py createsuperuser
    def create_superuser(self, username, profile, password, **extra_fields):
        extra_fields = extra_fields or {}
        extra_fields['is_superuser'] = True
        return self._create_user(username, profile, password, **extra_fields)
