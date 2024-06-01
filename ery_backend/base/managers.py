from graphql_relay.node.node import from_global_id

from django.db import models, transaction
from django.db.models import Count

from .exceptions import EryTypeError


class EryQuerySet(models.QuerySet):
    def _filter_privilege(self, privilege_name, user=None, group=None):
        """
        Return a filterset of all objects of model cls accessible under specified privilege.

        Args:
            - privilege_name (str)
            - user (Optional[:class:`~ery_backend.users.models.User`]): Used to filter
              :class:`~ery_backend.roles.models.RoleAssignment` instances.
            - group (Optional[:class:`~ery_backend.users.models.Group`]): Used to filter
              :class:`~ery_backend.roles.models.RoleAssignment` instances.

        Notes:
            - If a user is specified, said privilege may belong to a user or group containing user.
            - If a group is specified, said privilege must belong to the group.

        Raises:
            - :class:`~ery_backend.base.exceptions.EryValidationrError`: Raised on invalid use/combination
              of user and/or group.
        """
        from ery_backend.roles.utils import get_cached_role_ids_by_privilege

        # get ids of associated roles
        role_ids_with_privilege = get_cached_role_ids_by_privilege(privilege_name)

        # use ids to get cls specific objs for user/user groups or group (EryValidationError raised here if necessary.)
        filter_kwargs = {}
        if self.model.parent_field:
            # get linking attribute path between self.model and privilege_ancestor
            ancestor_match_ids = self.model.get_privilege_ancestor_cls().get_ids_by_role_assignment(
                role_ids_with_privilege, user, group
            )
            ancestor_path = self.model.get_privilege_ancestor_filter_path()
            filter_kwargs.update({'{}__id__in'.format(ancestor_path): ancestor_match_ids})
        else:
            obj_match_ids = self.model.get_ids_by_role_assignment(role_ids_with_privilege, user, group)
            filter_kwargs.update({'id__in': obj_match_ids})
        qs = self.filter(**filter_kwargs)
        return qs

    def filter_privilege(self, privilege_name, user=None, group=None, **kwargs):
        """
        Return a :class:`django.db.models.Queryset` of all objects of model cls accessible under specified
        privilege.

        Args:
            - privilege_name (str)
            - user (Optional[:class:`~ery_backend.users.models.User`]): Used to filter
              :class:`~ery_backend.roles.models.RoleAssignment` instances.
            - group (Optional[:class:`~ery_backend.users.models.Group`]): Used to filter
              :class:`~ery_backend.roles.models.RoleAssignment` instances.

        Notes:
            - If a user is specified, said privilege may belong to a user or group containing user.
            - If a group is specified, said privilege must belong to the group.

        Raises:
            - :class:`~ery_backend.base.exceptions.EryValidationrError`: Raised on invalid use/combination
              of user and/or group.
        """
        qs = self._filter_privilege(privilege_name, user, group)
        if kwargs:
            qs = qs.filter(**kwargs)
        return qs

    def filter_owner(self, user=None):
        """
        Returns a list of ids of all objects of model cls accessible only for it's owner.

        Note: EryValidationError is raised on invalid use/combination of user and/or group.
        """
        from ery_backend.roles.models import Role

        owner_role_id = Role.objects.values_list('id', flat=True).get(name='owner')

        # use ids to get cls specific objs for user/user groups or group (EryValidationError raised here if necessary.)
        obj_match_ids = self.model.get_ids_by_role_assignment([owner_role_id], user, None)
        return self.filter(id__in=obj_match_ids)

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


class EryManager(models.Manager):
    def get_by_gql_id(self, gql_id):
        """Get object based on provided gql_id"""
        (ts, pk) = from_global_id(gql_id)

        if ts != f"{self.model._meta.object_name}Node":
            raise ValueError("Invalid identifier")

        return self.model.objects.get(pk=pk)

    def _filter_privilege(self, privilege_name, context):
        """
        Used when additional query not needed (outside of get_cached_role_ids_by_privilege and
        model.get_ids_by_role_assignment).
        """
        from ery_backend.roles.utils import get_cached_role_ids_by_privilege

        user = context.user

        # get ids of associated roles
        role_ids_with_privilege = get_cached_role_ids_by_privilege(privilege_name)
        # use ids to get cls specific objs for user/user groups or group (EryValidationError raised here if necessary.)
        obj_match_ids = self.model.get_ids_by_role_assignment(role_ids_with_privilege, user, None)

        return obj_match_ids

    def get_queryset(self):
        return EryQuerySet(self.model, using=self._db)

    def filter_privilege(self, privilege_name, user=None, group=None, **kwargs):
        return self.get_queryset().filter_privilege(privilege_name, user, group, **kwargs)

    def filter_owner(self, user=None):
        return self.get_queryset().filter_owner(user)

    @transaction.atomic
    def create_with_owner(self, user, **kwargs):
        from ery_backend.roles.utils import grant_ownership

        obj = self.create(**kwargs)

        if obj.get_privilege_ancestor() != obj:
            raise EryTypeError(
                f"A role can only be granted to privilege ancestor objects. {obj.__class__}"
                f" is a descendant. Its privilege ancestor, {obj.get_privilege_ancestor().__class__}"
                f", must be used instead."
            )
        grant_ownership(obj, user)

        return obj

    def delete_with_owner(self, obj_ids, user):
        from ery_backend.roles.models import Role, RoleAssignment

        owner = Role.objects.get(name='owner')
        role_assignments = RoleAssignment.objects.filter(
            content_type=self.model.get_content_type(), user=user, role=owner, object_id__in=obj_ids
        )
        role_assignments.delete()


class EryFileQuerySet(EryQuerySet):
    def _filter_privilege(self, privilege_name, user=None, group=None):
        """
        Used when additional query not needed (outside of get_cached_role_ids_by_privilege and
        model.get_ids_by_role_assignment).
        """
        from ery_backend.roles.utils import get_cached_role_ids_by_privilege

        # get ids of associated roles
        role_ids_with_privilege = get_cached_role_ids_by_privilege(privilege_name)
        # use ids to get cls specific objs for user/user groups or group (EryValidationError raised here if necessary.)
        obj_match_ids = self.model.get_ids_by_role_assignment(role_ids_with_privilege, user, group)

        if privilege_name == 'read':
            published_ids_q = self.model.objects.filter(published=True).exclude(id__in=obj_match_ids)
            obj_match_ids += published_ids_q.values_list('id', flat=True)

        return self.filter(id__in=obj_match_ids)

    def add_popularity(self):
        """
        Update queryset with number of connected :class:`~ery_backend.comments.models.FileStar` instances.
        """
        return self.annotate(popularity=Count('filestar'))

    def exclude_deleted(self):
        return self.exclude(state=self.model.STATE_CHOICES.deleted)

    def filter_privilege(self, privilege_name, user=None, group=None):
        return super().filter_privilege(privilege_name, user, group).exclude_deleted()

    def filter_owner(self, user=None):
        return super().filter_owner(user).exclude_deleted()


class EryFileManager(EryManager):
    def get_queryset(self):
        return EryFileQuerySet(self.model, using=self._db)

    def add_popularity(self):
        return self.get_queryset().add_popularity()
